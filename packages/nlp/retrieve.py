import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from rapidfuzz import fuzz

from packages.util.normalize import truncate_text, extract_domain
from packages.nlp.embed import embed_query


# --------------------------
# Helpers
# --------------------------

def tokenize(text: str) -> List[str]:
    if not text:
        return []
    import re

    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def hours_old(published_at: Optional[Any]) -> float:
    if not published_at:
        return 9999.0
    try:
        if isinstance(published_at, str):
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        else:
            dt = published_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0.0, (now - dt).total_seconds() / 3600.0)
    except Exception:
        return 9999.0


def time_decay(published_at: Optional[Any]) -> float:
    h = hours_old(published_at)
    # exp(-h/24)
    import math

    return math.exp(-h / 24.0)


def bm25ish(query: str, text: str) -> float:
    if not query or not text:
        return 0.0
    
    # Normalize query and text for better matching
    query_lower = query.lower()
    text_lower = text.lower()
    
    # Partial fuzzy ratio in [0, 100]
    pr = fuzz.partial_ratio(query_lower, text_lower) / 100.0
    
    # Token overlap (Jaccard over sets)
    q_tokens = set(tokenize(query_lower))
    t_tokens = set(tokenize(text_lower))
    if not q_tokens or not t_tokens:
        overlap = 0.0
    else:
        inter = len(q_tokens & t_tokens)
        union = len(q_tokens | t_tokens)
        overlap = (inter / union) if union else 0.0
    
    # Add exact phrase matching bonus
    phrase_bonus = 0.0
    if len(query_lower) > 3 and query_lower in text_lower:
        phrase_bonus = 0.3
    
    # Enhanced scoring with phrase matching
    return 0.5 * pr + 0.3 * overlap + 0.2 * phrase_bonus


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    # Not used directly since DB returns cos_sim, but provide for completeness
    import math

    if not a or not b:
        return 0.0
    s = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return (s / (na * nb)) if na and nb else 0.0


def filter_by_category(items: List[Any], category: Optional[str]) -> List[Any]:
    if not category:
        return items
    return [it for it in items if getattr(it, "source_category", None) == category]


def _pairwise_text_sim(a_text: str, b_text: str) -> float:
    # Symmetric similarity for MMR diversification (token Jaccard)
    a_tokens = set(tokenize(a_text))
    b_tokens = set(tokenize(b_text))
    if not a_tokens or not b_tokens:
        return 0.0
    inter = len(a_tokens & b_tokens)
    union = len(a_tokens | b_tokens)
    return (inter / union) if union else 0.0


def mmr_diversify(candidates: List[Tuple[Any, float]], k: int = 8, lambda_: float = 0.7) -> List[Any]:
    """MMR diversify based on candidate score and pairwise text similarity.

    candidates: list of (article, score)
    returns: list of selected articles (length <= k)
    """
    if not candidates:
        return []

    # Precompute article text for pairwise sim
    texts = [f"{getattr(a, 'title', '')} {getattr(a, 'summary', '')}" for a, _ in candidates]

    selected: List[int] = []
    remaining = list(range(len(candidates)))

    # Seed with best-scoring item
    remaining.sort(key=lambda i: candidates[i][1], reverse=True)
    if remaining:
        selected.append(remaining.pop(0))

    while remaining and len(selected) < k:
        # For each remaining, compute MMR score wrt selected set
        best_idx = None
        best_score = -1e9
        for i in remaining:
            relevance = candidates[i][1]
            max_sim = 0.0
            for j in selected:
                sim = _pairwise_text_sim(texts[i], texts[j])
                if sim > max_sim:
                    max_sim = sim
            mmr_score = lambda_ * relevance - (1 - lambda_) * max_sim
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = i
        if best_idx is None:
            break
        selected.append(best_idx)
        remaining.remove(best_idx)

    return [candidates[i][0] for i in selected]


