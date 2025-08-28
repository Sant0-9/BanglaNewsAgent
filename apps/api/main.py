from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timezone
import sys
import os
import json
import asyncio
from pathlib import Path

# Add packages and services to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from packages.router.intent import classify
from packages.db import repo as db_repo
from packages.db.repo import init_db, get_recent_articles, search_articles_by_keyword, log_query, search_vectors
from services.ingest.scheduler import start_scheduler, ingest_cycle
from packages.handlers import weather, markets, sports, lookup, news
from packages.util import cache as cache_util
from packages.util.memory import (
    derive_session_id,
    remember_preferred_lang,
    remember_last_query,
    remember_last_evidence,
)
from packages.nlp.retrieve import retrieve_evidence
from packages.llm.openai_client import summarize_en, translate_bn
from packages.nlp.citation_gate import citation_gate

app = FastAPI(
    title="KhoborAgent API",
    description="Multi-intent query API supporting news, weather, markets, sports, and lookup",
    version="2.0.0"
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    query: str = Field(..., description="Query for various intents (news, weather, markets, sports, lookup)")
    lang: Literal['bn', 'en'] = Field(default="bn", description="Response language (bn/en)")
    window_hours: Optional[int] = Field(default=72, description="Time window for news search")
    mode: Optional[Literal['brief', 'deep']] = Field(default="brief", description="Answer depth")
    session_id: Optional[str] = Field(default=None, description="Client-provided session id")

class SourceInfo(BaseModel):
    name: str
    url: str
    published_at: Optional[str]

class AskResponse(BaseModel):
    answer_bn: Optional[str]
    answer_en: str
    sources: List[SourceInfo]
    metrics: Dict[str, Any]
    flags: Dict[str, bool]
    router_info: str

def resolve_handler(intent: str):
    """Resolve intent to appropriate handler function"""
    handler_map = {
        "weather": weather.handle,
        "markets": markets.handle,
        "sports": sports.handle,
        "lookup": lookup.handle,
        "news": news.handle
    }
    return handler_map.get(intent, news.handle)  # Default to news

@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "KhoborAgent API"
    }

@app.on_event("startup")
async def on_startup():
    """Initialize database and start ingest scheduler in development."""
    try:
        env = os.getenv("ENV", "dev")
        if env == "dev":
            init_db()
            start_scheduler()
            print("[startup] DB initialized and ingest scheduler started (dev)")
        else:
            print("[startup] Production mode: ingest scheduler not started")
    except Exception as e:
        print(f"[startup] init error: {e}")

