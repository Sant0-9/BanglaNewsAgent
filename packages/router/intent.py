import re
from typing import Dict, List, Optional

# Intent keywords with English and Bangla synonyms
INTENT_PATTERNS = {
    "weather": [
        # English
        "weather", "forecast", "temperature", "temp", "rain", "sunny", "cloudy", 
        "storm", "snow", "wind", "humidity", "climate", "hot", "cold",
        # Bangla
        "আবহাওয়া", "তাপমাত্রা", "বৃষ্টি", "পূর্বাভাস", "ঝড়", "গরম", "ঠান্ডা",
        "রৌদ্র", "মেঘ", "বাতাস"
    ],
    "markets": [
        # English
        "stock", "share", "price", "quote", "market", "trading", "invest",
        "portfolio", "dividend", "nasdaq", "nyse", "dow", "s&p", "crypto", 
        "bitcoin", "ethereum", "bull", "bear", "ticker", "earnings",
        # Bangla
        "বাজার", "দাম", "শেয়ার", "বিনিয়োগ", "ক্রিপ্টো", "বিটকয়েন", "ব্যবসা"
    ],
    "sports": [
        # English
        "score", "match", "game", "team", "player", "schedule", "fixture", 
        "tournament", "league", "championship", "football", "cricket", 
        "basketball", "tennis", "soccer", "goal", "win", "lose",
        # Bangla
        "ম্যাচ", "ফলাফল", "খেলা", "দল", "খেলোয়াড়", "ফুটবল", "ক্রিকেট", 
        "গোল", "জয়", "হার", "টুর্নামেন্ট"
    ],
    "lookup": [
        # English
        "who is", "what is", "define", "definition", "explain", "wiki",
        "wikipedia", "biography", "about", "meaning", "tell me about",
        # Bangla
        "উইকিপিডিয়া", "সম্পর্কে", "ব্যাখ্যা", "অর্থ",
        "বলো", "জানাও", "কে এই", "কে এই ব্যক্তি", "কি এই"
    ]
}

# Common locations for slot extraction
COMMON_LOCATIONS = [
    # Major cities
    "dhaka", "chittagong", "sylhet", "rajshahi", "khulna", "barisal", "rangpur",
    "london", "paris", "tokyo", "new york", "beijing", "delhi", "mumbai",
    "karachi", "bangkok", "singapore", "dubai", "cairo", "lagos",
    # Bangla cities
    "ঢাকা", "চট্টগ্রাম", "সিলেট", "রাজশাহী", "খুলনা", "বরিশাল", "রংপুর", "ডালাস"
]

# Team names for sports
TEAM_NAMES = [
    # Cricket
    "bangladesh", "india", "pakistan", "england", "australia", "south africa",
    "west indies", "new zealand", "sri lanka", "afghanistan",
    # Football
    "barcelona", "real madrid", "madrid", "manchester", "liverpool", "arsenal", "chelsea",
    "bayern", "juventus", "psg", "milan",
    # Bangla teams
    "বাংলাদেশ", "ভারত", "পাকিস্তান", "ইংল্যান্ড"
]

def extract_location(query: str) -> Optional[str]:
    """Extract location from query using capitalized words and common city list.
    More conservative to avoid false positives like 'Latest', and strips punctuation.
    """
    query_lower = query.lower()

    # Check against common locations first (substring match in BN/EN)
    for location in COMMON_LOCATIONS:
        if location.lower() in query_lower:
            return location.title()

    # Look for capitalized words (potential city names) with punctuation stripped
    words = query.split()
    exclude_words = {
        'i', 'the', 'a', 'an', 'in', 'at', 'for', 'to', 'of', 'on', 'about',
        'what', "what's", 'whats', 'who', 'is', 'news', 'today', 'latest', 'breaking',
        'score', 'match', 'vs'
    }
    for raw_word in words:
        word = raw_word.strip(",.?!:;()[]{}'\"“”’`")
        # Skip too short or excluded words
        if len(word) <= 2 or word.lower() in exclude_words:
            continue
        # If word is capitalized and remaining are lowercase, treat as location
        if word[0].isupper() and word[1:].islower():
            return word

    return None

def extract_ticker(query: str) -> Optional[str]:
    """Extract stock ticker symbols from query"""
    query_lower = query.lower()
    
    # Look for patterns like "AAPL stock", "ticker MSFT", "শেয়ার GOOGL"
    ticker_patterns = [
        r'\b([A-Z]{1,5})\s+(?:stock|share|price|quote)',
        r'(?:stock|share|ticker|শেয়ার)\s+([A-Z]{1,5})\b',
        r'\$([A-Z]{1,5})\b',  # $AAPL format
    ]
    
    for pattern in ticker_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Look for standalone uppercase words 1-5 chars (potential tickers)
    words = query.split()
    for word in words:
        if len(word) >= 1 and len(word) <= 5 and word.isupper():
            # Common words to exclude
            exclude = ['I', 'A', 'IS', 'THE', 'AND', 'OR', 'BUT', 'NOT', 'ALL', 'ANY']
            if word not in exclude:
                return word
    
    return None

