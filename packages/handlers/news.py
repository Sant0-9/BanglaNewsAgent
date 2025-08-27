"""
News handler for general news queries
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from packages.llm.text_processor import NewsProcessor
from packages.nlp.rank import rank_articles
from services.ingest.rss import gather_candidates, load_from_cache


async def handle(query: str, slots: dict, lang: str = "bn") -> dict:
    """
    Handle news queries using existing news pipeline:
    evidence pack → EN summary → BN translate
    
    Returns:
    {
      "answer_bn": "...",
      "sources": [{"name":"...", "url":"...", "published_at":"..."}],
      "flags": {"single_source": bool, "disagreement": bool},
      "metrics": {"latency_ms": int, "source_count": int, "updated_ct": "..."}
    }
    """
    start_time = datetime.now()
    
    # Initialize news processor
    news_processor = NewsProcessor()
    
    try:
        # Try to get cached articles first
        articles = load_from_cache()
        
        # If no cached articles, gather fresh ones
        if not articles:
            articles = gather_candidates(query=query, window_hours=72, max_items=100)
        
        if not articles:
            end_time = datetime.now()
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                "answer_bn": "বর্তমানে কোনো সংবাদ নিবন্ধ পাওয়া যাচ্ছে না।",
                "sources": [],
                "flags": {"single_source": False, "disagreement": False},
                "metrics": {
                    "latency_ms": latency_ms,
                    "source_count": 0,
                    "updated_ct": end_time.isoformat()
                }
            }
        
        # Rank articles by relevance to query
        ranked_articles = rank_articles(articles, query, top_k=6)
        
        # Process through news pipeline
        result = await news_processor.process_news(ranked_articles)

        # Extract information and honor language preference
        if (lang or "bn").lower() == "en":
            answer_text = result.get("summary_en", "There was a problem processing the news.")
        else:
            answer_text = result.get("summary_bn", "সংবাদ প্রক্রিয়াকরণে সমস্যা হয়েছে।")
        disagreement = result.get("disagreement", False)
        single_source = result.get("single_source", False)
        evidence_pack = result.get("evidence_pack", [])
        
        # Create sources list from evidence pack
        sources = []
        for item in evidence_pack:
            sources.append({
                "name": item.get("outlet", "Unknown"),
                "url": item.get("url", ""),
                "published_at": item.get("published_at", datetime.now().isoformat())
            })
        
        # Calculate metrics
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return {
            # UI expects this field name; we fill with selected language
            "answer_bn": answer_text,
            "sources": sources,
            "flags": {
                "single_source": single_source,
                "disagreement": disagreement
            },
            "metrics": {
                "latency_ms": latency_ms,
                "source_count": len(sources),
                "updated_ct": end_time.isoformat()
            }
        }
        
    except Exception as e:
        # Error fallback
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return {
            "answer_bn": f"সংবাদ প্রক্রিয়াকরণে সমস্যা হয়েছে। ত্রুটি: {str(e)}",
            "sources": [],
            "flags": {"single_source": False, "disagreement": False},
            "metrics": {
                "latency_ms": latency_ms,
                "source_count": 0,
                "updated_ct": end_time.isoformat()
            }
        }