import re
import math
from datetime import datetime, timezone
from typing import List, Dict, Set, Optional
from collections import defaultdict, Counter

def tokenize(text: str) -> Set[str]:
    """Tokenize text into lowercase words (split on non-letters)"""
    if not text:
        return set()
    
    # Split on non-letter characters and convert to lowercase
    tokens = re.findall(r'[a-zA-Z]+', text.lower())
    return set(tokens)

def keyword_score(query: str, text: str) -> float:
    """Calculate keyword match score between query and text"""
    if not query or not text:
        return 0.0
    
    query_tokens = tokenize(query)
    text_tokens = tokenize(text)
    
    if not query_tokens:
        return 0.0
    
    # Count matches
    matches = len(query_tokens.intersection(text_tokens))
    
    # Return weighted score (proportion of query tokens found)
    return matches / len(query_tokens)

def time_decay(published_at_iso: Optional[str], now: Optional[datetime] = None) -> float:
    """Calculate time decay score: exp(-hours/24)"""
    if not published_at_iso:
        return 0.1  # Low score for articles without timestamps
    
    if now is None:
        now = datetime.now(timezone.utc)
    
    try:
        # Parse ISO datetime
        if published_at_iso.endswith('Z'):
            published_dt = datetime.fromisoformat(published_at_iso.replace('Z', '+00:00'))
        else:
            published_dt = datetime.fromisoformat(published_at_iso)
        
        # Ensure both datetimes are timezone-aware
        if published_dt.tzinfo is None:
            published_dt = published_dt.replace(tzinfo=timezone.utc)
        
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        
        # Calculate hours difference
        time_diff = now - published_dt
        hours = time_diff.total_seconds() / 3600
        
        # Prevent negative hours (future articles)
        hours = max(0, hours)
        
        # Exponential decay: exp(-hours/24)
        # Articles decay to ~37% after 24 hours, ~13% after 48 hours
        decay_score = math.exp(-hours / 24)
        
        return decay_score
        
    except Exception:
        # If date parsing fails, return low score
        return 0.1

def score_article(query: str, article) -> float:
    """Score article based on keyword match and recency (70% keyword + 30% time)"""
    # Combine title and summary for keyword matching
    text_content = f"{article.title} {article.summary}"
    
    # Calculate component scores
    keyword_score_val = keyword_score(query, text_content)
    time_score_val = time_decay(article.published_at)
    
    # Weighted combination: 70% keyword relevance, 30% recency
    total_score = 0.7 * keyword_score_val + 0.3 * time_score_val
    
    return total_score

def diversify_by_domain(articles: List, per_domain: int = 2) -> List:
    """Keep at most N articles per domain, preserving score order"""
    domain_counts = defaultdict(int)
    diversified = []
    
    for article in articles:
        domain = article.domain
        
        if domain_counts[domain] < per_domain:
            diversified.append(article)
            domain_counts[domain] += 1
    
    return diversified

def rank_and_select(query: str, articles: List, k: int = 12) -> List:
    """Rank articles by score and select top k"""
    if not articles:
        return []
    
    # Score all articles
    scored_articles = []
    for article in articles:
        score = score_article(query, article)
        scored_articles.append((score, article))
    
    # Sort by score (highest first)
    scored_articles.sort(key=lambda x: x[0], reverse=True)
    
    # Extract articles and apply diversification
    ranked_articles = [article for score, article in scored_articles]
    diversified_articles = diversify_by_domain(ranked_articles, per_domain=2)
    
    # Return top k
    return diversified_articles[:k]

def search_candidates(query: str, articles: List, k: int = 12) -> List:
    """Main search function: rank and select top diversified articles for evidence pack"""
    return rank_and_select(query, articles, k)

# Alias for backwards compatibility
def rank_articles(articles: List, query: str, top_k: int = 12) -> List:
    """Alias for search_candidates with parameter order matching legacy usage"""
    return search_candidates(query, articles, top_k)