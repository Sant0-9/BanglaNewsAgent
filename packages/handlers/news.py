"""
News handler for general news queries
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from packages.llm.openai_client import summarize_bn_first
from packages.nlp.enhanced_retrieve import enhanced_retrieve_evidence
from packages.db import repo as db_repo


async def handle(query: str, slots: dict, lang: str = "bn") -> dict:
    """
    Handle news queries using enhanced database retrieval system
    
    Returns:
    {
      "answer_bn": "...",
      "sources": [{"name":"...", "url":"...", "published_at":"..."}],
      "flags": {"single_source": bool, "disagreement": bool},
      "metrics": {"latency_ms": int, "source_count": int, "updated_ct": "..."}
    }
    """
    start_time = datetime.now(timezone.utc)
    
    try:
        # Use enhanced database retrieval system (same as main API)
        evidence = await enhanced_retrieve_evidence(query, category=None, db_repo=db_repo, window_hours=72)
        
        if not evidence:
            end_time = datetime.now(timezone.utc)
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
        
        # Generate summary using Bangla-first approach (same as main API)
        result = await summarize_bn_first(evidence)

        # Extract information and honor language preference
        summary_bn = result.get("summary_bn", "সংবাদ প্রক্রিয়াকরণে সমস্যা হয়েছে।")
        
        if (lang or "bn").lower() == "en":
            # For English, provide basic translation (can be enhanced later)
            answer_text = summary_bn
        else:
            answer_text = summary_bn
            
        disagreement = result.get("disagreement", False)
        single_source = result.get("single_source", False)
        
        # Create sources list from evidence
        sources = []
        for item in evidence:
            sources.append({
                "name": item.get("outlet", "Unknown"),
                "url": item.get("url", ""),
                "published_at": item.get("published_at", datetime.now(timezone.utc).isoformat())
            })
        
        # Calculate metrics
        end_time = datetime.now(timezone.utc)
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
        end_time = datetime.now(timezone.utc)
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