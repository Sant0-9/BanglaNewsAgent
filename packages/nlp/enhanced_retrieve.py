import asyncio
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple
from rapidfuzz import fuzz

from packages.util.normalize import truncate_text, extract_domain
from packages.nlp.embed import embed_query


def analyze_query_complexity(query: str) -> Dict[str, Any]:
    """
    Analyze query complexity to determine optimal vector search parameters.
    
    Returns:
    {
        'term_count': int,
        'complexity_score': float, 
        'suggested_k': int,
        'is_simple': bool,
        'unique_terms': int
    }
    """
    if not query:
        return {
            'term_count': 0,
            'complexity_score': 0.0,
            'suggested_k': 150,
            'is_simple': True,
            'unique_terms': 0
        }
    
    # Tokenize and clean query
    tokens = re.findall(r'\b\w+\b', query.lower())
    unique_tokens = set(tokens)
    
    # Remove common stop words for better term counting
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can',
        'what', 'when', 'where', 'who', 'why', 'how', 'this', 'that', 'these', 'those',
        # Bangla stop words
        'এ', 'এই', 'ও', 'তে', 'এর', 'করে', 'হয়', 'হয়েছে', 'আছে', 'ছিল', 'থেকে', 'জন্য'
    }
    
    meaningful_tokens = [t for t in tokens if t not in stop_words and len(t) > 2]
    meaningful_unique = set(meaningful_tokens)
    
    term_count = len(meaningful_tokens)
    unique_terms = len(meaningful_unique)
    
    # Calculate complexity score
    complexity_factors = [
        term_count,                           # Raw term count
        unique_terms * 1.2,                   # Unique terms (weighted higher)
        len(query) / 50.0,                    # Query length factor
        1.5 if any(len(t) > 8 for t in meaningful_tokens) else 1.0,  # Long terms
        1.3 if '"' in query else 1.0,        # Quoted phrases
        1.4 if any(c in query for c in '?!') else 1.0,  # Question marks
    ]
    
    complexity_score = sum(complexity_factors)
    
    # Determine suggested K based on complexity
    if complexity_score <= 3.0:      # Very simple: 1-2 meaningful terms
        suggested_k = 150
    elif complexity_score <= 6.0:    # Simple: 3-4 terms
        suggested_k = 250  
    elif complexity_score <= 10.0:   # Medium: 5-7 terms
        suggested_k = 400
    elif complexity_score <= 15.0:   # Complex: 8-12 terms
        suggested_k = 600
    else:                             # Very complex: 13+ terms
        suggested_k = 800
    
    return {
        'term_count': term_count,
        'complexity_score': complexity_score,
        'suggested_k': suggested_k,
        'is_simple': complexity_score <= 6.0,
        'unique_terms': unique_terms
    }


def calculate_text_richness(text: str) -> float:
    """
    Calculate text richness score based on content quality indicators.
    Higher scores indicate richer, more informative content.
    """
    if not text:
        return 0.0
    
    # Length-based factors (with diminishing returns)
    length = len(text)
    length_score = min(length / 1000.0, 1.0)  # Cap at 1.0 for 1000+ chars
    
    # Sentence structure
    sentences = len(re.split(r'[.!?।]+', text))
    sentence_score = min(sentences / 10.0, 1.0)  # Cap at 10 sentences
    
    # Vocabulary richness
    words = re.findall(r'\b\w+\b', text.lower())
    unique_words = len(set(words))
    vocab_score = min(unique_words / 100.0, 1.0) if words else 0.0
    
    # Information density indicators
    info_indicators = [
        len(re.findall(r'\d+', text)) / 50.0,      # Numbers (dates, stats, etc.)
        len(re.findall(r'[A-Z][a-z]+', text)) / 20.0,  # Proper nouns
        text.count('"') / 10.0,                     # Quotes
        text.count(':') / 5.0,                      # Colons (often introduce details)
    ]
    info_score = min(sum(info_indicators), 1.0)
    
    # Content type bonuses
    content_bonuses = 0.0
    if any(word in text.lower() for word in ['analysis', 'report', 'investigation', 'বিশ্লেষণ', 'প্রতিবেদন']):
        content_bonuses += 0.2
    if any(word in text.lower() for word in ['exclusive', 'interview', 'statement', 'একচেটিয়া', 'সাক্ষাৎকার']):
        content_bonuses += 0.2
    
    # Combine scores with weights
    richness = (
        0.25 * length_score +
        0.25 * sentence_score + 
        0.25 * vocab_score +
        0.15 * info_score +
        0.10 * content_bonuses
    )
    
    return min(richness, 1.0)


def calculate_freshness_boost(published_at: Optional[Any]) -> float:
    """
    Calculate freshness boost for content published within 24h.
    Returns multiplier (1.0 = no boost, >1.0 = boosted).
    """
    if not published_at:
        return 1.0
    
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
            return 1.5
        elif hours_old < 6:    # Less than 6 hours  
            return 1.3
        elif hours_old < 24:   # Less than 24 hours
            return 1.2
        else:
            return 1.0         # No boost for older content
            
    except Exception:
        return 1.0


