import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import numpy as np
from rapidfuzz import fuzz

def create_minhash_signature(text: str, num_hashes: int = 64) -> Set[int]:
    """Create MinHash signature for near-duplicate detection."""
    # Normalize text
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    words = text.split()
    
    # Create shingles (2-grams)
    shingles = set()
    for i in range(len(words) - 1):
        shingle = f"{words[i]} {words[i+1]}"
        shingles.add(shingle)
    
    if not shingles:
        return set()
    
    # Generate hash values
    hashes = []
    for shingle in shingles:
        hash_val = int(hashlib.md5(shingle.encode()).hexdigest(), 16)
        hashes.append(hash_val)
    
    # MinHash signature - take minimum hash for each hash function
    signature = set()
    for i in range(num_hashes):
        seed = i * 123456789  # Different seed for each hash function
        min_hash = min((h ^ seed) & 0x7FFFFFFF for h in hashes)
        signature.add(min_hash)
    
    return signature


def jaccard_similarity(set1: Set[int], set2: Set[int]) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set1 or not set2:
        return 0.0
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0


def calculate_text_richness_for_clustering(article: Any) -> float:
    """Calculate text richness score for selecting cluster representative."""
    title = getattr(article, 'title', '')
    summary = getattr(article, 'summary', '')
    text = f"{title} {summary}"
    
    if not text.strip():
        return 0.0
    
    # Length factor (with diminishing returns)
    length_score = min(len(text) / 800.0, 1.0)
    
    # Information density
    num_words = len(text.split())
    unique_words = len(set(text.lower().split()))
    vocab_diversity = unique_words / num_words if num_words > 0 else 0.0
    
    # Specific content indicators
    has_numbers = 1.0 if re.search(r'\d+', text) else 0.0
    has_quotes = 1.0 if '"' in text or "'" in text else 0.0
    has_details = 1.0 if any(word in text.lower() for word in ['according', 'said', 'reported', 'announced', 'stated']) else 0.0
    
    # Combined score
    richness = (0.3 * length_score + 
               0.3 * vocab_diversity + 
               0.2 * has_numbers + 
               0.1 * has_quotes + 
               0.1 * has_details)
    
    return min(richness, 1.0)


def calculate_freshness_for_clustering(published_at: Optional[Any]) -> float:
    """Calculate freshness score for cluster representative selection."""
    if not published_at:
        return 0.0
    
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
            return 0.8
        elif hours_old < 24:   # Less than 24 hours
            return 0.6
        elif hours_old < 72:   # Less than 3 days
            return 0.4
        else:
            return 0.2
            
    except Exception:
        return 0.0


def cluster_similar_stories(articles: List[Any], similarity_threshold: float = 0.4) -> List[Dict[str, Any]]:
    """
    Cluster similar stories using MinHash signatures.
    
    Args:
        articles: List of article objects
        similarity_threshold: Minimum Jaccard similarity to group articles
        
    Returns:
        List of cluster dicts with representative and siblings
    """
    if not articles:
        return []
    
    # Create MinHash signatures for all articles
    signatures = {}
    for i, article in enumerate(articles):
        title = getattr(article, 'title', '')
        summary = getattr(article, 'summary', '')
        text = f"{title} {summary}"
        signatures[i] = create_minhash_signature(text)
    
    # Find clusters using similarity threshold
    clusters = []
    used_indices = set()
    
    for i, article_i in enumerate(articles):
        if i in used_indices:
            continue
            
        # Start new cluster
        cluster_members = [i]
        used_indices.add(i)
        
        # Find similar articles
        sig_i = signatures[i]
        for j, article_j in enumerate(articles[i+1:], start=i+1):
            if j in used_indices:
                continue
                
            sig_j = signatures[j]
            similarity = jaccard_similarity(sig_i, sig_j)
            
            if similarity >= similarity_threshold:
                cluster_members.append(j)
                used_indices.add(j)
        
        # Create cluster info
        cluster_articles = [articles[idx] for idx in cluster_members]
        
        # Select best representative (freshest + richest content)
        representative = select_cluster_representative(cluster_articles)
        siblings = [a for a in cluster_articles if a is not representative]
        
        # Generate cluster ID based on content
        cluster_id = generate_cluster_id(representative, len(cluster_articles))
        
        clusters.append({
            'cluster_id': cluster_id,
            'representative': representative,
            'siblings': siblings,
            'size': len(cluster_articles),
            'outlets': list(set(getattr(a, 'source', 'Unknown') for a in cluster_articles))
        })
    
    return clusters


