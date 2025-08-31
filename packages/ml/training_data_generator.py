import re
import json
import csv
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Set, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

from packages.db.repo import get_db_config

# Intent labels for multi-label classification
INTENT_LABELS = ["news", "sports", "markets", "weather", "lookup"]

# Enhanced rule-based patterns for initial labeling
TRAINING_PATTERNS = {
    "news": {
        "keywords": [
            # English
            "news", "headline", "headlines", "latest", "breaking", "update", "updates", 
            "report", "story", "article", "politics", "political", "government",
            "minister", "president", "parliament", "election", "vote", "crisis",
            "protest", "accident", "incident", "fire", "blast", "murder", "arrest",
            # Bangla
            "খবর", "সংবাদ", "আপডেট", "তাজা", "ব্রেকিং", "প্রতিবেদন", "নিবন্ধ",
            "রাজনীতি", "সরকার", "মন্ত্রী", "প্রধানমন্ত্রী", "সংসদ", "নির্বাচন",
            "ভোট", "সংকট", "বিক্ষোভ", "দুর্ঘটনা", "ঘটনা", "অগ্নিকাণ্ড", "বিস্ফোরণ",
            "হত্যা", "গ্রেফতার", "পুলিশ"
        ],
        "patterns": [
            r"what.*happen", r"what.*news", r"today.*news", r"latest.*from",
            r"breaking.*news", r"আজকের.*খবর", r"কি.*ঘটেছে", r"সর্বশেষ.*খবর"
        ]
    },
    "sports": {
        "keywords": [
            # English
            "score", "match", "game", "team", "player", "schedule", "fixture", 
            "tournament", "league", "championship", "football", "cricket", 
            "basketball", "tennis", "soccer", "goal", "win", "lose", "won", "lost",
            "final", "semifinal", "quarter", "cup", "series", "coach", "captain",
            # Bangla
            "ম্যাচ", "ফলাফল", "খেলা", "দল", "খেলোয়াড়", "ফুটবল", "ক্রিকেট", 
            "গোল", "জয়", "হার", "টুর্নামেন্ট", "ফাইনাল", "কোচ", "ক্যাপ্টেন",
            "সিরিজ", "কাপ", "লিগ"
        ],
        "patterns": [
            r"\d+\s*-\s*\d+", r"vs\s+", r"against", r"score.*today",
            r"match.*result", r"ম্যাচের.*ফলাফল", r"খেলার.*স্কোর"
        ]
    },
    "markets": {
        "keywords": [
            # English
            "stock", "share", "price", "quote", "market", "trading", "invest",
            "portfolio", "dividend", "nasdaq", "nyse", "dow", "s&p", "crypto", 
            "bitcoin", "ethereum", "bull", "bear", "ticker", "earnings", "revenue",
            "profit", "loss", "ipo", "bond", "commodity", "gold", "oil", "dollar",
            # Bangla
            "বাজার", "দাম", "শেয়ার", "বিনিয়োগ", "ক্রিপ্টো", "বিটকয়েন", "ব্যবসা",
            "মুনাফা", "ক্ষতি", "ডলার", "সোনা", "তেল"
        ],
        "patterns": [
            r"\$\d+", r"price.*of", r"stock.*price", r"market.*today",
            r"trading.*at", r"বাজার.*দাম", r"শেয়ারের.*দর"
        ]
    },
    "weather": {
        "keywords": [
            # English
            "weather", "forecast", "temperature", "temp", "rain", "sunny", "cloudy", 
            "storm", "snow", "wind", "humidity", "climate", "hot", "cold", "degree",
            "celsius", "fahrenheit", "precipitation", "drizzle", "thunderstorm",
            # Bangla
            "আবহাওয়া", "তাপমাত্রা", "বৃষ্টি", "পূর্বাভাস", "ঝড়", "গরম", "ঠান্ডা",
            "রৌদ্র", "মেঘ", "বাতাস", "ডিগ্রি", "বজ্রপাত"
        ],
        "patterns": [
            r"\d+\s*°", r"degrees?", r"weather.*today", r"temperature.*in",
            r"rain.*today", r"আজকের.*আবহাওয়া", r"তাপমাত্রা.*কত"
        ]
    },
    "lookup": {
        "keywords": [
            # English
            "who is", "what is", "define", "definition", "explain", "wiki",
            "wikipedia", "biography", "about", "meaning", "tell me about",
            "information about", "details about", "profile", "background",
            # Bangla
            "উইকিপিডিয়া", "সম্পর্কে", "ব্যাখ্যা", "অর্থ", "পরিচয়",
            "বলো", "জানাও", "কে এই", "কে এই ব্যক্তি", "কি এই", "তথ্য"
        ],
        "patterns": [
            r"who\s+is", r"what\s+is", r"tell\s+me\s+about", r"information\s+about",
            r"কে\s+এই", r"কি\s+এই", r"সম্পর্কে\s+বলো", r"তথ্য\s+দাও"
        ]
    }
}

