#!/usr/bin/env python3
"""
15-prompt evaluation set for KhoborAgent system

Tests: news, BD politics, sports last match, Dhaka 3-day weather, DSEX today, ambiguous queries.
Each eval asserts: recency, ≥2 citations for non-trivial claims, refusal when data thin, and correct mode routing.
"""

import unittest
from typing import Dict, List, Any, Tuple
from datetime import datetime, timezone, timedelta
import json

from packages.router.ml_intent import classify as ml_classify
from packages.quality.confidence_scorer import calculate_trustworthy_confidence
from packages.quality.guardrails import check_quality_and_refuse_if_needed

class EvaluationSet:
    """15-prompt evaluation dataset with expected outcomes"""
    
    def __init__(self):
        self.current_time = datetime.now(timezone.utc)
        self.evaluation_prompts = self._create_evaluation_set()
    
    def _create_evaluation_set(self) -> List[Dict[str, Any]]:
        """Create the 15-prompt evaluation dataset"""
        
        return [
            # 1. General News - Recent
            {
                "id": "news_001",
                "prompt": "Latest news from Bangladesh today",
                "expected_intent": "news",
                "expected_confidence": "high",
                "expected_refusal": False,
                "test_evidence": self._create_good_news_evidence(),
                "assertions": {
                    "recency": True,
                    "multiple_citations": True,
                    "correct_routing": True,
                    "data_sufficient": True
                },
                "description": "General breaking news with multiple recent sources"
            },
            
            # 2. Bangladesh Politics - Recent 
            {
                "id": "politics_001", 
                "prompt": "আজকের রাজনৈতিক খবর বাংলাদেশ থেকে",
                "expected_intent": "news",
                "expected_confidence": "high", 
                "expected_refusal": False,
                "test_evidence": self._create_politics_evidence(),
                "assertions": {
                    "recency": True,
                    "multiple_citations": True,
                    "correct_routing": True,
                    "data_sufficient": True
                },
                "description": "Bangladesh political news in Bangla with recent sources"
            },
            
            # 3. Sports Last Match - Specific
            {
                "id": "sports_001",
                "prompt": "Bangladesh vs India cricket match result yesterday",
                "expected_intent": "sports",
                "expected_confidence": "high",
                "expected_refusal": False, 
                "test_evidence": self._create_cricket_evidence(),
                "assertions": {
                    "recency": True,
                    "multiple_citations": True,
                    "correct_routing": True,
                    "data_sufficient": True
                },
                "description": "Recent cricket match with multiple sports sources"
            },
            
            # 4. Dhaka 3-day Weather
            {
                "id": "weather_001",
                "prompt": "Dhaka weather forecast next 3 days",
                "expected_intent": "weather",
                "expected_confidence": "medium",
                "expected_refusal": False,
                "test_evidence": self._create_weather_evidence(),
                "assertions": {
                    "recency": True,
                    "multiple_citations": True,
                    "correct_routing": True,
                    "data_sufficient": True
                },
                "description": "Weather forecast with meteorological sources"
            },
            
            # 5. DSEX Today - Markets
            {
                "id": "markets_001",
                "prompt": "DSEX index performance today",
                "expected_intent": "markets",
                "expected_confidence": "high",
                "expected_refusal": False,
                "test_evidence": self._create_dsex_evidence(),
                "assertions": {
                    "recency": True,
                    "multiple_citations": True,
                    "correct_routing": True,
                    "data_sufficient": True
                },
                "description": "Stock market data with financial sources"
            },
            
            # 6. Ambiguous Query - Multi-intent
            {
                "id": "ambiguous_001",
                "prompt": "update today",
                "expected_intent": "news",  # Should default to news
                "expected_confidence": "low",
                "expected_refusal": True,
                "test_evidence": self._create_thin_evidence(),
                "assertions": {
                    "recency": False,
                    "multiple_citations": False,
                    "correct_routing": True,
                    "data_sufficient": False
                },
                "description": "Ambiguous query with insufficient data should refuse"
            },
            
            # 7. Old News - Should refuse
            {
                "id": "news_002",
                "prompt": "Breaking news about economic crisis",
                "expected_intent": "news",
                "expected_confidence": "low",
                "expected_refusal": True,
                "test_evidence": self._create_stale_evidence(),
                "assertions": {
                    "recency": False,
                    "multiple_citations": True,
                    "correct_routing": True,
                    "data_sufficient": False
                },
                "description": "News with old sources should refuse due to staleness"
            },
            
            # 8. Single Source News - Should refuse
            {
                "id": "news_003",
                "prompt": "Major government policy announcement today",
                "expected_intent": "news",
                "expected_confidence": "low", 
                "expected_refusal": True,
                "test_evidence": self._create_single_source_evidence(),
                "assertions": {
                    "recency": True,
                    "multiple_citations": False,
                    "correct_routing": True,
                    "data_sufficient": False
                },
                "description": "Important news with single source should refuse"
            },
            
            # 9. Sports Without Numbers - Should refuse
            {
                "id": "sports_002",
                "prompt": "Bangladesh cricket team performance",
                "expected_intent": "sports",
                "expected_confidence": "low",
                "expected_refusal": True,
                "test_evidence": self._create_sports_no_markers_evidence(),
                "assertions": {
                    "recency": True,
                    "multiple_citations": True,
                    "correct_routing": True,
                    "data_sufficient": False
                },
                "description": "Sports content without numeric markers should refuse"
            },
            
            # 10. Market Data - Contradictory
            {
                "id": "markets_002",
                "prompt": "Stock market closing prices today",
                "expected_intent": "markets",
                "expected_confidence": "medium",
                "expected_refusal": False,
                "test_evidence": self._create_contradictory_market_evidence(),
                "assertions": {
                    "recency": True,
                    "multiple_citations": True,
                    "correct_routing": True,
                    "data_sufficient": True
                },
                "description": "Market data with minor contradictions - medium confidence"
            },
            
            # 11. Lookup Query
            {
                "id": "lookup_001",
                "prompt": "Who is Sheikh Hasina",
                "expected_intent": "lookup",
                "expected_confidence": "high",
                "expected_refusal": False,
                "test_evidence": self._create_biographical_evidence(),
                "assertions": {
                    "recency": False,  # Biographical info doesn't need recent sources
                    "multiple_citations": True,
                    "correct_routing": True,
                    "data_sufficient": True
                },
                "description": "Biographical lookup with established sources"
            },
            
            # 12. Weather - Insufficient Data
            {
                "id": "weather_002",
                "prompt": "আগামীকাল ঢাকায় বৃষ্টি হবে কি",
                "expected_intent": "weather",
                "expected_confidence": "low",
                "expected_refusal": True,
                "test_evidence": self._create_insufficient_weather_evidence(),
                "assertions": {
                    "recency": False,
                    "multiple_citations": False,
                    "correct_routing": True,
                    "data_sufficient": False
                },
                "description": "Weather query with insufficient reliable data should refuse"
            },
            
            # 13. Multi-intent Query - Sports + News
            {
                "id": "multi_001",
                "prompt": "Bangladesh cricket team news and latest match scores",
                "expected_intent": "sports",  # Primary intent
                "expected_confidence": "high",
                "expected_refusal": False,
                "test_evidence": self._create_sports_news_evidence(),
                "assertions": {
                    "recency": True,
                    "multiple_citations": True,
                    "correct_routing": True,
                    "data_sufficient": True
                },
                "description": "Multi-intent query with sufficient data for both aspects"
            },
            
            # 14. Very Recent Breaking News
            {
                "id": "breaking_001",
                "prompt": "Breaking: What just happened in Dhaka",
                "expected_intent": "news",
                "expected_confidence": "high",
                "expected_refusal": False,
                "test_evidence": self._create_breaking_news_evidence(),
                "assertions": {
                    "recency": True,
                    "multiple_citations": True, 
                    "correct_routing": True,
                    "data_sufficient": True
                },
                "description": "Breaking news with very recent, multiple sources"
            },
            
            # 15. Complex Economic Analysis
            {
                "id": "complex_001", 
                "prompt": "Bangladesh GDP growth analysis with inflation trends",
                "expected_intent": "news",
                "expected_confidence": "high",
                "expected_refusal": False,
                "test_evidence": self._create_economic_analysis_evidence(),
                "assertions": {
                    "recency": True,
                    "multiple_citations": True,
                    "correct_routing": True,
                    "data_sufficient": True
                },
                "description": "Complex economic analysis with comprehensive data"
            }
        ]
    
    def _create_good_news_evidence(self) -> List[Dict[str, Any]]:
        """Create good quality news evidence"""
        return [
            {
                "title": "Bangladesh Economy Shows Strong Recovery",
                "excerpt": "GDP growth accelerated to 6.8% in latest quarter with industrial production up 4.2%",
                "outlet": "reuters.com",
                "published_at": (self.current_time - timedelta(hours=2)).isoformat(),
                "url": "https://reuters.com/bangladesh-economy"
            },
            {
                "title": "Economic Growth Reaches New Heights",
                "excerpt": "Latest data confirms GDP expansion of 6.7% with employment figures improving significantly",
                "outlet": "prothomalo.com",
                "published_at": (self.current_time - timedelta(hours=4)).isoformat(),
                "url": "https://prothomalo.com/economy"
            },
            {
                "title": "Strong Economic Performance Continues",
                "excerpt": "Government reports show sustained growth of 6.9% in the manufacturing sector",
                "outlet": "thedailystar.net",
                "published_at": (self.current_time - timedelta(hours=6)).isoformat(),
                "url": "https://thedailystar.net/business"
            }
        ]
    
    def _create_politics_evidence(self) -> List[Dict[str, Any]]:
        """Create political news evidence"""
        return [
            {
                "title": "প্রধানমন্ত্রী নতুন নীতিমালা ঘোষণা করেছেন",
                "excerpt": "নতুন অর্থনৈতিক নীতিমালা ৫টি মূল খাতে ১২% বৃদ্ধির লক্ষ্য নির্ধারণ করেছে",
                "outlet": "prothomalo.com",
                "published_at": (self.current_time - timedelta(hours=1)).isoformat(),
                "url": "https://prothomalo.com/politics/policy"
            },
            {
                "title": "New Economic Policy Framework Announced",
                "excerpt": "Prime Minister outlines comprehensive economic strategy targeting 12% growth across 5 key sectors",
                "outlet": "thedailystar.net",
                "published_at": (self.current_time - timedelta(hours=3)).isoformat(),
                "url": "https://thedailystar.net/politics"
            },
            {
                "title": "Government Unveils Economic Roadmap",
                "excerpt": "Strategic plan includes 12.1% growth projections with focus on infrastructure and technology",
                "outlet": "bdnews24.com",
                "published_at": (self.current_time - timedelta(hours=5)).isoformat(),
                "url": "https://bdnews24.com/politics"
            }
        ]
    
    def _create_cricket_evidence(self) -> List[Dict[str, Any]]:
        """Create cricket match evidence"""
        return [
            {
                "title": "Bangladesh Defeats India by 5 Wickets",
                "excerpt": "Bangladesh chased down 287 runs with 8 balls to spare, Mushfiqur scored 89 not out",
                "outlet": "cricinfo.com",
                "published_at": (self.current_time - timedelta(hours=18)).isoformat(),
                "url": "https://cricinfo.com/bangladesh-india"
            },
            {
                "title": "Historic Win Against India in ODI",
                "excerpt": "Bangladesh secured victory by 5 wickets with Mushfiqur's unbeaten 89 leading the chase",
                "outlet": "prothomalo.com",
                "published_at": (self.current_time - timedelta(hours=20)).isoformat(),
                "url": "https://prothomalo.com/sports/cricket"
            },
            {
                "title": "Bangladesh Cricket Team Triumphs",
                "excerpt": "Successful chase of 287 runs completed with 5 wickets in hand, Mushfiqur remained 89*",
                "outlet": "thedailystar.net",
                "published_at": (self.current_time - timedelta(hours=19)).isoformat(),
                "url": "https://thedailystar.net/sports"
            }
        ]
    
    def _create_weather_evidence(self) -> List[Dict[str, Any]]:
        """Create weather forecast evidence"""
        return [
            {
                "title": "Dhaka Weather: Rain Expected Next 3 Days",
                "excerpt": "Meteorological forecast shows 60% rain probability with temperatures 28-32°C",
                "outlet": "weatherbd.com",
                "published_at": (self.current_time - timedelta(hours=6)).isoformat(),
                "url": "https://weatherbd.com/dhaka-forecast"
            },
            {
                "title": "3-Day Weather Outlook for Capital",
                "excerpt": "Heavy rainfall predicted with 65% probability, temperature range 27-33°C expected",
                "outlet": "bdmeteo.gov.bd",
                "published_at": (self.current_time - timedelta(hours=8)).isoformat(),
                "url": "https://bdmeteo.gov.bd/forecast"
            }
        ]
    
    def _create_dsex_evidence(self) -> List[Dict[str, Any]]:
        """Create stock market evidence"""
        return [
            {
                "title": "DSEX Closes 1.2% Higher at 6,245 Points",
                "excerpt": "Dhaka Stock Exchange index gained 74 points with trading volume reaching 285 crore taka",
                "outlet": "dsebd.org",
                "published_at": (self.current_time - timedelta(hours=4)).isoformat(),
                "url": "https://dsebd.org/market-update"
            },
            {
                "title": "Strong Trading Day for Dhaka Stocks",
                "excerpt": "DSEX index advanced 1.18% to close at 6,243 points with total turnover 283 crore",
                "outlet": "tbsnews.net",
                "published_at": (self.current_time - timedelta(hours=5)).isoformat(),
                "url": "https://tbsnews.net/economy/stock"
            },
            {
                "title": "DSE Index Posts Solid Gains",
                "excerpt": "Market closed higher with DSEX up 75 points at 6,244, turnover 284 crore taka",
                "outlet": "newagebd.net",
                "published_at": (self.current_time - timedelta(hours=6)).isoformat(),
                "url": "https://newagebd.net/business"
            }
        ]
    
    def _create_thin_evidence(self) -> List[Dict[str, Any]]:
        """Create insufficient evidence"""
        return [
            {
                "title": "Some Update Happened",
                "excerpt": "Something occurred recently according to sources",
                "outlet": "unknown-blog.com",
                "published_at": (self.current_time - timedelta(hours=12)).isoformat(),
                "url": "https://unknown-blog.com/update"
            }
        ]
    
    def _create_stale_evidence(self) -> List[Dict[str, Any]]:
        """Create stale/old evidence"""
        return [
            {
                "title": "Economic Crisis Develops",
                "excerpt": "Major economic disruption with 8.5% decline reported across sectors",
                "outlet": "reuters.com",
                "published_at": (self.current_time - timedelta(days=3)).isoformat(),
                "url": "https://reuters.com/old-crisis"
            },
            {
                "title": "Financial Sector Faces Challenges",
                "excerpt": "Banking sector reports 8.2% contraction with widespread impact",
                "outlet": "bloomberg.com",
                "published_at": (self.current_time - timedelta(days=4)).isoformat(),
                "url": "https://bloomberg.com/old-finance"
            }
        ]
    
    def _create_single_source_evidence(self) -> List[Dict[str, Any]]:
        """Create evidence with only one source"""
        return [
            {
                "title": "Government Announces Major Policy Changes",
                "excerpt": "Comprehensive policy reform includes 15% tax reduction and 8% infrastructure spending increase",
                "outlet": "reuters.com",
                "published_at": (self.current_time - timedelta(hours=2)).isoformat(),
                "url": "https://reuters.com/policy-announcement"
            }
        ]
    
    def _create_sports_no_markers_evidence(self) -> List[Dict[str, Any]]:
        """Create sports evidence without numeric markers"""
        return [
            {
                "title": "Bangladesh Cricket Team Performs Well",
                "excerpt": "The team showed good form in recent matches with excellent batting and bowling",
                "outlet": "cricinfo.com",
                "published_at": (self.current_time - timedelta(hours=6)).isoformat(),
                "url": "https://cricinfo.com/performance"
            },
            {
                "title": "Strong Showing by National Team",
                "excerpt": "Players demonstrated skill and determination throughout the tournament",
                "outlet": "prothomalo.com",
                "published_at": (self.current_time - timedelta(hours=8)).isoformat(),
                "url": "https://prothomalo.com/sports-performance"
            }
        ]
    
    def _create_contradictory_market_evidence(self) -> List[Dict[str, Any]]:
        """Create market evidence with contradictions"""
        return [
            {
                "title": "DSEX Closes at 6,245 Points",
                "excerpt": "Stock market ended 1.2% higher with index gaining 74 points in active trading",
                "outlet": "dsebd.org",
                "published_at": (self.current_time - timedelta(hours=3)).isoformat(),
                "url": "https://dsebd.org/market-close"
            },
            {
                "title": "DSE Index Finishes at 6,198 Points", 
                "excerpt": "Market closed 0.8% lower with DSEX declining 47 points amid selling pressure",
                "outlet": "tbsnews.net",
                "published_at": (self.current_time - timedelta(hours=4)).isoformat(),
                "url": "https://tbsnews.net/market-report"
            },
            {
                "title": "Mixed Trading Day on DSE",
                "excerpt": "DSEX ended at 6,221 points showing volatile movement throughout the session",
                "outlet": "newagebd.net",
                "published_at": (self.current_time - timedelta(hours=5)).isoformat(),
                "url": "https://newagebd.net/market-mixed"
            }
        ]
    
    def _create_biographical_evidence(self) -> List[Dict[str, Any]]:
        """Create biographical evidence (doesn't need recent sources)"""
        return [
            {
                "title": "Sheikh Hasina - Prime Minister Profile",
                "excerpt": "Sheikh Hasina Wazed is the Prime Minister of Bangladesh, daughter of Sheikh Mujibur Rahman",
                "outlet": "britannica.com",
                "published_at": (self.current_time - timedelta(days=30)).isoformat(),
                "url": "https://britannica.com/hasina"
            },
            {
                "title": "Political Leader Biography",
                "excerpt": "Current PM Sheikh Hasina has served multiple terms and leads the Awami League party",
                "outlet": "wikipedia.org",
                "published_at": (self.current_time - timedelta(days=15)).isoformat(),
                "url": "https://wikipedia.org/sheikh-hasina"
            },
            {
                "title": "Bangladesh Political Leadership",
                "excerpt": "Sheikh Hasina became PM in 2009 and has been a major figure in Bangladeshi politics",
                "outlet": "bbc.com",
                "published_at": (self.current_time - timedelta(days=45)).isoformat(),
                "url": "https://bbc.com/hasina-profile"
            }
        ]
    
    def _create_insufficient_weather_evidence(self) -> List[Dict[str, Any]]:
        """Create insufficient weather evidence"""
        return [
            {
                "title": "Weather Update",
                "excerpt": "Conditions may vary tomorrow",
                "outlet": "local-weather-blog.com",
                "published_at": (self.current_time - timedelta(hours=24)).isoformat(),
                "url": "https://local-weather-blog.com/update"
            }
        ]
    
    def _create_sports_news_evidence(self) -> List[Dict[str, Any]]:
        """Create multi-intent sports+news evidence"""
        return [
            {
                "title": "Bangladesh Cricket Team News: Captain Announcement",
                "excerpt": "New captain appointed with team scoring 320 runs in latest match, averaging 68 runs per game",
                "outlet": "cricinfo.com",
                "published_at": (self.current_time - timedelta(hours=4)).isoformat(),
                "url": "https://cricinfo.com/team-news"
            },
            {
                "title": "Cricket Squad Updates and Match Results",
                "excerpt": "Team changes announced alongside recent victory by 7 wickets with 42 balls remaining",
                "outlet": "prothomalo.com",
                "published_at": (self.current_time - timedelta(hours=6)).isoformat(),
                "url": "https://prothomalo.com/cricket-updates"
            },
            {
                "title": "National Cricket Team Latest Developments",
                "excerpt": "Squad selection completed for upcoming series, recent performance shows 85% win rate",
                "outlet": "thedailystar.net",
                "published_at": (self.current_time - timedelta(hours=8)).isoformat(),
                "url": "https://thedailystar.net/cricket-developments"
            }
        ]
    
    def _create_breaking_news_evidence(self) -> List[Dict[str, Any]]:
        """Create very recent breaking news evidence"""
        return [
            {
                "title": "Breaking: Major Development in Dhaka",
                "excerpt": "Significant infrastructure project announced with 12 billion taka investment approved",
                "outlet": "reuters.com",
                "published_at": (self.current_time - timedelta(minutes=30)).isoformat(),
                "url": "https://reuters.com/breaking-dhaka"
            },
            {
                "title": "Urgent: Infrastructure Investment Confirmed",
                "excerpt": "Government confirms 12.5 billion taka allocation for new Dhaka development project",
                "outlet": "prothomalo.com",
                "published_at": (self.current_time - timedelta(minutes=45)).isoformat(),
                "url": "https://prothomalo.com/breaking-investment"
            },
            {
                "title": "Flash: Major Dhaka Project Approved",
                "excerpt": "Cabinet approves 12.2 billion taka infrastructure initiative for capital city expansion",
                "outlet": "bdnews24.com",
                "published_at": (self.current_time - timedelta(minutes=60)).isoformat(),
                "url": "https://bdnews24.com/flash-project"
            }
        ]
    
    def _create_economic_analysis_evidence(self) -> List[Dict[str, Any]]:
        """Create complex economic analysis evidence"""
        return [
            {
                "title": "Bangladesh GDP Analysis: Growth Amid Inflation Challenges",
                "excerpt": "GDP expanded 6.8% while inflation rose to 5.2%, unemployment decreased to 3.9% in comprehensive economic review",
                "outlet": "worldbank.org",
                "published_at": (self.current_time - timedelta(hours=8)).isoformat(),
                "url": "https://worldbank.org/bangladesh-analysis"
            },
            {
                "title": "Economic Performance Review: Mixed Indicators",
                "excerpt": "Growth rate of 6.7% offset by inflation at 5.1%, with employment improving to 96.2% participation",
                "outlet": "imf.org",
                "published_at": (self.current_time - timedelta(hours=10)).isoformat(),
                "url": "https://imf.org/bangladesh-economy"
            },
            {
                "title": "Comprehensive Economic Assessment Released",
                "excerpt": "Latest data shows 6.9% GDP growth, 5.0% inflation rate, and unemployment at 3.8% in detailed analysis",
                "outlet": "adb.org",
                "published_at": (self.current_time - timedelta(hours=12)).isoformat(),
                "url": "https://adb.org/bangladesh-assessment"
            }
        ]

