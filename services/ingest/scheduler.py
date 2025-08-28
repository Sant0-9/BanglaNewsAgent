import os
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import feedparser
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from packages.db.repo import init_db, upsert_article, upsert_embedding, fetch_recent_candidates
from packages.nlp.embed import embed_store
from packages.util.normalize import truncate_text
import yaml

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "rss_sources.yaml")


def _load_feeds() -> List[Dict[str, Any]]:
    with open(DATA_PATH, "r") as f:
        data = yaml.safe_load(f)
    return data.get("feeds", [])


def _normalize_entry(entry: Dict[str, Any], feed_meta: Dict[str, Any]) -> Dict[str, Any]:
    title = entry.get("title") or entry.get("summary") or "Untitled"
    link = entry.get("link") or entry.get("id") or ""
    summary = truncate_text(entry.get("summary", ""), max_length=500)

    # published
    published = None
    for key in ("published", "updated", "created"):
        if entry.get(key + "_parsed"):
            try:
                published = datetime(*entry[key + "_parsed"][0:6], tzinfo=timezone.utc).isoformat()
                break
            except Exception:
                pass
        if entry.get(key):
            try:
                published = datetime.fromisoformat(str(entry[key]).replace("Z", "+00:00")).isoformat()
                break
            except Exception:
                continue

    source = feed_meta.get("name", "Unknown")
    category = feed_meta.get("category", "general")

    return {
        "title": title.strip()[:512],
        "url": link,
        "source": source,
        "source_category": category,
        "summary": summary,
        "published_at": published,
    }


async def ingest_cycle() -> Tuple[int, int]:
    feeds = _load_feeds()
    to_embed: List[Tuple[str, str]] = []  # (article_id, text)

    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries[:50]:
                article = _normalize_entry(entry, feed)
                article_id = upsert_article(article)
                text_for_store = f"{article['title']} {article['summary'][:400]}".strip()
                if text_for_store:
                    to_embed.append((str(article_id), text_for_store))
        except Exception as e:
            print(f"[ingest] feed error: {feed.get('name')} - {e}")
            continue

    # Deduplicate by article_id, keep the longest text
    dedup: Dict[str, str] = {}
    for aid, text in to_embed:
        if (aid not in dedup) or (len(text) > len(dedup[aid])):
            dedup[aid] = text

    ids = list(dedup.keys())
    texts = [dedup[aid] for aid in ids]

    if texts:
        try:
            vectors = await embed_store(texts)
            for aid, vec in zip(ids, vectors):
                upsert_embedding(uuid.UUID(aid), vec)  # type: ignore[name-defined]
        except Exception as e:
            print(f"[ingest] embedding error: {e}")

    return (len(feeds), len(ids))


_scheduler: AsyncIOScheduler | None = None


async def _scheduled_ingest():
    """Wrapper function to properly handle async ingest_cycle in scheduler"""
    try:
        await ingest_cycle()
    except Exception as e:
        print(f"[ingest] scheduled job error: {e}")

def start_scheduler():
    global _scheduler
    if _scheduler:
        return _scheduler

    init_db()
    _scheduler = AsyncIOScheduler(timezone="UTC")
    interval_min = int(os.getenv("INGEST_INTERVAL_MIN", "5"))
    _scheduler.add_job(_scheduled_ingest, "interval", minutes=interval_min, id="rss_ingest", replace_existing=True)
    _scheduler.start()
    print(f"[ingest] scheduler started interval={interval_min}min")
    return _scheduler
