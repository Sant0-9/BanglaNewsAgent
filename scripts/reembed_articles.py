#!/usr/bin/env python3
"""
Re-embed all articles with the current embedding model.
Run this after changing the embedding model or resetting the index.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent))

from packages.config.embedding import config
from packages.db.repo import session_scope, get_recent_articles
from packages.db.models import Article
from packages.nlp.embed import embed_store
from packages.db.repo import upsert_embedding
from sqlalchemy import select, func

async def reembed_all_articles():
    """Re-embed all articles with current model."""
    print(f"[REEMBED] Starting re-embedding with {config.model_name} (dim={config.dimension})")
    
    with session_scope() as session:
        # Count total articles
        total_articles = session.execute(
            select(func.count(Article.id))
        ).scalar() or 0
        
        print(f"[REEMBED] Found {total_articles} articles to process")
        
        if total_articles == 0:
            print("[REEMBED] No articles to process")
            return
        
        # Process articles in batches
        batch_size = 50
        processed = 0
        errors = 0
        
        for offset in range(0, total_articles, batch_size):
            articles = session.execute(
                select(Article)
                .order_by(Article.inserted_at.desc())
                .offset(offset)
                .limit(batch_size)
            ).scalars().all()
            
            if not articles:
                break
            
            try:
                # Prepare texts for embedding
                texts = []
                article_ids = []
                
                for article in articles:
                    # Create combined text for embedding
                    text = f"{article.title or ''}\n{article.summary or ''}".strip()
                    if text:
                        texts.append(text)
                        article_ids.append(article.id)
                
                if not texts:
                    processed += len(articles)
                    continue
                
                # Generate embeddings
                print(f"[REEMBED] Processing batch {offset//batch_size + 1}: {len(texts)} articles")
                embeddings = await embed_store(texts)
                
                # Store embeddings
                for article_id, embedding in zip(article_ids, embeddings):
                    try:
                        upsert_embedding(article_id, embedding)
                        processed += 1
                        
                        if processed % 100 == 0:
                            print(f"[REEMBED] Progress: {processed}/{total_articles} ({processed/total_articles*100:.1f}%)")
                            
                    except Exception as e:
                        print(f"[REEMBED] Error embedding article {article_id}: {e}")
                        errors += 1
                
                # Commit batch
                session.commit()
                
            except Exception as e:
                print(f"[REEMBED] Error processing batch {offset//batch_size + 1}: {e}")
                errors += batch_size
                session.rollback()
        
        print(f"[REEMBED] Completed: {processed} successful, {errors} errors")
        
        # Verify results
        from packages.db.repo import text
        vector_stats = session.execute(text("""
            SELECT 
                model_name, 
                model_dimension, 
                COUNT(*) as count
            FROM article_vectors 
            GROUP BY model_name, model_dimension
            ORDER BY count DESC
        """)).fetchall()
        
        print("[REEMBED] Final vector distribution:")
        for stat in vector_stats:
            print(f"  - {stat.model_name} (dim={stat.model_dimension}): {stat.count} vectors")

if __name__ == "__main__":
    print(f"Re-embedding articles with {config.model_name} (dimension: {config.dimension})")
    print("This may take several minutes depending on the number of articles...")
    
    try:
        asyncio.run(reembed_all_articles())
        print("[REEMBED] ✅ Re-embedding completed successfully!")
    except KeyboardInterrupt:
        print("[REEMBED] ❌ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"[REEMBED] ❌ Fatal error: {e}")
        sys.exit(1)