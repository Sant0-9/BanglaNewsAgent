"""
Test intent classification and routing with parameterized cases
"""
import pytest
import sys
from pathlib import Path

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent))
from packages.router.intent import classify


@pytest.mark.parametrize("query,expected_intent,expected_slots", [
    # Weather cases (EN)
    ("what's the weather in Dallas today?", "weather", {"location": "Dallas"}),
    ("temperature in New York", "weather", {"location": "New York"}),
    ("weather forecast for London", "weather", {"location": "London"}),
    ("how hot is it in Mumbai", "weather", {"location": "Mumbai"}),
    
    # Weather cases (BN)  
    ("আজ ডালাসের আবহাওয়া কেমন", "weather", {"location": "ডালাস"}),
    ("ঢাকার তাপমাত্রা কত", "weather", {"location": "ঢাকা"}),
    ("আজকের আবহাওয়া", "weather", {}),
    
    # Markets cases
    ("AAPL stock price", "markets", {"ticker": "AAPL"}),
    ("S&P 500 today", "markets", {}),  # No ticker extracted for index names
    ("Tesla share price", "markets", {}),  # No ticker (company name only)
    ("$MSFT quote", "markets", {"ticker": "MSFT"}),
    ("GOOGL stock", "markets", {"ticker": "GOOGL"}),
    ("শেয়ার বাজারের খবর", "markets", {}),
    
    # Sports cases
    ("Real Madrid score today", "sports", {"sport": "Real Madrid"}),
    ("Bangladesh vs India cricket", "sports", {"sport": "Bangladesh"}),
    ("football match result", "sports", {}),
    ("ম্যাচের ফলাফল", "sports", {}),
    
    # Lookup cases
    ("Who is Sundar Pichai?", "lookup", {"subject": "Sundar Pichai"}),
    ("What is artificial intelligence", "lookup", {"subject": "artificial intelligence"}),
    ("tell me about Elon Musk", "lookup", {"subject": "Elon Musk"}),
    ("কে এই ব্যক্তি Mark Zuckerberg", "lookup", {"subject": "Mark Zuckerberg"}),
    
    # News default cases
    ("Latest on semiconductor export controls", "news", {}),
    ("breaking news today", "news", {}),
    ("what's happening in the world", "news", {}),
    ("আজকের সংবাদ", "news", {}),
    ("", "news", {}),  # Empty query defaults to news
])
def test_intent_classification(query, expected_intent, expected_slots):
    """Test intent classification with various query types"""
    result = classify(query)
    
    # Assert intent is correctly classified
    assert result["intent"] == expected_intent, f"Expected {expected_intent}, got {result['intent']} for query: '{query}'"
    
    # Assert confidence is reasonable (> 0 for non-empty queries)
    if query.strip():
        assert result["confidence"] >= 0.0, f"Confidence should be non-negative, got {result['confidence']}"
    
    # Assert critical slots are present
    for slot_key, slot_value in expected_slots.items():
        assert slot_key in result["slots"], f"Expected slot '{slot_key}' not found in {result['slots']}"
        if slot_value:  # Only check value if specified
            assert result["slots"][slot_key] == slot_value, f"Expected slot '{slot_key}' = '{slot_value}', got '{result['slots'][slot_key]}'"


def test_weather_location_extraction():
    """Test specific weather location extraction"""
    test_cases = [
        ("weather in Dhaka", "Dhaka"),
        ("what's the temperature in Chicago?", "Chicago"),  
        ("London weather today", "London"),
        ("ঢাকার আবহাওয়া", "ঢাকা"),
    ]
    
    for query, expected_location in test_cases:
        result = classify(query)
        assert result["intent"] == "weather"
        assert "location" in result["slots"]
        assert result["slots"]["location"].lower() == expected_location.lower()


def test_markets_ticker_extraction():
    """Test specific markets ticker extraction"""
    test_cases = [
        ("AAPL stock price", "AAPL"),
        ("$TSLA quote", "TSLA"), 
        ("MSFT share", "MSFT"),
        ("stock GOOGL", "GOOGL"),
    ]
    
    for query, expected_ticker in test_cases:
        result = classify(query)
        assert result["intent"] == "markets"
        assert "ticker" in result["slots"]
        assert result["slots"]["ticker"] == expected_ticker


def test_lookup_subject_extraction():
    """Test specific lookup subject extraction"""
    test_cases = [
        ("Who is Elon Musk?", "Elon Musk"),
        ("What is machine learning", "machine learning"),
        ("tell me about Python programming", "Python programming"),
    ]
    
    for query, expected_subject in test_cases:
        result = classify(query)
        assert result["intent"] == "lookup"
        assert "subject" in result["slots"]
        assert result["slots"]["subject"].lower() == expected_subject.lower()


def test_confidence_scores():
    """Test that confidence scores are reasonable"""
    # High confidence cases
    high_conf_queries = [
        "what's the weather in Dallas?",  # Clear weather intent
        "AAPL stock price",               # Clear markets intent  
        "Who is Bill Gates?",             # Clear lookup intent
    ]
    
    for query in high_conf_queries:
        result = classify(query)
        assert result["confidence"] > 0.3, f"Expected high confidence for '{query}', got {result['confidence']}"
    
    # Lower confidence cases (ambiguous)
    low_conf_queries = [
        "news",  # Generic
        "today", # Very generic
    ]
    
    for query in low_conf_queries:
        result = classify(query)
        assert result["confidence"] >= 0.0, f"Confidence should be non-negative for '{query}'"


def test_empty_and_edge_cases():
    """Test edge cases and empty inputs"""
    edge_cases = [
        ("", "news"),           # Empty defaults to news
        ("   ", "news"),        # Whitespace defaults to news
        ("hello", "news"),      # No clear intent defaults to news
        ("12345", "news"),      # Numbers default to news
    ]
    
    for query, expected_intent in edge_cases:
        result = classify(query)
        assert result["intent"] == expected_intent
        assert isinstance(result["slots"], dict)
        assert isinstance(result["confidence"], (int, float))


if __name__ == "__main__":
    # Run a quick test
    print("Running intent classification tests...")
    
    test_queries = [
        "what's the weather in Dallas today?",
        "আজ ডালাসের আবহাওয়া কেমন", 
        "AAPL stock price",
        "Real Madrid score today",
        "Who is Sundar Pichai?",
        "Latest on semiconductor export controls"
    ]
    
    for query in test_queries:
        result = classify(query)
        print(f"'{query}' -> {result['intent']} ({result['confidence']:.2f}) {result['slots']}")