class TrainingDataGenerator:
    """Generate training data from query logs using enhanced rule-based labeling"""
    
    def __init__(self):
        self.db_config = get_db_config()
    
    def extract_query_logs(self, days_back: int = 30, min_queries: int = 100) -> List[Dict[str, Any]]:
        """Extract recent query logs from database"""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get queries from last N days
                    since_date = datetime.now(timezone.utc) - timedelta(days=days_back)
                    
                    cur.execute("""
                        SELECT DISTINCT q.question, 
                               COUNT(*) as query_count,
                               AVG(q.response_time_ms) as avg_response_time
                        FROM query_logs q 
                        WHERE q.created_at >= %s 
                          AND LENGTH(q.question) >= 3
                          AND LENGTH(q.question) <= 200
                        GROUP BY q.question
                        HAVING COUNT(*) >= 1
                        ORDER BY COUNT(*) DESC
                        LIMIT %s
                    """, (since_date, min_queries * 10))  # Get more than needed for filtering
                    
                    results = []
                    for row in cur.fetchall():
                        results.append({
                            'query': row['question'],
                            'count': row['query_count'],
                            'avg_response_time': row['avg_response_time']
                        })
                    
                    return results[:min_queries]  # Return top N most frequent
                    
        except Exception as e:
            print(f"Error extracting query logs: {e}")
            return []
    
    def label_query(self, query: str) -> Dict[str, float]:
        """
        Label a query with confidence scores for each intent.
        Returns dict with intent -> confidence (0.0-1.0)
        """
        labels = {intent: 0.0 for intent in INTENT_LABELS}
        query_lower = query.lower().strip()
        
        for intent, patterns in TRAINING_PATTERNS.items():
            score = 0.0
            
            # Keyword matching
            keyword_matches = 0
            for keyword in patterns["keywords"]:
                if keyword.lower() in query_lower:
                    keyword_matches += 1
            
            if keyword_matches > 0:
                score += min(keyword_matches * 0.3, 0.8)  # Max 0.8 from keywords
            
            # Pattern matching
            pattern_matches = 0
            for pattern in patterns["patterns"]:
                if re.search(pattern, query_lower):
                    pattern_matches += 1
            
            if pattern_matches > 0:
                score += min(pattern_matches * 0.4, 0.6)  # Max 0.6 from patterns
            
            # Normalize score to 0-1 range
            labels[intent] = min(score, 1.0)
        
        return labels
    
    def is_multi_intent(self, labels: Dict[str, float], threshold: float = 0.3) -> bool:
        """Check if query has multiple intents above threshold"""
        active_intents = sum(1 for score in labels.values() if score >= threshold)
        return active_intents > 1
    
    def get_primary_intent(self, labels: Dict[str, float]) -> str:
        """Get the primary intent with highest score"""
        return max(labels.items(), key=lambda x: x[1])[0]
    
    def create_training_dataset(self, 
                              output_file: str = "intent_training_data.json",
                              days_back: int = 30,
                              min_queries: int = 500) -> Dict[str, Any]:
        """
        Create training dataset from query logs.
        
        Returns:
            Dataset statistics and saves training data to file
        """
        print(f"[TRAINING] Extracting query logs from last {days_back} days...")
        query_logs = self.extract_query_logs(days_back, min_queries)
        
        if not query_logs:
            print("[TRAINING] No query logs found, creating synthetic dataset...")
            query_logs = self._create_synthetic_queries()
        
        print(f"[TRAINING] Processing {len(query_logs)} unique queries...")
        
        training_data = []
        stats = {
            "total_queries": len(query_logs),
            "multi_intent_queries": 0,
            "intent_distribution": {intent: 0 for intent in INTENT_LABELS},
            "confidence_distribution": {"high": 0, "medium": 0, "low": 0}
        }
        
        for log_entry in query_logs:
            query = log_entry['query']
            labels = self.label_query(query)
            
            # Determine primary intent and confidence
            primary_intent = self.get_primary_intent(labels)
            max_confidence = max(labels.values())
            is_multi = self.is_multi_intent(labels)
            
            # Skip very low confidence queries (likely noise)
            if max_confidence < 0.2:
                continue
            
            # Create training example
            training_example = {
                "query": query,
                "labels": labels,
                "primary_intent": primary_intent,
                "confidence": max_confidence,
                "is_multi_intent": is_multi,
                "query_count": log_entry.get('count', 1),
                "avg_response_time": log_entry.get('avg_response_time', 0)
            }
            
            training_data.append(training_example)
            
            # Update statistics
            stats["intent_distribution"][primary_intent] += 1
            if is_multi:
                stats["multi_intent_queries"] += 1
            
            if max_confidence >= 0.8:
                stats["confidence_distribution"]["high"] += 1
            elif max_confidence >= 0.5:
                stats["confidence_distribution"]["medium"] += 1
            else:
                stats["confidence_distribution"]["low"] += 1
        
        # Save training data
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "days_back": days_back,
                    "intent_labels": INTENT_LABELS,
                    "statistics": stats
                },
                "training_data": training_data
            }, f, indent=2, ensure_ascii=False)
        
        print(f"[TRAINING] Dataset saved to {output_file}")
        print(f"[TRAINING] Statistics:")
        print(f"  Total examples: {len(training_data)}")
        print(f"  Multi-intent queries: {stats['multi_intent_queries']}")
        print(f"  Intent distribution: {stats['intent_distribution']}")
        print(f"  Confidence distribution: {stats['confidence_distribution']}")
        
        return stats
    
    def _create_synthetic_queries(self) -> List[Dict[str, Any]]:
        """Create synthetic training queries when no logs available"""
        synthetic_queries = [
            # News queries
            {"query": "আজকের তাজা খবর", "count": 10},
            {"query": "latest news today", "count": 8},
            {"query": "breaking news Bangladesh", "count": 6},
            {"query": "সরকারের নতুন ঘোষণা", "count": 5},
            {"query": "political crisis update", "count": 4},
            
            # Sports queries  
            {"query": "Bangladesh cricket score", "count": 12},
            {"query": "ম্যাচের ফলাফল", "count": 9},
            {"query": "football match today", "count": 7},
            {"query": "টুর্নামেন্টের সময়সূচী", "count": 5},
            {"query": "player injury update", "count": 3},
            
            # Markets queries
            {"query": "stock market today", "count": 8},
            {"query": "বাজারের দাম", "count": 6},
            {"query": "bitcoin price", "count": 10},
            {"query": "dollar rate Bangladesh", "count": 7},
            {"query": "gold price today", "count": 4},
            
            # Weather queries
            {"query": "আজকের আবহাওয়া", "count": 15},
            {"query": "weather forecast Dhaka", "count": 12},
            {"query": "তাপমাত্রা কত", "count": 8},
            {"query": "will it rain today", "count": 6},
            {"query": "বৃষ্টির সম্ভাবনা", "count": 5},
            
            # Lookup queries
            {"query": "who is Elon Musk", "count": 4},
            {"query": "শেখ মুজিবুর রহমান সম্পর্কে", "count": 6},
            {"query": "what is artificial intelligence", "count": 5},
            {"query": "Bitcoin কি", "count": 3},
            {"query": "tell me about NASA", "count": 2},
            
            # Multi-intent queries
            {"query": "Bangladesh cricket team news today", "count": 8},  # sports + news
            {"query": "weather and stock market update", "count": 3},     # weather + markets  
            {"query": "sports news and scores", "count": 5},              # sports + news
        ]
        
        return synthetic_queries