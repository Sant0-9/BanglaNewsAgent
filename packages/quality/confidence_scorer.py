from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Set, Optional, Tuple
import re
from collections import defaultdict

from packages.util.normalize import extract_domain

class TrustworthyConfidenceScorer:
    """
    Trustworthy confidence scoring based on source quality and consistency.
    
    Confidence levels:
    - high: ≥3 reputable sources within 24h, no major contradictions
    - medium: 2 sources or minor discrepancies  
    - low: 1 source or explicit contradictions/refusal
    """
    
    def __init__(self):
        # Define reputable source tiers
        self.tier1_sources = {
            # International tier 1
            'reuters.com', 'ap.org', 'bbc.com', 'bbc.co.uk', 'bloomberg.com',
            'cnn.com', 'wsj.com', 'ft.com', 'theguardian.com', 'washingtonpost.com',
            'nytimes.com', 'economist.com', 'aljazeera.com', 'dw.com',
            
            # Bangladesh tier 1
            'prothomalo.com', 'thedailystar.net', 'bdnews24.com', 'newagebd.net',
            'dhakatribune.com', 'tbsnews.net', 'risingbd.com', 'dailysun.com'
        }
        
        self.tier2_sources = {
            # International tier 2
            'abcnews.go.com', 'cbsnews.com', 'nbcnews.com', 'usatoday.com',
            'independent.co.uk', 'telegraph.co.uk', 'france24.com', 'euronews.com',
            
            # Bangladesh tier 2
            'jugantor.com', 'ittefaq.com.bd', 'kalerkantho.com', 'banglanews24.com',
            'samakal.com', 'barta24.com', 'jagonews24.com'
        }
    
    def get_source_tier(self, outlet: str) -> int:
        """Get source reputation tier (1=highest, 3=lowest)"""
        if not outlet:
            return 3
            
        domain = extract_domain(outlet.lower())
        
        # Check if domain matches tier 1 sources
        for tier1_domain in self.tier1_sources:
            if tier1_domain in domain or domain.endswith(tier1_domain):
                return 1
        
        # Check if domain matches tier 2 sources
        for tier2_domain in self.tier2_sources:
            if tier2_domain in domain or domain.endswith(tier2_domain):
                return 2
        
        # Default to tier 3 for unknown sources
        return 3
    
    def is_recent_source(self, published_at: Any, hours_threshold: int = 24) -> bool:
        """Check if source is within time threshold"""
        if not published_at:
            return False
        
        try:
            if isinstance(published_at, str):
                dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            else:
                dt = published_at
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            hours_old = (now - dt).total_seconds() / 3600.0
            
            return hours_old <= hours_threshold
            
        except Exception:
            return False
    
    def extract_factual_claims(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract factual claims from text for contradiction analysis.
        
        Returns:
            List of claims with metadata for comparison
        """
        if not text:
            return []
        
        claims = []
        
        # Extract numeric facts (dates, percentages, amounts, etc.)
        numeric_patterns = [
            (r'\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:%|percent|percentage))', 'percentage'),
            (r'\$\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:million|billion|trillion|k))?', 'money'),
            (r'\d+(?:,\d{3})*(?:\.\d+)?\s*(?:people|person|individuals|deaths|casualties)', 'count'),
            (r'\d{1,2}[:/]\d{1,2}(?:[:/]\d{2,4})?', 'time_date'),
            (r'\d+(?:\.\d+)?\s*(?:years?|months?|days?|hours?)', 'duration'),
            (r'\d+(?:,\d{3})*(?:\.\d+)?', 'number')
        ]
        
        for pattern, claim_type in numeric_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                claims.append({
                    'type': claim_type,
                    'value': match.group().strip(),
                    'position': match.span(),
                    'context': text[max(0, match.start()-50):match.end()+50].strip()
                })
        
        # Extract key entity mentions (names, organizations, locations)
        entity_patterns = [
            (r'[A-Z][a-z]+\s+[A-Z][a-z]+', 'person_name'),
            (r'[A-Z][A-Z]+(?:\s+[A-Z][A-Z]+)*', 'organization'),  # Acronyms
            (r'(?:President|Prime Minister|Minister|CEO|Director)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', 'official')
        ]
        
        for pattern, claim_type in entity_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                claims.append({
                    'type': claim_type,
                    'value': match.group().strip(),
                    'position': match.span(),
                    'context': text[max(0, match.start()-30):match.end()+30].strip()
                })
        
        return claims
    
    def detect_contradictions(self, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect contradictions between sources.
        
        Args:
            evidence: List of evidence items with titles, excerpts, outlets
            
        Returns:
            Contradiction analysis results
        """
        if len(evidence) < 2:
            return {
                'has_contradictions': False,
                'contradiction_count': 0,
                'conflicting_claims': [],
                'agreement_score': 1.0
            }
        
        # Extract claims from all sources
        all_claims = []
        source_claims = {}
        
        for i, item in enumerate(evidence):
            text = f"{item.get('title', '')} {item.get('excerpt', '')}"
            claims = self.extract_factual_claims(text)
            
            source_claims[i] = claims
            for claim in claims:
                claim['source_index'] = i
                claim['outlet'] = item.get('outlet', 'Unknown')
                all_claims.append(claim)
        
        # Group similar claims by type and value similarity
        claim_groups = defaultdict(list)
        for claim in all_claims:
            key = f"{claim['type']}_{claim['value'][:20]}"  # First 20 chars for grouping
            claim_groups[key].append(claim)
        
        # Detect contradictions
        contradictions = []
        conflicting_claims = []
        
        for claim_type in ['percentage', 'money', 'count', 'number']:
            type_claims = [c for c in all_claims if c['type'] == claim_type]
            if len(type_claims) >= 2:
                # Check for numeric disagreements
                values = []
                for claim in type_claims:
                    try:
                        # Extract numeric value
                        numeric_str = re.sub(r'[^\d.]', '', claim['value'])
                        if numeric_str:
                            values.append((float(numeric_str), claim))
                    except ValueError:
                        continue
                
                if len(values) >= 2:
                    # Check if values are significantly different
                    sorted_values = sorted(values)
                    min_val, min_claim = sorted_values[0]
                    max_val, max_claim = sorted_values[-1]
                    
                    if min_val > 0 and (max_val / min_val) > 1.5:  # 50% difference threshold
                        contradictions.append({
                            'type': 'numeric_disagreement',
                            'claim_type': claim_type,
                            'min_value': min_val,
                            'max_value': max_val,
                            'sources': [min_claim['outlet'], max_claim['outlet']],
                            'contexts': [min_claim['context'], max_claim['context']]
                        })
                        
                        conflicting_claims.extend([min_claim, max_claim])
        
        # Calculate agreement score
        total_claims = len(all_claims)
        conflicting_claim_count = len(conflicting_claims)
        agreement_score = 1.0 - (conflicting_claim_count / max(total_claims, 1))
        
        return {
            'has_contradictions': len(contradictions) > 0,
            'contradiction_count': len(contradictions),
            'conflicting_claims': conflicting_claims,
            'contradictions': contradictions,
            'agreement_score': agreement_score,
            'total_claims_analyzed': total_claims
        }
    
    def calculate_confidence(self, evidence: List[Dict[str, Any]], 
                           summary_text: str = "",
                           was_refused: bool = False) -> Dict[str, Any]:
        """
        Calculate trustworthy confidence score based on evidence quality.
        
        Args:
            evidence: List of evidence items
            summary_text: Generated summary text
            was_refused: Whether the request was refused due to insufficient sources
            
        Returns:
            Confidence assessment with level, score, and rationale
        """
        if was_refused or not evidence:
            return {
                'level': 'low',
                'score': 0.1,
                'rationale': 'Request refused due to insufficient credible sources',
                'source_analysis': {
                    'total_sources': len(evidence),
                    'reputable_sources': 0,
                    'recent_sources': 0,
                    'tier1_count': 0,
                    'tier2_count': 0
                }
            }
        
        # Analyze sources
        source_analysis = {
            'total_sources': len(evidence),
            'reputable_sources': 0,  # Tier 1 + Tier 2
            'recent_sources': 0,     # Within 24h
            'tier1_count': 0,
            'tier2_count': 0,
            'tier3_count': 0,
            'unique_domains': set()
        }
        
        tier1_recent = 0
        tier2_recent = 0
        
        for item in evidence:
            outlet = item.get('outlet', '')
            published_at = item.get('published_at')
            
            # Analyze source tier
            tier = self.get_source_tier(outlet)
            if tier == 1:
                source_analysis['tier1_count'] += 1
                source_analysis['reputable_sources'] += 1
                if self.is_recent_source(published_at):
                    tier1_recent += 1
            elif tier == 2:
                source_analysis['tier2_count'] += 1
                source_analysis['reputable_sources'] += 1
                if self.is_recent_source(published_at):
                    tier2_recent += 1
            else:
                source_analysis['tier3_count'] += 1
            
            # Check recency
            if self.is_recent_source(published_at):
                source_analysis['recent_sources'] += 1
            
            # Track unique domains
            domain = extract_domain(outlet)
            source_analysis['unique_domains'].add(domain)
        
        # Convert unique domains to count for JSON serialization
        source_analysis['unique_domains_count'] = len(source_analysis['unique_domains'])
        del source_analysis['unique_domains']
        
        # Detect contradictions
        contradiction_analysis = self.detect_contradictions(evidence)
        
        # Calculate confidence level and score
        confidence_score = 0.0
        rationale_parts = []
        
        # Source quality scoring
        tier1_weight = source_analysis['tier1_count'] * 0.4
        tier2_weight = source_analysis['tier2_count'] * 0.25
        tier3_weight = source_analysis['tier3_count'] * 0.1
        source_quality_score = min(tier1_weight + tier2_weight + tier3_weight, 1.0)
        confidence_score += source_quality_score * 0.4
        
        # Recency scoring  
        recent_ratio = source_analysis['recent_sources'] / max(len(evidence), 1)
        recency_score = min(recent_ratio * 1.2, 1.0)  # Bonus for recent sources
        confidence_score += recency_score * 0.3
        
        # Contradiction penalty
        agreement_bonus = contradiction_analysis['agreement_score']
        confidence_score += agreement_bonus * 0.3
        
        # Normalize to 0-1 range
        confidence_score = min(confidence_score, 1.0)
        
        # Determine confidence level and rationale
        if confidence_score >= 0.8 and source_analysis['reputable_sources'] >= 3 and not contradiction_analysis['has_contradictions']:
            level = 'high'
            rationale_parts.append(f"≥3 reputable sources ({source_analysis['reputable_sources']})")
            if source_analysis['recent_sources'] >= 3:
                rationale_parts.append("within 24h")
            if not contradiction_analysis['has_contradictions']:
                rationale_parts.append("no contradictions")
                
        elif confidence_score >= 0.5 and source_analysis['reputable_sources'] >= 2:
            level = 'medium'
            rationale_parts.append(f"2+ sources ({source_analysis['reputable_sources']})")
            if contradiction_analysis['has_contradictions']:
                rationale_parts.append("minor discrepancies detected")
            else:
                rationale_parts.append("consistent information")
                
        else:
            level = 'low'
            if source_analysis['reputable_sources'] <= 1:
                rationale_parts.append("≤1 reputable source")
            if contradiction_analysis['has_contradictions']:
                rationale_parts.append("contradictions detected")
            if source_analysis['recent_sources'] == 0:
                rationale_parts.append("no recent sources")
        
        rationale = "; ".join(rationale_parts) if rationale_parts else "insufficient evidence quality"
        
        return {
            'level': level,
            'score': round(confidence_score, 3),
            'rationale': rationale,
            'source_analysis': source_analysis,
            'contradiction_analysis': {
                'has_contradictions': contradiction_analysis['has_contradictions'],
                'contradiction_count': contradiction_analysis['contradiction_count'],
                'agreement_score': round(contradiction_analysis['agreement_score'], 3)
            }
        }
    
    def get_confidence_badge_info(self, confidence_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Get UI badge information for confidence display.
        
        Args:
            confidence_data: Output from calculate_confidence()
            
        Returns:
            Badge display information
        """
        level = confidence_data['level']
        score = confidence_data['score']
        
        if level == 'high':
            return {
                'color': 'green',
                'text': 'High Confidence',
                'icon': '🟢',
                'description': 'Multiple reputable sources, recent, no contradictions'
            }
        elif level == 'medium':
            return {
                'color': 'orange', 
                'text': 'Medium Confidence',
                'icon': '🟡',
                'description': 'Limited sources or minor discrepancies'
            }
        else:
            return {
                'color': 'red',
                'text': 'Low Confidence',
                'icon': '🔴',
                'description': 'Single source, contradictions, or outdated information'
            }


# Global instance
_confidence_scorer = None

def get_confidence_scorer() -> TrustworthyConfidenceScorer:
    """Get global confidence scorer instance"""
    global _confidence_scorer
    if _confidence_scorer is None:
        _confidence_scorer = TrustworthyConfidenceScorer()
    return _confidence_scorer

def calculate_trustworthy_confidence(evidence: List[Dict[str, Any]], 
                                   summary_text: str = "",
                                   was_refused: bool = False) -> Dict[str, Any]:
    """
    Convenience function to calculate trustworthy confidence.
    
    Args:
        evidence: List of evidence items
        summary_text: Generated summary text
        was_refused: Whether request was refused
        
    Returns:
        Confidence assessment
    """
    scorer = get_confidence_scorer()
    return scorer.calculate_confidence(evidence, summary_text, was_refused)