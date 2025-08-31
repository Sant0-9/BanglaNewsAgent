import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from packages.nlp.retrieve import retrieve_evidence
from packages.nlp.enhanced_retrieve import enhanced_retrieve_evidence
from packages.nlp.window_analyzer import analyze_query_window, get_story_id


async def retrieve_story_context(
    query: str,
    category: Optional[str],
    repo,
    user_window_hours: Optional[int] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enhanced retrieval that handles background context and story continuity.
    
    Returns:
    {
        'recent_evidence': List[Dict],      # Last 24h updates
        'background_evidence': List[Dict],  # Historical context (if needed)
        'story_id': Optional[str],         # Story cluster identifier
        'window_analysis': Dict,           # Analysis results
        'retrieval_strategy': str,         # How evidence was retrieved
        'context_sections': Dict           # Organized context by timeframe
    }
    """
    
    # Analyze query for optimal windowing
    window_analysis = analyze_query_window(query, user_window_hours)
    
    # Extract analysis results
    window_hours = window_analysis['window_hours']
    needs_background = window_analysis['needs_background']
    is_immediate = window_analysis['is_immediate']
    story_detected = window_analysis['story_detected']
    
    # Base evidence retrieval with enhanced scoring
    primary_evidence = await enhanced_retrieve_evidence(query, category, repo, window_hours=window_hours)
    
    # Generate story ID for clustering
    story_id = get_story_id(query, primary_evidence) if story_detected else None
    
    # Determine retrieval strategy
    if needs_background and story_detected:
        return await _retrieve_with_background_context(
            query, category, repo, primary_evidence, story_id, window_analysis
        )
    elif is_immediate:
        return await _retrieve_immediate_context(
            query, category, repo, primary_evidence, window_analysis
        )
    else:
        return await _retrieve_standard_context(
            query, category, repo, primary_evidence, window_analysis
        )


async def _retrieve_with_background_context(
    query: str,
    category: Optional[str], 
    repo,
    primary_evidence: List[Dict],
    story_id: Optional[str],
    window_analysis: Dict
) -> Dict[str, Any]:
    """Retrieve both recent updates and historical background."""
    
    # Get recent evidence (last 24h for updates)
    recent_evidence = await enhanced_retrieve_evidence(query, category, repo, window_hours=24)
    
    # Get broader historical context (30 days)
    background_evidence = await enhanced_retrieve_evidence(query, category, repo, window_hours=720)
    
    # Remove overlap - keep items from background that aren't in recent
    recent_urls = {item.get('url', '') for item in recent_evidence}
    background_only = [
        item for item in background_evidence 
        if item.get('url', '') not in recent_urls
    ]
    
    # Organize by timeframe
    now = datetime.now(timezone.utc)
    context_sections = {
        'last_24h': recent_evidence,
        'background': background_only[:6],  # Limit background items
        'timeframe_split': now - timedelta(hours=24)
    }
    
    return {
        'recent_evidence': recent_evidence,
        'background_evidence': background_only[:6],
        'story_id': story_id,
        'window_analysis': window_analysis,
        'retrieval_strategy': 'background_context',
        'context_sections': context_sections
    }


async def _retrieve_immediate_context(
    query: str,
    category: Optional[str],
    repo,
    primary_evidence: List[Dict],
    window_analysis: Dict
) -> Dict[str, Any]:
    """Retrieve only the most recent updates for breaking news."""
    
    context_sections = {
        'breaking': primary_evidence,
        'timeframe_split': datetime.now(timezone.utc) - timedelta(hours=24)
    }
    
    return {
        'recent_evidence': primary_evidence,
        'background_evidence': [],
        'story_id': None,
        'window_analysis': window_analysis,
        'retrieval_strategy': 'immediate_breaking',
        'context_sections': context_sections
    }


async def _retrieve_standard_context(
    query: str,
    category: Optional[str],
    repo, 
    primary_evidence: List[Dict],
    window_analysis: Dict
) -> Dict[str, Any]:
    """Standard retrieval for general news queries."""
    
    context_sections = {
        'general': primary_evidence,
        'timeframe_split': datetime.now(timezone.utc) - timedelta(hours=window_analysis['window_hours'])
    }
    
    return {
        'recent_evidence': primary_evidence,
        'background_evidence': [],
        'story_id': None,
        'window_analysis': window_analysis, 
        'retrieval_strategy': 'standard',
        'context_sections': context_sections
    }


def organize_evidence_by_time(evidence: List[Dict], split_hours: int = 24) -> Dict[str, List[Dict]]:
    """
    Organize evidence into recent vs older timeframes.
    
    Args:
        evidence: List of evidence items
        split_hours: Hours cutoff for recent vs older
    
    Returns:
        {'recent': [...], 'older': [...]}
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=split_hours)
    recent = []
    older = []
    
    for item in evidence:
        published_str = item.get('published_at')
        if not published_str:
            older.append(item)  # No date = treat as older
            continue
            
        try:
            if isinstance(published_str, str):
                published_dt = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
            else:
                published_dt = published_str
                
            if published_dt >= cutoff:
                recent.append(item)
            else:
                older.append(item)
        except (ValueError, TypeError):
            older.append(item)  # Parse error = treat as older
    
    return {'recent': recent, 'older': older}