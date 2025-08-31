#!/usr/bin/env python3
"""
Unit tests for reranking order logic
"""

import unittest
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

# Mock reranking system for testing
class RerankingEngine:
    """Mock reranking engine with different strategies"""
    
    def __init__(self, strategy: str = "relevance", 
                 recency_weight: float = 0.3,
                 authority_weight: float = 0.4,
                 relevance_weight: float = 0.3):
        self.strategy = strategy
        self.recency_weight = recency_weight
        self.authority_weight = authority_weight
        self.relevance_weight = relevance_weight
        
        # Authority scores for different outlets
        self.authority_scores = {
            "reuters.com": 1.0,
            "bbc.com": 1.0,
            "prothomalo.com": 0.9,
            "thedailystar.net": 0.9,
            "bloomberg.com": 0.95,
            "cnn.com": 0.85,
            "unknown.com": 0.3
        }
    
    def rerank(self, articles: List[Dict[str, Any]], query: str = "") -> List[Dict[str, Any]]:
        """Rerank articles based on strategy"""
        if not articles:
            return []
        
        if self.strategy == "chronological":
            return self._chronological_rerank(articles)
        elif self.strategy == "authority":
            return self._authority_rerank(articles)
        elif self.strategy == "relevance":
            return self._relevance_rerank(articles, query)
        elif self.strategy == "mixed":
            return self._mixed_rerank(articles, query)
        else:
            return articles  # No reranking
    
    def _chronological_rerank(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort by publication time (newest first)"""
        def get_timestamp(article):
            published_at = article.get("published_at")
            if not published_at:
                return datetime.min.replace(tzinfo=timezone.utc)
            
            try:
                if isinstance(published_at, str):
                    dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                else:
                    dt = published_at
                
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except:
                return datetime.min.replace(tzinfo=timezone.utc)
        
        return sorted(articles, key=get_timestamp, reverse=True)
    
    def _authority_rerank(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort by outlet authority score"""
        def get_authority_score(article):
            outlet = article.get("outlet", "unknown.com")
            return self.authority_scores.get(outlet, 0.1)
        
        return sorted(articles, key=get_authority_score, reverse=True)
    
    def _relevance_rerank(self, articles: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Sort by relevance to query"""
        if not query:
            return articles
        
        query_words = set(query.lower().split())
        
        def get_relevance_score(article):
            title = article.get("title", "").lower()
            excerpt = article.get("excerpt", "").lower()
            
            title_words = set(title.split())
            excerpt_words = set(excerpt.split())
            
            title_overlap = len(query_words.intersection(title_words))
            excerpt_overlap = len(query_words.intersection(excerpt_words))
            
            # Weight title matches higher than excerpt matches
            return title_overlap * 2 + excerpt_overlap
        
        return sorted(articles, key=get_relevance_score, reverse=True)
    
    def _mixed_rerank(self, articles: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Combined ranking using multiple factors"""
        current_time = datetime.now(timezone.utc)
        query_words = set(query.lower().split()) if query else set()
        
        def get_mixed_score(article):
            # Recency score (0-1, newer = higher)
            published_at = article.get("published_at")
            recency_score = 0.0
            if published_at:
                try:
                    if isinstance(published_at, str):
                        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    else:
                        dt = published_at
                    
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    
                    hours_old = (current_time - dt).total_seconds() / 3600
                    recency_score = max(0, 1 - (hours_old / 168))  # Decay over 1 week
                except:
                    pass
            
            # Authority score
            outlet = article.get("outlet", "unknown.com")
            authority_score = self.authority_scores.get(outlet, 0.1)
            
            # Relevance score
            relevance_score = 0.0
            if query_words:
                title = article.get("title", "").lower()
                excerpt = article.get("excerpt", "").lower()
                
                title_words = set(title.split())
                excerpt_words = set(excerpt.split())
                
                title_overlap = len(query_words.intersection(title_words))
                excerpt_overlap = len(query_words.intersection(excerpt_words))
                
                max_possible = len(query_words) * 3  # title_overlap*2 + excerpt_overlap
                relevance_score = (title_overlap * 2 + excerpt_overlap) / max(max_possible, 1)
            
            # Combined score
            combined = (
                self.recency_weight * recency_score +
                self.authority_weight * authority_score +
                self.relevance_weight * relevance_score
            )
            
            return combined
        
        return sorted(articles, key=get_mixed_score, reverse=True)

class TestRerankingOrder(unittest.TestCase):
    """Test reranking order logic and strategies"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.current_time = datetime.now(timezone.utc)
        
        self.sample_articles = [
            {
                "title": "Breaking: Economic Crisis Unfolds",
                "excerpt": "A major economic crisis is developing with significant market impacts.",
                "outlet": "reuters.com",
                "published_at": (self.current_time - timedelta(hours=1)).isoformat(),
                "url": "https://reuters.com/crisis"
            },
            {
                "title": "Economic Policy Changes Announced",
                "excerpt": "Government announces new economic policy to address recent issues.",
                "outlet": "prothomalo.com",
                "published_at": (self.current_time - timedelta(hours=6)).isoformat(),
                "url": "https://prothomalo.com/policy"
            },
            {
                "title": "Stock Market Volatility Continues", 
                "excerpt": "Markets remain volatile amid economic uncertainty and policy debates.",
                "outlet": "unknown.com",
                "published_at": (self.current_time - timedelta(hours=2)).isoformat(),
                "url": "https://unknown.com/markets"
            },
            {
                "title": "Sports News: Cricket Match Results",
                "excerpt": "Bangladesh wins cricket match against visiting team yesterday.",
                "outlet": "bbc.com",
                "published_at": (self.current_time - timedelta(hours=12)).isoformat(),
                "url": "https://bbc.com/cricket"
            }
        ]
    
    def test_chronological_reranking(self):
        """Test chronological reranking puts newest articles first"""
        engine = RerankingEngine(strategy="chronological")
        reranked = engine.rerank(self.sample_articles)
        
        # Should be ordered by publication time (newest first)
        timestamps = []
        for article in reranked:
            timestamp = datetime.fromisoformat(article["published_at"].replace("Z", "+00:00"))
            timestamps.append(timestamp)
        
        # Verify descending chronological order
        for i in range(len(timestamps) - 1):
            self.assertGreaterEqual(timestamps[i], timestamps[i + 1])
        
        # Verify the breaking news (1h old) is first
        self.assertIn("Breaking", reranked[0]["title"])
    
    def test_authority_reranking(self):
        """Test authority-based reranking prioritizes reputable sources"""
        engine = RerankingEngine(strategy="authority")
        reranked = engine.rerank(self.sample_articles)
        
        # Reuters and BBC (authority 1.0) should be first
        top_outlets = [article["outlet"] for article in reranked[:2]]
        self.assertIn("reuters.com", top_outlets)
        self.assertIn("bbc.com", top_outlets)
        
        # Unknown.com (authority 0.3) should be last
        self.assertEqual(reranked[-1]["outlet"], "unknown.com")
    
    def test_relevance_reranking(self):
        """Test relevance-based reranking for query matching"""
        engine = RerankingEngine(strategy="relevance")
        
        # Query about economic issues
        economic_query = "economic crisis policy"
        reranked = engine.rerank(self.sample_articles, economic_query)
        
        # Articles about economics should rank higher than sports
        economics_indices = []
        sports_index = None
        
        for i, article in enumerate(reranked):
            if "economic" in article["title"].lower() or "economic" in article["excerpt"].lower():
                economics_indices.append(i)
            elif "sports" in article["title"].lower() or "cricket" in article["title"].lower():
                sports_index = i
        
        # All economic articles should rank higher than sports
        if sports_index is not None:
            for econ_idx in economics_indices:
                self.assertLess(econ_idx, sports_index)
    
    def test_mixed_reranking_balances_factors(self):
        """Test mixed strategy balances recency, authority, and relevance"""
        engine = RerankingEngine(
            strategy="mixed",
            recency_weight=0.3,
            authority_weight=0.4,
            relevance_weight=0.3
        )
        
        query = "economic policy"
        reranked = engine.rerank(self.sample_articles, query)
        
        # Should not be purely chronological or purely by authority
        chronological_engine = RerankingEngine(strategy="chronological")
        chronological_order = chronological_engine.rerank(self.sample_articles)
        
        authority_engine = RerankingEngine(strategy="authority")
        authority_order = authority_engine.rerank(self.sample_articles)
        
        # Mixed order should be different from pure strategies
        mixed_titles = [article["title"] for article in reranked]
        chrono_titles = [article["title"] for article in chronological_order]
        auth_titles = [article["title"] for article in authority_order]
        
        # At least one should be different
        different_from_chrono = mixed_titles != chrono_titles
        different_from_auth = mixed_titles != auth_titles
        
        self.assertTrue(different_from_chrono or different_from_auth)
    
    def test_reranking_weight_adjustment(self):
        """Test that adjusting weights changes ranking behavior"""
        # High recency weight
        recency_heavy = RerankingEngine(
            strategy="mixed",
            recency_weight=0.8,
            authority_weight=0.1,
            relevance_weight=0.1
        )
        
        # High authority weight
        authority_heavy = RerankingEngine(
            strategy="mixed",
            recency_weight=0.1,
            authority_weight=0.8,
            relevance_weight=0.1
        )
        
        query = "news update"
        recency_order = recency_heavy.rerank(self.sample_articles, query)
        authority_order = authority_heavy.rerank(self.sample_articles, query)
        
        # Different weight configurations should produce different orders
        recency_titles = [article["title"] for article in recency_order]
        authority_titles = [article["title"] for article in authority_order]
        
        self.assertNotEqual(recency_titles, authority_titles)
    
    def test_empty_query_handling(self):
        """Test reranking behavior with empty or no query"""
        engine = RerankingEngine(strategy="relevance")
        
        # Empty query
        reranked_empty = engine.rerank(self.sample_articles, "")
        self.assertEqual(len(reranked_empty), len(self.sample_articles))
        
        # No query parameter
        reranked_none = engine.rerank(self.sample_articles)
        self.assertEqual(len(reranked_none), len(self.sample_articles))
    
    def test_missing_timestamp_handling(self):
        """Test handling of articles with missing publication timestamps"""
        articles_with_missing = [
            {
                "title": "Article with timestamp",
                "excerpt": "Content",
                "outlet": "reuters.com",
                "published_at": self.current_time.isoformat()
            },
            {
                "title": "Article without timestamp",
                "excerpt": "Content",
                "outlet": "bbc.com"
                # No published_at field
            },
            {
                "title": "Article with invalid timestamp",
                "excerpt": "Content", 
                "outlet": "cnn.com",
                "published_at": "invalid-date"
            }
        ]
        
        engine = RerankingEngine(strategy="chronological")
        reranked = engine.rerank(articles_with_missing)
        
        # Should not crash and should handle gracefully
        self.assertEqual(len(reranked), 3)
        
        # Article with valid timestamp should be first
        self.assertEqual(reranked[0]["title"], "Article with timestamp")
    
    def test_reranking_preserves_article_integrity(self):
        """Test that reranking doesn't modify article content"""
        original_articles = [article.copy() for article in self.sample_articles]
        
        engine = RerankingEngine(strategy="mixed")
        reranked = engine.rerank(self.sample_articles, "test query")
        
        # All original articles should still be present
        self.assertEqual(len(reranked), len(original_articles))
        
        # Content should be unchanged (though order may differ)
        original_titles = set(article["title"] for article in original_articles)
        reranked_titles = set(article["title"] for article in reranked)
        self.assertEqual(original_titles, reranked_titles)
    
    def test_single_article_reranking(self):
        """Test reranking with single article"""
        single_article = [self.sample_articles[0]]
        
        engine = RerankingEngine(strategy="mixed")
        reranked = engine.rerank(single_article, "test query")
        
        self.assertEqual(len(reranked), 1)
        self.assertEqual(reranked[0]["title"], single_article[0]["title"])
    
    def test_empty_list_reranking(self):
        """Test reranking with empty article list"""
        engine = RerankingEngine(strategy="mixed")
        reranked = engine.rerank([], "test query")
        
        self.assertEqual(reranked, [])
    
    def test_reranking_performance(self):
        """Test reranking performance with larger datasets"""
        import time
        
        # Generate larger dataset
        large_dataset = []
        outlets = ["reuters.com", "bbc.com", "cnn.com", "bloomberg.com", "unknown.com"]
        
        for i in range(500):
            article = {
                "title": f"Article {i} about economic policy and market trends",
                "excerpt": f"Content {i} discussing various economic indicators and policy implications.",
                "outlet": outlets[i % len(outlets)],
                "published_at": (self.current_time - timedelta(hours=i % 72)).isoformat(),
                "url": f"https://example{i}.com/article{i}"
            }
            large_dataset.append(article)
        
        engine = RerankingEngine(strategy="mixed")
        
        start_time = time.time()
        reranked = engine.rerank(large_dataset, "economic policy market")
        end_time = time.time()
        
        # Should complete within reasonable time (< 2 seconds for 500 articles)
        self.assertLess(end_time - start_time, 2.0)
        self.assertEqual(len(reranked), 500)
    
    def test_reranking_stability(self):
        """Test that reranking is stable for identical inputs"""
        engine = RerankingEngine(strategy="mixed")
        query = "economic news"
        
        # Run reranking multiple times
        result1 = engine.rerank(self.sample_articles.copy(), query)
        result2 = engine.rerank(self.sample_articles.copy(), query)
        result3 = engine.rerank(self.sample_articles.copy(), query)
        
        # Results should be identical
        titles1 = [article["title"] for article in result1]
        titles2 = [article["title"] for article in result2]  
        titles3 = [article["title"] for article in result3]
        
        self.assertEqual(titles1, titles2)
        self.assertEqual(titles2, titles3)

if __name__ == "__main__":
    unittest.main()