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
            "temperature": 0.5,  # Increased for more varied, natural responses
            "max_tokens": 4000,  # Doubled for longer, more detailed responses
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
EVIDENCE_TO_SUMMARY_SYSTEM = """You are a comprehensive, citation-first news summarizer focused on delivering detailed, insightful analysis.
Input: 2–6 sources with {title, outlet, published_at (ISO), excerpt, url}.

Tasks:
1) Identify what's NEW in the last 24–72 hours with comprehensive context.
2) Write a detailed 12–20 sentence analysis in English. Place inline citations [1][2] immediately
   after the specific claims they support. Use dates and specific details when useful.
3) Include background context, implications, and multiple perspectives where available.
4) If sources conflict on numbers/facts, explain the discrepancy in detail and add [disagreement].
5) If any key claim is from a single source, note this clearly and add [single-source].
6) End with 2-3 sentences explaining "Why it matters" with broader implications.
7) Then list 4–6 detailed "What to watch" bullets with specific actionable insights.
8) Provide nuanced analysis rather than just summarizing headlines.

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

# Strict citation-per-sentence summarization system
CITATION_STRICT_SUMMARY_SYSTEM = """You are a comprehensive, citation-first news summarizer.
Use ONLY the provided sources, referenced by numeric IDs [1..N]. Do NOT invent sources.

Rules:
- Every sentence MUST end with at least one inline citation like [1] or [2][3].
- If you cannot support a sentence with a provided source, DELETE the sentence.
- Write 12–18 detailed sentences covering what's NEW in the last 24–72 hours.
- Include context, background, implications, and multiple perspectives from the sources.
- Call out disagreements on numbers/facts explicitly and set disagreement=true.
- If any key claim rests on a single source, add "[single-source]" inline and set single_source=true.
- End with 2-3 "Why it matters" sentences explaining broader significance, also cited.
- Provide substantive analysis, not just headline summaries.
- Use specific details, numbers, dates, and quotes from sources when available.

Return strict JSON ONLY:
{ "summary_en": "... [1] ...",
  "disagreement": true|false,
  "single_source": true|false,
  "notes": "optional short caveats or empty string" }"""

# Translation system that preserves [n] markers exactly
CITED_EN_TO_BN_TRANSLATION_SYSTEM = """Translate the English news summary to standard Bangla.
Rules:
- Keep every inline citation marker [n] exactly as-is and in the same positions.
- Neutral newsroom tone; use Bangla punctuation "।".
- Preserve named entities (people/orgs/places/products) in Latin unless a very common Bangla form exists; you may add the Bangla in parentheses.
- Do not add or remove facts.

Return strict JSON ONLY: { "summary_bn": "…" }"""

def build_evidence_pack(selected_articles: List[Any]) -> List[Dict[str, Any]]:
    """Format articles into evidence pack structure with expanded excerpts for better summarization"""
    evidence_pack = []
    
    for i, article in enumerate(selected_articles, 1):
        # Increase excerpt length for more detailed summarization
        excerpt = truncate_text(getattr(article, 'summary', ''), max_length=800)
        
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


# New convenience functions with env-driven models
async def summarize_en(evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize with strict per-sentence citations. Evidence is a list of dicts
    with keys: outlet, title, published_at, excerpt, url. Returns JSON with
    keys: summary_en, disagreement, single_source, notes.
    """
    if not evidence:
        return {"summary_en": "", "disagreement": False, "single_source": False, "notes": ""}

    # Format evidence with numeric IDs
    evidence_text = ""
    for i, item in enumerate(evidence, start=1):
        published_date = item.get("published_at") or "Unknown date"
        try:
            if isinstance(published_date, str) and published_date not in ("", "Unknown date"):
                dt = datetime.fromisoformat(str(published_date).replace('Z', '+00:00'))
                published_date = dt.strftime('%Y-%m-%d %H:%M UTC')
        except Exception:
            pass
        excerpt = truncate_text(item.get("excerpt", ""), max_length=800)
        evidence_text += f"""[{i}] {item.get('title','Untitled')}
Outlet: {item.get('outlet','Unknown')}
Published: {published_date}
Excerpt: {excerpt}
URL: {item.get('url','')}

"""

    prompt = f"""Summarize only using the sources below. Use [n] citation markers.

{evidence_text}

Return strict JSON only.
"""

    client = OpenAIClient()
    # Use summarizer model if provided
    client.model = os.getenv("OPENAI_SUMMARIZER_MODEL", client.model)
    return await client.chat_json(prompt, CITATION_STRICT_SUMMARY_SYSTEM)


async def translate_bn(summary_en: str) -> Dict[str, Any]:
    """Translate English summary to Bangla, preserving [n] citation markers and entities."""
    if not summary_en:
        return {"summary_bn": ""}

    prompt = f"""Translate to Bangla while preserving [n] exactly:

{summary_en}
"""
    client = OpenAIClient()
    client.model = os.getenv("OPENAI_TRANSLATOR_MODEL", client.model)
    return await client.chat_json(prompt, CITED_EN_TO_BN_TRANSLATION_SYSTEM)
