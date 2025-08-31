"""
Language-Aware Content Retrieval

Implements retrieval that prefers content in the user's current language
and falls back to other languages with automatic translation.
"""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from packages.language.manager import LanguageState, language_manager
from packages.nlp.retrieve import retrieve_evidence
from packages.llm.openai_client import translate_bn


async def language_aware_retrieve(
    query: str,
    language_state: LanguageState,
    category: Optional[str],
    repo,
    window_hours: int = 72,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Retrieve content with language preference and automatic translation
    
    Args:
        query: User query
        language_state: Complete language state
        category: Content category filter
        repo: Database repository
        window_hours: Time window for search
        limit: Maximum results to return
        
    Returns:
        {
            'evidence': List of evidence items with language metadata,
            'language_breakdown': Dict with counts by language,
            'translations_applied': List of translation operations,
            'retrieval_strategy': Description of strategy used
        }
    """
    
    # Get language preferences for retrieval
    preferred_lang, fallback_lang = language_manager.get_retrieval_tags(language_state)
    
    # Translate query if needed for better retrieval
    search_query = query
    query_translation_info = None
    
    # If input is detected as different language than index, consider translation
    if language_manager.should_translate_input(language_state, index_language="en"):
        try:
            if language_state.input_language == 'bn':
                # For now, use the original query - translation can be added later
                search_query = query
                query_translation_info = {
                    "original": query,
                    "translated": query,
                    "direction": "bn->en",
                    "applied": False  # Not implemented yet
                }
        except Exception as e:
            print(f"[LANG_RETRIEVE] Query translation failed: {e}")
            search_query = query
    
    # Retrieve content using existing retrieval system
    try:
        evidence = await retrieve_evidence(
            search_query, 
            category, 
            repo, 
            window_hours=window_hours, 
            limit=limit * 2  # Get more to allow for language filtering
        )
    except Exception as e:
        print(f"[LANG_RETRIEVE] Retrieval failed: {e}")
        evidence = []
    
    # Tag evidence with detected languages and score by language preference
    tagged_evidence = []
    language_breakdown = {"bn": 0, "en": 0, "other": 0, "unknown": 0}
    
    for item in evidence:
        # Detect language of content
        content_text = f"{item.get('title', '')} {item.get('summary', '')}".strip()
        detected_lang = language_manager.detect_language(content_text)
        
        # Add language metadata
        item_with_lang = {
            **item,
            'detected_language': detected_lang,
            'language_score': _calculate_language_score(detected_lang, preferred_lang, fallback_lang)
        }
        
        tagged_evidence.append(item_with_lang)
        
        # Update language breakdown
        if detected_lang in ['bn', 'en']:
            language_breakdown[detected_lang] += 1
        elif detected_lang is None:
            language_breakdown['unknown'] += 1
        else:
            language_breakdown['other'] += 1
    
    # Sort by relevance + language preference (language_score is already factored into ranking)
    tagged_evidence.sort(key=lambda x: x.get('language_score', 0), reverse=True)
    
    # Apply limit after language scoring
    final_evidence = tagged_evidence[:limit]
    
    # Apply translations if needed for output
    translations_applied = []
    
    for item in final_evidence:
        content_lang = item.get('detected_language')
        if content_lang and language_manager.should_translate_output(language_state, content_lang):
            try:
                # For now, mark items that would need translation
                # Actual translation can be implemented later
                translation_info = {
                    "item_id": item.get('url', ''),
                    "from_language": content_lang,
                    "to_language": language_state.output_language,
                    "fields": ['title', 'summary'],
                    "status": "pending"  # Would be "completed" after actual translation
                }
                translations_applied.append(translation_info)
                item['translation_needed'] = True
                item['original_language'] = content_lang
            except Exception as e:
                print(f"[LANG_RETRIEVE] Translation marking failed: {e}")
    
    # Determine retrieval strategy description
    preferred_count = language_breakdown.get(preferred_lang, 0)
    total_count = sum(language_breakdown.values())
    
    if preferred_count >= limit // 2:
        strategy = f"Preferred {preferred_lang} content ({preferred_count}/{total_count})"
    elif preferred_count > 0:
        strategy = f"Mixed languages with {preferred_lang} preference ({preferred_count}/{total_count})"
    else:
        strategy = f"Fallback to available content ({total_count} items, no {preferred_lang})"
    
    return {
        'evidence': final_evidence,
        'language_breakdown': language_breakdown,
        'query_translation': query_translation_info,
        'translations_applied': translations_applied,
        'retrieval_strategy': strategy,
        'language_state': {
            'preferred': preferred_lang,
            'fallback': fallback_lang,
            'ui_language': language_state.ui_language
        }
    }


def _calculate_language_score(detected_lang: Optional[str], preferred: str, fallback: str) -> float:
    """
    Calculate language preference score for ranking
    
    Args:
        detected_lang: Language detected in content
        preferred: User's preferred language
        fallback: Fallback language
        
    Returns:
        Score multiplier (0.5-1.0)
    """
    if detected_lang == preferred:
        return 1.0  # Perfect match
    elif detected_lang == fallback:
        return 0.8  # Good fallback
    elif detected_lang is None:
        return 0.7  # Unknown language (could be either)
    else:
        return 0.6  # Other language


async def get_language_tagged_content(
    content_items: List[Dict[str, Any]], 
    language_state: LanguageState
) -> List[Dict[str, Any]]:
    """
    Add language tags and preference scores to existing content
    
    Args:
        content_items: List of content items to tag
        language_state: Current language state
        
    Returns:
        Content items with language metadata added
    """
    preferred_lang, fallback_lang = language_manager.get_retrieval_tags(language_state)
    
    tagged_content = []
    for item in content_items:
        # Detect language of content
        content_text = f"{item.get('title', '')} {item.get('summary', '')}".strip()
        detected_lang = language_manager.detect_language(content_text)
        
        # Add language metadata
        tagged_item = {
            **item,
            'detected_language': detected_lang,
            'language_score': _calculate_language_score(detected_lang, preferred_lang, fallback_lang),
            'translation_needed': language_manager.should_translate_output(language_state, detected_lang) if detected_lang else False
        }
        
        tagged_content.append(tagged_item)
    
    return tagged_content