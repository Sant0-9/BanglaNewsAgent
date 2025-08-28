import feedparser
import httpx
import trafilatura
import yaml
import ujson as json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from urllib.parse import urlparse, urlunparse
import sys
import os
import re

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from packages.util.normalize import normalize_text, clean_title, extract_domain, truncate_text, clean_text, fingerprint
from packages.db.repo import upsert_article, fetch_recent_candidates, upsert_embedding, init_db
from packages.nlp.embed import embed_text

class Feed(BaseModel):
    name: str
    url: str
    country: str

class RawItem(BaseModel):
    title: str
    url: str
    summary: str = ""
    published: Optional[str] = None
    
class Article(BaseModel):
    title: str
    url: str
    source: str
    published_at: Optional[str] = None
    summary: str
    domain: str
    fp_title: str

def load_sources() -> List[Feed]:
    """Load RSS feed sources from YAML configuration"""
    sources_file = Path(__file__).parent.parent.parent / "data" / "rss_sources.yaml"
    
    if not sources_file.exists():
        return []
    
    try:
        with open(sources_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            feeds_data = data.get('feeds', [])
            return [Feed(**feed) for feed in feeds_data]
    except (yaml.YAMLError, FileNotFoundError, Exception) as e:
        print(f"Error loading RSS sources: {e}")
        return []

def fetch_feed(url: str) -> List[RawItem]:
    """Fetch and parse RSS feed using feedparser with timeout"""
    try:
        # Use feedparser with timeout (feedparser handles HTTP internally)
        feed = feedparser.parse(url)
        
        if not hasattr(feed, 'entries') or not feed.entries:
            print(f"No entries found in feed: {url}")
            return []
        
        items = []
        items_parsed = 0
        
        for entry in feed.entries:
            try:
                # Extract basic fields
                title = getattr(entry, 'title', '').strip()
                link = getattr(entry, 'link', '').strip()
                summary = getattr(entry, 'summary', '').strip()
                
                if not title or not link:
                    continue
                
                # Parse published date
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        published_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        published = published_dt.isoformat()
                    except (ValueError, TypeError):
                        pass
                elif hasattr(entry, 'published'):
                    published = entry.published
                
                raw_item = RawItem(
                    title=title,
                    url=link,
                    summary=summary,
                    published=published
                )
                items.append(raw_item)
                items_parsed += 1
                
            except Exception as e:
                # Skip individual items that fail to parse
                continue
        
        print(f"Fetched {len(items)} items from {extract_domain(url)} ({items_parsed} parsed)")
        return items
        
    except Exception as e:
        print(f"Error fetching feed {url}: {e}")
        return []

def extract_excerpt(url: str, timeout: int = 3) -> Optional[str]:
    """Extract article content using trafilatura with 3s timeout"""
    try:
        # Use httpx with 3s timeout
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            
            # Extract main content using trafilatura
            content = trafilatura.extract(response.text)
            if content:
                # Truncate to 500 chars to avoid token bloat
                content = truncate_text(content, 500)
            return content
            
    except Exception:
        # Fail silently on any error (network, parsing, etc.)
        return None

def canonicalize_url(url: str) -> str:
    """Canonicalize URL for deduplication (remove fragments, normalize)"""
    try:
        parsed = urlparse(url)
        # Remove fragment and query parameters for basic canonicalization
        canonical = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        return canonical
    except Exception:
        return url.lower()

def normalize_item(raw: RawItem, source_name: str) -> Article:
    """Convert RawItem to normalized Article"""
    # Clean and normalize title
    title = clean_title(raw.title)
    
    # Get domain from URL
    domain = extract_domain(raw.url)
    
    # Parse published date
    published_at = None
    if raw.published:
        try:
            # Try to parse various date formats
            if isinstance(raw.published, str):
                # Handle ISO format with Z suffix
                if raw.published.endswith('Z'):
                    dt = datetime.fromisoformat(raw.published.replace('Z', '+00:00'))
                else:
                    # Try parsing as ISO format
                    try:
                        dt = datetime.fromisoformat(raw.published)
                    except ValueError:
                        # Fallback to feedparser's date parsing
                        import email.utils
                        parsed_time = email.utils.parsedate_to_datetime(raw.published)
                        dt = parsed_time
                
                published_at = dt.isoformat()
        except Exception:
            # If date parsing fails, leave as None
            pass
    
    # Start with RSS summary
    summary = normalize_text(raw.summary) if raw.summary else ""
    
    # If summary is too short, try to extract excerpt
    if len(summary) < 100:
        excerpt = extract_excerpt(raw.url)
        if excerpt:
            summary = normalize_text(excerpt)
    
    # Truncate summary to 500 chars to avoid token bloat
    summary = truncate_text(summary, 500)
    
    # Generate fingerprint for deduplication
    fp_title = fingerprint(title)
    
    return Article(
        title=title,
        url=raw.url,
        source=source_name,
        published_at=published_at,
        summary=summary,
        domain=domain,
        fp_title=fp_title
    )

def gather_candidates(query: str = "", window_hours: int = 72, max_items: int = 200) -> List[Article]:
    """Gather and normalize recent articles from all RSS feeds, storing them in database"""
    
    # Initialize database if needed
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
    
    # Load RSS sources
    feeds = load_sources()
    if not feeds:
        print("No RSS feeds configured")
        return []
    
    print(f"Loaded {len(feeds)} RSS feeds")
    
    # Calculate time window
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    
    all_articles = []
    seen_urls = set()
    seen_fingerprints = set()
    feeds_hit = 0
    items_parsed = 0
    unique_articles = 0
    inserted_to_db = 0
    
    for feed in feeds:
        try:
            # Fetch raw items from feed
            raw_items = fetch_feed(feed.url)
            if raw_items:
                feeds_hit += 1
                items_parsed += len(raw_items)
            
            for raw_item in raw_items:
                try:
                    # Check if item is recent enough
                    if raw_item.published:
                        try:
                            if raw_item.published.endswith('Z'):
                                item_time = datetime.fromisoformat(raw_item.published.replace('Z', '+00:00'))
                            else:
                                item_time = datetime.fromisoformat(raw_item.published)
                                
                            if item_time < cutoff_time:
                                continue
                        except Exception:
                            # If we can't parse the date, include the item
                            pass
                    
                    # Normalize the item
                    article = normalize_item(raw_item, feed.name)
                    
                    # De-duplicate by URL and title fingerprint
                    canonical_url = canonicalize_url(article.url)
                    if canonical_url in seen_urls or article.fp_title in seen_fingerprints:
                        continue
                    
                    seen_urls.add(canonical_url)
                    seen_fingerprints.add(article.fp_title)
                    all_articles.append(article)
                    unique_articles += 1
                    
                    # Store in database
                    try:
                        db_article = {
                            "url": article.url,
                            "title": article.title,
                            "source": article.source,
                            "source_category": article.domain,  # Map domain to source_category
                            "summary": article.summary,
                            "published_at": article.published_at
                        }
                        article_id = upsert_article(db_article)
                        inserted_to_db += 1
                        
                        # Generate embedding for new articles
                        content_for_embedding = ""
                        if article.title:
                            content_for_embedding += article.title
                        if article.summary:
                            content_for_embedding += " " + article.summary
                        
                        if content_for_embedding.strip():
                            try:
                                embedding = embed_text(content_for_embedding.strip())
                                if embedding and len(embedding) == 1536:
                                    upsert_embedding(article_id, embedding)
                            except Exception as e:
                                print(f"Warning: Failed to generate embedding for {article.url}: {e}")
                    
                    except Exception as e:
                        print(f"Warning: Failed to save article to database {article.url}: {e}")
                    
                    # Stop if we've reached max items
                    if len(all_articles) >= max_items:
                        break
                        
                except Exception as e:
                    # Skip individual items that fail to normalize
                    continue
            
            # Stop if we've reached max items
            if len(all_articles) >= max_items:
                break
                
        except Exception as e:
            # Skip feeds that fail entirely but continue with others
            print(f"Error processing feed {feed.name}: {e}")
            continue
    
    # Log ingestion statistics
    print(f"Ingestion stats: {feeds_hit}/{len(feeds)} feeds hit, {items_parsed} items parsed, {unique_articles} unique articles kept, {inserted_to_db} saved to database")
    
    # Sort by published date (most recent first)
    all_articles.sort(key=lambda x: x.published_at or "1970-01-01T00:00:00Z", reverse=True)
    
    # Save to cache as backup (keep for backward compatibility)
    save_to_cache(all_articles[:max_items])
    
    return all_articles[:max_items]

def save_to_cache(articles: List[Article]):
    """Save articles to JSON cache file"""
    try:
        cache_dir = Path(__file__).parent.parent.parent / "data" / "cache"
        cache_dir.mkdir(exist_ok=True, parents=True)
        cache_file = cache_dir / "latest.json"
        
        # Convert to dict for JSON serialization
        articles_data = [article.dict() for article in articles]
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(articles_data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"Error saving to cache: {e}")

def load_from_cache() -> List[Article]:
    """Load articles from database, with fallback to JSON cache file"""
    try:
        # First try to load from database
        try:
            init_db()
            db_articles = fetch_recent_candidates(window_hours=72, limit=800)
            
            if db_articles:
                # Convert database articles to Article objects
                articles = []
                for db_article in db_articles:
                    try:
                        article = Article(
                            title=db_article.title,
                            url=db_article.url,
                            source=db_article.source,
                            published_at=db_article.published_at.isoformat() if db_article.published_at else None,
                            summary=db_article.summary or "",
                            domain=extract_domain(db_article.url),
                            fp_title=fingerprint(db_article.title)
                        )
                        articles.append(article)
                    except Exception as e:
                        print(f"Warning: Failed to convert database article: {e}")
                        continue
                
                print(f"Loaded {len(articles)} articles from database")
                return articles
        
        except Exception as e:
            print(f"Warning: Failed to load from database, falling back to JSON cache: {e}")
    
        # Fallback to JSON cache
        cache_file = Path(__file__).parent.parent.parent / "data" / "cache" / "latest.json"
        
        if not cache_file.exists():
            return []
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
            articles = [Article(**data) for data in articles_data]
            print(f"Loaded {len(articles)} articles from JSON cache")
            return articles
            
    except Exception as e:
        print(f"Error loading from cache: {e}")
        return []