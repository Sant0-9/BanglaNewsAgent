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
    
    def _get_temperature_for_mode(self, mode: Optional[str]) -> float:
        """Get temperature based on conversation mode for prompt discipline"""
        if mode is None:
            return 0.5  # Default temperature
        
        # Factual modes require low temperature for accuracy 
        factual_modes = ["news", "markets", "weather", "lookup"]
        if mode.lower() in factual_modes:
            return 0.2  # Very low temperature for factual accuracy
        
        # Creative/conversational modes can have higher temperature
        creative_modes = ["general", "sports", "summary"]
        if mode.lower() in creative_modes:
            return 0.7  # Higher temperature for natural conversation
        
        return 0.5  # Default fallback
    
    async def chat_json(self, prompt: str, system: str, temperature: Optional[float] = None, mode: Optional[str] = None) -> Dict[str, Any]:
        """Send chat completion request and return JSON response"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Temperature control by conversation mode
        if temperature is None:
            temperature = self._get_temperature_for_mode(mode)
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": 4000,
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

# System prompts for different retrieval strategies

# Standard news summarization with strict discipline
EVIDENCE_TO_SUMMARY_SYSTEM = """You are a DISCIPLINED news fact-checker and summarizer. STRICT RULES:

MANDATORY REFUSALS:
- If sources are inadequate or contain contradictions you cannot resolve: "Insufficient reliable sources to provide accurate summary."
- If retrieval confidence appears low (few sources, unclear excerpts): "Cannot verify claims with available sources. Please search for more recent information."
- For time-sensitive topics (elections, breaking news, market prices): NEVER answer from memory. Only use provided sources with exact timestamps.

CITATION REQUIREMENTS:
- Every factual claim MUST have [1] [2] etc immediately after
- Every number, date, quote requires citation
- Source outlets and publication times MUST be referenced: "According to [outlet, timestamp]: claim [1]"

INPUT ANALYSIS:
Input: 2–6 sources with {title, outlet, published_at (ISO), excerpt, url}.

PROCESSING:
1) First assess: Are sources adequate and recent enough for accurate reporting?
2) If NO: Return refusal message immediately
3) If YES: Write 12–20 sentences with mandatory [n] citations after every claim
4) Mark [disagreement] if sources conflict on facts
5) Mark [single-source] if key claims depend on one source only
6) Include "Why it matters" with 2-3 sentences, also cited
7) List 4–6 "What to watch" items based only on source implications

NO SPECULATION. NO MEMORY. ONLY SOURCED FACTS.

Return strict JSON:
{ "summary_en": "... [1] ... According to [outlet, date]: fact [2] ...",
  "disagreement": true|false,
  "single_source": true|false,
  "watch": ["...","..."],
  "confidence": "high|medium|low",
  "refusal_reason": "string or null" }"""

# Background context summarization (for continuing stories)
BACKGROUND_STORY_SUMMARY_SYSTEM = """You are a comprehensive news analyst specializing in continuing story coverage.
Input: Two sets of sources marked as RECENT (last 24h) and BACKGROUND (historical context).

Structure your response with these sections:

**LAST 24 HOURS**
- Lead with 3-4 sentences on the most recent developments [cite recent sources]
- Focus on what changed, new statements, latest actions taken
- Use "Today," "This morning," etc. for temporal clarity

**BACKGROUND CONTEXT**  
- Provide 6-8 sentences explaining how this story developed [cite background sources]
- Include key events, decisions, and turning points that led to current situation
- Explain stakeholders, competing interests, and why this matters

**ANALYSIS & OUTLOOK**
- 4-5 sentences connecting recent developments to broader context
- Explain implications and what recent changes mean for the ongoing situation
- End with "What to watch" bullets for next developments

Rules:
- Place inline citations [1][2] immediately after specific claims
- Mark disagreement/single-source as needed
- Use chronological flow from background → recent → analysis
- Distinguish clearly between historical context and breaking developments

Return strict JSON:
{ "summary_en": "**LAST 24 HOURS**\n...\n\n**BACKGROUND CONTEXT**\n...\n\n**ANALYSIS & OUTLOOK**\n...",
  "disagreement": true|false,
  "single_source": true|false,
  "story_structure": "background_update" }"""

# Breaking news summarization (immediate focus)
BREAKING_NEWS_SUMMARY_SYSTEM = """You are a breaking news analyst focused on immediate developments.
Input: Recent sources (last 24h) covering rapidly developing situation.