def detect_content_angle(article: Any) -> str:
    """
    Detect the editorial angle/type of content to help with domain diversity.
    Returns: 'opinion', 'analysis', 'wire', 'local', 'interview', 'breaking', 'generic'
    """
    title = getattr(article, 'title', '').lower()
    summary = getattr(article, 'summary', '').lower()
    source = getattr(article, 'source', '').lower()
    
    content = f"{title} {summary}"
    
    # Opinion indicators
    opinion_markers = ['opinion', 'editorial', 'op-ed', 'comment', 'analysis', 'perspective', 
                      'মতামত', 'সম্পাদকীয়', 'বিশ্লেষণ']
    if any(marker in content or marker in source for marker in opinion_markers):
        return 'opinion'
    
    # Interview indicators  
    interview_markers = ['interview', 'exclusive', 'speaks', 'says', 'tells', 
                        'সাক্ষাৎকার', 'একচেটিয়া', 'বলেন', 'জানান']
    if any(marker in content for marker in interview_markers):
        return 'interview'
    
    # Breaking news indicators
    breaking_markers = ['breaking', 'urgent', 'just in', 'developing', 'সদ্য', 'জরুরি', 'ব্রেকিং']
    if any(marker in content for marker in breaking_markers):
        return 'breaking'
    
    # Wire service indicators
    wire_markers = ['reuters', 'ap', 'afp', 'bloomberg', 'xinhua', 'ians']
    if any(marker in source for marker in wire_markers):
        return 'wire'
    
    # Local reporting indicators
    local_markers = ['local', 'correspondent', 'staff reporter', 'স্থানীয়', 'প্রতিনিধি']
    if any(marker in content or marker in source for marker in local_markers):
        return 'local'
    
    # Analysis indicators
    analysis_markers = ['report', 'investigation', 'study', 'finds', 'reveals', 
                       'প্রতিবেদন', 'তদন্ত', 'গবেষণা', 'প্রকাশ']
    if any(marker in content for marker in analysis_markers):
        return 'analysis'
    
    return 'generic'


def enhanced_domain_diversity(
    articles: List[Tuple[Any, float]], 
    target_count: int = 6,
    max_per_domain: int = 2
) -> List[Any]:
    """
    Enhanced domain diversity that considers content angles and uniqueness.
    Allows up to 3 per domain if they offer unique angles.
    """
    if not articles:
        return []
    
    selected: List[Any] = []
    domain_info: Dict[str, List[Dict[str, Any]]] = {}
    
    # Sort by score (highest first)
    sorted_articles = sorted(articles, key=lambda x: x[1], reverse=True)
    
    for article, score in sorted_articles:
        domain = extract_domain(getattr(article, "url", ""))
        angle = detect_content_angle(article)
        
        if domain not in domain_info:
            domain_info[domain] = []
        
        # Check if we can add this article
        domain_articles = domain_info[domain]
        domain_count = len(domain_articles)
        
        can_add = False
        
        if domain_count < max_per_domain:
            # Always allow up to base limit
            can_add = True
        elif domain_count < 3:
            # Allow 3rd article if it offers unique angle
            existing_angles = {item['angle'] for item in domain_articles}
            if angle not in existing_angles and angle != 'generic':
                can_add = True
        
        if can_add:
            domain_info[domain].append({
                'article': article,
                'score': score,
                'angle': angle
            })
            selected.append(article)
            
            if len(selected) >= target_count:
                break
    
    return selected


