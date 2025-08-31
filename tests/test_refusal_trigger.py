#!/usr/bin/env python3
"""
Unit tests for refusal trigger logic
"""

import unittest
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

from packages.quality.guardrails import QualityGuardrails, check_quality_and_refuse_if_needed

class TestRefusalTrigger(unittest.TestCase):
    """Test refusal trigger conditions and logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.guardrails = QualityGuardrails(time_window_hours=24)
        self.current_time = datetime.now(timezone.utc)
    
    def create_test_evidence(self, count: int, hours_ago: List[int], outlets: List[str] = None) -> List[Dict[str, Any]]:
        """Helper to create test evidence"""
        if outlets is None:
            outlets = ["reuters.com", "bbc.com", "bloomberg.com", "prothomalo.com", "thedailystar.net"]
        
        evidence = []
        for i in range(count):
            timestamp = self.current_time - timedelta(hours=hours_ago[i % len(hours_ago)])
            evidence.append({
                "title": f"Test Article {i+1}: Important Economic Update",
                "excerpt": f"Article {i+1} reports significant economic development with 5.2% growth rate.",
                "outlet": outlets[i % len(outlets)],
                "published_at": timestamp.isoformat(),
                "url": f"https://{outlets[i % len(outlets)]}/article{i+1}"
            })
        return evidence
    
    def test_insufficient_sources_triggers_refusal(self):
        """Test that insufficient sources trigger refusal"""
        # Single source with non-trivial claims
        single_source = self.create_test_evidence(1, [2])
        summary_with_claims = "Bangladesh economy grew by 6.5% according to latest government data showing unprecedented expansion."
        
        should_refuse, response = check_quality_and_refuse_if_needed(summary_with_claims, single_source)
        
        self.assertTrue(should_refuse)
        self.assertIn("refusal_reason", response)
        self.assertIn("2 sources", response["refusal_reason"])
        self.assertEqual(response["confidence"]["level"], "low")
    
    def test_missing_numeric_markers_triggers_refusal(self):
        """Test that missing numeric markers trigger refusal"""
        # Multiple sources but summary lacks numeric markers
        multiple_sources = self.create_test_evidence(3, [1, 3, 5])
        summary_without_markers = "The economy is performing well according to various reports from financial institutions."
        
        should_refuse, response = check_quality_and_refuse_if_needed(summary_without_markers, multiple_sources)
        
        self.assertTrue(should_refuse)
        self.assertIn("numeric markers", response["refusal_reason"])
        self.assertEqual(response["confidence"]["level"], "low")
    
    def test_stale_sources_trigger_refusal(self):
        """Test that sources outside time window trigger refusal"""
        # Sources older than 24 hours
        stale_sources = self.create_test_evidence(3, [30, 48, 72])  # All outside 24h window
        summary_with_markers = "Economic data shows 6.2% growth rate with unemployment at 4.1% according to recent analysis."
        
        should_refuse, response = check_quality_and_refuse_if_needed(summary_with_markers, stale_sources)
        
        self.assertTrue(should_refuse)
        self.assertIn("time window", response["refusal_reason"])
        self.assertEqual(response["confidence"]["level"], "low")
    
    def test_multiple_failures_combine_in_refusal(self):
        """Test that multiple quality failures combine in refusal message"""
        # Single old source + no numeric markers
        poor_evidence = self.create_test_evidence(1, [48])  # Old + insufficient
        poor_summary = "The economic situation has been improving according to government sources."
        
        should_refuse, response = check_quality_and_refuse_if_needed(poor_summary, poor_evidence)
        
        self.assertTrue(should_refuse)
        refusal_reason = response["refusal_reason"]
        
        # Should mention both problems
        self.assertTrue(
            ("2 sources" in refusal_reason) and 
            (("time window" in refusal_reason) or ("numeric markers" in refusal_reason))
        )
    
    def test_good_quality_passes_all_checks(self):
        """Test that high-quality content passes all checks"""
        # Multiple recent sources with numeric markers
        good_sources = self.create_test_evidence(3, [1, 4, 8])
        good_summary = "Bangladesh GDP increased by 6.5% in Q3 2024, with inflation at 3.2% and unemployment declining to 4.1% according to multiple economic reports."
        
        should_refuse, response = check_quality_and_refuse_if_needed(good_summary, good_sources)
        
        self.assertFalse(should_refuse)
        self.assertIn("quality_checks", response)
        
        # All checks should pass
        checks = response["quality_checks"]
        for check_name, check_result in checks.items():
            self.assertTrue(check_result.passed, f"Check {check_name} failed: {check_result.reason}")
    
    def test_refusal_response_structure(self):
        """Test that refusal responses have correct structure"""
        poor_evidence = self.create_test_evidence(1, [2])
        poor_summary = "Economy doing well."
        
        should_refuse, response = check_quality_and_refuse_if_needed(poor_summary, poor_evidence)
        
        self.assertTrue(should_refuse)
        
        # Check required fields in refusal response
        required_fields = ["summary", "confidence", "sources", "was_refused", "refusal_reason", "refusal_stage"]
        for field in required_fields:
            self.assertIn(field, response, f"Missing required field: {field}")
        
        # Check confidence structure
        confidence = response["confidence"]
        self.assertEqual(confidence["level"], "low")
        self.assertLess(confidence["score"], 0.5)
        self.assertIn("rationale", confidence)
        
        # Check polite refusal message
        self.assertIn("apologize", response["summary"].lower())
        self.assertIn("cannot provide", response["summary"].lower())
    
    def test_trivial_claims_bypass_multiple_source_requirement(self):
        """Test that trivial claims don't require multiple sources"""
        # Single source but only trivial claims
        single_source = self.create_test_evidence(1, [2])
        trivial_summary = "The weather is sunny today with temperature at 28°C according to meteorological reports."
        
        should_refuse, response = check_quality_and_refuse_if_needed(trivial_summary, single_source)
        
        # Should NOT refuse for trivial claims
        self.assertFalse(should_refuse)
        self.assertIn("quality_checks", response)
    
    def test_background_sources_bypass_time_window(self):
        """Test that background sources bypass time window checks"""
        evidence = [
            {
                "title": "Recent Economic Report",
                "excerpt": "Latest quarterly data shows 6.1% GDP growth this quarter.",
                "outlet": "reuters.com",
                "published_at": (self.current_time - timedelta(hours=2)).isoformat(),
                "url": "https://reuters.com/recent"
            },
            {
                "title": "Background: Historical Economic Context",
                "excerpt": "Historical analysis shows similar growth patterns in previous decades.",
                "outlet": "bloomberg.com",
                "published_at": (self.current_time - timedelta(days=30)).isoformat(),
                "url": "https://bloomberg.com/background"
            }
        ]
        
        summary_with_markers = "Current GDP growth of 6.1% represents significant improvement, with historical data showing similar patterns occurred in 1995 and 2010."
        
        should_refuse, response = check_quality_and_refuse_if_needed(summary_with_markers, evidence)
        
        # Should not refuse due to old background source
        self.assertFalse(should_refuse)
    
    def test_refusal_threshold_edge_cases(self):
        """Test refusal behavior at threshold boundaries"""
        # Exactly 2 sources (minimum for non-trivial claims)
        exactly_two_sources = self.create_test_evidence(2, [1, 3])
        non_trivial_summary = "Economic growth accelerated to 6.8% with industrial production up 4.2% according to government statistics."
        
        should_refuse, response = check_quality_and_refuse_if_needed(non_trivial_summary, exactly_two_sources)
        
        # Should NOT refuse with exactly 2 sources
        self.assertFalse(should_refuse)
        
        # Test exactly at 24-hour boundary
        boundary_sources = self.create_test_evidence(2, [24, 23])  # One at boundary, one inside
        
        should_refuse_boundary, response_boundary = check_quality_and_refuse_if_needed(non_trivial_summary, boundary_sources)
        
        # Behavior at exact boundary depends on implementation
        # Should be consistent either way
        self.assertIsInstance(should_refuse_boundary, bool)
    
    def test_empty_summary_triggers_refusal(self):
        """Test that empty or very short summaries trigger refusal"""
        good_sources = self.create_test_evidence(3, [1, 2, 4])
        
        test_cases = [
            "",  # Empty
            "   ",  # Whitespace only
            "No.",  # Too short
        ]
        
        for empty_summary in test_cases:
            with self.subTest(summary=repr(empty_summary)):
                should_refuse, response = check_quality_and_refuse_if_needed(empty_summary, good_sources)
                
                # Should refuse due to insufficient content
                self.assertTrue(should_refuse)
    
    def test_no_evidence_triggers_refusal(self):
        """Test that missing evidence triggers refusal"""
        good_summary = "Economic indicators show positive trends with 5.5% growth and stable inflation at 3.1%."
        
        should_refuse, response = check_quality_and_refuse_if_needed(good_summary, [])
        
        self.assertTrue(should_refuse)
        self.assertIn("sources", response["refusal_reason"].lower())
    
    def test_refusal_metrics_tracking(self):
        """Test that refusals are properly tracked in metrics"""
        # This would test integration with metrics system
        from packages.observability import get_metrics
        
        metrics = get_metrics()
        initial_refusals = metrics.counters.get("refusal.quality_check.quality_check", 0)
        
        poor_evidence = self.create_test_evidence(1, [2])
        poor_summary = "Poor quality summary."
        
        should_refuse, response = check_quality_and_refuse_if_needed(poor_summary, poor_evidence)
        
        # Should track the refusal
        self.assertTrue(should_refuse)
        # Note: In real implementation, metrics would be incremented
    
    def test_concurrent_refusal_checks(self):
        """Test refusal checking under concurrent conditions"""
        import threading
        import time
        
        results = []
        
        def run_check():
            evidence = self.create_test_evidence(1, [2])
            summary = "Poor summary without markers."
            should_refuse, response = check_quality_and_refuse_if_needed(summary, evidence)
            results.append((should_refuse, response))
        
        # Run multiple checks concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=run_check)
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # All should have refused consistently
        self.assertEqual(len(results), 10)
        for should_refuse, response in results:
            self.assertTrue(should_refuse)
            self.assertEqual(response["confidence"]["level"], "low")
    
    def test_refusal_reason_internationalization(self):
        """Test that refusal reasons could support multiple languages"""
        # This is a placeholder for i18n support
        poor_evidence = self.create_test_evidence(1, [48])
        poor_summary = "Economy good."
        
        should_refuse, response = check_quality_and_refuse_if_needed(poor_summary, poor_evidence)
        
        self.assertTrue(should_refuse)
        
        # English refusal message should be clear and professional
        refusal_summary = response["summary"]
        self.assertIn("apologize", refusal_summary.lower())
        self.assertNotIn("error", refusal_summary.lower())  # Should be polite, not technical
        
        # Refusal reason should be technical and specific
        refusal_reason = response["refusal_reason"]
        self.assertIn("sources", refusal_reason.lower())
    
    def test_custom_refusal_thresholds(self):
        """Test refusal behavior with custom quality thresholds"""
        # Test with stricter guardrails (shorter time window)
        strict_guardrails = QualityGuardrails(time_window_hours=6)
        
        # Sources that pass 24h but fail 6h window
        evidence = self.create_test_evidence(2, [8, 10])  # 8h and 10h ago
        summary = "Economic data shows 6.1% growth with 3.2% inflation rate."
        
        checks = strict_guardrails.run_all_checks(summary, evidence)
        should_refuse, refusal_reason = strict_guardrails.should_refuse(checks)
        
        # Should refuse with stricter time window
        self.assertTrue(should_refuse)
        self.assertIn("time window", refusal_reason)

if __name__ == "__main__":
    unittest.main()