def select_cluster_representative(cluster_articles: List[Any]) -> Any:
    """Select the best representative from a cluster of similar articles."""
    if len(cluster_articles) == 1:
        return cluster_articles[0]
    
    best_article = None
    best_score = -1.0
    
    for article in cluster_articles:
        # Combine freshness and text richness
        freshness = calculate_freshness_for_clustering(getattr(article, 'published_at', None))
        richness = calculate_text_richness_for_clustering(article)
        
        # Weight freshness slightly higher for news
        combined_score = 0.6 * freshness + 0.4 * richness
        
        if combined_score > best_score:
            best_score = combined_score
            best_article = article
    
    return best_article or cluster_articles[0]


def generate_cluster_id(representative: Any, cluster_size: int) -> str:
    """Generate a unique cluster ID based on representative content."""
    title = getattr(representative, 'title', '')
    source = getattr(representative, 'source', '')
    
    # Extract key terms from title
    title_words = re.findall(r'\b\w{3,}\b', title.lower())
    key_terms = title_words[:4]  # Take first 4 meaningful words
    
    # Create ID
    terms_part = '_'.join(key_terms) if key_terms else 'story'
    source_part = re.sub(r'[^\w]', '', source.lower())[:8] if source else 'news'
    
    cluster_id = f"{terms_part}_{source_part}_{cluster_size}"
    
    # Ensure ID is not too long
    if len(cluster_id) > 50:
        cluster_id = cluster_id[:50]
    
    return cluster_id


def format_clustered_evidence(clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format clustered articles into evidence pack with cluster metadata.
    
    Returns evidence pack where each item includes cluster_id and sibling outlets.
    """
    evidence = []
    
    for cluster in clusters:
        representative = cluster['representative']
        siblings = cluster['siblings']
        cluster_id = cluster['cluster_id']
        
        # Format representative article
        published = getattr(representative, 'published_at', None)
        if isinstance(published, datetime):
            published_iso = published.isoformat()
        else:
            published_iso = str(published) if published else None
        
        from packages.util.normalize import truncate_text
        
        # Create sibling outlets list
        sibling_outlets = [getattr(s, 'source', 'Unknown') for s in siblings]
        all_outlets = [getattr(representative, 'source', 'Unknown')] + sibling_outlets
        
        evidence_item = {
            "outlet": getattr(representative, "source", "Unknown"),
            "title": getattr(representative, "title", "Untitled"),
            "published_at": published_iso,
            "excerpt": truncate_text(getattr(representative, "summary", "") or "", 800),
            "url": getattr(representative, "url", ""),
            "cluster_id": cluster_id,
            "cluster_size": cluster['size'],
            "sibling_outlets": sibling_outlets,
            "all_outlets": all_outlets  # For citation formatting
        }
        
        evidence.append(evidence_item)
    
    return evidence


def detect_story_clusters(articles: List[Any], 
                         min_cluster_size: int = 2,
                         similarity_threshold: float = 0.4) -> Dict[str, Any]:
    """
    Main function to detect and format story clusters.
    
    Args:
        articles: List of article objects
        min_cluster_size: Minimum articles needed to form a cluster
        similarity_threshold: MinHash similarity threshold
        
    Returns:
        Dict with clustered evidence and clustering stats
    """
    if not articles:
        return {
            'evidence': [],
            'clustering_stats': {
                'total_articles': 0,
                'clusters_found': 0,
                'duplicate_reduction': 0.0
            }
        }
    
    # Cluster similar stories
    clusters = cluster_similar_stories(articles, similarity_threshold)
    
    # Filter out single-article clusters if min_cluster_size > 1
    significant_clusters = [c for c in clusters if c['size'] >= min_cluster_size]
    single_clusters = [c for c in clusters if c['size'] < min_cluster_size]
    
    # For single-article "clusters", still include them but without cluster metadata
    all_clusters_for_evidence = significant_clusters
    for single_cluster in single_clusters:
        # Mark as non-clustered
        single_cluster['cluster_id'] = None
        single_cluster['sibling_outlets'] = []
        all_clusters_for_evidence.append(single_cluster)
    
    # Format evidence
    evidence = format_clustered_evidence(all_clusters_for_evidence)
    
    # Calculate stats
    total_articles = len(articles)
    clusters_found = len(significant_clusters)
    articles_after_clustering = len(evidence)
    duplicate_reduction = (total_articles - articles_after_clustering) / total_articles if total_articles > 0 else 0.0
    
    return {
        'evidence': evidence,
        'clustering_stats': {
            'total_articles': total_articles,
            'clusters_found': clusters_found,
            'articles_after_clustering': articles_after_clustering,
            'duplicate_reduction': duplicate_reduction
        }
    }