async def enhanced_retrieve_evidence(
    query: str,
    category: Optional[str],
    repo,
    window_hours: int = 72,
    latency_budget_ms: int = 3000  # 3 second latency budget
) -> List[Dict[str, Any]]:
    """
    Enhanced retrieval with dynamic K, improved scoring, and domain diversity.
    
    Returns evidence pack optimized for relevance, freshness, and diversity.
    """
    start_time = datetime.now()
    
    # 1) Analyze query complexity for dynamic K
    complexity = analyze_query_complexity(query)
    dynamic_k = complexity['suggested_k']
    
    # Cap K based on latency budget (rough estimate: 1ms per result)
    max_k_for_budget = min(latency_budget_ms, 800)  
    vector_limit = min(dynamic_k, max_k_for_budget)
    
    # 2) Query embedding
    qvec = await embed_query(query)
    
    # 3) Vector search with dynamic limit
    vector_hits: List[Tuple[Any, float]] = repo.search_vectors(
        qvec, 
        window_hours=window_hours, 
        limit=vector_limit
    )
    
    # 4) Optional category filter
    articles = [a for (a, cos) in vector_hits]
    cos_sims = {a.id: cos for (a, cos) in vector_hits}
    if category:
        articles = [a for a in articles if getattr(a, "source_category", None) == category]
    
    # 5) Enhanced hybrid scoring
    scored: List[Tuple[Any, float]] = []
    for a in articles:
        # Text content for BM25
        title = getattr(a, 'title', '')
        summary = getattr(a, 'summary', '')
        text = f"{title} {summary}"
        
        # Core scores
        from packages.nlp.retrieve import bm25ish, time_decay
        bm25_score = bm25ish(query, text)
        cos_sim = float(cos_sims.get(a.id, 0.0) or 0.0)
        time_decay_score = time_decay(getattr(a, 'published_at', None))
        
        # New quality factors
        text_richness = calculate_text_richness(text)
        freshness_boost = calculate_freshness_boost(getattr(a, 'published_at', None))
        
        # Enhanced scoring formula
        # Base: semantic similarity + text matching + time
        base_score = 0.45 * cos_sim + 0.35 * bm25_score + 0.20 * time_decay_score
        
        # Apply richness preference (boost for richer content)
        richness_multiplier = 1.0 + (0.3 * text_richness)
        
        # Apply freshness boost for <24h content
        final_score = base_score * richness_multiplier * freshness_boost
        
        scored.append((a, final_score))
    
    # 6) Take top candidates based on complexity
    top_count = min(50 if complexity['is_simple'] else 80, len(scored))
    scored.sort(key=lambda x: x[1], reverse=True)
    top_candidates = scored[:top_count]
    
    # 7) Semantic reranking with cross-encoder
    from packages.nlp.semantic_reranker import lightweight_cross_encoder_rerank
    reranked_articles = await lightweight_cross_encoder_rerank(
        query, 
        top_candidates, 
        top_k=min(40, len(top_candidates))  # Rerank top 40 candidates
    )
    
    # Restore scores for reranked articles
    reranked_with_scores = []
    for article in reranked_articles:
        # Find original score
        original_score = next((s for a, s in top_candidates if a is article), 0.0)
        reranked_with_scores.append((article, original_score))
    
    # 8) Story clustering for duplicate detection
    from packages.nlp.story_clustering import detect_story_clusters
    clustering_result = detect_story_clusters(
        reranked_articles, 
        min_cluster_size=2, 
        similarity_threshold=0.4
    )
    
    clustered_evidence = clustering_result['evidence']
    clustering_stats = clustering_result['clustering_stats']
    
    # 9) Enhanced domain diversity on clustered articles
    # Convert clustered evidence back to article objects for diversity selection
    evidence_with_scores = []
    for evidence_item in clustered_evidence:
        # Find corresponding article object
        article = next((a for a in reranked_articles if getattr(a, 'url', '') == evidence_item['url']), None)
        if article:
            original_score = next((s for a, s in reranked_with_scores if a is article), 0.0)
            evidence_with_scores.append((article, original_score))
    
    final_articles = enhanced_domain_diversity(
        evidence_with_scores, 
        target_count=6,     # Target top 6 for relevance
        max_per_domain=2    # Base limit per domain
    )
    
    # Check latency and adjust if needed
    elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
    if elapsed_ms > latency_budget_ms:
        print(f"Warning: Retrieval exceeded latency budget: {elapsed_ms:.0f}ms > {latency_budget_ms}ms")
    
    # 10) Build enhanced evidence pack with clustering information
    evidence: List[Dict[str, Any]] = []
    for a in final_articles:
        published = getattr(a, "published_at", None)
        if isinstance(published, datetime):
            published_iso = published.isoformat()
        else:
            published_iso = str(published) if published else None
        
        # Find cluster information for this article
        cluster_info = next(
            (item for item in clustered_evidence if item['url'] == getattr(a, 'url', '')), 
            None
        )
        
        evidence_item = {
            "outlet": getattr(a, "source", "Unknown"),
            "title": getattr(a, "title", "Untitled"),
            "published_at": published_iso,
            "excerpt": truncate_text(getattr(a, "summary", "") or "", 800),
            "url": getattr(a, "url", ""),
            "content_angle": detect_content_angle(a),
            "text_richness": calculate_text_richness(f"{getattr(a, 'title', '')} {getattr(a, 'summary', '')}"),
            "hours_old": (datetime.now(timezone.utc) - 
                         (getattr(a, "published_at", datetime.now(timezone.utc)) if isinstance(getattr(a, "published_at", None), datetime) 
                          else datetime.now(timezone.utc))).total_seconds() / 3600.0
        }
        
        # Add clustering information if available
        if cluster_info:
            evidence_item.update({
                "cluster_id": cluster_info.get("cluster_id"),
                "cluster_size": cluster_info.get("cluster_size", 1),
                "sibling_outlets": cluster_info.get("sibling_outlets", []),
                "all_outlets": cluster_info.get("all_outlets", [getattr(a, "source", "Unknown")])
            })
        else:
            # Single article, no clustering
            evidence_item.update({
                "cluster_id": None,
                "cluster_size": 1,
                "sibling_outlets": [],
                "all_outlets": [getattr(a, "source", "Unknown")]
            })
        
        evidence.append(evidence_item)
    
    return evidence