#!/usr/bin/env python3
"""
Script to migrate existing JSON cache files to PostgreSQL database.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from packages.db.repo import upsert_article, init_db, upsert_embedding
from packages.nlp.embed import embed_text


def load_json_cache(cache_file: str) -> list:
    """Load articles from JSON cache file."""
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {cache_file}: {e}")
        return []


def convert_article_to_db_format(article: dict) -> dict:
    """Convert JSON article format to database format."""
    return {
        "url": article["url"],
        "title": article.get("title", "Untitled"),
        "source": article.get("source", "Unknown"),
        "source_category": article.get("domain", "general"),  # Map domain to source_category
        "summary": article.get("summary", ""),
        "published_at": article.get("published_at")  # Keep as-is, repo will handle parsing
    }


def migrate_json_to_database():
    """Main migration function."""
    print("Starting JSON to database migration...")
    
    # Initialize database
    print("Initializing database...")
    init_db()
    
    # Find all JSON cache files
    data_dir = project_root / "data" / "cache"
    json_files = list(data_dir.glob("*.json"))
    
    if not json_files:
        print("No JSON cache files found in data/cache/")
        return
    
    total_articles = 0
    total_inserted = 0
    total_with_embeddings = 0
    
    for json_file in json_files:
        print(f"Processing {json_file.name}...")
        articles = load_json_cache(str(json_file))
        
        for i, article in enumerate(articles):
            try:
                # Convert to database format
                db_article = convert_article_to_db_format(article)
                
                # Insert article
                article_id = upsert_article(db_article)
                total_inserted += 1
                
                # Generate and store embedding if we have content
                content_for_embedding = ""
                if article.get("title"):
                    content_for_embedding += article["title"]
                if article.get("summary"):
                    content_for_embedding += " " + article["summary"]
                
                if content_for_embedding.strip():
                    try:
                        embedding = embed_text(content_for_embedding.strip())
                        if embedding and len(embedding) == 1536:
                            upsert_embedding(article_id, embedding)
                            total_with_embeddings += 1
                    except Exception as e:
                        print(f"Warning: Failed to generate embedding for article {article.get('url', 'unknown')}: {e}")
                
                if (i + 1) % 100 == 0:
                    print(f"  Processed {i + 1}/{len(articles)} articles from {json_file.name}")
                
            except Exception as e:
                print(f"Error processing article {article.get('url', 'unknown')}: {e}")
                continue
            
            total_articles += 1
        
        print(f"Finished {json_file.name}: {len(articles)} articles")
    
    print(f"\nMigration complete!")
    print(f"Total articles processed: {total_articles}")
    print(f"Total articles inserted/updated: {total_inserted}")
    print(f"Total articles with embeddings: {total_with_embeddings}")


if __name__ == "__main__":
    migrate_json_to_database()