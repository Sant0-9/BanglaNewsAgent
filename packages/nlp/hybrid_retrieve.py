"""
Hybrid Retrieval System with Guardrails

Implements BM25 + Vector search hybrid ranking with context gating,
language filtering, and tool routing for volatile facts.
"""
import asyncio
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from rapidfuzz import fuzz

from packages.util.normalize import truncate_text, extract_domain
from packages.nlp.embed import embed_query


class RetrievalConfig:
    """Configuration for retrieval guardrails."""
    
    # Context gating thresholds
    MIN_HITS_THRESHOLD = 3           # Minimum number of hits required
    MIN_SCORE_THRESHOLD = 0.4        # Minimum best score threshold
    INSUFFICIENT_CONTEXT_THRESHOLD = 0.3  # Combined threshold for insufficient context
    
    # BM25 parameters
    BM25_TOP_N = 200                # Top N candidates from BM25
    VECTOR_TOP_M = 300              # Top M candidates from vector search
    FINAL_INTERLEAVE_K = 12         # Final interleaved results
    
    # Language filtering
    LANGUAGE_CONFIDENCE_THRESHOLD = 0.7
    
    # Citation requirements
    CITATIONS_REQUIRED_INTENTS = {"news", "markets", "sports"}
    
    # Volatile facts patterns (must route to tools)
    VOLATILE_PATTERNS = [
        # Stock prices and financial
        r'\b(stock|share|price|trading|nasdaq|nyse|market cap)\b',
        r'\b(nvidia|apple|tesla|microsoft|amazon|google|meta)\s+(stock|share|price)\b',
        r'\b(bitcoin|ethereum|crypto|btc|eth)\s+(price|value)\b',
        
        # Sports scores and results  
        r'\b(score|result|match|game|final|won|lost|vs)\b',
        r'\b(last\s+(match|game)|today.*(match|game)|latest\s+(score|result))\b',
        
        # Exchange rates
        r'\b(exchange\s+rate|currency|usd|eur|gbp|jpy|cad)\b',
        r'\b(dollar|euro|pound|yen)\s+(rate|price|value)\b',
        
        # Time-sensitive queries
        r'\b(today|latest|current|now|recent|breaking)\b',
        r'\b(what.*(happen|occur)|latest\s+news)\b',
    ]


def detect_language(text: str) -> Dict[str, Union[str, float]]:
    """
    Simple language detection for Bangla vs English.
    Returns dict with 'language' and 'confidence'.
    """
    if not text:
        return {"language": "unknown", "confidence": 0.0}
    
    # Count Bangla Unicode characters
    bangla_chars = len(re.findall(r'[\u0980-\u09FF]', text))
    total_chars = len(re.findall(r'\S', text))  # Non-whitespace chars
    
    if total_chars == 0:
        return {"language": "unknown", "confidence": 0.0}
    
    bangla_ratio = bangla_chars / total_chars
    
    if bangla_ratio > 0.3:  # Significant Bangla content
        return {"language": "bn", "confidence": min(bangla_ratio * 2, 1.0)}
    elif bangla_ratio < 0.05:  # Minimal Bangla content
        return {"language": "en", "confidence": 1.0 - bangla_ratio}
    else:
        return {"language": "mixed", "confidence": 0.5}


def should_route_to_tool(query: str) -> Dict[str, Any]:
    """
    Determine if query should be routed to external tools for volatile facts.
    Returns dict with routing decision and recommended tool.
    """
    query_lower = query.lower()
    
    for pattern in RetrievalConfig.VOLATILE_PATTERNS:
        if re.search(pattern, query_lower):
            # Determine specific tool based on pattern
            if re.search(r'\b(stock|share|price|trading|market|bitcoin|crypto)\b', query_lower):
                return {
                    "route_to_tool": True,
                    "tool": "markets",
                    "reason": "Financial data query requires real-time tool",
                    "pattern_matched": pattern
                }
            elif re.search(r'\b(score|match|game|sport|final|won|lost)\b', query_lower):
                return {
                    "route_to_tool": True,
                    "tool": "sports",
                    "reason": "Sports query requires real-time tool", 
                    "pattern_matched": pattern
                }
            elif re.search(r'\b(exchange|currency|rate|dollar|euro)\b', query_lower):
                return {
                    "route_to_tool": True,
                    "tool": "markets", 
                    "reason": "Currency query requires real-time tool",
                    "pattern_matched": pattern
                }
            else:
                return {
                    "route_to_tool": True,
                    "tool": "news",
                    "reason": "Time-sensitive query may need fresh data",
                    "pattern_matched": pattern
                }
    
    return {
        "route_to_tool": False,
        "tool": None,
        "reason": "No volatile patterns detected",
        "pattern_matched": None
    }


