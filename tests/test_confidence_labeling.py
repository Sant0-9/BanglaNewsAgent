#!/usr/bin/env python3
"""
Unit tests for confidence labeling system
"""

import unittest
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

from packages.quality.confidence_scorer import TrustworthyConfidenceScorer, calculate_trustworthy_confidence

class TestConfidenceLabeling(unittest.TestCase):
    """Test confidence labeling logic and accuracy"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scorer = TrustworthyConfidenceScorer()
        self.current_time = datetime.now(timezone.utc)
    
    def create_test_evidence(self, count: int, outlets: List[str], hours_ago: List[int]) -> List[Dict[str, Any]]:
        """Helper to create test evidence with specific outlets and timing"""
        evidence = []
        for i in range(count):
            timestamp = self.current_time - timedelta(hours=hours_ago[i % len(hours_ago)])
            evidence.append({
                "title": f"Economic Report {i+1}: GDP Growth Analysis",
                "excerpt": f"Report {i+1} indicates GDP growth of {6.0 + i*0.1:.1f}% with detailed economic analysis.",
                "outlet": outlets[i % len(outlets)],
                "published_at": timestamp.isoformat(),
                "url": f"https://{outlets[i % len(outlets)]}/report{i+1}"
            })
        return evidence
    
    def test_high_confidence_criteria(self):
        """Test high confidence labeling (≥3 reputable sources, recent, no contradictions)"""
        # 3 tier-1 sources, all recent
        tier1_outlets = ["reuters.com", "bbc.com", "prothomalo.com"]
        evidence = self.create_test_evidence(3, tier1_outlets, [1, 2, 3])
        
        confidence = self.scorer.calculate_confidence(evidence)
        
        # Should be high confidence
        self.assertEqual(confidence["level"], "high")
        self.assertGreaterEqual(confidence["score"], 0.8)
        self.assertIn("3 reputable sources", confidence["rationale"])
        self.assertIn("no contradictions", confidence["rationale"])
        
        # Source analysis should show strong metrics
        source_analysis = confidence["source_analysis"]
        self.assertEqual(source_analysis["reputable_sources"], 3)
        self.assertEqual(source_analysis["recent_sources"], 3)
        self.assertEqual(source_analysis["tier1_count"], 3)
    
    def test_medium_confidence_criteria(self):
        """Test medium confidence labeling (2 sources or minor discrepancies)"""
        # 2 reputable sources, recent
        mixed_outlets = ["bloomberg.com", "thedailystar.net"]
        evidence = self.create_test_evidence(2, mixed_outlets, [2, 4])
        
        confidence = self.scorer.calculate_confidence(evidence)
        
        # Should be medium confidence
        self.assertEqual(confidence["level"], "medium")
        self.assertGreaterEqual(confidence["score"], 0.5)
        self.assertLess(confidence["score"], 0.8)
        self.assertIn("2+ sources", confidence["rationale"])
        
        # Source analysis should show adequate metrics
        source_analysis = confidence["source_analysis"]
        self.assertEqual(source_analysis["reputable_sources"], 2)
        self.assertEqual(source_analysis["recent_sources"], 2)
    
    def test_low_confidence_criteria(self):
        """Test low confidence labeling (≤1 source, contradictions, or outdated)"""
        # Single unknown source, old
        unknown_outlets = ["unknown-blog.com"]
        evidence = self.create_test_evidence(1, unknown_outlets, [48])  # 2 days old
        
        confidence = self.scorer.calculate_confidence(evidence)
        
        # Should be low confidence
        self.assertEqual(confidence["level"], "low")
        self.assertLess(confidence["score"], 0.5)
        
        # Source analysis should show weak metrics
        source_analysis = confidence["source_analysis"]
        self.assertEqual(source_analysis["reputable_sources"], 0)
        self.assertEqual(source_analysis["recent_sources"], 0)
        self.assertEqual(source_analysis["tier3_count"], 1)
    
    def test_source_tier_classification(self):
        """Test proper classification of source tiers"""
        test_outlets = [
            ("reuters.com", 1),
            ("prothomalo.com", 1),
            ("bbc.co.uk", 1),
            ("abcnews.go.com", 2),
            ("jugantor.com", 2),
            ("unknown-source.com", 3),
            ("random-blog.net", 3)
        ]
        
        for outlet, expected_tier in test_outlets:
            with self.subTest(outlet=outlet, expected_tier=expected_tier):
                tier = self.scorer.get_source_tier(outlet)
                self.assertEqual(tier, expected_tier, f"Wrong tier for {outlet}")
    
    def test_recency_impact_on_confidence(self):
        """Test how source recency affects confidence levels"""
        tier1_outlets = ["reuters.com", "bloomberg.com", "prothomalo.com"]
        
        # Recent sources (within 24h)
        recent_evidence = self.create_test_evidence(3, tier1_outlets, [1, 6, 12])
        recent_confidence = self.scorer.calculate_confidence(recent_evidence)
        
        # Old sources (48-72h ago)
        old_evidence = self.create_test_evidence(3, tier1_outlets, [48, 60, 72])
        old_confidence = self.scorer.calculate_confidence(old_evidence)
        
        # Recent sources should have higher confidence
        self.assertGreater(recent_confidence["score"], old_confidence["score"])
        
        # Recent should likely be high, old should be medium/low
        self.assertEqual(recent_confidence["level"], "high")
        self.assertIn(old_confidence["level"], ["medium", "low"])
    
    def test_contradiction_detection_impact(self):
        """Test how contradictions affect confidence levels"""
        # Create evidence with contradictory numeric claims
        contradictory_evidence = [
            {
                "title": "GDP Growth Reaches 6.2%",
                "excerpt": "Official data shows GDP expanded by 6.2% in the third quarter.",
                "outlet": "reuters.com",
                "published_at": (self.current_time - timedelta(hours=2)).isoformat(),
                "url": "https://reuters.com/gdp1"
            },
            {
                "title": "Economic Growth Hits 8.5%",
                "excerpt": "Government reports show GDP growth accelerated to 8.5% this quarter.",
                "outlet": "bloomberg.com", 
                "published_at": (self.current_time - timedelta(hours=3)).isoformat(),
                "url": "https://bloomberg.com/gdp2"
            },
            {
                "title": "GDP Data Shows 6.1% Expansion",
                "excerpt": "Latest figures indicate economic growth of 6.1% for the quarter.",
                "outlet": "bbc.com",
                "published_at": (self.current_time - timedelta(hours=4)).isoformat(),
                "url": "https://bbc.com/gdp3"
            }
        ]
        
        confidence = self.scorer.calculate_confidence(contradictory_evidence)
        
        # Should detect contradictions and lower confidence
        contradiction_analysis = confidence["contradiction_analysis"]
        self.assertTrue(contradiction_analysis["has_contradictions"])
        self.assertGreater(contradiction_analysis["contradiction_count"], 0)
        self.assertLess(contradiction_analysis["agreement_score"], 1.0)
        
        # Confidence should be medium despite good sources due to contradictions
        self.assertEqual(confidence["level"], "medium")
        self.assertIn("discrepancies", confidence["rationale"])
    
    def test_refusal_confidence_labeling(self):
        """Test confidence labeling for refused requests"""
        # Test explicit refusal
        refused_confidence = self.scorer.calculate_confidence([], "", was_refused=True)
        
        self.assertEqual(refused_confidence["level"], "low")
        self.assertEqual(refused_confidence["score"], 0.1)
        self.assertIn("refused", refused_confidence["rationale"])
        
        # Source analysis should show zeros
        source_analysis = refused_confidence["source_analysis"]
        self.assertEqual(source_analysis["total_sources"], 0)
        self.assertEqual(source_analysis["reputable_sources"], 0)
    
    def test_mixed_source_tiers(self):
        """Test confidence with mixed source tiers"""
        # Mix of tier 1, 2, and 3 sources
        mixed_outlets = ["reuters.com", "jugantor.com", "unknown-blog.com"]
        evidence = self.create_test_evidence(3, mixed_outlets, [1, 2, 3])
        
        confidence = self.scorer.calculate_confidence(evidence)
        
        # Source analysis should show the mix
        source_analysis = confidence["source_analysis"]
        self.assertEqual(source_analysis["tier1_count"], 1)
        self.assertEqual(source_analysis["tier2_count"], 1)
        self.assertEqual(source_analysis["tier3_count"], 1)
        self.assertEqual(source_analysis["reputable_sources"], 2)  # Tier 1 + Tier 2
    
    def test_factual_claim_extraction(self):
        """Test extraction of factual claims for contradiction analysis"""
        test_text = "Bangladesh GDP grew by 6.5% in Q3 2024, with inflation at 3.2% and unemployment falling to 4.1%. The population reached 170 million people."
        
        claims = self.scorer.extract_factual_claims(test_text)
        
        # Should extract multiple numeric facts
        self.assertGreater(len(claims), 0)
        
        # Check for specific claim types
        claim_types = [claim["type"] for claim in claims]
        self.assertIn("percentage", claim_types)
        self.assertIn("count", claim_types)
        
        # Verify claim values
        percentage_claims = [claim for claim in claims if claim["type"] == "percentage"]
        self.assertGreater(len(percentage_claims), 0)
        
        # Should capture context around claims
        for claim in claims:
            self.assertIn("context", claim)
            self.assertIsInstance(claim["context"], str)
            self.assertGreater(len(claim["context"]), 0)
    
    def test_confidence_badge_info(self):
        """Test UI badge information generation"""
        # High confidence example
        high_evidence = self.create_test_evidence(3, ["reuters.com", "bbc.com", "bloomberg.com"], [1, 2, 3])
        high_confidence = self.scorer.calculate_confidence(high_evidence)
        high_badge = self.scorer.get_confidence_badge_info(high_confidence)
        
        self.assertEqual(high_badge["color"], "green")
        self.assertEqual(high_badge["text"], "High Confidence")
        self.assertEqual(high_badge["icon"], "🟢")
        
        # Medium confidence example
        medium_evidence = self.create_test_evidence(2, ["prothomalo.com", "thedailystar.net"], [1, 4])
        medium_confidence = self.scorer.calculate_confidence(medium_evidence)
        medium_badge = self.scorer.get_confidence_badge_info(medium_confidence)
        
        self.assertEqual(medium_badge["color"], "orange")
        self.assertEqual(medium_badge["text"], "Medium Confidence")
        self.assertEqual(medium_badge["icon"], "🟡")
        
        # Low confidence example
        low_evidence = self.create_test_evidence(1, ["unknown.com"], [48])
        low_confidence = self.scorer.calculate_confidence(low_evidence)
        low_badge = self.scorer.get_confidence_badge_info(low_confidence)
        
        self.assertEqual(low_badge["color"], "red")
        self.assertEqual(low_badge["text"], "Low Confidence")
        self.assertEqual(low_badge["icon"], "🔴")
    
    def test_confidence_score_calculation_components(self):
        """Test individual components of confidence score calculation"""
        # Test with known good evidence
        tier1_evidence = self.create_test_evidence(3, ["reuters.com", "bbc.com", "bloomberg.com"], [1, 2, 4])
        confidence = self.scorer.calculate_confidence(tier1_evidence)
        
        # Should have high score due to:
        # - 3 tier-1 sources (high source quality score)
        # - All recent sources (high recency score) 
        # - No contradictions (high agreement score)
        self.assertGreaterEqual(confidence["score"], 0.8)
        
        # Verify source analysis calculations
        source_analysis = confidence["source_analysis"]
        self.assertEqual(source_analysis["tier1_count"], 3)
        self.assertEqual(source_analysis["reputable_sources"], 3)
        self.assertEqual(source_analysis["recent_sources"], 3)
        
        # Verify contradiction analysis
        contradiction_analysis = confidence["contradiction_analysis"]
        self.assertFalse(contradiction_analysis["has_contradictions"])
        self.assertEqual(contradiction_analysis["contradiction_count"], 0)
        self.assertEqual(contradiction_analysis["agreement_score"], 1.0)
    
    def test_edge_case_confidence_scenarios(self):
        """Test edge cases in confidence calculation"""
        # No evidence
        no_evidence_confidence = self.scorer.calculate_confidence([])
        self.assertEqual(no_evidence_confidence["level"], "low")
        
        # Evidence with no published dates
        no_date_evidence = [{
            "title": "Article without date",
            "excerpt": "Some content here",
            "outlet": "reuters.com",
            "url": "https://reuters.com/article"
        }]
        no_date_confidence = self.scorer.calculate_confidence(no_date_evidence)
        self.assertIn(no_date_confidence["level"], ["low", "medium"])  # Should handle gracefully
        
        # Evidence with invalid dates
        invalid_date_evidence = [{
            "title": "Article with bad date",
            "excerpt": "Some content here",
            "outlet": "reuters.com",
            "published_at": "invalid-date-string",
            "url": "https://reuters.com/article"
        }]
        invalid_date_confidence = self.scorer.calculate_confidence(invalid_date_evidence)
        self.assertIsInstance(invalid_date_confidence["level"], str)
    
    def test_confidence_calculation_performance(self):
        """Test confidence calculation performance with many sources"""
        import time
        
        # Create large evidence set (100 sources)
        large_outlets = ["reuters.com", "bbc.com", "bloomberg.com", "prothomalo.com", "thedailystar.net"]
        large_hours = list(range(1, 101))  # 1 to 100 hours ago
        large_evidence = self.create_test_evidence(100, large_outlets * 20, large_hours)
        
        start_time = time.time()
        confidence = self.scorer.calculate_confidence(large_evidence)
        end_time = time.time()
        
        # Should complete quickly (< 2 seconds for 100 sources)
        self.assertLess(end_time - start_time, 2.0)
        
        # Should still produce valid confidence
        self.assertIn(confidence["level"], ["high", "medium", "low"])
        self.assertIsInstance(confidence["score"], float)
        self.assertGreaterEqual(confidence["score"], 0.0)
        self.assertLessEqual(confidence["score"], 1.0)
    
    def test_convenience_function(self):
        """Test the convenience function for confidence calculation"""
        evidence = self.create_test_evidence(2, ["reuters.com", "bbc.com"], [1, 3])
        
        # Test convenience function
        confidence = calculate_trustworthy_confidence(evidence, "Test summary", False)
        
        # Should return same structure as direct scorer call
        self.assertIn("level", confidence)
        self.assertIn("score", confidence)
        self.assertIn("rationale", confidence)
        self.assertIn("source_analysis", confidence)
        
        # Should match direct scorer call
        direct_confidence = self.scorer.calculate_confidence(evidence, "Test summary", False)
        self.assertEqual(confidence["level"], direct_confidence["level"])
        self.assertEqual(confidence["score"], direct_confidence["score"])

if __name__ == "__main__":
    unittest.main()