class TestFifteenPromptEval(unittest.TestCase):
    """15-prompt evaluation test suite"""
    
    def setUp(self):
        """Set up evaluation"""
        self.eval_set = EvaluationSet()
        self.results = []
    
    def test_all_prompts(self):
        """Run all 15 evaluation prompts"""
        for i, prompt_data in enumerate(self.eval_set.evaluation_prompts):
            with self.subTest(prompt_id=prompt_data["id"], i=i+1):
                result = self._evaluate_single_prompt(prompt_data)
                self.results.append(result)
                
                # Assert based on expected outcomes
                self._assert_prompt_expectations(prompt_data, result)
    
    def _evaluate_single_prompt(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a single prompt"""
        prompt = prompt_data["prompt"]
        evidence = prompt_data["test_evidence"]
        
        # 1. Test intent classification
        intent_result = ml_classify(prompt)
        
        # 2. Test confidence labeling
        confidence_result = calculate_trustworthy_confidence(evidence)
        
        # 3. Test quality guardrails and refusal logic
        should_refuse, response = check_quality_and_refuse_if_needed(
            f"Test summary for: {prompt}", evidence
        )
        
        # Create test summary with/without numeric markers based on evidence
        test_summary = self._create_test_summary(prompt_data, evidence)
        should_refuse_real, response_real = check_quality_and_refuse_if_needed(test_summary, evidence)
        
        return {
            "prompt_id": prompt_data["id"],
            "prompt": prompt,
            "intent_result": intent_result,
            "confidence_result": confidence_result,
            "quality_result": response_real,
            "should_refuse": should_refuse_real,
            "test_summary": test_summary,
            "recency_check": self._check_recency(evidence),
            "citation_check": self._check_citations(evidence),
            "routing_check": intent_result["intent"] == prompt_data["expected_intent"]
        }
    
    def _create_test_summary(self, prompt_data: Dict[str, Any], evidence: List[Dict[str, Any]]) -> str:
        """Create appropriate test summary based on prompt type"""
        prompt_id = prompt_data["id"]
        
        if "sports" in prompt_id and "no_markers" in prompt_id:
            return "The cricket team performed well in recent matches showing good form."
        elif "sports" in prompt_id:
            return "Bangladesh defeated India by 5 wickets with Mushfiqur scoring 89 not out in yesterday's ODI match."
        elif "weather" in prompt_id and "insufficient" in prompt_data.get("description", ""):
            return "Weather conditions may change tomorrow."
        elif "weather" in prompt_id:
            return "Dhaka weather forecast shows 60-65% rain probability over next 3 days with temperatures 27-33°C."
        elif "markets" in prompt_id and "contradictory" in prompt_data.get("description", ""):
            return "DSEX closed with mixed reports showing values between 6,198-6,245 points with varied trading activity."
        elif "markets" in prompt_id:
            return "DSEX index closed 1.2% higher at 6,245 points with trading volume reaching 285 crore taka."
        elif "politics" in prompt_id:
            return "Prime Minister announced new economic policy targeting 12% growth across 5 key sectors with comprehensive reforms."
        elif "breaking" in prompt_id:
            return "Major infrastructure project announced in Dhaka with 12+ billion taka investment approved by government."
        elif "complex" in prompt_id:
            return "Bangladesh GDP grew 6.8% while inflation rose to 5.2% and unemployment decreased to 3.9% in latest economic analysis."
        elif "lookup" in prompt_id:
            return "Sheikh Hasina is the Prime Minister of Bangladesh and daughter of Sheikh Mujibur Rahman, leading the Awami League party."
        elif "ambiguous" in prompt_id or "thin" in prompt_data.get("description", ""):
            return "Some updates occurred recently according to available sources."
        else:
            return "Bangladesh economy shows strong performance with 6.8% GDP growth and improved industrial production at 4.2%."
    
    def _check_recency(self, evidence: List[Dict[str, Any]]) -> bool:
        """Check if evidence meets recency requirements"""
        if not evidence:
            return False
        
        current_time = datetime.now(timezone.utc)
        recent_count = 0
        
        for item in evidence:
            published_at = item.get("published_at")
            if not published_at:
                continue
                
            try:
                if isinstance(published_at, str):
                    dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                else:
                    dt = published_at
                
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                
                hours_old = (current_time - dt).total_seconds() / 3600
                if hours_old <= 24:  # Within 24 hours
                    recent_count += 1
                    
            except:
                continue
        
        return recent_count >= 2  # At least 2 recent sources
    
    def _check_citations(self, evidence: List[Dict[str, Any]]) -> bool:
        """Check if there are sufficient citations for non-trivial claims"""
        return len(evidence) >= 2
    
    def _assert_prompt_expectations(self, prompt_data: Dict[str, Any], result: Dict[str, Any]):
        """Assert that results match expectations"""
        assertions = prompt_data["assertions"]
        
        # Check correct routing
        if assertions["correct_routing"]:
            self.assertEqual(
                result["intent_result"]["intent"], 
                prompt_data["expected_intent"],
                f"Intent mismatch for {prompt_data['id']}: expected {prompt_data['expected_intent']}, got {result['intent_result']['intent']}"
            )
        
        # Check refusal behavior
        self.assertEqual(
            result["should_refuse"],
            prompt_data["expected_refusal"],
            f"Refusal mismatch for {prompt_data['id']}: expected {prompt_data['expected_refusal']}, got {result['should_refuse']}"
        )
        
        # Check confidence level (only if not refused)
        if not result["should_refuse"]:
            actual_confidence = result["confidence_result"]["level"]
            expected_confidence = prompt_data["expected_confidence"]
            self.assertEqual(
                actual_confidence,
                expected_confidence,
                f"Confidence mismatch for {prompt_data['id']}: expected {expected_confidence}, got {actual_confidence}"
            )
        
        # Check recency assertion
        if assertions["recency"]:
            self.assertTrue(
                result["recency_check"],
                f"Recency check failed for {prompt_data['id']}: expected recent sources"
            )
        
        # Check multiple citations assertion
        if assertions["multiple_citations"]:
            self.assertTrue(
                result["citation_check"],
                f"Citation check failed for {prompt_data['id']}: expected ≥2 citations"
            )
        
        # Check data sufficiency matches refusal
        if assertions["data_sufficient"]:
            self.assertFalse(
                result["should_refuse"],
                f"Data sufficiency check failed for {prompt_data['id']}: should not refuse with sufficient data"
            )
        else:
            self.assertTrue(
                result["should_refuse"],
                f"Data sufficiency check failed for {prompt_data['id']}: should refuse with insufficient data"
            )
    
    def tearDown(self):
        """Generate evaluation report"""
        self._generate_evaluation_report()
    
    def _generate_evaluation_report(self):
        """Generate detailed evaluation report"""
        if not self.results:
            return
        
        total_prompts = len(self.results)
        
        # Calculate metrics
        correct_intent = sum(1 for r in self.results if r["routing_check"])
        correct_refusal = sum(1 for r in self.results if "should_refuse" in r)
        recency_passed = sum(1 for r in self.results if r.get("recency_check", False))
        citation_passed = sum(1 for r in self.results if r.get("citation_check", False))
        
        print("\n" + "="*60)
        print("15-PROMPT EVALUATION REPORT")
        print("="*60)
        print(f"Total prompts evaluated: {total_prompts}")
        print(f"Intent routing accuracy: {correct_intent}/{total_prompts} ({correct_intent/total_prompts*100:.1f}%)")
        print(f"Recency checks passed: {recency_passed}/{total_prompts} ({recency_passed/total_prompts*100:.1f}%)")
        print(f"Citation checks passed: {citation_passed}/{total_prompts} ({citation_passed/total_prompts*100:.1f}%)")
        
        # Detailed breakdown by category
        categories = {}
        for result in self.results:
            category = result["prompt_id"].split("_")[0]
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        print("\nBREAKDOWN BY CATEGORY:")
        for category, results in categories.items():
            correct = sum(1 for r in results if r["routing_check"])
            print(f"  {category}: {correct}/{len(results)} correct routing")
        
        # Failed cases
        failed_results = [r for r in self.results if not r["routing_check"]]
        if failed_results:
            print(f"\nFAILED CASES ({len(failed_results)}):")
            for result in failed_results:
                print(f"  {result['prompt_id']}: {result['prompt'][:50]}...")
                print(f"    Expected: {result.get('expected_intent', 'unknown')}, Got: {result['intent_result']['intent']}")
        
        print("="*60)

def run_evaluation():
    """Run the 15-prompt evaluation"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFifteenPromptEval)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result

if __name__ == "__main__":
    run_evaluation()