async def _maybe_rerank(query: str, articles: List[Any]) -> List[Any]:
    """Optionally rerank using a cross-encoder if installed."""
    if not articles:
        return []
    try:
        from sentence_transformers import CrossEncoder
    except Exception:
        return articles  # Reranker not installed

    pairs = [(query, f"{getattr(a, 'title', '')} {getattr(a, 'summary', '')}") for a in articles]

    def score_pairs() -> List[float]:
        model_name = "BAAI/bge-reranker-large"
        model = CrossEncoder(model_name, max_length=512)
        return model.predict(pairs).tolist()

    try:
        scores: List[float] = await asyncio.to_thread(score_pairs)
    except Exception:
        return articles

    ranked = list(zip(articles, scores))
    ranked.sort(key=lambda x: x[1], reverse=True)
    return [a for a, _ in ranked]


# --------------------------
# Main entry
# --------------------------

async def retrieve_evidence(
    query: str,
    category: Optional[str],
    repo,
    window_hours: int = 72,
) -> List[Dict[str, Any]]:
    """Hybrid retrieval: BM25-ish + embeddings + time decay + MMR.

    Returns evidence pack of dicts: {outlet,title,published_at,excerpt,url}
    """
    # 1) Query embedding
    qvec = await embed_query(query)

    # 2) Vector search from DB - increased for better coverage
    limit_db = 500
    vector_hits: List[Tuple[Any, float]] = repo.search_vectors(qvec, window_hours=window_hours, limit=limit_db)

    # 3) Optional category filter
    articles = [a for (a, cos) in vector_hits]
    cos_sims = {a.id: cos for (a, cos) in vector_hits}
    if category:
        articles = filter_by_category(articles, category)

    # 4) Score hybrid with improved weighting
    scored: List[Tuple[Any, float]] = []
    for a in articles:
        text = f"{getattr(a, 'title', '')} {getattr(a, 'summary', '')}"
        bm = bm25ish(query, text)
        cos_sim = float(cos_sims.get(a.id, 0.0) or 0.0)
        td = time_decay(getattr(a, 'published_at', None))
        # Improved scoring: more weight on semantic similarity and content relevance
        score = 0.35 * bm + 0.55 * cos_sim + 0.10 * td
        scored.append((a, score))

    # 5) Take top 50 for better diversity before MMR
    scored.sort(key=lambda x: x[1], reverse=True)
    topk = [a for a, s in scored[:50]]

    # 6) Optional rerank (if installed)
    topk = await _maybe_rerank(query, topk)

    # 7) MMR diversify to 12 for more comprehensive coverage
    mmr_selected = mmr_diversify([(a, next(s for (aa, s) in scored if aa is a)) for a in topk], k=12, lambda_=0.6)

    # 8) Allow up to 2 per domain, keep 6–8 sources for richer information
    final: List[Any] = []
    domain_counts = {}
    for a in mmr_selected:
        dom = extract_domain(getattr(a, "url", ""))
        if domain_counts.get(dom, 0) >= 2:  # Allow up to 2 per domain
            continue
        domain_counts[dom] = domain_counts.get(dom, 0) + 1
        final.append(a)
        if len(final) >= 8:  # Increase to 8 sources
            break

    if len(final) < 3:  # Ensure minimum of 3 sources
        # Backfill from remaining topk, allowing more per domain if needed
        for a in topk:
            if a in final:
                continue
            dom = extract_domain(getattr(a, "url", ""))
            if domain_counts.get(dom, 0) >= 3:  # Allow up to 3 in backfill
                continue
            final.append(a)
            domain_counts[dom] = domain_counts.get(dom, 0) + 1
            if len(final) >= 3:
                break

    # 9) Build evidence pack
    evidence: List[Dict[str, Any]] = []
    for a in final:
        published = getattr(a, "published_at", None)
        if isinstance(published, datetime):
            published_iso = published.isoformat()
        else:
            published_iso = str(published) if published else None
        evidence.append(
            {
                "outlet": getattr(a, "source", "Unknown"),
                "title": getattr(a, "title", "Untitled"),
                "published_at": published_iso,
                "excerpt": truncate_text(getattr(a, "summary", "") or "", 800),
                "url": getattr(a, "url", ""),
            }
        )

    return evidence