@app.get("/admin/ingest/run")
async def admin_ingest_run():
    """Force one ingest cycle (dev/admin). Returns counts."""
    try:
        feeds_ct, embedded_ct = await ingest_cycle()
        return {
            "status": "ok",
            "feeds": feeds_ct,
            "embedded": embedded_ct,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/articles")
async def get_articles(limit: int = 50):
    """Get recent articles from database."""
    try:
        articles = get_recent_articles(limit=limit)
        return {
            "articles": [
                {
                    "id": str(article.id),
                    "title": article.title,
                    "url": article.url,
                    "source": article.source,
                    "source_category": article.source_category,
                    "summary": article.summary,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "inserted_at": article.inserted_at.isoformat()
                }
                for article in articles
            ],
            "count": len(articles),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/articles/search")
async def search_articles(q: str, limit: int = 50):
    """Search articles by keyword."""
    try:
        articles = search_articles_by_keyword(q, limit=limit)
        return {
            "articles": [
                {
                    "id": str(article.id),
                    "title": article.title,
                    "url": article.url,
                    "source": article.source,
                    "source_category": article.source_category,
                    "summary": article.summary,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "inserted_at": article.inserted_at.isoformat()
                }
                for article in articles
            ],
            "query": q,
            "count": len(articles),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/articles/similar")
async def find_similar_articles(q: str, limit: int = 10):
    """Find articles similar to query using vector search."""
    try:
        from packages.nlp.embed import embed_text
        
        # Generate query embedding
        query_embedding = embed_text(q)
        if not query_embedding or len(query_embedding) != 1536:
            return {"status": "error", "error": "Failed to generate query embedding"}
        
        # Search for similar articles
        results = search_vectors(query_embedding, window_hours=72, limit=limit)
        
        return {
            "articles": [
                {
                    "id": str(article.id),
                    "title": article.title,
                    "url": article.url,
                    "source": article.source,
                    "source_category": article.source_category,
                    "summary": article.summary,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "similarity_score": similarity,
                }
                for article, similarity in results
            ],
            "query": q,
            "count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest, http_request: Request):
    """
    Process queries using intent classification and specialized handlers
    
    Flow:
    1. Classify query intent and extract slots
    2. Resolve appropriate handler for intent
    3. Call handler with query, slots, and language
    4. Return standardized response with metrics
    """
    try:
        # Step 1: Classify intent
        clf = classify(request.query)
        
        # Dev log
        print(f"[router] intent={clf['intent']} conf={clf['confidence']:.2f} slots={clf['slots']}")
        
        # Step 2: Non-news intents use existing handlers
        if clf["intent"] != "news":
            handler = resolve_handler(clf["intent"])            
            resp = await handler(request.query, clf["slots"], lang=request.lang or "bn")
            # Always include intent and confidence in metrics
            resp["metrics"]["intent"] = clf["intent"]
            resp["metrics"]["confidence"] = clf["confidence"]
            sources = []
            for source_info in resp.get("sources", []):
                sources.append(SourceInfo(
                    name=source_info.get("name", "Unknown"),
                    url=source_info.get("url", ""),
                    published_at=source_info.get("published_at")
                ))
            router_info = f"Routed to: {clf['intent'].title()} ({clf['confidence']:.2f})"
            return AskResponse(
                answer_bn=resp["answer_bn"],
                answer_en=resp.get("answer_en", resp["answer_bn"]),
                sources=sources,
                metrics=resp["metrics"],
                flags=resp["flags"],
                router_info=router_info
            )

        # News intent: run hybrid retrieval + summarization with cache and memory
        start_ts = datetime.now(timezone.utc)

        # Derive session id
        client_ip = http_request.client.host if http_request.client else ""
        user_agent = http_request.headers.get("user-agent", "")
        sid = request.session_id or derive_session_id(client_ip, user_agent)
        remember_preferred_lang(sid, request.lang)
        remember_last_query(sid, request.query)

        # Cache key and lookup with improved uniqueness
        wh = int(request.window_hours or 72)
        cache_key = cache_util.create_query_cache_key(request.query, request.lang, wh)
        cached = cache_util.get(cache_key)
        if cached is not None:
            # Fill router info and return cached payload
            router_info = f"Routed to: News ({clf['confidence']:.2f}) [cache]"
            cached["router_info"] = router_info
            return AskResponse(**cached)

        # Map intent to category if applicable
        intent_to_category = {"sports": "sports", "markets": "finance"}
        category = intent_to_category.get(clf["intent"], None)

        # Retrieve evidence
        evidence = await retrieve_evidence(request.query, category, db_repo, window_hours=wh)
        remember_last_evidence(sid, evidence)

        # Summarize EN with citation gate
        en_res = await summarize_en(evidence)
        summary_en_raw = en_res.get("summary_en", "")
        clean_en = citation_gate(summary_en_raw, max_id=len(evidence))

        # Fallback bullets if gate empties summary
        if not clean_en:
            bullets = []
            for i, item in enumerate(evidence, start=1):
                title = item.get("title", "Untitled")
                bullets.append(f"- {title} [{i}]")
            clean_en = "\n".join(bullets)

        # Translate if requested and also ensure frontend gets content in answer_bn for both languages
        answer_bn: Optional[str] = None
        if request.lang == "bn":
            bn_res = await translate_bn(clean_en)
            answer_bn = bn_res.get("summary_bn", None)

        # Build sources list
        sources: List[SourceInfo] = []
        for item in evidence:
            sources.append(SourceInfo(
                name=item.get("outlet", "Unknown"),
                url=item.get("url", ""),
                published_at=item.get("published_at")
            ))

        # Confidence heuristic
        from packages.util.normalize import extract_domain
        domains = {extract_domain(s.url) for s in sources if s.url}
        distinct_domains = len(domains)
        disagreement = bool(en_res.get("disagreement", False))
        # Avg recency
        def _hours_old(p):
            try:
                if not p:
                    return 1e6
                from datetime import datetime
                return (datetime.now(timezone.utc) - datetime.fromisoformat(str(p).replace('Z', '+00:00'))).total_seconds() / 3600.0
            except Exception:
                return 1e6
        avg_hours = 1e6
        try:
            vals = [
                _hours_old(s.published_at) for s in sources if s.published_at
            ]
            if vals:
                avg_hours = sum(vals) / len(vals)
        except Exception:
            pass

        if (not disagreement) and distinct_domains >= 3 and avg_hours <= 24:
            conf = 0.85
        elif distinct_domains >= 2 and avg_hours <= 72:
            conf = 0.55
        else:
            conf = 0.25

        end_ts = datetime.now(timezone.utc)
        latency_ms = int((end_ts - start_ts).total_seconds() * 1000)

        # For compatibility with the web app, always place the selected-language text in answer_bn
        answer_for_ui = clean_en if request.lang == "en" else (answer_bn or clean_en)

        payload = {
            "answer_bn": answer_for_ui,
            "answer_en": clean_en,
            "sources": [s.dict() for s in sources],
            "metrics": {
                "latency_ms": latency_ms,
                "source_count": len(sources),
                "updated_ct": end_ts.isoformat(),
                "intent": clf["intent"],
                "confidence": conf,
            },
            "flags": {
                "single_source": bool(en_res.get("single_source", False)),
                "disagreement": disagreement,
            },
            "router_info": f"Routed to: News ({clf['confidence']:.2f})",
        }

        # Log the query and response to database
        try:
            source_article_ids = [s.get("url") for s in payload.get("sources", []) if s.get("url")]
            log_query(
                question=request.query,
                answer=payload.get("answer_en", ""),
                source_article_ids=source_article_ids,
                response_time_ms=latency_ms
            )
        except Exception as e:
            print(f"Warning: Failed to log query to database: {e}")
        
        # Cache the payload
        cache_util.set(cache_key, payload)

        return AskResponse(**payload)
        
    except Exception as e:
        # Clean error with official sources for weather/markets
        intent = clf.get("intent", "unknown") if 'clf' in locals() else "unknown"
        
        error_msg = "সেবায় সাময়িক সমস্যা হয়েছে।"
        error_sources = []
        
        if intent == "weather":
            error_sources = [{
                "name": "OpenWeatherMap",
                "url": "https://openweathermap.org/",
                "published_at": datetime.now(timezone.utc).isoformat()
            }]
        elif intent == "markets":
            error_sources = [{
                "name": "Alpha Vantage",
                "url": "https://www.alphavantage.co/",
                "published_at": datetime.now(timezone.utc).isoformat()
            }]
        
        print(f"Error processing request for intent={intent}: {e}")
        
        # Return clean error response
        return AskResponse(
            answer_bn=error_msg,
            sources=[SourceInfo(**src) for src in error_sources],
            metrics={
                "intent": intent,
                "confidence": 0.0,
                "latency_ms": 0,
                "source_count": len(error_sources),
                "updated_ct": datetime.now(timezone.utc).isoformat()
            },
            flags={
                "single_source": len(error_sources) <= 1,
                "disagreement": False
            },
            router_info=f"Routed to: {intent.title()} (0.00)"
        )

async def generate_stream(request: AskRequest, http_request: Request):
    """
    Generate SSE stream for the /ask/stream endpoint
    This mimics the logic from /ask but streams the response
    """
    try:
        # Step 1: Classify intent
        clf = classify(request.query)
        
        # Yield intent classification result
        yield f"data: {json.dumps({'type': 'intent', 'data': {'intent': clf['intent'], 'confidence': clf['confidence']}})}\n\n"
        
        # Step 2: Non-news intents use existing handlers
        if clf["intent"] != "news":
            handler = resolve_handler(clf["intent"])            
            resp = await handler(request.query, clf["slots"], lang=request.lang or "bn")
            # Always include intent and confidence in metrics
            resp["metrics"]["intent"] = clf["intent"]
            resp["metrics"]["confidence"] = clf["confidence"]
            sources = []
            for source_info in resp.get("sources", []):
                sources.append(SourceInfo(
                    name=source_info.get("name", "Unknown"),
                    url=source_info.get("url", ""),
                    published_at=source_info.get("published_at")
                ))
            router_info = f"Routed to: {clf['intent'].title()} ({clf['confidence']:.2f})"
            
            # Stream the complete response
            complete_response = AskResponse(
                answer_bn=resp["answer_bn"],
                answer_en=resp.get("answer_en", resp["answer_bn"]),
                sources=sources,
                metrics=resp["metrics"],
                flags=resp["flags"],
                router_info=router_info
            )
            yield f"data: {json.dumps({'type': 'complete', 'data': complete_response.dict()})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # News intent: run hybrid retrieval + summarization with streaming
        start_ts = datetime.now(timezone.utc)

        # Derive session id
        client_ip = http_request.client.host if http_request.client else ""
        user_agent = http_request.headers.get("user-agent", "")
        sid = request.session_id or derive_session_id(client_ip, user_agent)
        remember_preferred_lang(sid, request.lang)
        remember_last_query(sid, request.query)

        # Cache key and lookup with improved uniqueness
        wh = int(request.window_hours or 72)
        cache_key = cache_util.create_query_cache_key(request.query, request.lang, wh)
        cached = cache_util.get(cache_key)
        if cached is not None:
            # Stream cached payload
            router_info = f"Routed to: News ({clf['confidence']:.2f}) [cache]"
            cached["router_info"] = router_info
            yield f"data: {json.dumps({'type': 'complete', 'data': cached})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Map intent to category if applicable
        intent_to_category = {"sports": "sports", "markets": "finance"}
        category = intent_to_category.get(clf["intent"], None)

        # Stream progress: retrieving evidence
        yield f"data: {json.dumps({'type': 'status', 'data': 'Retrieving evidence...'})}\n\n"
        
        # Retrieve evidence
        evidence = await retrieve_evidence(request.query, category, db_repo, window_hours=wh)
        remember_last_evidence(sid, evidence)

        # Stream sources
        sources: List[SourceInfo] = []
        for item in evidence:
            sources.append(SourceInfo(
                name=item.get("outlet", "Unknown"),
                url=item.get("url", ""),
                published_at=item.get("published_at")
            ))
        
        yield f"data: {json.dumps({'type': 'sources', 'data': [s.dict() for s in sources]})}\n\n"

        # Stream progress: generating summary
        yield f"data: {json.dumps({'type': 'status', 'data': 'Generating summary...'})}\n\n"

        # Summarize EN with citation gate
        en_res = await summarize_en(evidence)
        summary_en_raw = en_res.get("summary_en", "")
        clean_en = citation_gate(summary_en_raw, max_id=len(evidence))

        # Fallback bullets if gate empties summary
        if not clean_en:
            bullets = []
            for i, item in enumerate(evidence, start=1):
                title = item.get("title", "Untitled")
                bullets.append(f"- {title} [{i}]")
            clean_en = "\n".join(bullets)

        # Stream tokens progressively (simulate streaming)
        words = clean_en.split()
        streamed_answer = ""
        for i, word in enumerate(words):
            streamed_answer += word + " "
            if i % 3 == 0:  # Stream every 3 words
                yield f"data: {json.dumps({'type': 'token', 'delta': word + ' '})}\n\n"
                await asyncio.sleep(0.01)  # Small delay for streaming effect
        
        # Translate if requested
        answer_bn: Optional[str] = None
        if request.lang == "bn":
            yield f"data: {json.dumps({'type': 'status', 'data': 'Translating...'})}\n\n"
            bn_res = await translate_bn(clean_en)
            answer_bn = bn_res.get("summary_bn", None)

        # Confidence heuristic
        from packages.util.normalize import extract_domain
        domains = {extract_domain(s.url) for s in sources if s.url}
        distinct_domains = len(domains)
        disagreement = bool(en_res.get("disagreement", False))
        # Avg recency
        def _hours_old(p):
            try:
                if not p:
                    return 1e6
                from datetime import datetime
                return (datetime.now(timezone.utc) - datetime.fromisoformat(str(p).replace('Z', '+00:00'))).total_seconds() / 3600.0
            except Exception:
                return 1e6
        avg_hours = 1e6
        try:
            vals = [
                _hours_old(s.published_at) for s in sources if s.published_at
            ]
            if vals:
                avg_hours = sum(vals) / len(vals)
        except Exception:
            pass

        if (not disagreement) and distinct_domains >= 3 and avg_hours <= 24:
            conf = 0.85
        elif distinct_domains >= 2 and avg_hours <= 72:
            conf = 0.55
        else:
            conf = 0.25

        end_ts = datetime.now(timezone.utc)
        latency_ms = int((end_ts - start_ts).total_seconds() * 1000)

        # For compatibility with the web app, always place the selected-language text in answer_bn
        answer_for_ui = clean_en if request.lang == "en" else (answer_bn or clean_en)

        payload = {
            "answer_bn": answer_for_ui,
            "answer_en": clean_en,
            "sources": [s.dict() for s in sources],
            "metrics": {
                "latency_ms": latency_ms,
                "source_count": len(sources),
                "updated_ct": end_ts.isoformat(),
                "intent": clf["intent"],
                "confidence": conf,
            },
            "flags": {
                "single_source": bool(en_res.get("single_source", False)),
                "disagreement": disagreement,
            },
            "router_info": f"Routed to: News ({clf['confidence']:.2f})",
        }

        # Log the query and response to database
        try:
            source_article_ids = [s.get("url") for s in payload.get("sources", []) if s.get("url")]
            log_query(
                question=request.query,
                answer=payload.get("answer_en", ""),
                source_article_ids=source_article_ids,
                response_time_ms=latency_ms
            )
        except Exception as e:
            print(f"Warning: Failed to log query to database: {e}")
        
        # Cache the payload
        cache_util.set(cache_key, payload)

        # Stream final complete response
        yield f"data: {json.dumps({'type': 'complete', 'data': payload})}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        # Stream error
        error_data = {
            "type": "error",
            "data": {
                "message": "সেবায় সাময়িক সমস্যা হয়েছে।",
                "error": str(e)
            }
        }
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"

@app.post("/ask/stream")
async def ask_stream(request: AskRequest, http_request: Request):
    """
    Streaming version of the /ask endpoint using Server-Sent Events (SSE)
    """
    return StreamingResponse(
        generate_stream(request, http_request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "KhoborAgent API",
        "version": "2.0.0",
        "description": "Multi-intent query API supporting news, weather, markets, sports, and lookup",
        "intents": ["news", "weather", "markets", "sports", "lookup"],
        "endpoints": {
            "POST /ask": "Submit query and get intent-routed response",
            "GET /healthz": "Health check endpoint",
            "GET /": "This information endpoint"
        },
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)