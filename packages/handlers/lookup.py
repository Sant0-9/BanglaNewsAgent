"""
Lookup handler for Wikipedia-based queries
"""
import asyncio
import httpx
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent))
from llm.openai_client import NewsProcessor


class WikipediaClient:
    """Wikipedia API client for summary extraction"""
    
    def __init__(self):
        self.base_url = "https://en.wikipedia.org/api/rest_v1/page/summary"
    
    async def get_summary(self, subject: str) -> Optional[Dict[str, Any]]:
        """Get Wikipedia page summary for subject"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Clean subject for URL
                clean_subject = subject.replace(" ", "_")
                url = f"{self.base_url}/{clean_subject}"
                
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                # Check if disambiguation page
                if data.get("type") == "disambiguation":
                    return None
                
                return {
                    "title": data.get("title", subject),
                    "extract": data.get("extract", ""),
                    "page_url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    "thumbnail": data.get("thumbnail", {}).get("source", "")
                }
                
        except Exception as e:
            print(f"Wikipedia API error for '{subject}': {e}")
            return None


async def translate_to_bangla(text: str, llm_client: NewsProcessor) -> str:
    """Translate English text to Bangla using local processor"""
    if not text:
        return ""
    
    system_prompt = """Translate the provided English text to standard Bangla.
Rules:
- Use natural, fluent Bangla
- Preserve named entities (people/places/organizations) in Latin unless very common Bangla form exists
- Use Bangla punctuation "।"
- Keep the content informative and accurate

Return strict JSON: { "translation_bn": "..." }"""
    
    try:
        # Use provider-backed translation via NewsProcessor for consistency
        result = await llm_client.translate_to_bangla(text)
        if isinstance(result, dict):
            return result.get("summary_bn", text)
        return str(result)
    except Exception as e:
        print(f"Translation error: {e}")
        return f"অনুবাদ করতে সমস্যা হয়েছে: {text}"


async def handle(query: str, slots: dict, lang: str = "bn") -> dict:
    """
    Handle lookup queries using Wikipedia
    
    Returns:
    {
      "answer_bn": "...",
      "sources": [{"name":"...", "url":"...", "published_at":"..."}],
      "flags": {"single_source": bool, "disagreement": bool},
      "metrics": {"latency_ms": int, "source_count": int, "updated_ct": "..."}
    }
    """
    start_time = datetime.now()
    
    # Get subject from slots
    subject = slots.get("subject", "").strip()
    if not subject:
        # Extract subject from query as fallback
        words = query.lower().split()
        stop_words = {"who", "is", "what", "tell", "me", "about", "কে", "কি", "এই", "সম্পর্কে"}
        subject_words = [word for word in words if word not in stop_words]
        subject = " ".join(subject_words)
    
    if not subject:
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return {
            "answer_bn": "অনুসন্ধানের বিষয় স্পষ্ট নয়। অনুগ্রহ করে আরো সুনির্দিষ্ট প্রশ্ন করুন।",
            "sources": [],
            "flags": {"single_source": False, "disagreement": False},
            "metrics": {
                "latency_ms": latency_ms,
                "source_count": 0,
                "updated_ct": end_time.isoformat()
            }
        }
    
    # Initialize clients
    wiki_client = WikipediaClient()
    llm_client = NewsProcessor()
    
    try:
        # Get Wikipedia summary
        wiki_data = await wiki_client.get_summary(subject)
        
        if not wiki_data or not wiki_data.get("extract"):
            end_time = datetime.now()
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                "answer_bn": f"'{subject}' সম্পর্কে Wikipedia-তে কোন তথ্য পাওয়া যায়নি।",
                "sources": [],
                "flags": {"single_source": False, "disagreement": False},
                "metrics": {
                    "latency_ms": latency_ms,
                    "source_count": 0,
                    "updated_ct": end_time.isoformat()
                }
            }
        
        # Prepare answer honoring language
        english_text = wiki_data["extract"]
        if (lang or "bn").lower() == "en":
            answer_text = english_text
        else:
            answer_text = await translate_to_bangla(english_text, llm_client)
        
        # Create source info
        sources = [{
            "name": "Wikipedia",
            "url": wiki_data["page_url"],
            "published_at": datetime.now().isoformat()
        }]
        
        # Calculate metrics
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return {
            "answer_bn": answer_text,
            "sources": sources,
            "flags": {"single_source": True, "disagreement": False},
            "metrics": {
                "latency_ms": latency_ms,
                "source_count": 1,
                "updated_ct": end_time.isoformat()
            }
        }
        
    except Exception as e:
        # Error fallback
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return {
            "answer_bn": f"'{subject}' সম্পর্কে তথ্য খোঁজায় সমস্যা হয়েছে। ত্রুটি: {str(e)}",
            "sources": [],
            "flags": {"single_source": False, "disagreement": False},
            "metrics": {
                "latency_ms": latency_ms,
                "source_count": 0,
                "updated_ct": end_time.isoformat()
            }
        }