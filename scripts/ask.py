#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add packages and services to path
sys.path.append(str(Path(__file__).parent.parent))

from services.ingest.rss import gather_candidates
from packages.nlp.rank import search_candidates
from packages.llm.text_processor import NewsProcessor

def select_diverse_evidence(ranked_articles, max_sources=5):
    """Select 2-5 diverse sources from ranked articles, prioritizing fresh + different domains"""
    if not ranked_articles:
        return []
    
    selected = []
    used_domains = set()
    
    # First pass: pick the freshest article from each domain
    for article in ranked_articles:
        if len(selected) >= max_sources:
            break
            
        domain = article.domain
        if domain not in used_domains:
            selected.append(article)
            used_domains.add(domain)
    
    # Second pass: if we need more sources and have capacity, add from domains we've used
    if len(selected) < max_sources and len(selected) < len(ranked_articles):
        for article in ranked_articles:
            if len(selected) >= max_sources:
                break
                
            if article not in selected:
                selected.append(article)
    
    # If we have fewer than 2 sources, take what we can get
    if len(selected) < 2:
        selected = ranked_articles[:min(max_sources, len(ranked_articles))]
    
    return selected

async def process_query(query: str, window_hours: int = 72):
    """Process news query using the same flow as the API"""
    
    print(f"Searching for: '{query}'")
    print(f"Time window: {window_hours} hours")
    print("-" * 60)
    
    try:
        # Step 1: Gather candidate articles
        print("Gathering candidate articles from RSS feeds...")
        candidates = gather_candidates(
            query=query,
            window_hours=window_hours,
            max_items=200
        )
        
        if not candidates:
            print("No recent articles found matching your criteria")
            return
        
        print(f"Found {len(candidates)} candidate articles")
        
        # Step 2: Rank and select top articles
        print("Ranking articles by relevance...")
        ranked_articles = search_candidates(
            query=query,
            articles=candidates,
            k=12
        )
        
        if not ranked_articles:
            print("No relevant articles found for your query")
            return
        
        print(f"Ranked to {len(ranked_articles)} top articles")
        
        # Step 3: Select diverse evidence pack
        print("Selecting diverse evidence pack...")
        evidence_articles = select_diverse_evidence(ranked_articles, max_sources=5)
        
        if not evidence_articles:
            print("Unable to create evidence pack from articles")
            return
        
        print(f"Selected {len(evidence_articles)} articles for evidence pack")
        
        # Step 4: Process summary and translation
        print("Processing...")
        news_processor = NewsProcessor()
        result = await news_processor.process_news(evidence_articles)
        
        print("Processing complete")
        print("=" * 60)
        
        # Display results
        print("SUMMARY (Bangla):")
        print("-" * 60)
        print(result["summary_bn"])
        print()
        
        # Display sources
        print("SOURCES:")
        print("-" * 60)
        for i, article in enumerate(evidence_articles, 1):
            published_date = article.published_at or "Unknown date"
            if published_date and published_date != "Unknown date":
                try:
                    dt = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                    published_date = dt.strftime('%Y-%m-%d %H:%M UTC')
                except:
                    pass
            
            print(f"[{i}] {article.source} — {published_date}")
            print(f"    {article.url}")
            print()
        
        # Display flags if present
        flags = []
        if result.get("disagreement"):
            flags.append("Sources disagree on facts")
        # Check for single source at evidence level
        if len(evidence_articles) < 2 or result.get("single_source"):
            flags.append("Limited source diversity (single source)")
        
        if flags:
            print("FLAGS:")
            print("-" * 60)
            for flag in flags:
                print(f"- {flag}")
            print()
        
        # Display "What to watch" if present
        watch_items = result.get("watch", [])
        if watch_items:
            print("WHAT TO WATCH:")
            print("-" * 60)
            for item in watch_items:
                print(f"- {item}")
            print()
        
        print("=" * 60)
        print(f"Processing complete. Used {len(evidence_articles)} sources.")
        
    except Exception as e:
        print(f"Error: {e}")
        return

def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/ask.py \"<your query>\"")
        print("Example: python scripts/ask.py \"সেমিকন্ডাক্টর এক্সপোর্ট কন্ট্রোল\"")
        sys.exit(1)
    
    query = sys.argv[1]
    
    # Run the async function
    asyncio.run(process_query(query))

if __name__ == "__main__":
    main()