import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass

from packages.observability import get_logger, get_metrics

@dataclass
class QualityCheckResult:
    """Result of a quality guardrail check"""
    passed: bool
    reason: str
    details: Dict[str, Any]

class QualityGuardrails:
    """Quality guardrails to prevent hallucinations and ensure recency"""
    
    def __init__(self, time_window_hours: int = 24):
        self.time_window_hours = time_window_hours
        self.logger = get_logger()
        self.metrics = get_metrics()
        
        # Patterns for factual sentences that need verification
        self.factual_patterns = [
            r'\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:%|percent|percentage))',  # Percentages
            r'\$\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:million|billion|trillion|k))?',  # Money
            r'\d+(?:,\d{3})*(?:\.\d+)?\s*(?:people|person|individuals|deaths|casualties)',  # Counts
            r'\d{1,2}[:/]\d{1,2}(?:[:/]\d{2,4})?',  # Dates/times
            r'\d+(?:\.\d+)?\s*(?:years?|months?|days?|hours?)',  # Durations
            r'\d+(?:,\d{3})*(?:\.\d+)?\s*(?:degrees?|°[CF]?)',  # Temperatures
            r'\d+(?:,\d{3})*(?:\.\d+)?',  # General numbers
        ]
        
        # Numeric markers that indicate factual claims
        self.numeric_markers = [
            r'\d+', r'increase[ds]?', r'decrease[ds]?', r'rose', r'fell', r'dropped',
            r'higher', r'lower', r'more', r'less', r'grew', r'shrank', r'up', r'down',
            r'বৃদ্ধি', r'হ্রাস', r'বেড়েছে', r'কমেছে', r'বেশি', r'কম'
        ]
        
        # Trivial claim patterns that don't need multiple sources
        self.trivial_patterns = [
            r'today\s+is',
            r'the\s+weather\s+is',
            r'আজ\s+',
            r'আবহাওয়া\s+'
        ]
    
    def check_factual_sentences_have_markers(self, summary_text: str) -> QualityCheckResult:
        """Check that every factual sentence has at least one numeric marker"""
        if not summary_text:
            return QualityCheckResult(
                passed=False,
                reason="Empty summary text",
                details={"text_length": 0}
            )
        
        sentences = self._split_into_sentences(summary_text)
        factual_sentences = []
        sentences_without_markers = []
        
        for sentence in sentences:
            if self._is_factual_sentence(sentence):
                factual_sentences.append(sentence)
                if not self._has_numeric_marker(sentence):
                    sentences_without_markers.append(sentence)
        
        passed = len(sentences_without_markers) == 0
        
        result = QualityCheckResult(
            passed=passed,
            reason="Factual sentences missing numeric markers" if not passed else "All factual sentences have numeric markers",
            details={
                "total_sentences": len(sentences),
                "factual_sentences": len(factual_sentences),
                "sentences_without_markers": len(sentences_without_markers),
                "problematic_sentences": sentences_without_markers[:3]  # First 3 for debugging
            }
        )
        
        self.metrics.record_quality_check("factual_markers", passed)
        self.logger.log_quality_check("factual_markers", passed, result.reason)
        
        return result
    
    def check_non_trivial_claims_have_multiple_sources(self, summary_text: str, 
                                                     evidence: List[Dict[str, Any]]) -> QualityCheckResult:
        """Check that non-trivial claims are supported by at least 2 sources"""
        if not evidence:
            return QualityCheckResult(
                passed=False,
                reason="No evidence sources provided",
                details={"source_count": 0}
            )
        
        source_count = len(evidence)
        
        # Extract non-trivial claims from summary
        non_trivial_claims = self._extract_non_trivial_claims(summary_text)
        
        # If there are non-trivial claims and only 1 source, fail
        has_non_trivial = len(non_trivial_claims) > 0
        sufficient_sources = source_count >= 2 or not has_non_trivial
        
        passed = sufficient_sources
        
        reason = ""
        if not passed:
            reason = f"Non-trivial claims require ≥2 sources (found {source_count})"
        else:
            if has_non_trivial:
                reason = f"Non-trivial claims supported by {source_count} sources"
            else:
                reason = "Only trivial claims found, single source acceptable"
        
        result = QualityCheckResult(
            passed=passed,
            reason=reason,
            details={
                "source_count": source_count,
                "non_trivial_claims_found": len(non_trivial_claims),
                "has_non_trivial_claims": has_non_trivial,
                "sample_claims": non_trivial_claims[:3]  # First 3 for debugging
            }
        )
        
        self.metrics.record_quality_check("multiple_sources", passed)
        self.logger.log_quality_check("multiple_sources", passed, result.reason)
        
        return result
    
    def check_sources_within_time_window(self, evidence: List[Dict[str, Any]]) -> QualityCheckResult:
        """Check that cited sources fall within the time window unless marked as background"""
        if not evidence:
            return QualityCheckResult(
                passed=False,
                reason="No evidence sources to check",
                details={"source_count": 0}
            )
        
        current_time = datetime.now(timezone.utc)
        cutoff_time = current_time - timedelta(hours=self.time_window_hours)
        
        sources_checked = 0
        sources_within_window = 0
        sources_outside_window = []
        background_sources = 0
        
        for item in evidence:
            published_at = item.get('published_at')
            outlet = item.get('outlet', 'Unknown')
            title = item.get('title', '')
            
            # Skip sources marked as background (in title or marked explicitly)
            is_background = (
                'background' in title.lower() or 
                'context' in title.lower() or
                item.get('is_background', False)
            )
            
            if is_background:
                background_sources += 1
                continue
            
            sources_checked += 1
            
            if not published_at:
                sources_outside_window.append({
                    'outlet': outlet,
                    'title': title[:100],
                    'reason': 'No published_at timestamp'
                })
                continue
            
            try:
                if isinstance(published_at, str):
                    # Parse ISO format timestamp
                    pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                else:
                    pub_dt = published_at
                
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                
                if pub_dt >= cutoff_time:
                    sources_within_window += 1
                else:
                    age_hours = (current_time - pub_dt).total_seconds() / 3600
                    sources_outside_window.append({
                        'outlet': outlet,
                        'title': title[:100],
                        'reason': f'Published {age_hours:.1f}h ago (>{self.time_window_hours}h cutoff)'
                    })
                    
            except Exception as e:
                sources_outside_window.append({
                    'outlet': outlet,
                    'title': title[:100],
                    'reason': f'Invalid timestamp: {e}'
                })
        
        # Pass if all checked sources are within window
        passed = len(sources_outside_window) == 0
        
        result = QualityCheckResult(
            passed=passed,
            reason=f"{sources_within_window}/{sources_checked} sources within {self.time_window_hours}h window" if passed else f"{len(sources_outside_window)} sources outside time window",
            details={
                "time_window_hours": self.time_window_hours,
                "sources_checked": sources_checked,
                "sources_within_window": sources_within_window,
                "sources_outside_window": len(sources_outside_window),
                "background_sources": background_sources,
                "outdated_sources": sources_outside_window[:3]  # First 3 for debugging
            }
        )
        
        self.metrics.record_quality_check("time_window", passed)
        self.logger.log_quality_check("time_window", passed, result.reason)
        
        return result
    
    def run_all_checks(self, summary_text: str, evidence: List[Dict[str, Any]]) -> Dict[str, QualityCheckResult]:
        """Run all quality checks and return results"""
        self.logger.log_structured("INFO", "quality_checks_start", 
                                 summary_length=len(summary_text),
                                 evidence_count=len(evidence))
        
        checks = {
            "factual_markers": self.check_factual_sentences_have_markers(summary_text),
            "multiple_sources": self.check_non_trivial_claims_have_multiple_sources(summary_text, evidence),
            "time_window": self.check_sources_within_time_window(evidence)
        }
        
        all_passed = all(check.passed for check in checks.values())
        failed_checks = [name for name, check in checks.items() if not check.passed]
        
        self.logger.log_structured("INFO", "quality_checks_complete",
                                 all_passed=all_passed,
                                 failed_checks=failed_checks,
                                 check_count=len(checks))
        
        return checks
    
    def should_refuse(self, checks: Dict[str, QualityCheckResult]) -> Tuple[bool, str]:
        """Determine if request should be refused based on quality checks"""
        failed_checks = [(name, check) for name, check in checks.items() if not check.passed]
        
        if not failed_checks:
            return False, ""
        
        # Create refusal message based on failed checks
        refusal_reasons = []
        for check_name, check in failed_checks:
            refusal_reasons.append(check.reason)
        
        should_refuse = True
        refusal_message = "Unable to provide reliable information: " + "; ".join(refusal_reasons)
        
        return should_refuse, refusal_message
    
    def create_polite_refusal(self, refusal_reason: str, stage: str = "quality_check") -> Dict[str, Any]:
        """Create polite refusal response with low confidence"""
        self.metrics.record_refusal(refusal_reason[:50], stage)  # Truncate reason for metrics
        self.logger.log_refusal(refusal_reason, stage)
        
        return {
            "summary": "I apologize, but I cannot provide a reliable answer to your query at this time. The available sources don't meet our quality standards for accuracy and recency.",
            "confidence": {
                "level": "low",
                "score": 0.1,
                "rationale": refusal_reason
            },
            "sources": [],
            "was_refused": True,
            "refusal_reason": refusal_reason,
            "refusal_stage": stage
        }
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting - could be enhanced with NLP libraries
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _is_factual_sentence(self, sentence: str) -> bool:
        """Check if sentence contains factual claims that need verification"""
        sentence_lower = sentence.lower()
        
        # Skip trivial sentences
        for pattern in self.trivial_patterns:
            if re.search(pattern, sentence_lower):
                return False
        
        # Check for factual patterns
        for pattern in self.factual_patterns:
            if re.search(pattern, sentence):
                return True
        
        # Check for factual keywords
        factual_keywords = [
            'according to', 'reported', 'announced', 'confirmed', 'stated',
            'increased', 'decreased', 'rose', 'fell', 'reached', 'hit',
            'published', 'revealed', 'showed', 'found', 'discovered',
            'অনুযায়ী', 'প্রতিবেদন', 'ঘোষণা', 'নিশ্চিত', 'বলেছে',
            'বৃদ্ধি', 'হ্রাস', 'বেড়েছে', 'কমেছে', 'পৌঁছেছে'
        ]
        
        return any(keyword in sentence_lower for keyword in factual_keywords)
    
    def _has_numeric_marker(self, sentence: str) -> bool:
        """Check if sentence has numeric markers indicating factual claims"""
        for pattern in self.numeric_markers:
            if re.search(pattern, sentence, re.IGNORECASE):
                return True
        return False
    
    def _extract_non_trivial_claims(self, text: str) -> List[str]:
        """Extract non-trivial claims from text"""
        sentences = self._split_into_sentences(text)
        non_trivial_claims = []
        
        for sentence in sentences:
            if self._is_factual_sentence(sentence) and not self._is_trivial_claim(sentence):
                non_trivial_claims.append(sentence)
        
        return non_trivial_claims
    
    def _is_trivial_claim(self, sentence: str) -> bool:
        """Check if claim is trivial (doesn't need multiple sources)"""
        sentence_lower = sentence.lower()
        
        for pattern in self.trivial_patterns:
            if re.search(pattern, sentence_lower):
                return True
        
        # Weather observations, time statements, etc.
        trivial_keywords = [
            'weather is', 'temperature is', 'it is raining', 'sunny today',
            'currently', 'right now', 'at this moment',
            'আবহাওয়া', 'তাপমাত্রা', 'বৃষ্টি হচ্ছে', 'রৌদ্র'
        ]
        
        return any(keyword in sentence_lower for keyword in trivial_keywords)

# Global guardrails instance
_global_guardrails = None

def get_guardrails(time_window_hours: int = 24) -> QualityGuardrails:
    """Get global quality guardrails instance"""
    global _global_guardrails
    if _global_guardrails is None:
        _global_guardrails = QualityGuardrails(time_window_hours)
    return _global_guardrails

def check_quality_and_refuse_if_needed(summary_text: str, evidence: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    """
    Convenience function to check quality and create refusal if needed
    
    Returns:
        (should_refuse, response_or_refusal)
    """
    guardrails = get_guardrails()
    checks = guardrails.run_all_checks(summary_text, evidence)
    should_refuse, refusal_reason = guardrails.should_refuse(checks)
    
    if should_refuse:
        refusal_response = guardrails.create_polite_refusal(refusal_reason)
        return True, refusal_response
    
    return False, {"quality_checks": checks}