def extract_sport_team(query: str) -> Optional[str]:
    """Extract sports team names from query; prefer longest match and preserve casing"""
    query_lower = query.lower()

    matches: List[str] = [team for team in TEAM_NAMES if team.lower() in query_lower]
    if not matches:
        return None

    # Prefer the longest match (e.g., "Real Madrid" over "Madrid")
    best = max(matches, key=len)

    # Return with original casing from the query if possible
    start_idx = query_lower.find(best.lower())
    if start_idx != -1:
        return query[start_idx:start_idx + len(best)]
    return best.title()

def calculate_intent_score(query: str, intent: str, patterns: List[str]) -> float:
    """Calculate score for an intent based on keyword matches"""
    query_lower = query.lower()
    score = 0.0
    
    # Count keyword matches
    for pattern in patterns:
        if pattern.lower() in query_lower:
            score += 1.0
    
    # Bonus for slot presence
    if intent == "weather" and extract_location(query):
        score += 0.2
    elif intent == "markets" and extract_ticker(query):
        score += 0.2
    elif intent == "sports" and extract_sport_team(query):
        score += 0.2
    elif intent == "lookup" and any(
        phrase in query_lower for phrase in [
            "who is", "what is", "tell me about", "কে এই ব্যক্তি", "কে এই", "কি এই"
        ]
    ):
        score += 0.2
    
    return score

def classify(query: str) -> Dict:
    """
    Classify query intent using rule-based approach
    
    Returns:
        {"intent": str, "confidence": float, "slots": dict}
    """
    if not query or not query.strip():
        return {"intent": "news", "confidence": 0.0, "slots": {}}
    
    intent_scores = {}
    
    # Calculate scores for each intent
    for intent, patterns in INTENT_PATTERNS.items():
        score = calculate_intent_score(query, intent, patterns)
        if score > 0:
            intent_scores[intent] = score
    
    # If no intents matched, default to news
    if not intent_scores:
        return {"intent": "news", "confidence": 0.0, "slots": {}}
    
    # Find best intent(s)
    max_score = max(intent_scores.values())
    best_intents = [intent for intent, score in intent_scores.items() if score == max_score]
    
    # Tie-breaking priority: weather > markets > sports > lookup > news
    priority_order = ["weather", "markets", "sports", "lookup", "news"]
    
    chosen_intent = "news"  # default
    for intent in priority_order:
        if intent in best_intents:
            chosen_intent = intent
            break
    
    # Calculate confidence (normalize score)
    confidence = min(max_score / 3.0, 1.0)  # Cap at 1.0
    
    # Extract relevant slots
    slots = {}
    
    if chosen_intent == "weather":
        location = extract_location(query)
        if location:
            slots["location"] = location
    
    elif chosen_intent == "markets":
        ticker = extract_ticker(query)
        if ticker:
            slots["ticker"] = ticker
    
    elif chosen_intent == "sports":
        team = extract_sport_team(query)
        if team:
            slots["sport"] = team
    
    elif chosen_intent == "lookup":
        # Try to extract the subject being looked up (prefer specific BN patterns first)
        lookup_patterns = [
            r'কে এই ব্যক্তি\s+(.+?)(?:\?|$)',
            r'কে এই\s+(.+?)(?:\?|$)',
            r'who is\s+(.+?)(?:\?|$)',
            r'what is\s+(.+?)(?:\?|$)', 
            r'tell me about\s+(.+?)(?:\?|$)',
            r'কে\s+(.+?)(?:\?|$)',
            r'কি\s+(.+?)(?:\?|$)',
        ]

        for pattern in lookup_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                subject = match.group(1).strip()
                # Clean common Bangla prefixes that slip through
                for prefix in ["এই ব্যক্তি ", "এই "]:
                    if subject.startswith(prefix):
                        subject = subject[len(prefix):].strip()
                slots["subject"] = subject
                break
    
    return {
        "intent": chosen_intent,
        "confidence": confidence,
        "slots": slots
    }

# Test function for development
def test_classifier():
    """Test the intent classifier with sample queries"""
    test_queries = [
        "What's the weather in Dhaka?",
        "আজকের আবহাওয়া কেমন?",
        "AAPL stock price",
        "বিটকয়েনের দাম কত?", 
        "Bangladesh vs India cricket score",
        "ম্যাচের ফলাফল কি?",
        "Who is Elon Musk?",
        "কে এই ব্যক্তি?",
        "Latest news about climate change"
    ]
    
    for query in test_queries:
        result = classify(query)
        print(f"Query: '{query}'")
        print(f"Result: {result}")
        print("-" * 50)

if __name__ == "__main__":
    test_classifier()