def enhanced_bm25(query: str, text: str, boost_factors: Dict[str, float] = None) -> float:
    """
    Enhanced BM25-like scoring with configurable boost factors.
    """
    if not query or not text:
        return 0.0
    
    boost_factors = boost_factors or {}
    
    query_lower = query.lower()
    text_lower = text.lower()
    
    # Base fuzzy matching
    partial_ratio = fuzz.partial_ratio(query_lower, text_lower) / 100.0
    token_set_ratio = fuzz.token_set_ratio(query_lower, text_lower) / 100.0
    
    # Token overlap (Jaccard)
    q_tokens = set(re.findall(r'\b\w+\b', query_lower))
    t_tokens = set(re.findall(r'\b\w+\b', text_lower))
    
    if q_tokens and t_tokens:
        intersection = len(q_tokens & t_tokens)
        union = len(q_tokens | t_tokens)
        jaccard = intersection / union if union > 0 else 0.0
    else:
        jaccard = 0.0
    
    # Exact phrase matching
    phrase_bonus = 0.0
    if len(query_lower) > 3 and query_lower in text_lower:
        phrase_bonus = 0.4
    
    # Title vs summary boost
    title_boost = boost_factors.get("title_boost", 1.0)
    
    # Base score
    base_score = (
        0.35 * partial_ratio + 
        0.25 * token_set_ratio + 
        0.25 * jaccard + 
        0.15 * phrase_bonus
    )
    
    return base_score * title_boost


def assess_context_quality(
    candidates: List[Tuple[Any, float]], 
    query: str,
    lang: str = "bn"
) -> Dict[str, Any]:
    """
    Assess the quality of retrieved context and determine if it's sufficient
    for generating a reliable answer.
    """
    if not candidates:
        return {
            "sufficient": False,
            "reason": "No candidates found",
            "best_score": 0.0,
            "avg_score": 0.0,
            "candidate_count": 0,
            "language_matches": 0,
            "quality_score": 0.0,
            "recommendation": "insufficient_context"
        }
    
    # Extract scores and count language matches
    scores = [score for _, score in candidates]
    best_score = max(scores) if scores else 0.0
    avg_score = sum(scores) / len(scores) if scores else 0.0
    candidate_count = len(candidates)
    
    # Count language-appropriate candidates
    language_matches = 0
    for article, _ in candidates:
        title = getattr(article, 'title', '') 
        summary = getattr(article, 'summary', '')
        content = f"{title} {summary}"
        
        lang_detection = detect_language(content)
        if lang == "bn" and lang_detection["language"] in ["bn", "mixed"]:
            language_matches += 1
        elif lang == "en" and lang_detection["language"] in ["en", "mixed"]:
            language_matches += 1
    
    # Apply gating criteria
    sufficient = True
    reasons = []
    
    if candidate_count < RetrievalConfig.MIN_HITS_THRESHOLD:
        sufficient = False
        reasons.append(f"Too few candidates ({candidate_count} < {RetrievalConfig.MIN_HITS_THRESHOLD})")
    
    if best_score < RetrievalConfig.MIN_SCORE_THRESHOLD:
        sufficient = False
        reasons.append(f"Best score too low ({best_score:.3f} < {RetrievalConfig.MIN_SCORE_THRESHOLD})")
    
    # Combined quality check
    quality_score = (best_score * 0.4 + avg_score * 0.3 + (language_matches / max(candidate_count, 1)) * 0.3)
    if quality_score < RetrievalConfig.INSUFFICIENT_CONTEXT_THRESHOLD:
        sufficient = False
        reasons.append(f"Overall quality too low ({quality_score:.3f} < {RetrievalConfig.INSUFFICIENT_CONTEXT_THRESHOLD})")
    
    # Recommendation based on assessment
    if sufficient:
        recommendation = "proceed_with_answer"
    elif candidate_count > 0 and best_score > 0.2:
        recommendation = "proceed_with_low_confidence"
    else:
        recommendation = "insufficient_context"
    
    return {
        "sufficient": sufficient,
        "reason": "; ".join(reasons) if reasons else "Context quality acceptable",
        "best_score": best_score,
        "avg_score": avg_score,
        "candidate_count": candidate_count,
        "language_matches": language_matches,
        "quality_score": quality_score,
        "recommendation": recommendation
    }


