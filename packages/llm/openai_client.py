import os
import asyncio
import httpx
import ujson as json
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from packages.util.normalize import truncate_text

# Load environment variables
load_dotenv()

class OpenAIClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.base_url = "https://api.openai.com/v1"
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
    
    async def chat_json(self, prompt: str, system: str) -> Dict[str, Any]:
        """Send chat completion request and return JSON response"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    content=json.dumps(data)
                )
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Parse JSON response
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Retry once on JSON parse failure
                    print("JSON parse failed, retrying...")
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        content=json.dumps(data)
                    )
                    response.raise_for_status()
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    return json.loads(content)
                    
            except httpx.HTTPError as e:
                raise Exception(f"OpenAI API error: {e}")
            except (KeyError, IndexError) as e:
                raise Exception(f"Unexpected OpenAI response format: {e}")
            except json.JSONDecodeError as e:
                raise Exception(f"Failed to parse JSON response after retry: {e}")

# System prompts
EVIDENCE_TO_SUMMARY_SYSTEM = """You are a neutral, citation-first news summarizer.
Input: 2–6 sources with {title, outlet, published_at (ISO), excerpt, url}.

Tasks:
1) Identify what's NEW in the last 24–72 hours.
2) Write 6–10 sentences in English. Place inline citations [1][2] immediately
   after the specific claims they support. Use dates when useful.
3) If sources conflict on numbers/facts, say so and add [disagreement].
4) If any key claim is from a single source, add [single-source].
5) End with one sentence: "Why it matters".
6) Then list 2–4 "What to watch" bullets.

Return strict JSON:
{ "summary_en": "... [1][2] ...",
  "disagreement": true|false,
  "single_source": true|false,
  "watch": ["...","..."] }"""

EN_TO_BN_TRANSLATION_SYSTEM = """Translate the provided English news summary to standard Bangla.
Rules:
- Neutral newsroom tone; use Bangla punctuation "।"
- Preserve named entities (people/orgs/places/products) in Latin unless a very common
  Bangla form exists; you may add the Bangla in parentheses.
- Preserve inline citation markers [1][2] exactly.
- Keep numbers/dates readable for Bangla readers; do not add or remove facts.

Return strict JSON: { "summary_bn": "…" }"""

def build_evidence_pack(selected_articles: List[Any]) -> List[Dict[str, Any]]:
    """Format articles into evidence pack structure with trimmed excerpts"""
    evidence_pack = []
    
    for i, article in enumerate(selected_articles, 1):
        # Trim excerpt to 500 chars to avoid token bloat
        excerpt = truncate_text(getattr(article, 'summary', ''), max_length=500)
        
        evidence = {
            "id": i,
            "outlet": getattr(article, 'source', 'Unknown'),
            "title": getattr(article, 'title', 'Untitled'),
            "published_at": getattr(article, 'published_at', None),
            "excerpt": excerpt,
            "url": getattr(article, 'url', ''),
        }
        evidence_pack.append(evidence)
    
    return evidence_pack

class NewsProcessor:
    def __init__(self):
        self.client = OpenAIClient()
    
    async def summarize_evidence(self, selected_articles: List[Any]) -> Dict[str, Any]:
        """Create English summary from evidence pack"""
        if not selected_articles:
            return {
                "summary_en": "No recent news articles available.",
                "disagreement": False,
                "single_source": False,
                "watch": []
            }
        
        # Build evidence pack
        evidence_pack = build_evidence_pack(selected_articles)
        
        # Create prompt with formatted evidence
        evidence_text = ""
        for item in evidence_pack:
            published_date = item.get('published_at', 'Unknown date')
            if published_date and published_date != 'Unknown date':
                try:
                    dt = datetime.fromisoformat(str(published_date).replace('Z', '+00:00'))
                    published_date = dt.strftime('%Y-%m-%d %H:%M UTC')
                except Exception:
                    pass
            
            evidence_text += f"""[{item['id']}] {item['title']}
Outlet: {item['outlet']}
Published: {published_date}
Excerpt: {item['excerpt']}
URL: {item['url']}

"""
        
        prompt = f"""Here are the news sources to summarize:

{evidence_text}

Please analyze these sources and provide a comprehensive summary following the guidelines."""
        
        return await self.client.chat_json(prompt, EVIDENCE_TO_SUMMARY_SYSTEM)
    
    async def translate_to_bangla(self, english_summary: str) -> Dict[str, Any]:
        """Translate English summary to Bangla"""
        if not english_summary:
            return {"summary_bn": ""}
        
        prompt = f"""Please translate this English news summary to Bangla:

{english_summary}"""
        
        return await self.client.chat_json(prompt, EN_TO_BN_TRANSLATION_SYSTEM)
    
    async def process_news(self, selected_articles: List[Any]) -> Dict[str, Any]:
        """Complete pipeline: evidence → English summary → Bangla translation"""
        try:
            # Generate English summary
            summary_result = await self.summarize_evidence(selected_articles)
            english_summary = summary_result.get("summary_en", "")
            
            # Translate to Bangla
            translation_result = await self.translate_to_bangla(english_summary)
            bangla_summary = translation_result.get("summary_bn", "")
            
            # Combine results
            return {
                "summary_en": english_summary,
                "summary_bn": bangla_summary,
                "disagreement": summary_result.get("disagreement", False),
                "single_source": summary_result.get("single_source", False),
                "watch": summary_result.get("watch", []),
                "evidence_pack": build_evidence_pack(selected_articles)
            }
            
        except Exception as e:
            print(f"Error processing news: {e}")
            return {
                "summary_en": f"Error processing news: {str(e)}",
                "summary_bn": f"সংবাদ প্রক্রিয়াকরণে ত্রুটি: {str(e)}",
                "disagreement": False,
                "single_source": False,
                "watch": [],
                "evidence_pack": build_evidence_pack(selected_articles) if selected_articles else []
            }
