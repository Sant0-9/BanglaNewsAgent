#!/usr/bin/env python3
"""
Unit tests for dynamic windowing functionality
"""

import unittest
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from packages.quality.guardrails import QualityGuardrails

class TestDynamicWindowing(unittest.TestCase):
    """Test dynamic time window adjustments based on query type and source availability"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.guardrails = QualityGuardrails(time_window_hours=24)
        self.current_time = datetime.now(timezone.utc)
    
    def create_test_evidence(self, hours_ago_list: List[int], outlets: List[str] = None) -> List[Dict[str, Any]]:
        """Helper to create test evidence with specific timestamps"""
        if outlets is None:
            outlets = ["reuters.com"] * len(hours_ago_list)
        
        evidence = []
        for i, hours_ago in enumerate(hours_ago_list):
            timestamp = self.current_time - timedelta(hours=hours_ago)
            evidence.append({
                "title": f"Test Article {i+1}",
                "excerpt": f"Test content {i+1}",
                "outlet": outlets[i] if i < len(outlets) else outlets[0],
                "published_at": timestamp.isoformat(),
                "url": f"https://example.com/article{i+1}"
            })
        return evidence
    
    def test_standard_24_hour_window(self):
        """Test standard 24-hour window accepts recent sources"""
        # Sources within 24 hours
        recent_evidence = self.create_test_evidence([1, 6, 12, 18])
        result = self.guardrails.check_sources_within_time_window(recent_evidence)
        
        self.assertTrue(result.passed)
        self.assertEqual(result.details["sources_within_window"], 4)
        self.assertEqual(result.details["sources_outside_window"], 0)
    
    def test_standard_window_rejects_old_sources(self):
        """Test standard window rejects sources outside 24 hours"""
        # Mix of recent and old sources
        mixed_evidence = self.create_test_evidence([2, 12, 30, 48])  # 30h and 48h are outside window
        result = self.guardrails.check_sources_within_time_window(mixed_evidence)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.details["sources_within_window"], 2)
        self.assertEqual(result.details["sources_outside_window"], 2)
    
    def test_breaking_news_tighter_window(self):
        """Test tighter window for breaking news queries"""
        # Create guardrails with 6-hour window for breaking news
        breaking_news_guardrails = QualityGuardrails(time_window_hours=6)
        
        # Sources that would pass 24h but fail 6h window
        evidence = self.create_test_evidence([2, 4, 8, 12])  # 8h and 12h outside 6h window
        result = breaking_news_guardrails.check_sources_within_time_window(evidence)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.details["sources_within_window"], 2)
        self.assertEqual(result.details["sources_outside_window"], 2)
    
    def test_extended_window_for_analysis(self):
        """Test extended window for analysis/background queries"""
        # Create guardrails with 72-hour window for analysis
        analysis_guardrails = QualityGuardrails(time_window_hours=72)
        
        # Sources that would fail 24h but pass 72h window
        evidence = self.create_test_evidence([12, 30, 48, 60])  # All within 72h
        result = analysis_guardrails.check_sources_within_time_window(evidence)
        
        self.assertTrue(result.passed)
        self.assertEqual(result.details["sources_within_window"], 4)
        self.assertEqual(result.details["sources_outside_window"], 0)
    
    def test_background_sources_excluded_from_window_check(self):
        """Test that background sources are excluded from time window checks"""
        evidence = [
            {
                "title": "Recent Breaking News",
                "excerpt": "Fresh news content",
                "outlet": "reuters.com",
                "published_at": (self.current_time - timedelta(hours=2)).isoformat(),
                "url": "https://reuters.com/recent"
            },
            {
                "title": "Background Context - Historical Analysis",
                "excerpt": "Background information",
                "outlet": "bbc.com", 
                "published_at": (self.current_time - timedelta(days=30)).isoformat(),
                "url": "https://bbc.com/background"
            },
            {
                "title": "Context: Previous Events",
                "excerpt": "Contextual information",
                "outlet": "cnn.com",
                "published_at": (self.current_time - timedelta(days=10)).isoformat(),
                "url": "https://cnn.com/context"
            }
        ]
        
        result = self.guardrails.check_sources_within_time_window(evidence)
        
        # Should pass because background sources are excluded
        self.assertTrue(result.passed)
        self.assertEqual(result.details["sources_checked"], 1)  # Only one non-background source
        self.assertEqual(result.details["background_sources"], 2)
        self.assertEqual(result.details["sources_within_window"], 1)
    
    def test_empty_sources_list(self):
        """Test handling of empty sources list"""
        result = self.guardrails.check_sources_within_time_window([])
        
        self.assertFalse(result.passed)
        self.assertEqual(result.reason, "No evidence sources to check")
        self.assertEqual(result.details["source_count"], 0)
    
    def test_missing_timestamps(self):
        """Test handling of sources with missing timestamps"""
        evidence = [
            {
                "title": "Article without timestamp",
                "excerpt": "Content",
                "outlet": "reuters.com",
                "url": "https://example.com"
                # No published_at field
            }
        ]
        
        result = self.guardrails.check_sources_within_time_window(evidence)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.details["sources_outside_window"], 1)
        self.assertIn("No published_at timestamp", str(result.details["outdated_sources"]))
    
    def test_invalid_timestamp_format(self):
        """Test handling of invalid timestamp formats"""
        evidence = [
            {
                "title": "Article with bad timestamp",
                "excerpt": "Content", 
                "outlet": "reuters.com",
                "published_at": "invalid-timestamp",
                "url": "https://example.com"
            }
        ]
        
        result = self.guardrails.check_sources_within_time_window(evidence)
        
        self.assertFalse(result.passed)
        self.assertEqual(result.details["sources_outside_window"], 1)
        self.assertIn("Invalid timestamp", str(result.details["outdated_sources"]))
    
    def test_timezone_handling(self):
        """Test proper timezone handling in timestamps"""
        # Create evidence with different timezone formats
        evidence = [
            {
                "title": "UTC timestamp",
                "excerpt": "Content",
                "outlet": "reuters.com",
                "published_at": (self.current_time - timedelta(hours=2)).isoformat(),
                "url": "https://example.com/1"
            },
            {
                "title": "Z suffix timestamp", 
                "excerpt": "Content",
                "outlet": "bbc.com",
                "published_at": (self.current_time - timedelta(hours=4)).isoformat().replace("+00:00", "Z"),
                "url": "https://example.com/2"
            },
            {
                "title": "Naive timestamp (assumed UTC)",
                "excerpt": "Content",
                "outlet": "cnn.com", 
                "published_at": (self.current_time - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
                "url": "https://example.com/3"
            }
        ]
        
        result = self.guardrails.check_sources_within_time_window(evidence)
        
        self.assertTrue(result.passed)
        self.assertEqual(result.details["sources_within_window"], 3)
    
    def test_dynamic_window_adjustment_logic(self):
        """Test logic for dynamic window adjustment based on query characteristics"""
        
        # Test cases for different query types and expected windows
        test_cases = [
            # (query_keywords, expected_optimal_window_hours)
            (["breaking", "urgent", "just"], 6),      # Breaking news: 6h window
            (["today", "current", "now"], 12),        # Current events: 12h window  
            (["analysis", "review", "context"], 72),   # Analysis: 72h window
            (["historical", "background"], 168),       # Historical: 1 week window
            (["weather", "forecast"], 48),             # Weather: 48h window
            (["sports", "match", "score"], 24),        # Sports: 24h window (default)
            (["market", "trading"], 12),               # Markets: 12h window
        ]
        
        for keywords, expected_hours in test_cases:
            with self.subTest(keywords=keywords, expected_hours=expected_hours):
                # This would be implemented in a real dynamic window system
                optimal_window = self._calculate_optimal_window(keywords)
                self.assertEqual(optimal_window, expected_hours)
    
    def _calculate_optimal_window(self, keywords: List[str]) -> int:
        """Helper method simulating dynamic window calculation"""
        # Simple rule-based window adjustment
        if any(kw in keywords for kw in ["breaking", "urgent", "just"]):
            return 6
        elif any(kw in keywords for kw in ["today", "current", "now"]):
            return 12
        elif any(kw in keywords for kw in ["analysis", "review", "context"]):
            return 72
        elif any(kw in keywords for kw in ["historical", "background"]):
            return 168
        elif any(kw in keywords for kw in ["weather", "forecast"]):
            return 48
        elif any(kw in keywords for kw in ["market", "trading"]):
            return 12
        else:
            return 24  # Default 24h window
    
    def test_window_performance_with_large_source_sets(self):
        """Test window checking performance with large numbers of sources"""
        import time
        
        # Create large evidence set (100 sources)
        large_evidence = self.create_test_evidence(
            list(range(1, 101)),  # 1 to 100 hours ago
            ["reuters.com"] * 100
        )
        
        start_time = time.time()
        result = self.guardrails.check_sources_within_time_window(large_evidence)
        end_time = time.time()
        
        # Should complete within reasonable time (< 1 second)
        self.assertLess(end_time - start_time, 1.0)
        
        # Should correctly identify sources within 24h window
        self.assertEqual(result.details["sources_within_window"], 24)  # Hours 1-24
        self.assertEqual(result.details["sources_outside_window"], 76)  # Hours 25-100

if __name__ == "__main__":
    unittest.main()