from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timezone
import sys
import os
import json
import asyncio
import uuid
from pathlib import Path

# Add packages and services to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from packages.router.intent import classify
from packages.db import repo as db_repo
from packages.db.repo import init_db, get_recent_articles, search_articles_by_keyword, log_query, search_vectors, reset_embedding_index
from services.ingest.enhanced_scheduler import start_enhanced_scheduler, enhanced_ingest_cycle
from packages.db.feed_health import get_feed_health_metrics, disable_unhealthy_feeds
from packages.handlers import weather, markets, sports, lookup, news
from packages.util import cache as cache_util
from packages.config.embedding import config as embedding_config
from packages.config.model_tracking import model_tracker, ensure_model_consistency
from packages.util.cache import get_async, set_async, check_negative_cache, cache_negative_result
from packages.util.memory import (
    derive_session_id,
    remember_preferred_lang,
    remember_last_query,
    remember_last_evidence,
)
from packages.nlp.retrieve import retrieve_evidence
from packages.nlp.enhanced_retrieve import enhanced_retrieve_evidence
from packages.nlp.story_retrieval import retrieve_story_context
from packages.nlp.window_analyzer import should_filter_by_region
from packages.nlp.hybrid_retrieve import hybrid_retrieve_with_guardrails
from packages.handlers.insufficient_context import insufficient_context_handler
from packages.router.tool_routing import volatile_router, ToolType
from packages.llm.openai_client import summarize_en, summarize_bn_first, summarize_story_context, summarize_breaking_news, translate_bn
from packages.llm.conversational_client import conversational_client
from packages.language.manager import language_manager, LanguageState
from packages.nlp.language_aware_retrieve import language_aware_retrieve
from packages.nlp.citation_gate_v2 import advanced_citation_gate, create_polite_refusal
from packages.observability import get_logger, request_context
from packages.util.rate_limiter import api_manager

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
    window_hours: Optional[int] = Field(default=None, description="Time window for news search (auto-detected if not provided)")
    mode: Optional[Literal['brief', 'deep']] = Field(default="brief", description="Answer depth")
    session_id: Optional[str] = Field(default=None, description="Client-provided session id")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID for memory continuity")
    region: Optional[str] = Field(default=None, description="Regional filter (auto-detected if not provided)")
    stream: Optional[bool] = Field(default=False, description="Stream response")

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
    conversation_id: Optional[str] = None
    memory_context: Optional[Dict[str, Any]] = None

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
        "service": "KhoborAgent API",
        "embedding": embedding_config.model_info()
    }

