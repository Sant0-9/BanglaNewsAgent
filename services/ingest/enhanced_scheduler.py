import os
import asyncio
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional
import aiohttp
import feedparser
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import yaml

from packages.db.repo import init_db, upsert_article, upsert_embedding, fetch_recent_candidates
from packages.db.feed_health import (
    init_feed_health_db, record_feed_attempt, get_healthy_feeds, 
    disable_unhealthy_feeds, get_feed_timeout
)
from packages.nlp.embed import embed_store
from packages.util.normalize import truncate_text

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "rss_sources.yaml")


def _load_feeds() -> List[Dict[str, Any]]:
    """Load feeds from YAML configuration"""
    with open(DATA_PATH, "r") as f:
        data = yaml.safe_load(f)
    return data.get("feeds", [])


def _normalize_entry(entry: Dict[str, Any], feed_meta: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize RSS entry to article format"""
    title = entry.get("title") or entry.get("summary") or "Untitled"
    link = entry.get("link") or entry.get("id") or ""
    summary = truncate_text(entry.get("summary", ""), max_length=500)

    # Parse published date
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


async def fetch_feed_with_backoff(
    session: aiohttp.ClientSession, 
    feed: Dict[str, Any],
    max_retries: int = 3
) -> Tuple[Optional[feedparser.FeedParserDict], int, Optional[str]]:
    """
    Fetch a single RSS feed with exponential backoff and jitter.
    
    Returns:
        Tuple of (parsed_feed, latency_ms, error_message)
    """
    feed_url = feed["url"]
    feed_name = feed.get("name", "Unknown")
    timeout = get_feed_timeout(feed_url) / 1000.0  # Convert to seconds
    
    for attempt in range(max_retries + 1):
        start_time = time.time()
        error_message = None
        
        try:
            # Calculate backoff delay with jitter
            if attempt > 0:
                base_delay = min(2 ** (attempt - 1), 16)  # Exponential backoff, max 16s
                jitter = random.uniform(0.1, 0.3) * base_delay  # 10-30% jitter
                delay = base_delay + jitter
                
                print(f"[INGEST] Retry {attempt} for {feed_name} after {delay:.1f}s delay")
                await asyncio.sleep(delay)
            
            # Fetch feed with timeout
            async with session.get(
                feed_url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={
                    'User-Agent': 'KhoborAgent/2.0 RSS Reader',
                    'Accept': 'application/rss+xml, application/xml, text/xml'
                }
            ) as response:
                if response.status == 200:
                    content = await response.text()
                    latency_ms = int((time.time() - start_time) * 1000)
                    
                    # Parse RSS content
                    parsed = feedparser.parse(content)
                    if parsed.bozo and parsed.bozo_exception:
                        # RSS parsing had issues but might still be usable
                        print(f"[INGEST] RSS parsing warning for {feed_name}: {parsed.bozo_exception}")
                    
                    return parsed, latency_ms, None
                else:
                    error_message = f"HTTP {response.status}: {response.reason}"
                    
        except asyncio.TimeoutError:
            error_message = f"Timeout after {timeout:.1f}s"
        except aiohttp.ClientError as e:
            error_message = f"Network error: {str(e)}"
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Don't retry on certain errors
        if error_message and any(x in error_message.lower() for x in ['404', '403', '401', 'not found']):
            print(f"[INGEST] Permanent error for {feed_name}: {error_message}")
            break
            
        if attempt < max_retries:
            print(f"[INGEST] Attempt {attempt + 1} failed for {feed_name}: {error_message}")
    
    return None, latency_ms, error_message


async def fetch_single_feed(
    session: aiohttp.ClientSession, 
    feed: Dict[str, Any]
) -> Tuple[List[Tuple[str, str]], int]:
    """
    Fetch and process a single feed.
    
    Returns:
        Tuple of (articles_to_embed, articles_count)
    """
    feed_url = feed["url"]
    feed_name = feed.get("name", "Unknown")
    
    # Fetch with backoff
    parsed, latency_ms, error_message = await fetch_feed_with_backoff(session, feed)
    
    articles_to_embed = []
    articles_count = 0
    
    if parsed is None:
        # Record failed attempt
        record_feed_attempt(feed_url, feed_name, False, latency_ms, error_message, 0)
        print(f"[INGEST] Failed to fetch {feed_name}: {error_message}")
        return articles_to_embed, 0
    
    # Process entries
    try:
        for entry in parsed.entries[:50]:  # Limit to 50 most recent
            try:
                article = _normalize_entry(entry, feed)
                article_id = upsert_article(article)
                
                text_for_store = f"{article['title']} {article['summary'][:400]}".strip()
                if text_for_store:
                    articles_to_embed.append((str(article_id), text_for_store))
                    articles_count += 1
                    
            except Exception as e:
                print(f"[INGEST] Error processing entry from {feed_name}: {e}")
                continue
        
        # Record successful attempt
        record_feed_attempt(feed_url, feed_name, True, latency_ms, None, articles_count)
        print(f"[INGEST] ✓ {feed_name}: {articles_count} articles in {latency_ms}ms")
        
    except Exception as e:
        # Record failed attempt if processing failed
        record_feed_attempt(feed_url, feed_name, False, latency_ms, f"Processing error: {str(e)}", 0)
        print(f"[INGEST] Processing failed for {feed_name}: {e}")
    
    return articles_to_embed, articles_count


async def enhanced_ingest_cycle() -> Tuple[int, int]:
    """
    Enhanced concurrent ingestion with health monitoring and backoff.
    
    Returns:
        Tuple of (feeds_attempted, articles_embedded)
    """
    start_time = time.time()
    
    # Initialize health monitoring if needed
    try:
        init_feed_health_db()
    except Exception as e:
        print(f"[INGEST] Warning: Could not initialize feed health DB: {e}")
    
    # Disable unhealthy feeds automatically
    try:
        disabled_feeds = disable_unhealthy_feeds()
        if disabled_feeds:
            print(f"[INGEST] Auto-disabled {len(disabled_feeds)} unhealthy feeds")
    except Exception as e:
        print(f"[INGEST] Warning: Could not check feed health: {e}")
    
    # Load all feeds and filter by health
    all_feeds = _load_feeds()
    healthy_feed_urls = {f['feed_url'] for f in get_healthy_feeds()} if get_healthy_feeds else set()
    
    # Use healthy feeds if available, otherwise fall back to all feeds
    if healthy_feed_urls:
        feeds_to_process = [f for f in all_feeds if f['url'] in healthy_feed_urls]
        print(f"[INGEST] Processing {len(feeds_to_process)} healthy feeds (skipped {len(all_feeds) - len(feeds_to_process)} unhealthy)")
    else:
        feeds_to_process = all_feeds
        print(f"[INGEST] Processing all {len(feeds_to_process)} feeds (health data unavailable)")
    
    to_embed: List[Tuple[str, str]] = []  # (article_id, text)
    
    # Create session with connection pooling
    connector = aiohttp.TCPConnector(
        limit=20,  # Total connection pool size
        limit_per_host=5,  # Max connections per host
        keepalive_timeout=60,
        enable_cleanup_closed=True
    )
    
    timeout = aiohttp.ClientTimeout(total=30)  # Default timeout, overridden per feed
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers={'User-Agent': 'KhoborAgent/2.0 RSS Reader'}
    ) as session:
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent feed fetches
        
        async def bounded_fetch(feed):
            async with semaphore:
                return await fetch_single_feed(session, feed)
        
        # Execute all feeds concurrently with rate limiting
        tasks = [bounded_fetch(feed) for feed in feeds_to_process]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        total_articles = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                feed_name = feeds_to_process[i].get('name', 'Unknown')
                print(f"[INGEST] Task failed for {feed_name}: {result}")
                continue
            
            articles_to_embed, articles_count = result
            to_embed.extend(articles_to_embed)
            total_articles += articles_count
    
    # Deduplicate by article_id, keep the longest text
    dedup: Dict[str, str] = {}
    for aid, text in to_embed:
        if (aid not in dedup) or (len(text) > len(dedup[aid])):
            dedup[aid] = text

    ids = list(dedup.keys())
    texts = [dedup[aid] for aid in ids]
    
    # Batch embed with error handling
    embedded_count = 0
    if texts:
        try:
            print(f"[INGEST] Embedding {len(texts)} articles...")
            vectors = await embed_store(texts)
            
            for aid, vec in zip(ids, vectors):
                try:
                    upsert_embedding(uuid.UUID(aid), vec)
                    embedded_count += 1
                except Exception as e:
                    print(f"[INGEST] Error storing embedding for {aid}: {e}")
                    
        except Exception as e:
            print(f"[INGEST] Embedding batch failed: {e}")
    
    total_time = time.time() - start_time
    print(f"[INGEST] Cycle complete: {len(feeds_to_process)} feeds, {total_articles} articles, "
          f"{embedded_count} embedded in {total_time:.1f}s")
    
    return len(feeds_to_process), embedded_count


# Scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


async def _scheduled_enhanced_ingest():
    """Wrapper function for scheduled enhanced ingest"""
    try:
        feeds_count, embedded_count = await enhanced_ingest_cycle()
        print(f"[SCHEDULER] Enhanced ingest completed: {feeds_count} feeds, {embedded_count} articles embedded")
    except Exception as e:
        print(f"[SCHEDULER] Enhanced ingest failed: {e}")


def start_enhanced_scheduler():
    """Start the enhanced ingestion scheduler"""
    global _scheduler
    
    if _scheduler is not None:
        print("[SCHEDULER] Enhanced scheduler already running")
        return
    
    _scheduler = AsyncIOScheduler()
    
    # Schedule enhanced ingest every 5 minutes
    _scheduler.add_job(
        _scheduled_enhanced_ingest,
        trigger="interval",
        minutes=5,
        id="enhanced_ingest_cycle",
        replace_existing=True,
        max_instances=1  # Prevent overlapping runs
    )
    
    # Schedule health monitoring cleanup every hour
    _scheduler.add_job(
        disable_unhealthy_feeds,
        trigger="interval",
        hours=1,
        id="feed_health_cleanup",
        replace_existing=True
    )
    
    _scheduler.start()
    print("[SCHEDULER] Enhanced ingestion scheduler started (5min intervals)")


def stop_enhanced_scheduler():
    """Stop the enhanced ingestion scheduler"""
    global _scheduler
    
    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
        print("[SCHEDULER] Enhanced ingestion scheduler stopped")


# Backward compatibility functions
async def ingest_cycle() -> Tuple[int, int]:
    """Legacy function that calls enhanced ingestion"""
    return await enhanced_ingest_cycle()


def start_scheduler():
    """Legacy function that starts enhanced scheduler"""
    start_enhanced_scheduler()