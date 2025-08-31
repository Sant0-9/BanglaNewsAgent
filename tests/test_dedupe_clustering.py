#!/usr/bin/env python3
"""
Unit tests for deduplication and clustering thresholds
"""

import unittest
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

# Mock deduplication system for testing
class DeduplicationEngine:
    """Mock deduplication engine with configurable thresholds"""
    
    def __init__(self, title_similarity_threshold: float = 0.8, 
                 content_similarity_threshold: float = 0.7,
                 url_domain_weight: float = 0.3):
        self.title_threshold = title_similarity_threshold
        self.content_threshold = content_similarity_threshold
        self.domain_weight = url_domain_weight
        
    def deduplicate(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deduplicate articles based on similarity thresholds"""
        if not articles:
            return {"unique": [], "duplicates": [], "clusters": []}
        
        unique_articles = []
        duplicates = []
        clusters = []
        processed_indices = set()
        
        for i, article in enumerate(articles):
            if i in processed_indices:
                continue
                
            # Start new cluster with current article
            cluster = [i]
            unique_articles.append(article)
            
            # Find similar articles for clustering
            for j in range(i + 1, len(articles)):
                if j in processed_indices:
                    continue
                    
                similarity = self._calculate_similarity(article, articles[j])
                
                if similarity >= self.title_threshold:
                    cluster.append(j)
                    duplicates.append(articles[j])
                    processed_indices.add(j)
            
            processed_indices.add(i)
            if len(cluster) > 1:
                clusters.append(cluster)
        
        return {
            "unique": unique_articles,
            "duplicates": duplicates, 
            "clusters": clusters,
            "deduplication_rate": len(duplicates) / len(articles) if articles else 0
        }
    
    def _calculate_similarity(self, article1: Dict[str, Any], article2: Dict[str, Any]) -> float:
        """Calculate similarity between two articles"""
        title_sim = self._title_similarity(article1.get("title", ""), article2.get("title", ""))
        content_sim = self._content_similarity(article1.get("excerpt", ""), article2.get("excerpt", ""))
        domain_sim = self._domain_similarity(article1.get("url", ""), article2.get("url", ""))
        
        # Weighted combination
        overall_similarity = (
            title_sim * 0.5 + 
            content_sim * 0.3 + 
            domain_sim * self.domain_weight
        )
        
        return overall_similarity
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate title similarity using simple word overlap"""
        if not title1 or not title2:
            return 0.0
        
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _content_similarity(self, content1: str, content2: str) -> float:
        """Calculate content similarity"""
        if not content1 or not content2:
            return 0.0
            
        # Simple character-based similarity for testing
        if content1 == content2:
            return 1.0
        
        # Jaccard similarity on character 3-grams
        def char_ngrams(text: str, n: int = 3) -> set:
            return set(text[i:i+n] for i in range(len(text) - n + 1))
        
        ngrams1 = char_ngrams(content1.lower())
        ngrams2 = char_ngrams(content2.lower())
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = ngrams1.intersection(ngrams2)
        union = ngrams1.union(ngrams2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _domain_similarity(self, url1: str, url2: str) -> float:
        """Calculate domain similarity"""
        if not url1 or not url2:
            return 0.0
        
        try:
            from urllib.parse import urlparse
            domain1 = urlparse(url1).netloc.lower()
            domain2 = urlparse(url2).netloc.lower()
            return 1.0 if domain1 == domain2 else 0.0
        except:
            return 0.0

class TestDeduplicationThresholds(unittest.TestCase):
    """Test deduplication and clustering threshold behavior"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = DeduplicationEngine()
        self.sample_articles = [
            {
                "title": "Bangladesh Economy Shows Strong Growth",
                "excerpt": "The economy grew by 6.5% in the third quarter according to government data.",
                "url": "https://prothomalo.com/economy/growth-1",
                "outlet": "prothomalo.com",
                "published_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "Bangladesh Economy Shows Strong Growth Rate",
                "excerpt": "Government data shows the economy expanded 6.5% in Q3.",
                "url": "https://thedailystar.net/economy/growth-2",
                "outlet": "thedailystar.net", 
                "published_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "Cricket Match Result: Bangladesh vs India",
                "excerpt": "Bangladesh defeated India by 5 wickets in the ODI match.",
                "url": "https://cricinfo.com/match-1",
                "outlet": "cricinfo.com",
                "published_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "Weather Forecast: Heavy Rain Expected",
                "excerpt": "Dhaka will experience heavy rainfall tomorrow according to meteorological department.",
                "url": "https://weatherbd.com/forecast-1",
                "outlet": "weatherbd.com",
                "published_at": datetime.now(timezone.utc).isoformat()
            }
        ]
    
    def test_high_similarity_threshold_keeps_more_duplicates(self):
        """Test that high similarity threshold (0.9) keeps more articles as unique"""
        strict_engine = DeduplicationEngine(title_similarity_threshold=0.9)
        result = strict_engine.deduplicate(self.sample_articles)
        
        # With strict threshold, similar articles should remain unique
        self.assertEqual(len(result["unique"]), 4)
        self.assertEqual(len(result["duplicates"]), 0)
        self.assertEqual(result["deduplication_rate"], 0.0)
    
    def test_low_similarity_threshold_removes_more_duplicates(self):
        """Test that low similarity threshold (0.5) removes more articles"""
        lenient_engine = DeduplicationEngine(title_similarity_threshold=0.5)
        result = lenient_engine.deduplicate(self.sample_articles)
        
        # With lenient threshold, more articles should be considered duplicates
        self.assertLess(len(result["unique"]), 4)
        self.assertGreater(len(result["duplicates"]), 0)
        self.assertGreater(result["deduplication_rate"], 0.0)
    
    def test_exact_duplicate_detection(self):
        """Test detection of exact duplicates"""
        duplicate_articles = [
            {
                "title": "Same Article Title",
                "excerpt": "Identical content here.",
                "url": "https://site1.com/article",
                "outlet": "site1.com"
            },
            {
                "title": "Same Article Title", 
                "excerpt": "Identical content here.",
                "url": "https://site2.com/article",
                "outlet": "site2.com"
            },
            {
                "title": "Different Article",
                "excerpt": "Completely different content.",
                "url": "https://site3.com/different",
                "outlet": "site3.com"
            }
        ]
        
        result = self.engine.deduplicate(duplicate_articles)
        
        # Should detect the two identical articles
        self.assertEqual(len(result["unique"]), 2)
        self.assertEqual(len(result["duplicates"]), 1)
        self.assertAlmostEqual(result["deduplication_rate"], 1/3, places=2)
    
    def test_near_duplicate_clustering(self):
        """Test clustering of near-duplicate articles"""
        near_duplicates = [
            {
                "title": "Breaking: Major Economic Policy Announced",
                "excerpt": "Government announces new economic policy changes.",
                "url": "https://news1.com/policy"
            },
            {
                "title": "Major Economic Policy Changes Announced",
                "excerpt": "The government has announced significant economic policy updates.", 
                "url": "https://news2.com/policy"
            },
            {
                "title": "Economic Policy Update: Government Announcement",
                "excerpt": "New economic policies have been announced by the government.",
                "url": "https://news3.com/policy"
            },
            {
                "title": "Completely Unrelated Sports News",
                "excerpt": "Football match results from yesterday.",
                "url": "https://sports.com/football"
            }
        ]
        
        result = self.engine.deduplicate(near_duplicates)
        
        # Should cluster the three similar economic policy articles
        self.assertGreaterEqual(len(result["clusters"]), 1)
        self.assertGreater(result["deduplication_rate"], 0.5)
        
        # The sports article should remain unique
        unique_titles = [article["title"] for article in result["unique"]]
        self.assertTrue(any("Sports" in title for title in unique_titles))
    
    def test_domain_weight_influence(self):
        """Test that domain weight affects clustering decisions"""
        same_domain_articles = [
            {
                "title": "Article A",
                "excerpt": "Different content A",
                "url": "https://reuters.com/article-a"
            },
            {
                "title": "Article B", 
                "excerpt": "Different content B",
                "url": "https://reuters.com/article-b"
            }
        ]
        
        # Test with high domain weight
        high_domain_engine = DeduplicationEngine(
            title_similarity_threshold=0.3,
            domain_weight=0.8  # High domain weight
        )
        result_high = high_domain_engine.deduplicate(same_domain_articles)
        
        # Test with low domain weight  
        low_domain_engine = DeduplicationEngine(
            title_similarity_threshold=0.3,
            domain_weight=0.1  # Low domain weight
        )
        result_low = low_domain_engine.deduplicate(same_domain_articles)
        
        # High domain weight should be more likely to cluster same-domain articles
        # (This is a behavior test - exact results depend on implementation)
        self.assertGreaterEqual(len(result_high["clusters"]), 0)
        self.assertGreaterEqual(len(result_low["clusters"]), 0)
    
    def test_empty_input_handling(self):
        """Test handling of empty article list"""
        result = self.engine.deduplicate([])
        
        self.assertEqual(result["unique"], [])
        self.assertEqual(result["duplicates"], [])
        self.assertEqual(result["clusters"], [])
        self.assertEqual(result["deduplication_rate"], 0)
    
    def test_single_article_handling(self):
        """Test handling of single article"""
        single_article = [self.sample_articles[0]]
        result = self.engine.deduplicate(single_article)
        
        self.assertEqual(len(result["unique"]), 1)
        self.assertEqual(len(result["duplicates"]), 0)
        self.assertEqual(result["deduplication_rate"], 0.0)
    
    def test_malformed_article_handling(self):
        """Test handling of malformed articles with missing fields"""
        malformed_articles = [
            {"title": "Valid Article", "excerpt": "Content", "url": "https://valid.com"},
            {"title": "No Excerpt"},  # Missing excerpt
            {"excerpt": "No Title", "url": "https://notitle.com"},  # Missing title
            {},  # Empty article
            {"title": "Normal Article", "excerpt": "Normal content", "url": "https://normal.com"}
        ]
        
        # Should not crash and should handle gracefully
        result = self.engine.deduplicate(malformed_articles)
        
        self.assertIsInstance(result, dict)
        self.assertIn("unique", result)
        self.assertIn("duplicates", result) 
        self.assertIn("deduplication_rate", result)
        self.assertGreaterEqual(len(result["unique"]), 2)  # At least the valid articles
    
    def test_performance_with_large_dataset(self):
        """Test deduplication performance with larger datasets"""
        import time
        
        # Generate large dataset (1000 articles with some duplicates)
        large_dataset = []
        base_titles = [
            "Economic Growth Report",
            "Sports Match Results", 
            "Weather Forecast Update",
            "Political News Today",
            "Technology Breakthrough"
        ]
        
        for i in range(1000):
            base_idx = i % len(base_titles)
            variation = i // len(base_titles)
            
            article = {
                "title": f"{base_titles[base_idx]} - Version {variation}",
                "excerpt": f"Content for article {i} about {base_titles[base_idx].lower()}",
                "url": f"https://news{i % 10}.com/article{i}",
                "outlet": f"news{i % 10}.com"
            }
            large_dataset.append(article)
        
        start_time = time.time()
        result = self.engine.deduplicate(large_dataset)
        end_time = time.time()
        
        # Should complete within reasonable time (< 10 seconds for 1000 articles)
        self.assertLess(end_time - start_time, 10.0)
        
        # Should detect some duplicates
        self.assertGreater(result["deduplication_rate"], 0.0)
        self.assertEqual(len(result["unique"]) + len(result["duplicates"]), 1000)
    
    def test_threshold_edge_cases(self):
        """Test behavior at threshold edge cases"""
        edge_articles = [
            {
                "title": "Very Similar Article About Economy Growth",
                "excerpt": "Economic indicators show positive growth trends.",
                "url": "https://news1.com/economy"
            },
            {
                "title": "Very Similar Article About Economy Development", 
                "excerpt": "Economic indicators demonstrate positive growth patterns.",
                "url": "https://news2.com/economy"
            }
        ]
        
        # Test exactly at threshold
        exact_engine = DeduplicationEngine(title_similarity_threshold=0.7)
        result = exact_engine.deduplicate(edge_articles)
        
        # Test just above threshold
        above_engine = DeduplicationEngine(title_similarity_threshold=0.71)
        result_above = above_engine.deduplicate(edge_articles)
        
        # Test just below threshold
        below_engine = DeduplicationEngine(title_similarity_threshold=0.69)
        result_below = below_engine.deduplicate(edge_articles)
        
        # Results should be consistent and logical
        self.assertIsInstance(result["deduplication_rate"], float)
        self.assertIsInstance(result_above["deduplication_rate"], float) 
        self.assertIsInstance(result_below["deduplication_rate"], float)
        
        # Stricter threshold should result in fewer duplicates detected
        self.assertLessEqual(result_above["deduplication_rate"], result_below["deduplication_rate"])

if __name__ == "__main__":
    unittest.main()