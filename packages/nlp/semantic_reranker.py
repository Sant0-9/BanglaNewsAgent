import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from rapidfuzz import fuzz

def calculate_freshness_score(published_at: Optional[Any]) -> float:
    """Calculate freshness score (0.0-1.0) with higher scores for recent content."""
    if not published_at:
        return 0.1
    
    try:
        if isinstance(published_at, str):
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        else:
            dt = published_at
        
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        hours_old = (now - dt).total_seconds() / 3600.0
        
        if hours_old < 1:      # Less than 1 hour
            return 1.0
        elif hours_old < 6:    # Less than 6 hours  
            return 0.9
        elif hours_old < 24:   # Less than 24 hours
            return 0.8
        elif hours_old < 72:   # Less than 3 days
            return 0.6
        elif hours_old < 168:  # Less than 1 week
            return 0.4
        else:
            return 0.2         # Older content
            
    except Exception:
        return 0.1


def calculate_source_authority(outlet: str) -> float:
    """Calculate source authority score based on outlet reputation."""
    # Define authority tiers for Bangladeshi and international outlets
    tier1_outlets = {
        'prothom alo', 'the daily star', 'bdnews24', 'new age', 'dhaka tribune',
        'reuters', 'ap', 'bbc', 'cnn', 'bloomberg', 'financial times'
    }
    
    tier2_outlets = {
        'daily sun', 'the business standard', 'independent', 'jugantor', 'ittefaq',
        'washington post', 'new york times', 'guardian', 'al jazeera', 'dw'
    }
    
    tier3_outlets = {
        'banglanews24', 'risingbd', 'daily observer', 'kaler kantho',
        'abc news', 'cbs news', 'nbc news', 'sky news', 'france24'
    }
    
    outlet_lower = outlet.lower().strip()
    
    if any(tier1 in outlet_lower for tier1 in tier1_outlets):
        return 1.0
    elif any(tier2 in outlet_lower for tier2 in tier2_outlets):
        return 0.8
    elif any(tier3 in outlet_lower for tier3 in tier3_outlets):
        return 0.6
    else:
        return 0.4  # Unknown outlets get moderate score


async def lightweight_cross_encoder_rerank(
    query: str, 
    candidates: List[Tuple[Any, float]], 
    top_k: int = 20
) -> List[Any]:
    """
    Lightweight cross-encoder reranking using semantic similarity + quality signals.
    Falls back to rule-based approach if cross-encoder is not available.
    
    Args:
        query: The user query
        candidates: List of (article, original_score) tuples
        top_k: Number of top candidates to rerank
        
    Returns:
        Reranked list of articles
    """
    if not candidates:
        return []
    
    # Take top candidates for reranking (limit computational cost)
    rerank_candidates = candidates[:min(top_k, len(candidates))]
    
    try:
        # Try to use cross-encoder if available
        from sentence_transformers import CrossEncoder
        return await _cross_encoder_rerank(query, rerank_candidates)
    except ImportError:
        # Fallback to lightweight semantic + quality scoring
        return await _lightweight_rerank(query, rerank_candidates)


async def _cross_encoder_rerank(
    query: str, 
    candidates: List[Tuple[Any, float]]
) -> List[Any]:
    """Rerank using actual cross-encoder model."""
    
    def score_pairs() -> List[float]:
        # Use a lightweight multilingual cross-encoder
        model_name = "BAAI/bge-reranker-base"  # Smaller, faster model
        model = CrossEncoder(model_name, max_length=256)  # Shorter context for speed
        
        pairs = []
        for article, _ in candidates:
            text = f"{getattr(article, 'title', '')} {getattr(article, 'summary', '')}"[:500]
            pairs.append((query, text))
        
        return model.predict(pairs).tolist()
    
    try:
        # Run in thread to avoid blocking
        semantic_scores = await asyncio.to_thread(score_pairs)
    except Exception:
        # Fallback if model fails
        return await _lightweight_rerank(query, candidates)
    
    # Combine semantic scores with quality signals
    enhanced_scores = []
    for i, (article, original_score) in enumerate(candidates):
        semantic_score = semantic_scores[i]
        
        # Quality multipliers
        freshness = calculate_freshness_score(getattr(article, 'published_at', None))
        authority = calculate_source_authority(getattr(article, 'source', ''))
        
        # Weighted combination: 70% semantic, 15% freshness, 15% authority
        final_score = (0.70 * semantic_score + 
                      0.15 * freshness + 
                      0.15 * authority)
        
        enhanced_scores.append((article, final_score))
    
    # Sort by enhanced score and return articles
    enhanced_scores.sort(key=lambda x: x[1], reverse=True)
    return [article for article, _ in enhanced_scores]


async def _lightweight_rerank(
    query: str, 
    candidates: List[Tuple[Any, float]]
) -> List[Any]:
    """Lightweight reranking using fuzzy matching + quality signals."""
    
    enhanced_scores = []
    
    for article, original_score in candidates:
        title = getattr(article, 'title', '')
        summary = getattr(article, 'summary', '')
        text = f"{title} {summary}"
        
        # Semantic approximation using fuzzy matching
        title_relevance = fuzz.partial_ratio(query.lower(), title.lower()) / 100.0
        summary_relevance = fuzz.partial_ratio(query.lower(), summary.lower()) / 100.0
        semantic_score = 0.6 * title_relevance + 0.4 * summary_relevance
        
        # Quality signals
        freshness = calculate_freshness_score(getattr(article, 'published_at', None))
        authority = calculate_source_authority(getattr(article, 'source', ''))
        
        # Text quality indicators
        text_length = min(len(text) / 1000.0, 1.0)  # Longer articles often more substantive
        has_numbers = 1.0 if any(c.isdigit() for c in text) else 0.5  # Numbers indicate specificity
        
        # Weighted combination
        final_score = (0.50 * semantic_score +
                      0.20 * freshness +
                      0.15 * authority +
                      0.10 * text_length +
                      0.05 * has_numbers)
        
        enhanced_scores.append((article, final_score))
    
    # Sort by enhanced score
    enhanced_scores.sort(key=lambda x: x[1], reverse=True)
    return [article for article, _ in enhanced_scores]