@app.get("/admin/embedding/active")
async def admin_embedding_active():
    """Return active embedding model and dimension (single source of truth)."""
    info = embedding_config.model_info()
    return {
        "status": "ok",
        "model_name": info["model_name"],
        "dimension": info["dimension"],
        "supported_models": info["supported_models"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.on_event("startup")
async def on_startup():
    """Initialize database and start ingest scheduler in development."""
    try:
        # Initialize DB first; this will hard-block if vectors are incompatible
        init_db()

        # Check model consistency to prevent mixed-version vectors
        print("[startup] Checking embedding model consistency...")
        is_consistent, status_info = model_tracker.check_model_consistency()
        if not is_consistent:
            print(f"[startup] ❌ Model inconsistency detected: {status_info['reason']}")
            print("[startup] 🔄 Reindex required. Use /admin/embedding/force-reindex or scripts/reembed_articles.py")
        else:
            print(f"[startup] ✅ Model consistency verified: {status_info['current_model']}")
        
        env = os.getenv("ENV", "dev")
        if env == "dev":
            start_enhanced_scheduler()
            print("[startup] Ingest scheduler started (dev)")
        else:
            print("[startup] Production mode: ingest scheduler not started")
    except SystemExit as e:
        # Propagate hard block from embedding validation
        raise
    except Exception as e:
        print(f"[startup] init error: {e}")

@app.get("/admin/ingest/run")
async def admin_ingest_run():
    """Force one ingest cycle (dev/admin). Returns counts."""
    try:
        feeds_ct, embedded_ct = await enhanced_ingest_cycle()
        return {
            "status": "ok",
            "feeds": feeds_ct,
            "embedded": embedded_ct,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/admin/feeds/health")
async def admin_feed_health():
    """Get feed health status for all feeds."""
    try:
        metrics = get_feed_health_metrics()
        return {
            "status": "ok",
            "feeds": [
                {
                    "name": m.feed_name,
                    "url": m.feed_url,
                    "health_score": m.health_score,
                    "uptime_percentage": m.uptime_percentage,
                    "avg_latency_ms": m.avg_latency_ms,
                    "hours_since_success": m.hours_since_success,
                    "success_count": m.success_count,
                    "error_count": m.error_count,
                    "is_enabled": m.is_enabled,
                    "error_details": m.error_details
                }
                for m in metrics
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/admin/feeds/cleanup")
async def admin_feed_cleanup():
    """Disable unhealthy feeds manually."""
    try:
        disabled = disable_unhealthy_feeds()
        return {
            "status": "ok",
            "disabled_count": len(disabled),
            "disabled_feeds": disabled,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/admin/cache/stats")
async def admin_cache_stats():
    """Get Redis cache statistics."""
    try:
        from packages.util.redis_cache import get_cache
        cache = await get_cache()
        stats = await cache.get_cache_stats()
        return {
            "status": "ok",
            "cache_stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/admin/embedding/reset")
async def admin_reset_embedding_index():
    """Reset the embedding index with current model."""
    try:
        result = reset_embedding_index()
        return {
            "status": "ok",
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/admin/embedding/model-consistency")
async def admin_check_model_consistency():
    """Check embedding model consistency and safety status."""
    try:
        model_info = model_tracker.get_model_info()
        return {
            "status": "ok",
            "model_info": model_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/admin/embedding/force-reindex")
async def admin_force_model_reindex():
    """Force reindex due to model changes (with safety checks)."""
    try:
        is_consistent, status_info = model_tracker.check_model_consistency()
        
        if is_consistent:
            return {
                "status": "skipped",
                "reason": "Model is already consistent, no reindex needed",
                "model_info": status_info,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Perform forced reindex
        reindex_result = model_tracker.force_reindex_and_update()
        
        return {
            "status": "ok",
            "reindex_result": reindex_result,
            "model_changes": status_info.get("changes", []),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/admin/api-manager/stats")
async def admin_api_manager_stats():
    """Get rate limiting and caching statistics for external APIs."""
    try:
        stats = api_manager.get_stats()
        return {
            "status": "ok",
            "api_manager_stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/admin/api-manager/cleanup")
async def admin_api_manager_cleanup():
    """Clean up expired cache entries in the API manager."""
    try:
        cleanup_result = await api_manager.cleanup()
        return {
            "status": "ok",
            "cleanup_result": cleanup_result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/admin/embedding/info")
async def admin_embedding_info():
    """Get detailed embedding configuration and statistics."""
    try:
        # Get vector statistics
        with db_repo.session_scope() as session:
            vector_stats = session.execute(db_repo.text("""
                SELECT 
                    COUNT(*) as total_vectors,
                    COUNT(DISTINCT model_name) as unique_models,
                    COUNT(DISTINCT model_dimension) as unique_dimensions,
                    model_name,
                    model_dimension,
                    COUNT(*) as count
                FROM article_vectors 
                GROUP BY model_name, model_dimension
                ORDER BY count DESC
            """)).fetchall()
            
            total_articles = session.execute(
                db_repo.text("SELECT COUNT(*) FROM articles")
            ).scalar() or 0
            
        return {
            "status": "ok",
            "current_config": embedding_config.model_info(),
            "database_stats": {
                "total_articles": total_articles,
                "vector_distribution": [
                    {
                        "model_name": row.model_name,
                        "model_dimension": row.model_dimension, 
                        "count": row.count
                    } for row in vector_stats
                ],
                "total_vectors": sum(row.count for row in vector_stats),
                "unique_models": len(set(row.model_name for row in vector_stats if row.model_name)),
                "unique_dimensions": len(set(row.model_dimension for row in vector_stats if row.model_dimension))
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
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
async def ask(request: AskRequest, http_request: Request, response: Response):
    """
    Process queries using intent classification and specialized handlers
    
    Flow:
    1. Classify query intent and extract slots
    2. Resolve appropriate handler for intent
    3. Call handler with query, slots, and language
    4. Return standardized response with metrics
    """
    # Generate or use provided request ID
    request_id = http_request.headers.get("x-request-id") or str(uuid.uuid4())
    response.headers["X-Request-Id"] = request_id
    
    # Initialize observability logger with request context
    logger = get_logger()
    start_time = datetime.now(timezone.utc)
    
    with request_context(request_id, request.query, "ask"):
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
                
                # Log non-news intent metrics
                end_time = datetime.now(timezone.utc)
                non_news_latency_ms = (end_time - start_time).total_seconds() * 1000
                
                logger.log_per_answer_metrics(
                    conversation_id=request.conversation_id,
                    language=request.lang,
                    retrieval_scores=[],  # Non-news intents don't use retrieval
                    k_hits=len(sources),
                    tool_calls=[{"tool": clf["intent"], "success": True, "duration_ms": non_news_latency_ms}],
                    token_usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                    total_latency_ms=non_news_latency_ms,
                    answer_type="answer",
                    refusal_reason=None,
                    gate_triggered=None,
                    intent=clf["intent"],
                    confidence=clf["confidence"],
                    has_cache_hit=False,
                    region=None
                )
                
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

            # Determine region filter
            region = request.region or ("BD" if should_filter_by_region(request.query) else None)

            # Map intent to category if applicable (compute before use)
            intent_to_category = {"sports": "sports", "markets": "finance"}
            category = intent_to_category.get(clf["intent"], None)

            # Smart story retrieval with window analysis and guardrails
            story_context = await retrieve_story_context(
                request.query,
                category,
                db_repo,
                user_window_hours=request.window_hours,
                session_id=sid
            )
            
            # Extract context
            window_analysis = story_context['window_analysis']
            retrieval_strategy = story_context['retrieval_strategy']
            recent_evidence = story_context['recent_evidence']
            background_evidence = story_context['background_evidence']
            story_id = story_context['story_id']
            
            # Check Redis cache with story context
            cached_data, is_cache_hit = await get_async(
                mode="news",
                query=request.query,
                lang=request.lang,
                window_hours=window_analysis['window_hours'],
                region=region,
                story_id=story_id
            )
            
            if cached_data is not None:
                # Add cache header and router info
                response.headers["X-Cache"] = "HIT"
                router_info = f"Routed to: News ({clf['confidence']:.2f}) [cache:{retrieval_strategy}]"
                cached_data["router_info"] = router_info
                
                # Log cached response metrics
                end_time = datetime.now(timezone.utc)
                cache_latency_ms = (end_time - start_time).total_seconds() * 1000
                
                logger.log_per_answer_metrics(
                    conversation_id=request.conversation_id,
                    language=request.lang,
                    retrieval_scores=[],  # No retrieval for cached responses
                    k_hits=len(cached_data.get("sources", [])),
                    tool_calls=[],
                    token_usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                    total_latency_ms=cache_latency_ms,
                    answer_type="answer",
                    refusal_reason=None,
                    gate_triggered=None,
                    intent=clf["intent"],
                    confidence=clf["confidence"],
                    has_cache_hit=True,
                    region=region
                )
                
                return AskResponse(**cached_data)

            # Guardrails and routing using hybrid retrieval
            guardrail_info = await hybrid_retrieve_with_guardrails(
                request.query, category, db_repo, lang=request.lang, intent="news",
                window_hours=window_analysis['window_hours']
            )

            # Route to external tool for volatile facts (stocks, sports, etc.)
            if guardrail_info['routing'].get('route_to_tool') and guardrail_info['routing'].get('tool'):
                tool_name = guardrail_info['routing']['tool']
                handler_func = None
                tool_type = None
                if tool_name == 'markets':
                    from packages.handlers import markets as markets_handler
                    handler_func = markets_handler.handle
                    tool_type = ToolType.MARKETS
                elif tool_name == 'sports':
                    from packages.handlers import sports as sports_handler
                    handler_func = sports_handler.handle
                    tool_type = ToolType.SPORTS

                if handler_func and tool_type:
                    tool_result = await volatile_router.route_to_tool(
                        query=request.query,
                        tool_type=tool_type,
                        handler_func=handler_func,
                        lang=request.lang,
                        slots=clf.get('slots', {})
                    )

                    if tool_result.success and isinstance(tool_result.data, dict):
                        tr = tool_result.data
                        sources = [SourceInfo(
                            name=s.get('name', 'Unknown'),
                            url=s.get('url', ''),
                            published_at=s.get('published_at')
                        ) for s in tr.get('sources', [])]
                        return AskResponse(
                            answer_bn=tr.get('answer_bn', ''),
                            answer_en=tr.get('answer_en', tr.get('answer_bn', '')),
                            sources=sources,
                            metrics={**tr.get('metrics', {}), 'intent': tool_name},
                            flags=tr.get('flags', {}),
                            router_info=f"Routed to: {tool_name.title()} (volatile)"
                        )
                    else:
                        failure = volatile_router.get_failure_message(tool_result, request.query, request.lang)
                        return AskResponse(
                            answer_bn=failure['message_bn'] if request.lang == 'bn' else failure['message_en'],
                            answer_en=failure['message_en'],
                            sources=[],
                            metrics={
                                'intent': tool_name,
                                'confidence': 0.0,
                                'latency_ms': 0,
                                'source_count': 0,
                                'updated_ct': datetime.now(timezone.utc).isoformat(),
                                'tool_execution_time_ms': tool_result.execution_time_ms
                            },
                            flags={'single_source': True, 'disagreement': False, 'tool_failure': True},
                            router_info=f"Routed to: {tool_name.title()} (error)"
                        )

            # If context is insufficient, return structured refusal per guardrails
            if not guardrail_info['quality']['sufficient']:
                insufficient = insufficient_context_handler.generate_insufficient_context_response(
                    query=request.query,
                    quality_assessment=guardrail_info['quality'],
                    routing_info=guardrail_info['routing'],
                    lang=request.lang,
                    intent="news"
                )
                # Build controlled refusal AskResponse
                return AskResponse(
                    answer_bn=insufficient['message'] if request.lang == 'bn' else insufficient['reason']['en'],
                    answer_en=insufficient['reason']['en'],
                    sources=[],
                    metrics={
                        "intent": "news",
                        "confidence": 0.0,
                        "latency_ms": int((datetime.now(timezone.utc) - start_ts).total_seconds() * 1000),
                        "source_count": 0,
                        "updated_ct": datetime.now(timezone.utc).isoformat(),
                    },
                    flags={"single_source": False, "disagreement": False},
                    router_info=f"Routed to: News (insufficient_context)"
                )

            # Remember evidence for session continuity
            all_evidence = recent_evidence + background_evidence
            remember_last_evidence(sid, all_evidence)

            # Use conversational client for memory integration
            try:
                response_data, conv_id = await conversational_client.generate_with_memory(
                    query=request.query,
                    evidence=all_evidence,
                    conversation_id=request.conversation_id,
                    lang=request.lang,
                    intent="news",
                    stream=False
                )
                
                answer_bn = response_data.get("answer_bn", "")
                answer_en = response_data.get("answer_en", answer_bn)
                
                # Use sources from conversational client
                conv_sources = response_data.get("sources", [])
                sources: List[SourceInfo] = []
                for source in conv_sources:
                    sources.append(SourceInfo(
                        name=source.get("name", "Unknown"),
                        url=source.get("url", ""),
                        published_at=source.get("published_at")
                    ))
                
                # Apply advanced citation filtering for safety
                gate_result = advanced_citation_gate(answer_bn, max_id=len(all_evidence))
                
                if gate_result['action'] == 'refuse':
                    answer_bn = create_polite_refusal(gate_result['reason'], lang="bn")
                    answer_en = create_polite_refusal(gate_result['reason'], lang="en")
                    single_source_flag = True
                    disagreement_flag = False
                else:
                    answer_bn = gate_result['text']
                    # Keep original English answer from conversational client
                    single_source_flag = len(conv_sources) <= 1
                    disagreement_flag = False
                # Ensure clean_en is always defined for payload construction
                clean_en = answer_en or ""
                
            except Exception as e:
                print(f"[CONV] Error with conversational client, falling back: {e}")
                # Fallback to original Bangla-first summarization
                bn_res = await summarize_bn_first(all_evidence)
                summary_bn_raw = bn_res.get("summary_bn", "")
                
                # Apply advanced citation filtering (use all evidence for citation count)
                total_evidence_count = len(recent_evidence) + len(background_evidence)
                gate_result = advanced_citation_gate(summary_bn_raw, max_id=total_evidence_count)
                
                # Handle refusal cases with polite responses
                if gate_result['action'] == 'refuse':
                    answer_bn = create_polite_refusal(gate_result['reason'], lang="bn")
                    answer_en = create_polite_refusal(gate_result['reason'], lang="en")
                    # Set flags to indicate this is a refusal with explanation
                    single_source_flag = True
                    disagreement_flag = False
                else:
                    answer_bn = gate_result['text']
                    answer_en = answer_bn  # Placeholder - will be handled by translate endpoint
                    single_source_flag = bool(bn_res.get("single_source", False))
                    disagreement_flag = bool(bn_res.get("disagreement", False))

                # Build sources list from all evidence (fallback case)
                sources: List[SourceInfo] = []
                for item in all_evidence:
                    sources.append(SourceInfo(
                        name=item.get("outlet", "Unknown"),
                        url=item.get("url", ""),
                        published_at=item.get("published_at")
                    ))
                conv_id = None  # No conversation ID in fallback

            # Confidence heuristic
            from packages.util.normalize import extract_domain
            domains = {extract_domain(s.url) for s in sources if s.url}
            distinct_domains = len(domains)
            disagreement = disagreement_flag
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
            answer_for_ui = (clean_en if request.lang == "en" else (answer_bn or clean_en))

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
                    "single_source": bool(single_source_flag),
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
            
            # Cache the payload with Redis
            response.headers["X-Cache"] = "MISS"
            is_breaking = window_analysis.get('is_immediate', False)
            await set_async(
                mode="news",
                query=request.query,
                value=payload,
                lang=request.lang,
                window_hours=window_analysis['window_hours'],
                region=region,
                story_id=story_id,
                is_breaking=is_breaking
            )

            # Log comprehensive per-answer metrics for observability
            end_time = datetime.now(timezone.utc)
            total_latency_ms = (end_time - start_time).total_seconds() * 1000
            
            # Extract retrieval scores from sources (optional, may be empty)
            retrieval_scores = []
            
            # Determine answer type
            gate_triggered = gate_result.get('reason') if 'gate_result' in locals() and gate_result.get('action') == 'refuse' else None
            answer_type = "refusal" if gate_triggered else "answer"
            
            # Omit token usage estimation to avoid misleading numbers
            token_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            
            # Mock tool calls (would be tracked from actual tool usage)
            tool_calls = []
            if clf["intent"] != "news":
                tool_calls.append({
                    "tool": clf["intent"],
                    "success": True,
                    "duration_ms": latency_ms
                })
            
            logger.log_per_answer_metrics(
                conversation_id=request.conversation_id,
                language=request.lang,
                retrieval_scores=retrieval_scores,
                k_hits=len(payload.get("sources", [])),
                tool_calls=tool_calls,
                token_usage=token_usage,
                total_latency_ms=total_latency_ms,
                answer_type=answer_type,
                refusal_reason=gate_triggered,
                gate_triggered=gate_triggered,
                # Additional context
                intent=clf["intent"],
                confidence=clf["confidence"],
                has_cache_hit=False,
                region=region if 'region' in locals() else None
            )

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
                answer_en="Service temporarily unavailable.",
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
    Generate SSE stream for the /ask/stream endpoint with enhanced phase tracking
    Maintains backward compatibility while adding new phase events
    """
    try:
        # Step 1: Classify intent
        clf = classify(request.query)
        
        # Maintain backward compatibility - emit intent classification
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

        # News intent: run hybrid retrieval + summarization with enhanced streaming
        start_ts = datetime.now(timezone.utc)

        # Derive session id
        client_ip = http_request.client.host if http_request.client else ""
        user_agent = http_request.headers.get("user-agent", "")
        sid = request.session_id or derive_session_id(client_ip, user_agent)
        remember_preferred_lang(sid, request.lang)
        remember_last_query(sid, request.query)

        # Check Redis cache for streaming endpoint
        wh = int(request.window_hours or 72)
        region = request.region or ("BD" if should_filter_by_region(request.query) else None)
        
        cached_data, is_cache_hit = await get_async(
            mode="news",
            query=request.query,
            lang=request.lang,
            window_hours=wh,
            region=region
        )
        
        if cached_data is not None:
            # Stream cached payload (can't set headers within generator)
            router_info = f"Routed to: News ({clf['confidence']:.2f}) [cache]"
            cached_data["router_info"] = router_info
            yield f"data: {json.dumps({'type': 'complete', 'data': cached_data})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Map intent to category if applicable
        intent_to_category = {"sports": "sports", "markets": "finance"}
        category = intent_to_category.get(clf["intent"], None)

        # Phase 1: Fetch - Start
        yield f"data: {json.dumps({'type': 'phase', 'data': {'stage': 'fetch', 'status': 'start', 'meta': {'providers': ['rss', 'database'], 'count': 0}}})}\n\n"
        
        # Maintain backward compatibility
        yield f"data: {json.dumps({'type': 'status', 'data': 'Retrieving evidence...'})}\n\n"
        
        # Retrieve evidence with progress tracking
        evidence = await enhanced_retrieve_evidence(request.query, category, db_repo, window_hours=wh)
        remember_last_evidence(sid, evidence)
        
        # Phase 1: Fetch - Done
        yield f"data: {json.dumps({'type': 'phase', 'data': {'stage': 'fetch', 'status': 'done', 'meta': {'providers': ['rss', 'database'], 'count': len(evidence)}}})}\n\n"
        
        # Phase 2: Dedupe - Start
        yield f"data: {json.dumps({'type': 'phase', 'data': {'stage': 'dedupe', 'status': 'start', 'meta': {'clusters': 0}}})}\n\n"
        
        # Analyze domain clustering (evidence is already deduplicated)
        from packages.util.normalize import extract_domain
        domains = {extract_domain(item.get("url", "")) for item in evidence}
        
        # Phase 2: Dedupe - Done
        yield f"data: {json.dumps({'type': 'phase', 'data': {'stage': 'dedupe', 'status': 'done', 'meta': {'clusters': len(domains)}}})}\n\n"
        
        # Phase 3: Rerank - Start
        yield f"data: {json.dumps({'type': 'phase', 'data': {'stage': 'rerank', 'status': 'start', 'meta': {'kept': 0}}})}\n\n"
        
        # Evidence is already ranked by retrieve_evidence
        # Phase 3: Rerank - Done
        yield f"data: {json.dumps({'type': 'phase', 'data': {'stage': 'rerank', 'status': 'done', 'meta': {'kept': len(evidence)}}})}\n\n"

        # Build sources for backward compatibility
        sources: List[SourceInfo] = []
        for item in evidence:
            sources.append(SourceInfo(
                name=item.get("outlet", "Unknown"),
                url=item.get("url", ""),
                published_at=item.get("published_at")
            ))
        
        # Maintain backward compatibility
        yield f"data: {json.dumps({'type': 'sources', 'data': [s.dict() for s in sources]})}\n\n"

        # Phase 4: Summarize - Start
        yield f"data: {json.dumps({'type': 'phase', 'data': {'stage': 'summarize', 'status': 'start', 'meta': {}}})}\n\n"
        
        # Maintain backward compatibility
        yield f"data: {json.dumps({'type': 'status', 'data': 'Generating summary...'})}\n\n"

        # Bangla-first summarization with advanced citation gate
        bn_res = await summarize_bn_first(evidence)
        summary_bn_raw = bn_res.get("summary_bn", "")
        
        # Apply advanced citation filtering
        gate_result = advanced_citation_gate(summary_bn_raw, max_id=len(evidence))
        
        # Handle refusal cases with polite responses
        if gate_result['action'] == 'refuse':
            answer_bn = create_polite_refusal(gate_result['reason'], lang="bn")
            clean_en = create_polite_refusal(gate_result['reason'], lang="en")
            # Set flags to indicate this is a refusal with explanation
            bn_res['single_source'] = True
            bn_res['disagreement'] = False
        else:
            answer_bn = gate_result['text']
            # For streaming, we'll stream Bangla by default and translate if needed
            clean_en = answer_bn  # Placeholder

        # Stream tokens progressively with enhanced chunking (stream Bangla)
        words = answer_bn.split()
        current_chunk = ""
        for i, word in enumerate(words):
            current_chunk += word + " "
            if i % 3 == 0 or i == len(words) - 1:  # Stream every 3 words or at the end
                chunk_text = current_chunk.strip()
                if chunk_text:
                    # New chunk event
                    yield f"data: {json.dumps({'type': 'chunk', 'delta': chunk_text})}\n\n"
                    # Maintain backward compatibility with token events
                    yield f"data: {json.dumps({'type': 'token', 'delta': chunk_text + ' '})}\n\n"
                current_chunk = ""
                await asyncio.sleep(0.01)  # Small delay for streaming effect
        
        # answer_bn is already set above from Bangla-first summarization
        # No need for additional translation step since we generate in Bangla first

        # Confidence heuristic
        domains = {extract_domain(s.url) for s in sources if s.url}
        distinct_domains = len(domains)
        disagreement = bool(bn_res.get("disagreement", False))
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
                "single_source": bool(bn_res.get("single_source", False)),
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
        
        # Cache the payload with Redis (headers set in outer response)
        await set_async(
            mode="news",
            query=request.query,
            value=payload,
            lang=request.lang,
            window_hours=wh,
            region=region
        )

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
    Enhanced with phase tracking and request ID support
    """
    # Generate or use provided request ID
    request_id = http_request.headers.get("x-request-id") or str(uuid.uuid4())
    
    return StreamingResponse(
        generate_stream(request, http_request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-Request-Id",
            "X-Request-Id": request_id,
        }
    )

# Chat alias endpoints (optional - /ask remains authoritative)
@app.post("/chat", response_model=AskResponse)
async def chat(request: AskRequest, http_request: Request, response: Response):
    """
    Alias for /ask endpoint for chat-style interactions
    Maintains compatibility with existing clients
    """
    return await ask(request, http_request, response)

@app.post("/chat/stream")
async def chat_stream(request: AskRequest, http_request: Request):
    """
    Alias for /ask/stream endpoint for chat-style streaming
    Maintains compatibility with existing clients
    """
    return await ask_stream(request, http_request)

@app.post("/ask/conversation", response_model=AskResponse)
async def ask_with_conversation(request: AskRequest, http_request: Request, response: Response):
    """
    Process queries with conversation memory for multi-turn interactions
    """
    request_id = http_request.headers.get("x-request-id") or str(uuid.uuid4())
    response.headers["X-Request-Id"] = request_id
    
    try:
        # Step 1: Classify intent
        clf = classify(request.query)
        
        print(f"[conversation] intent={clf['intent']} conf={clf['confidence']:.2f}")
        
        # Only news queries support conversation memory for now
        if clf["intent"] != "news":
            # Fall back to regular ask endpoint for non-news
            return await ask(request, http_request, response)

        # News intent: Use conversational client
        start_ts = datetime.now(timezone.utc)

        # Get evidence first 
        client_ip = http_request.client.host if http_request.client else ""
        user_agent = http_request.headers.get("user-agent", "")
        sid = request.session_id or derive_session_id(client_ip, user_agent)
        remember_preferred_lang(sid, request.lang)
        remember_last_query(sid, request.query)

        # Smart story retrieval
        story_context = await retrieve_story_context(
            request.query, 
            None,  # category not needed for news
            db_repo, 
            user_window_hours=request.window_hours,
            session_id=sid
        )
        
        all_evidence = story_context['recent_evidence'] + story_context['background_evidence']
        remember_last_evidence(sid, all_evidence)

        # Use conversational client for memory integration
        response_data, conv_id = await conversational_client.generate_with_memory(
            query=request.query,
            evidence=all_evidence,
            conversation_id=request.conversation_id,
            lang=request.lang,
            intent="news",
            stream=request.stream or False
        )
        
        answer_bn = response_data.get("answer_bn", "")
        answer_en = response_data.get("answer_en", answer_bn)
        
        # Use sources from conversational client
        conv_sources = response_data.get("sources", [])
        sources: List[SourceInfo] = []
        for source in conv_sources:
            sources.append(SourceInfo(
                name=source.get("name", "Unknown"),
                url=source.get("url", ""),
                published_at=source.get("published_at")
            ))
        
        end_ts = datetime.now(timezone.utc)
        latency_ms = int((end_ts - start_ts).total_seconds() * 1000)

        # For compatibility with the web app, always place the selected-language text in answer_bn
        answer_for_ui = answer_en if request.lang == "en" else (answer_bn or answer_en)

        payload = {
            "answer_bn": answer_for_ui,
            "answer_en": answer_en,
            "sources": [s.dict() for s in sources],
            "metrics": {
                "latency_ms": latency_ms,
                "source_count": len(sources),
                "updated_ct": end_ts.isoformat(),
                "intent": clf["intent"],
                "confidence": clf["confidence"],
            },
            "flags": {
                "single_source": len(conv_sources) <= 1,
                "disagreement": False,
            },
            "router_info": f"Routed to: News+Memory ({clf['confidence']:.2f})",
            "conversation_id": conv_id,
            "memory_context": response_data.get("memory_context")
        }

        return AskResponse(**payload)
        
    except Exception as e:
        print(f"Error in conversation endpoint: {e}")
        # Fall back to regular ask endpoint
        return await ask(request, http_request, response)


@app.get("/conversation/{conversation_id}/history")
async def get_conversation_history(conversation_id: str, limit: int = 20):
    """Get conversation history for a given conversation ID."""
    try:
        history = await conversational_client.get_conversation_history(
            conversation_id=conversation_id,
            limit=limit
        )
        
        if not history:
            return {"status": "error", "error": "Conversation not found"}
            
        return {
            "status": "ok",
            "conversation": history,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/admin/conversations/cleanup")
async def admin_cleanup_conversations():
    """Clean up old conversations."""
    try:
        stats = await conversational_client.cleanup_old_conversations()
        return {
            "status": "ok",
            "cleanup_stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/conversation/{conversation_id}/language/toggle")
async def toggle_conversation_language(conversation_id: str):
    """Toggle language for a specific conversation (BN↔EN)."""
    try:
        # Toggle in language manager
        new_language = language_manager.toggle_conversation_language(conversation_id)
        
        # Get conversation thread and update its language state
        thread = await conversational_client.conversation_manager.persistence.load_conversation(conversation_id)
        if thread:
            changed = thread.toggle_language(new_language)
            if changed:
                # Save updated thread
                await conversational_client.conversation_manager.persistence.save_conversation(thread)
        
        ui_strings = language_manager.get_ui_strings(new_language)
        
        return {
            "status": "ok",
            "conversation_id": conversation_id,
            "new_language": new_language,
            "message": ui_strings["language_toggled"],
            "ui_strings": ui_strings,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/conversation/{conversation_id}/language")
async def get_conversation_language(conversation_id: str):
    """Get current language for a conversation."""
    try:
        # Get language state
        language_state = language_manager.get_language_state(conversation_id=conversation_id)
        
        # Get conversation thread for additional context
        thread = await conversational_client.conversation_manager.persistence.load_conversation(conversation_id)
        thread_language = None
        language_history = []
        
        if thread:
            thread_language = thread.get_current_language()
            language_history = thread.user_context.get("language_history", [])
        
        return {
            "status": "ok",
            "conversation_id": conversation_id,
            "current_language": language_state.ui_language,
            "thread_language": thread_language,
            "global_default": language_manager.global_language,
            "language_history": language_history[-5:],  # Last 5 changes
            "ui_strings": language_manager.get_ui_strings(language_state.ui_language),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


class LanguageRequest(BaseModel):
    language: Literal['bn', 'en'] = Field(..., description="Language to set (bn/en)")

@app.post("/settings/language/global")
async def set_global_language(request: LanguageRequest):
    """Set global default language."""
    try:
        language_manager.set_global_language(request.language)
        ui_strings = language_manager.get_ui_strings(request.language)
        
        return {
            "status": "ok",
            "global_language": request.language,
            "ui_strings": ui_strings,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/settings/language/global") 
async def get_global_language():
    """Get current global language setting."""
    try:
        global_lang = language_manager.global_language
        return {
            "status": "ok",
            "global_language": global_lang,
            "ui_strings": language_manager.get_ui_strings(global_lang),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/conversation/{conversation_id}/regenerate")
async def regenerate_last_message(conversation_id: str, language: Optional[str] = None):
    """
    Regenerate the last assistant message in the current or specified language.
    
    This endpoint allows users to get a fresh response in their current language
    without needing to re-ask the question.
    """
    try:
        # Get conversation thread
        thread = await conversational_client.conversation_manager.persistence.load_conversation(conversation_id)
        if not thread or not thread.turns:
            return {"status": "error", "error": "Conversation not found or empty"}
        
        # Get the last turn
        last_turn = thread.turns[-1]
        
        # Determine target language
        if language and language in ['bn', 'en']:
            target_language = language
        else:
            # Use conversation's current language
            target_language = thread.get_current_language()
        
        # Get language state
        language_state = language_manager.get_language_state(
            conversation_id=conversation_id,
            explicit_lang=target_language,
            input_text=last_turn.user_message
        )
        
        # Recreate the evidence from the last turn's sources
        evidence = []
        for source in last_turn.sources:
            evidence.append({
                "outlet": source.get("name", "Unknown"),
                "title": last_turn.user_message,  # Use original query
                "url": source.get("url", ""),
                "published_at": source.get("published_at", ""),
                "summary": f"Regenerating response for: {last_turn.user_message}"
            })
        
        # Generate new response using conversational client
        response_data, conv_id = await conversational_client.generate_with_memory(
            query=last_turn.user_message,
            evidence=evidence,
            conversation_id=conversation_id,
            lang=target_language,
            intent=last_turn.intent or "news",
            stream=False
        )
        
        ui_strings = language_manager.get_ui_strings(target_language)
        
        return {
            "status": "ok",
            "conversation_id": conversation_id,
            "original_message": last_turn.user_message,
            "regenerated_response": {
                "answer_bn": response_data.get("answer_bn", ""),
                "answer_en": response_data.get("answer_en", ""),
                "language": target_language,
                "sources": response_data.get("sources", []),
                "memory_context": response_data.get("memory_context", {})
            },
            "language_info": {
                "target_language": target_language,
                "conversation_language": thread.get_current_language(),
                "global_language": language_manager.global_language
            },
            "ui_strings": ui_strings,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        print(f"[REGENERATE] Error: {e}")
        return {"status": "error", "error": str(e)}


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "KhoborAgent API",
        "version": "2.0.0",
        "description": "Multi-intent query API supporting news, weather, markets, sports, and lookup",
        "intents": ["news", "weather", "markets", "sports", "lookup"],
        "endpoints": {
            "POST /ask": "Submit query and get intent-routed response (authoritative)",
            "POST /ask/stream": "Submit query and get streaming response with phases",
            "POST /ask/conversation": "Submit query with conversation memory for multi-turn interactions",
            "GET /conversation/{id}/history": "Get conversation history by ID",
            "GET /conversation/{id}/language": "Get current language for a conversation",
            "POST /conversation/{id}/language/toggle": "Toggle language for a conversation (BN↔EN)",
            "POST /conversation/{id}/regenerate": "Regenerate last message in current language",
            "GET /settings/language/global": "Get global default language setting",
            "POST /settings/language/global": "Set global default language setting",
            "POST /chat": "Alias for /ask endpoint",
            "POST /chat/stream": "Alias for /ask/stream endpoint", 
            "GET /api/articles": "Get recent articles from database",
            "GET /api/articles/search": "Search articles by keyword",
            "GET /api/articles/similar": "Find similar articles using vector search",
            "GET /admin/ingest/run": "Force RSS ingestion cycle (dev/admin)",
            "GET /admin/embedding/info": "Get embedding model configuration and statistics",
            "POST /admin/embedding/reset": "Reset embedding index with current model",
            "POST /admin/conversations/cleanup": "Clean up old conversations",
            "GET /healthz": "Health check endpoint with embedding info",
            "GET /": "This information endpoint"
        },
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)