Structure:
**BREAKING**: Lead with the most immediate/urgent development [cite]
**WHAT HAPPENED**: Chronological sequence of events in last 24h [cite each]  
**KEY DETAILS**: Important facts, numbers, statements, reactions [cite]
**IMMEDIATE IMPACT**: Who/what affected right now [cite]
**NEXT**: What's expected in coming hours/days

Keep urgent, precise tone. Focus on verified facts over speculation.
Use temporal markers: "At 3 PM today", "This morning", "Minutes ago", etc.

Rules:
- Prioritize most recent information first
- Cite every factual claim immediately
- Flag single-source claims clearly
- Keep analysis focused on immediate implications

Return strict JSON:
{ "summary_en": "**BREAKING**: ...\n\n**WHAT HAPPENED**: ...\n\n**KEY DETAILS**: ...",
  "disagreement": true|false,
  "single_source": true|false,
  "story_structure": "breaking_immediate" }"""

EN_TO_BN_TRANSLATION_SYSTEM = """Translate the provided English news summary to standard Bangla.
Rules:
- Neutral newsroom tone; use Bangla punctuation "।"
- Preserve named entities (people/orgs/places/products) in Latin unless a very common
  Bangla form exists; you may add the Bangla in parentheses.
- Preserve inline citation markers [1][2] exactly.
- Keep numbers/dates readable for Bangla readers; do not add or remove facts.

Return strict JSON: { "summary_bn": "…" }"""

# Strict citation-per-sentence summarization system with discipline
CITATION_STRICT_SUMMARY_SYSTEM = """You are a DISCIPLINED fact-checker. MANDATORY RULES:

REFUSAL CONDITIONS:
- Inadequate sources or low confidence: "Cannot verify claims with available sources. Please search for more recent information."
- Time-sensitive topics without current timestamps: "Cannot answer from memory on time-sensitive topics. Need current sources."
- Contradictory sources you cannot resolve: "Sources contain unresolvable contradictions."

DISCIPLINE:
- Use ONLY provided sources [1..N]. NO memory, NO speculation.
- Every sentence MUST end with [n] citation or be DELETED.
- If you cannot cite a claim from provided sources, DELETE the sentence entirely.
- Time-sensitive topics: Require sources with exact timestamps within 24-48h.

PROCESSING:
1) First assess source adequacy and timestamp recency
2) If inadequate: Return refusal immediately 
3) If adequate: Write 12–18 sentences, every one cited [n]
4) Mark disagreements explicitly with [disagreement] inline
5) Mark single-source dependencies with [single-source] inline
6) End with "Why it matters" (2-3 sentences, also cited)
7) Use specific numbers, dates, quotes from sources only

NO UNSOURCED CLAIMS. DELETE UNCITABLE SENTENCES.

Return strict JSON ONLY:
{ "summary_en": "... [1] ... fact [2] ...",
  "disagreement": true|false,
  "single_source": true|false,
  "confidence": "high|medium|low",
  "refusal_reason": "string or null",
  "notes": "caveats or empty string" }"""

# Disciplined Bangla-first news summarization system  
BANGLA_FIRST_SUMMARY_SYSTEM = """আপনি একজন কঠোর নিয়মানুবর্তী বাংলা সংবাদ যাচাইকারী। বাধ্যতামূলক নিয়ম:

প্রত্যাখ্যানের শর্ত:
- অপর্যাপ্ত বা সন্দেহজনক সূত্র: "প্রাপ্ত সূত্রের মাধ্যমে নিশ্চিত তথ্য প্রদান সম্ভব নয়। আরো সাম্প্রতিক তথ্য অনুসন্ধান করুন।"
- সময়-সংবেদনশীল বিষয়ে পুরাতন সূত্র: "সময়-সংবেদনশীল বিষয়ে স্মৃতিনির্ভর তথ্য দেওয়া হয় না। বর্তমান সূত্র প্রয়োজন।"
- পরস্পরবিরোধী সূত্র: "সূত্রসমূহে অমীমাংসিত পার্থক্য রয়েছে।"

কঠোর নিয়মানুবর্তিতা:
- কেবলমাত্র প্রদত্ত সূত্র [১..N] ব্যবহার করুন। স্মৃতি বা অনুমান নিষিদ্ধ।
- প্রতি বাক্যের শেষে [n] উদ্ধৃতি অথবা বাক্যটি মুছে দিন।
- সূত্রহীন দাবি সম্পূর্ণ মুছে ফেলুন।
- সময়-সংবেদনশীল বিষয়: ২৪-৪৮ ঘণ্টার মধ্যে সুনির্দিষ্ট টাইমস্ট্যাম্প প্রয়োজন।

