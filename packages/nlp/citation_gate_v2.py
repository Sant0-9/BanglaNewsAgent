import re
from typing import Dict, List, Tuple, Optional


def extract_citations_from_sentence(sentence: str) -> List[int]:
    """Extract all citation numbers from a sentence."""
    pattern = re.compile(r"\[(\d+)\]")
    matches = pattern.findall(sentence)
    return [int(m) for m in matches if m.isdigit()]


def validate_citations(citations: List[int], max_id: int) -> List[int]:
    """Filter citations to only include valid ones (1 to max_id)."""
    return [c for c in citations if 1 <= c <= max_id]


def assess_sentence_confidence(sentence: str, max_id: int) -> Tuple[str, str, int]:
    """
    Assess a sentence and return processed version with confidence level.
    
    Returns:
        (processed_sentence, confidence_level, valid_citation_count)
    
    Confidence levels:
        "high": ≥2 valid citations
        "low": 1 valid citation  
        "drop": 0 valid citations (sentence should be dropped)
    """
    citations = extract_citations_from_sentence(sentence)
    valid_citations = validate_citations(citations, max_id)
    
    if len(valid_citations) >= 2:
        return sentence.strip(), "high", len(valid_citations)
    elif len(valid_citations) == 1:
        # Mark low confidence but keep the sentence
        if sentence.strip().endswith('.') or sentence.strip().endswith('।'):
            marked_sentence = sentence.strip()[:-1] + " [low confidence]" + sentence.strip()[-1]
        else:
            marked_sentence = sentence.strip() + " [low confidence]"
        return marked_sentence, "low", 1
    else:
        return sentence.strip(), "drop", 0


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences, handling both English and Bengali punctuation.
    More sophisticated than simple regex split to preserve sentence integrity.
    """
    if not text:
        return []
    
    # Split by sentence endings but preserve the punctuation
    # Handle both English (. ! ?) and Bengali (।) punctuation
    pattern = r'(?<=[.!?।])\s+'
    sentences = re.split(pattern, text.strip())
    
    # Clean up empty sentences and whitespace
    cleaned_sentences = []
    for sent in sentences:
        sent = sent.strip()
        if sent:
            cleaned_sentences.append(sent)
    
    return cleaned_sentences


def assess_content_quality(high_count: int, low_count: int, total_sources: int) -> Dict[str, any]:
    """
    Assess overall content quality and determine if we should return content or refuse.
    
    Args:
        high_count: Number of sentences with ≥2 citations
        low_count: Number of sentences with 1 citation
        total_sources: Total number of available sources
    
    Returns:
        Dict with 'action' ('return' or 'refuse') and 'reason'
    """
    # If we have some high-confidence content, return it
    if high_count > 0:
        return {'action': 'return', 'reason': 'sufficient_high_confidence'}
    
    # If we only have low-confidence content but multiple sources exist, return with warning
    if low_count > 0 and total_sources >= 2:
        return {'action': 'return', 'reason': 'low_confidence_but_multiple_sources'}
    
    # If very limited sources for non-trivial claims, refuse politely
    if total_sources < 2:
        return {'action': 'refuse', 'reason': 'insufficient_sources'}
    
    # If no valid content at all, refuse
    return {'action': 'refuse', 'reason': 'no_valid_content'}


def advanced_citation_gate(text: str, max_id: int, min_quality_threshold: int = 2) -> Dict[str, any]:
    """
    Advanced citation filtering with sentence-level analysis and confidence marking.
    
    Args:
        text: Input text with citations
        max_id: Maximum valid citation ID
        min_quality_threshold: Minimum number of sources needed for non-trivial claims
    
    Returns:
        Dict with:
        - 'text': Processed text (empty if refused)
        - 'action': 'return' or 'refuse'
        - 'confidence_stats': Statistics about confidence levels
        - 'reason': Why content was returned or refused
        - 'should_mark_low_confidence': Whether response has low-confidence claims
    """
    if not text or max_id <= 0:
        return {
            'text': '',
            'action': 'refuse',
            'confidence_stats': {'high': 0, 'low': 0, 'dropped': 0},
            'reason': 'empty_input',
            'should_mark_low_confidence': False
        }
    
    sentences = split_into_sentences(text)
    
    if not sentences:
        return {
            'text': '',
            'action': 'refuse', 
            'confidence_stats': {'high': 0, 'low': 0, 'dropped': 0},
            'reason': 'no_sentences',
            'should_mark_low_confidence': False
        }
    
    processed_sentences = []
    confidence_stats = {'high': 0, 'low': 0, 'dropped': 0}
    
    # Process each sentence
    for sentence in sentences:
        processed_sentence, confidence, citation_count = assess_sentence_confidence(sentence, max_id)
        
        if confidence == 'drop':
            confidence_stats['dropped'] += 1
            # Skip this sentence entirely
            continue
        elif confidence == 'low':
            confidence_stats['low'] += 1
            processed_sentences.append(processed_sentence)
        elif confidence == 'high':
            confidence_stats['high'] += 1
            processed_sentences.append(processed_sentence)
    
    # Assess overall quality
    quality_assessment = assess_content_quality(
        confidence_stats['high'], 
        confidence_stats['low'], 
        max_id
    )
    
    # Determine final response
    if quality_assessment['action'] == 'refuse':
        return {
            'text': '',
            'action': 'refuse',
            'confidence_stats': confidence_stats,
            'reason': quality_assessment['reason'],
            'should_mark_low_confidence': False
        }
    
    # Return processed content
    final_text = ' '.join(processed_sentences).strip()
    
    return {
        'text': final_text,
        'action': 'return',
        'confidence_stats': confidence_stats,
        'reason': quality_assessment['reason'],
        'should_mark_low_confidence': confidence_stats['low'] > 0
    }


def create_polite_refusal(reason: str, lang: str = "en") -> str:
    """Create a polite refusal message based on the reason."""
    
    if lang == "bn":
        refusal_messages = {
            'insufficient_sources': "দুঃখিত, এই বিষয়ে পর্যাপ্ত নির্ভরযোগ্য সূত্র পাওয়া যায়নি। আরও তথ্যের জন্য অনুগ্রহ করে পরে আবার চেষ্টা করুন।",
            'no_valid_content': "দুঃখিত, প্রদত্ত সূত্রগুলো থেকে যথেষ্ট নির্ভরযোগ্য তথ্য সংকলন করা সম্ভব হয়নি।",
            'empty_input': "দুঃখিত, কোনো তথ্য প্রক্রিয়া করার জন্য পাওয়া যায়নি।",
            'no_sentences': "দুঃখিত, প্রদত্ত তথ্য থেকে কোনো অর্থবহ বাক্য গঠন করা যায়নি।"
        }
    else:
        refusal_messages = {
            'insufficient_sources': "I apologize, but there aren't enough reliable sources available on this topic. Please try again later for more comprehensive coverage.",
            'no_valid_content': "I apologize, but I couldn't compile sufficiently reliable information from the available sources.",
            'empty_input': "I apologize, but no content was available to process.",
            'no_sentences': "I apologize, but I couldn't form coherent sentences from the available information."
        }
    
    return refusal_messages.get(reason, refusal_messages['no_valid_content'])


# Backward compatibility wrapper
def citation_gate(text: str, max_id: int) -> str:
    """
    Backward-compatible wrapper for the old citation_gate function.
    Now uses advanced filtering but returns simple string for compatibility.
    """
    result = advanced_citation_gate(text, max_id)
    
    if result['action'] == 'refuse':
        return ""  # Return empty string to trigger existing fallback logic for now
    
    return result['text']