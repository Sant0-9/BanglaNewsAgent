import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from packages.router.intent import extract_location, extract_ticker, TEAM_NAMES
from packages.ml.intent_classifier import CompactIntentClassifier

class MLIntentRouter:
    """
    Enhanced intent router using ML classifier with rule-based fallback.
    Logs model performance and chosen classification method.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or "models/intent_classifier.pkl"
        self.classifier = None
        self.fallback_used_count = 0
        self.ml_used_count = 0
        self.performance_log = []
        
        # Create models directory if it doesn't exist
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        # Try to load ML classifier
        self._initialize_classifier()
    
    def _initialize_classifier(self) -> bool:
        """Initialize ML classifier if available"""
        try:
            self.classifier = CompactIntentClassifier(self.model_path)
            if self.classifier.is_trained:
                print(f"[ML_ROUTER] Loaded trained classifier from {self.model_path}")
                return True
            else:
                print(f"[ML_ROUTER] No trained model found, will use rule-based fallback")
                return False
        except Exception as e:
            print(f"[ML_ROUTER] Failed to initialize classifier: {e}")
            return False
    
    def classify(self, query: str, log_performance: bool = True) -> Dict[str, Any]:
        """
        Classify query intent using ML model with rule-based fallback.
        
        Args:
            query: Input query string
            log_performance: Whether to log performance metrics
            
        Returns:
            Classification result with intent, confidence, and metadata
        """
        start_time = time.time()
        
        # Try ML classification first
        ml_result = None
        if self.classifier and self.classifier.is_trained:
            try:
                ml_result = self.classifier.predict(query)
                self.ml_used_count += 1
                
                # Extract slots using rule-based methods (still valuable)
                slots = self._extract_slots(query, ml_result["primary_intent"])
                
                result = {
                    "intent": ml_result["primary_intent"],
                    "confidence": ml_result["confidence"],
                    "slots": slots,
                    "all_scores": ml_result["all_scores"],
                    "is_multi_intent": ml_result["is_multi_intent"],
                    "active_intents": ml_result["active_intents"],
                    "classification_method": ml_result["model_used"],
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
                
            except Exception as e:
                print(f"[ML_ROUTER] ML classification failed: {e}")
                ml_result = None
        
        # Fall back to rule-based classification
        if ml_result is None:
            result = self._classify_rule_based(query)
            result["processing_time_ms"] = (time.time() - start_time) * 1000
            self.fallback_used_count += 1
        
        # Log performance if requested
        if log_performance:
            self._log_performance(query, result)
        
        return result
    
    def _classify_rule_based(self, query: str) -> Dict[str, Any]:
        """Enhanced rule-based classification with better patterns"""
        query_lower = query.lower().strip()
        
        # Intent scoring with improved weights
        intent_scores = {
            "news": 0.0,
            "sports": 0.0,
            "markets": 0.0,
            "weather": 0.0,
            "lookup": 0.0
        }
        
        # Enhanced keyword patterns with weights
        patterns = {
            "news": {
                "high_weight": ["breaking", "latest", "news", "headline", "ব্রেকিং", "খবর", "সংবাদ", "তাজা"],
                "medium_weight": ["update", "report", "politics", "government", "আপডেট", "প্রতিবেদন", "সরকার"],
                "context_boost": ["today", "now", "current", "আজ", "এখন", "বর্তমান"]
            },
            "sports": {
                "high_weight": ["score", "match", "game", "team", "ম্যাচ", "খেলা", "দল", "স্কোর"],
                "medium_weight": ["player", "tournament", "league", "খেলোয়াড়", "টুর্নামেন্ট", "লিগ"],
                "context_boost": ["vs", "against", "final", "championship", "বনাম", "ফাইনাল"]
            },
            "markets": {
                "high_weight": ["stock", "price", "market", "trading", "শেয়ার", "বাজার", "দাম"],
                "medium_weight": ["crypto", "bitcoin", "investment", "ক্রিপ্টো", "বিনিয়োগ"],
                "context_boost": ["$", "usd", "dollar", "ডলার", "টাকা"]
            },
            "weather": {
                "high_weight": ["weather", "temperature", "rain", "আবহাওয়া", "তাপমাত্রা", "বৃষ্টি"],
                "medium_weight": ["forecast", "sunny", "cloudy", "পূর্বাভাস", "রৌদ্র", "মেঘ"],
                "context_boost": ["today", "tomorrow", "°", "degree", "আজ", "কাল", "ডিগ্রি"]
            },
            "lookup": {
                "high_weight": ["who is", "what is", "define", "কে এই", "কি এই", "ব্যাখ্যা"],
                "medium_weight": ["about", "information", "wiki", "সম্পর্কে", "তথ্য"],
                "context_boost": ["tell me", "explain", "বলো", "জানাও"]
            }
        }
        
        # Calculate scores
        for intent, pattern_groups in patterns.items():
            score = 0.0
            
            # High weight keywords
            for keyword in pattern_groups["high_weight"]:
                if keyword in query_lower:
                    score += 0.4
            
            # Medium weight keywords
            for keyword in pattern_groups["medium_weight"]:
                if keyword in query_lower:
                    score += 0.25
            
            # Context boost
            for keyword in pattern_groups["context_boost"]:
                if keyword in query_lower:
                    score += 0.15
            
            intent_scores[intent] = min(score, 1.0)
        
        # Special pattern bonuses
        # Sports team names
        if any(team.lower() in query_lower for team in TEAM_NAMES):
            intent_scores["sports"] += 0.3
        
        # Stock ticker patterns
        if extract_ticker(query):
            intent_scores["markets"] += 0.4
        
        # Question patterns for lookup
        if any(pattern in query_lower for pattern in ["who is", "what is", "কে এই", "কি এই"]):
            intent_scores["lookup"] += 0.5
        
        # Time-sensitive patterns for news
        if any(pattern in query_lower for pattern in ["today", "now", "latest", "আজ", "এখন", "সর্বশেষ"]):
            intent_scores["news"] += 0.2
        
        # Find primary intent
        primary_intent = max(intent_scores.items(), key=lambda x: x[1])[0]
        max_confidence = intent_scores[primary_intent]
        
        # Multi-intent detection
        active_intents = [intent for intent, score in intent_scores.items() if score >= 0.3]
        is_multi_intent = len(active_intents) > 1
        
        # Extract slots
        slots = self._extract_slots(query, primary_intent)
        
        return {
            "intent": primary_intent,
            "confidence": max_confidence,
            "slots": slots,
            "all_scores": intent_scores,
            "is_multi_intent": is_multi_intent,
            "active_intents": active_intents,
            "classification_method": "rule_based_enhanced"
        }
    
    def _extract_slots(self, query: str, primary_intent: str) -> Dict[str, Any]:
        """Extract relevant slots based on intent"""
        slots = {}
        
        # Location extraction for weather/sports/news
        location = extract_location(query)
        if location and primary_intent in ["weather", "sports", "news"]:
            slots["location"] = location
        
        # Ticker extraction for markets
        if primary_intent == "markets":
            ticker = extract_ticker(query)
            if ticker:
                slots["ticker"] = ticker
        
        # Team extraction for sports
        if primary_intent == "sports":
            query_lower = query.lower()
            for team in TEAM_NAMES:
                if team.lower() in query_lower:
                    if "teams" not in slots:
                        slots["teams"] = []
                    slots["teams"].append(team)
        
        # Time extraction
        time_indicators = {
            "today": ["today", "আজ"],
            "tomorrow": ["tomorrow", "কাল"],
            "this_week": ["this week", "এই সপ্তাহ"],
            "latest": ["latest", "recent", "সর্বশেষ", "সাম্প্রতিক"]
        }
        
        query_lower = query.lower()
        for time_key, indicators in time_indicators.items():
            if any(indicator in query_lower for indicator in indicators):
                slots["time"] = time_key
                break
        
        return slots
    
    def _log_performance(self, query: str, result: Dict[str, Any]):
        """Log classification performance for analysis"""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query[:100],  # Truncate for privacy
            "intent": result["intent"],
            "confidence": result["confidence"],
            "method": result["classification_method"],
            "processing_time_ms": result["processing_time_ms"],
            "is_multi_intent": result.get("is_multi_intent", False),
            "active_intents": result.get("active_intents", [])
        }
        
        self.performance_log.append(log_entry)
        
        # Keep only last 1000 entries to prevent memory bloat
        if len(self.performance_log) > 1000:
            self.performance_log = self.performance_log[-1000:]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        total_classifications = self.ml_used_count + self.fallback_used_count
        
        if not self.performance_log:
            return {
                "total_classifications": total_classifications,
                "ml_usage_ratio": 0.0,
                "fallback_usage_ratio": 0.0,
                "avg_processing_time_ms": 0.0,
                "recent_performance": []
            }
        
        # Calculate averages from recent performance log
        recent_entries = self.performance_log[-100:]  # Last 100 entries
        avg_processing_time = sum(entry["processing_time_ms"] for entry in recent_entries) / len(recent_entries)
        
        # Intent distribution
        intent_distribution = {}
        method_distribution = {}
        
        for entry in recent_entries:
            intent = entry["intent"]
            method = entry["method"]
            
            intent_distribution[intent] = intent_distribution.get(intent, 0) + 1
            method_distribution[method] = method_distribution.get(method, 0) + 1
        
        return {
            "total_classifications": total_classifications,
            "ml_used_count": self.ml_used_count,
            "fallback_used_count": self.fallback_used_count,
            "ml_usage_ratio": self.ml_used_count / max(total_classifications, 1),
            "fallback_usage_ratio": self.fallback_used_count / max(total_classifications, 1),
            "avg_processing_time_ms": avg_processing_time,
            "intent_distribution": intent_distribution,
            "method_distribution": method_distribution,
            "recent_entries_analyzed": len(recent_entries),
            "classifier_info": self.classifier.get_model_info() if self.classifier else None
        }
    
    def retrain_classifier(self, training_data_file: str) -> Dict[str, Any]:
        """Retrain the ML classifier with new data"""
        if not self.classifier:
            self.classifier = CompactIntentClassifier(self.model_path)
        
        try:
            stats = self.classifier.train(training_data_file)
            print(f"[ML_ROUTER] Classifier retrained successfully")
            return stats
        except Exception as e:
            print(f"[ML_ROUTER] Failed to retrain classifier: {e}")
            return {"error": str(e)}


# Global instance for the application
_ml_router_instance = None

def get_ml_router() -> MLIntentRouter:
    """Get global ML router instance"""
    global _ml_router_instance
    if _ml_router_instance is None:
        _ml_router_instance = MLIntentRouter()
    return _ml_router_instance

def classify(query: str) -> Dict[str, Any]:
    """
    Main classification function - drop-in replacement for original intent.classify()
    
    Args:
        query: Input query string
        
    Returns:
        Classification result compatible with existing API
    """
    router = get_ml_router()
    return router.classify(query)

def get_classification_stats() -> Dict[str, Any]:
    """Get ML router performance statistics"""
    router = get_ml_router()
    return router.get_performance_stats()