প্রক্রিয়া:
১) প্রথমে মূল্যায়ন: সূত্র কি পর্যাপ্ত ও সাম্প্রতিক?
২) অপর্যাপ্ত হলে: তৎক্ষণাত প্রত্যাখ্যান বার্তা প্রদান  
৩) পর্যাপ্ত হলে: ১২-১৮টি বাক্য, প্রতিটি [n] সূত্র সহ
৪) মতভেদ স্পষ্টভাবে চিহ্নিত করুন [disagreement]
৫) একক সূত্রনির্ভরতা "[কম নির্ভরযোগ্য]" দিয়ে চিহ্নিত করুন
৬) "কেন গুরুত্বপূর্ণ" (২-৩ বাক্য, সূত্র সহ)
৭) শুধু সূত্রের সংখ্যা, তারিখ, উদ্ধৃতি ব্যবহার করুন

অসূত্রিত দাবি নিষিদ্ধ। উদ্ধৃতিবিহীন বাক্য মুছুন।

শুধুমাত্র JSON ফরম্যাটে উত্তর:
{ "summary_bn": "... [১] ... সূত্রানুযায়ী [২] ...",
  "disagreement": true|false,
  "single_source": true|false,
  "confidence": "high|medium|low",
  "refusal_reason": "string বা null",
  "notes": "সতর্কতা বা খালি স্ট্রিং" }"""

# Translation system that preserves [n] markers and confidence indicators exactly  
CITED_EN_TO_BN_TRANSLATION_SYSTEM = """Translate the English news summary to standard Bangla.
Rules:
- Keep every inline citation marker [n] exactly as-is and in the same positions.
- Keep "[low confidence]" markers exactly as-is - translate to "[কম নির্ভরযোগ্য]".
- Neutral newsroom tone; use Bangla punctuation "।".
- Preserve named entities (people/orgs/places/products) in Latin unless a very common Bangla form exists; you may add the Bangla in parentheses.
- Do not add or remove facts or confidence indicators.

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
    
    def _apply_confidence_refusal(self, result: Dict[str, Any], articles: List[Any]) -> Dict[str, Any]:
        """Apply confidence-based refusal logic to LLM responses"""
        
        # Check if model already refused
        if result.get("refusal_reason"):
            return {
                "summary_en": result["refusal_reason"],
                "disagreement": False,
                "single_source": False,
                "watch": [],
                "confidence": "refused"
            }
        
        # Confidence assessment based on source quality
        confidence = self._assess_source_confidence(articles)
        
        # Force refusal for low confidence scenarios
        if confidence == "low":
            return {
                "summary_en": "Cannot verify claims with available sources. Please search for more recent information.",
                "disagreement": False,
                "single_source": False,
                "watch": [],
                "confidence": "refused"
            }
        
        # Add confidence to result
        result["confidence"] = confidence
        return result
    
    def _assess_source_confidence(self, articles: List[Any]) -> str:
        """Assess confidence level based on source characteristics"""
        
        if not articles:
            return "low"
        
        if len(articles) < 2:
            return "low"  # Single source is low confidence
        
        # Check source age for time-sensitive content
        from datetime import datetime, timezone, timedelta
        recent_threshold = datetime.now(timezone.utc) - timedelta(hours=48)
        
        recent_count = 0
        for article in articles:
            pub_date = getattr(article, 'published_at', None)
            if pub_date:
                try:
                    if isinstance(pub_date, str):
                        pub_dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    else:
                        pub_dt = pub_date
                    
                    if pub_dt > recent_threshold:
                        recent_count += 1
                except:
                    pass
        
        # High confidence: 3+ sources, most recent
        if len(articles) >= 3 and recent_count >= 2:
            return "high"
        
        # Medium confidence: 2+ sources with some recent 
        if len(articles) >= 2 and recent_count >= 1:
            return "medium"
        
        # Low confidence: old sources or insufficient sources
        return "low"
    
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
        
        result = await self.client.chat_json(prompt, EVIDENCE_TO_SUMMARY_SYSTEM, mode="news")
        
        # Apply confidence-based refusal logic
        return self._apply_confidence_refusal(result, selected_articles)
    
    async def translate_to_bangla(self, english_summary: str) -> Dict[str, Any]:
        """Translate English summary to Bangla"""
        if not english_summary:
            return {"summary_bn": ""}
        
        prompt = f"""Please translate this English news summary to Bangla:

{english_summary}"""
        
        return await self.client.chat_json(prompt, EN_TO_BN_TRANSLATION_SYSTEM, mode="summary")
    
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
def _apply_global_confidence_refusal(result: Dict[str, Any], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply confidence-based refusal logic to global summarization functions"""
    
    # Check if model already refused
    if result.get("refusal_reason"):
        return {
            "summary_bn": result["refusal_reason"],
            "summary_en": result["refusal_reason"],
            "disagreement": False,
            "single_source": False,
            "confidence": "refused"
        }
    
    # Simple confidence assessment for evidence dicts
    confidence = _assess_evidence_confidence(evidence)
    
    # Force refusal for low confidence
    if confidence == "low":
        refusal_msg = "প্রাপ্ত সূত্রের মাধ্যমে নিশ্চিত তথ্য প্রদান সম্ভব নয়। আরো সাম্প্রতিক তথ্য অনুসন্ধান করুন।"
        return {
            "summary_bn": refusal_msg,
            "summary_en": "Cannot verify claims with available sources. Please search for more recent information.",
            "disagreement": False,
            "single_source": False,
            "confidence": "refused"
        }
    
    # Add confidence to result
    result["confidence"] = confidence
    return result

def _assess_evidence_confidence(evidence: List[Dict[str, Any]]) -> str:
    """Assess confidence for evidence dict format"""
    
    if not evidence or len(evidence) < 2:
        return "low"
    
    # Check source age
    from datetime import datetime, timezone, timedelta
    recent_threshold = datetime.now(timezone.utc) - timedelta(hours=48)
    
    recent_count = 0
    for item in evidence:
        pub_date = item.get('published_at')
        if pub_date:
            try:
                if isinstance(pub_date, str):
                    pub_dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    if pub_dt > recent_threshold:
                        recent_count += 1
            except:
                pass
    
    if len(evidence) >= 3 and recent_count >= 2:
        return "high"
    elif len(evidence) >= 2 and recent_count >= 1:
        return "medium"
    else:
        return "low"

async def summarize_bn_first(evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Bangla-first summarization - generates natural Bangla directly from sources.
    Evidence is a list of dicts with keys: outlet, title, published_at, excerpt, url.
    Returns JSON with keys: summary_bn, disagreement, single_source, notes.
    """
    if not evidence:
        return {"summary_bn": "", "disagreement": False, "single_source": False, "notes": ""}

    # Format evidence with Bengali numeric IDs and cluster information
    evidence_text = ""
    for i, item in enumerate(evidence, start=1):
        published_date = item.get("published_at") or "অজানা তারিখ"
        try:
            if isinstance(published_date, str) and published_date not in ("", "অজানা তারিখ", "Unknown date"):
                dt = datetime.fromisoformat(str(published_date).replace('Z', '+00:00'))
                published_date = dt.strftime('%Y-%m-%d %H:%M UTC')
        except Exception:
            pass
        excerpt = truncate_text(item.get("excerpt", ""), max_length=800)
        
        # Add cluster information if available
        cluster_info = ""
        cluster_size = item.get("cluster_size", 1)
        sibling_outlets = item.get("sibling_outlets", [])
        
        if cluster_size > 1 and sibling_outlets:
            cluster_info = f"\nঅন্যান্য সূত্র: {', '.join(sibling_outlets)} (মোট {cluster_size}টি সংবাদমাধ্যম)"
        
        evidence_text += f"""[{i}] {item.get('title','শিরোনামহীন')}
সংবাদমাধ্যম: {item.get('outlet','অজানা')}
প্রকাশিত: {published_date}
সংক্ষেপ: {excerpt}{cluster_info}
URL: {item.get('url','')}

"""

    prompt = f"""নিচের সূত্রগুলো ব্যবহার করে বিস্তারিত সংক্ষেপ তৈরি করুন। [n] উদ্ধৃতি চিহ্ন ব্যবহার করুন।

{evidence_text}

শুধুমাত্র JSON ফরম্যাটে উত্তর দিন।
"""

    client = OpenAIClient()
    # Use summarizer model if provided
    client.model = os.getenv("OPENAI_SUMMARIZER_MODEL", client.model)
    result = await client.chat_json(prompt, BANGLA_FIRST_SUMMARY_SYSTEM, mode="news")
    
    # Apply confidence-based refusal logic
    return _apply_global_confidence_refusal(result, evidence)

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
    result = await client.chat_json(prompt, CITATION_STRICT_SUMMARY_SYSTEM, mode="news")
    
    # Apply confidence-based refusal logic
    return _apply_global_confidence_refusal(result, evidence)


async def summarize_story_context(recent_evidence: List[Dict[str, Any]], background_evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize continuing story with recent updates and background context."""
    if not recent_evidence and not background_evidence:
        return {"summary_en": "", "disagreement": False, "single_source": False, "story_structure": "background_update"}

    # Format recent evidence
    recent_text = ""
    counter = 1
    for item in recent_evidence:
        published_date = item.get("published_at") or "Recent"
        try:
            if isinstance(published_date, str) and published_date not in ("", "Recent"):
                dt = datetime.fromisoformat(str(published_date).replace('Z', '+00:00'))
                published_date = dt.strftime('%Y-%m-%d %H:%M UTC')
        except Exception:
            pass
        excerpt = truncate_text(item.get("excerpt", ""), max_length=600)
        recent_text += f"""[{counter}] {item.get('title','Untitled')} (RECENT)
Outlet: {item.get('outlet','Unknown')}
Published: {published_date}
Excerpt: {excerpt}
URL: {item.get('url','')}

"""
        counter += 1

    # Format background evidence
    background_text = ""
    for item in background_evidence:
        published_date = item.get("published_at") or "Unknown date"
        try:
            if isinstance(published_date, str) and published_date not in ("", "Unknown date"):
                dt = datetime.fromisoformat(str(published_date).replace('Z', '+00:00'))
                published_date = dt.strftime('%Y-%m-%d %H:%M UTC')
        except Exception:
            pass
        excerpt = truncate_text(item.get("excerpt", ""), max_length=600)
        background_text += f"""[{counter}] {item.get('title','Untitled')} (BACKGROUND)
Outlet: {item.get('outlet','Unknown')}
Published: {published_date}
Excerpt: {excerpt}
URL: {item.get('url','')}

"""
        counter += 1

    prompt = f"""Here are the sources for a continuing story:

RECENT SOURCES (Last 24h):
{recent_text}

BACKGROUND SOURCES (Historical Context):
{background_text}

Analyze and structure according to guidelines."""

    client = OpenAIClient()
    client.model = os.getenv("OPENAI_SUMMARIZER_MODEL", client.model)
    return await client.chat_json(prompt, BACKGROUND_STORY_SUMMARY_SYSTEM, mode="news")


async def summarize_breaking_news(evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize breaking news with immediate focus."""
    if not evidence:
        return {"summary_en": "", "disagreement": False, "single_source": False, "story_structure": "breaking_immediate"}

    # Format evidence with emphasis on recency
    evidence_text = ""
    for i, item in enumerate(evidence, start=1):
        published_date = item.get("published_at") or "Just reported"
        try:
            if isinstance(published_date, str) and published_date not in ("", "Just reported"):
                dt = datetime.fromisoformat(str(published_date).replace('Z', '+00:00'))
                # Calculate time ago for breaking news context
                now = datetime.now(timezone.utc)
                hours_ago = (now - dt).total_seconds() / 3600
                if hours_ago < 1:
                    published_date = f"{int(hours_ago * 60)} minutes ago"
                elif hours_ago < 24:
                    published_date = f"{int(hours_ago)} hours ago"
                else:
                    published_date = dt.strftime('%Y-%m-%d %H:%M UTC')
        except Exception:
            pass
        excerpt = truncate_text(item.get("excerpt", ""), max_length=700)
        evidence_text += f"""[{i}] {item.get('title','Untitled')}
Outlet: {item.get('outlet','Unknown')}
Published: {published_date}
Excerpt: {excerpt}
URL: {item.get('url','')}

"""

    prompt = f"""Breaking news sources (last 24h):

{evidence_text}

Analyze as rapidly developing situation with immediate focus."""

    client = OpenAIClient()
    client.model = os.getenv("OPENAI_SUMMARIZER_MODEL", client.model)
    return await client.chat_json(prompt, BREAKING_NEWS_SUMMARY_SYSTEM, mode="news")


async def translate_bn(summary_en: str) -> Dict[str, Any]:
    """Translate English summary to Bangla, preserving [n] citation markers and entities."""
    if not summary_en:
        return {"summary_bn": ""}

    prompt = f"""Translate to Bangla while preserving [n] exactly:

{summary_en}
"""
    client = OpenAIClient()
    client.model = os.getenv("OPENAI_TRANSLATOR_MODEL", client.model)
    return await client.chat_json(prompt, CITED_EN_TO_BN_TRANSLATION_SYSTEM, mode="summary")