def filter_by_language(
    candidates: List[Tuple[Any, float]], 
    target_lang: str,
    confidence_threshold: float = None
) -> List[Tuple[Any, float]]:
    """
    Filter candidates by target language with confidence threshold.
    """
    if not candidates:
        return []
    
    confidence_threshold = confidence_threshold or RetrievalConfig.LANGUAGE_CONFIDENCE_THRESHOLD
    filtered = []
    
    for article, score in candidates:
        title = getattr(article, 'title', '')
        summary = getattr(article, 'summary', '')
        content = f"{title} {summary}"
        
        lang_detection = detect_language(content)
        
        # Language matching logic
        include = False
        if target_lang == "bn":
            # For Bangla, accept bn, mixed, or unknown (could be transliterated)
            include = lang_detection["language"] in ["bn", "mixed", "unknown"]
        elif target_lang == "en":
            # For English, accept en, mixed, or high-confidence unknown
            include = (lang_detection["language"] in ["en", "mixed"] or 
                      (lang_detection["language"] == "unknown" and lang_detection["confidence"] < 0.3))
        else:
            # Default: include everything
            include = True
        
        if include:
            filtered.append((article, score))
    
    return filtered


async def hybrid_retrieve_with_guardrails(
    query: str,
    category: Optional[str],
    repo,
    lang: str = "bn",
    intent: str = "news",
    window_hours: int = 72,
) -> Dict[str, Any]:
    """
    Hybrid retrieval with BM25 + Vector search and comprehensive guardrails.
    
    Returns:
    {
        'evidence': List[Dict] - Evidence items for answer generation
        'routing': Dict - Tool routing information  
        'quality': Dict - Context quality assessment
        'guardrails': Dict - Applied guardrail information
        'citations_required': bool - Whether citations are mandatory
    }
    """
    start_time = datetime.now()
    
    # 1) Check for volatile facts requiring tool routing
    routing = should_route_to_tool(query)
    
    # 2) Query embedding for vector search
    try:
        qvec = await embed_query(query)
    except Exception as e:
        return {
            'evidence': [],
            'routing': {"route_to_tool": False, "tool": None, "error": str(e)},
            'quality': {"sufficient": False, "reason": "Embedding generation failed"},
            'guardrails': {"applied": ["embedding_failure"], "lang_filter": False},
            'citations_required': intent in RetrievalConfig.CITATIONS_REQUIRED_INTENTS
        }
    
    # 3) Vector search (Top M candidates)
    vector_hits = repo.search_vectors(
        qvec, 
        window_hours=window_hours, 
        limit=RetrievalConfig.VECTOR_TOP_M
    )
    
    # 4) BM25 search on vector results (Top N candidates)  
    articles = [a for (a, _) in vector_hits]
    cos_sims = {a.id: cos for (a, cos) in vector_hits}
    
    # Apply category filter if specified
    if category:
        articles = [a for a in articles if getattr(a, "source_category", None) == category]
    
    # BM25 scoring on the articles
    bm25_scored = []
    for article in articles:
        title = getattr(article, 'title', '')
        summary = getattr(article, 'summary', '')
        
        # BM25 score with title boost
        title_score = enhanced_bm25(query, title, {"title_boost": 1.5})
        summary_score = enhanced_bm25(query, summary, {"title_boost": 1.0})
        bm25_final = max(title_score, summary_score * 0.8)  # Prefer title matches
        
        bm25_scored.append((article, bm25_final))
    
    # Take top N from BM25
    bm25_scored.sort(key=lambda x: x[1], reverse=True)
    bm25_top = bm25_scored[:RetrievalConfig.BM25_TOP_N]
    
    # 5) Hybrid scoring: Combine BM25 + Vector + Time decay
    from packages.nlp.retrieve import time_decay
    
    hybrid_scored = []
    for article, bm25_score in bm25_top:
        cos_sim = cos_sims.get(article.id, 0.0)
        time_score = time_decay(getattr(article, 'published_at', None))
        
        # Hybrid combination (tuned weights)
        hybrid_score = (
            0.40 * float(cos_sim) +      # Vector similarity 
            0.45 * bm25_score +          # BM25 text relevance
            0.15 * time_score            # Temporal relevance  
        )
        
        hybrid_scored.append((article, hybrid_score))
    
    # Sort by hybrid score
    hybrid_scored.sort(key=lambda x: x[1], reverse=True)
    
    # 6) Language filtering
    lang_filtered = filter_by_language(hybrid_scored, lang)
    lang_filter_applied = len(lang_filtered) < len(hybrid_scored)
    
    # 7) Context quality assessment
    quality = assess_context_quality(lang_filtered, query, lang)
    
    # 8) Take final top K for interleaving/MMR  
    final_candidates = lang_filtered[:RetrievalConfig.FINAL_INTERLEAVE_K]
    
    # 9) MMR diversification (import from existing)
    from packages.nlp.retrieve import mmr_diversify
    final_articles = mmr_diversify(final_candidates, k=8, lambda_=0.7)
    
    # 10) Build evidence pack with enhanced metadata
    evidence = []
    for article in final_articles:
        published = getattr(article, "published_at", None)
        if isinstance(published, datetime):
            published_iso = published.isoformat()
            # Format for citations (News mode)
            pub_display = published.strftime("%Y-%m-%d %H:%M UTC") if intent == "news" else published_iso
        else:
            published_iso = str(published) if published else None
            pub_display = published_iso
        
        title = getattr(article, "title", "Untitled")
        source = getattr(article, "source", "Unknown")
        
        evidence_item = {
            "outlet": source,
            "title": title, 
            "published_at": published_iso,
            "published_display": pub_display,  # Formatted for citations
            "excerpt": truncate_text(getattr(article, "summary", "") or "", 800),
            "url": getattr(article, "url", ""),
            "language_detected": detect_language(f"{title} {getattr(article, 'summary', '')}"),
        }
        
        # Add citation info for news mode
        if intent == "news":
            evidence_item["citation"] = f"{title} ({source}, {pub_display})"
        
        evidence.append(evidence_item)
    
    # 11) Compile guardrail information
    applied_guardrails = []
    if lang_filter_applied:
        applied_guardrails.append(f"language_filter_{lang}")
    if routing["route_to_tool"]:
        applied_guardrails.append("volatile_fact_routing")
    if quality["recommendation"] == "insufficient_context":
        applied_guardrails.append("context_gating")
    
    elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
    
    return {
        'evidence': evidence,
        'routing': routing,
        'quality': quality,
        'guardrails': {
            'applied': applied_guardrails,
            'lang_filter': lang_filter_applied,
            'lang_matches': quality.get('language_matches', 0),
            'processing_time_ms': elapsed_ms
        },
        'citations_required': intent in RetrievalConfig.CITATIONS_REQUIRED_INTENTS,
        'stats': {
            'vector_hits': len(vector_hits),
            'bm25_candidates': len(bm25_top),
            'lang_filtered': len(lang_filtered),
            'final_evidence': len(evidence)
        }
    }