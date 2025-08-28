#!/usr/bin/env python3
"""
Demo script showing KhoborAgent backend improvements
"""
import sys
from pathlib import Path

# Add packages to path
sys.path.append(str(Path(__file__).parent))

from packages.util.cache import create_query_cache_key
from packages.nlp.retrieve import bm25ish

def demo_cache_improvements():
    """Demonstrate improved cache key generation"""
    print("🔧 CACHE IMPROVEMENTS DEMO")
    print("=" * 60)
    
    print("\n1. Query Uniqueness:")
    print("   Before: Similar queries would get same cache key")
    print("   After: Each unique query gets unique cache key\n")
    
    queries = [
        "Bangladesh politics news",
        "Politics in Bangladesh", 
        "What's happening in Bangladesh politics",
        "Bangladesh political situation"
    ]
    
    for i, query in enumerate(queries, 1):
        key = create_query_cache_key(query, "bn", 72)
        print(f"   {i}. '{query}'")
        print(f"      Cache key: {key}")
    
    print("\n2. Time-based Cache Invalidation:")
    print("   Before: Cache lasted 15 minutes regardless of news freshness")
    print("   After: Cache keys include 30-minute time windows for fresh news")
    
    import time
    query = "Breaking news Bangladesh"
    current_key = create_query_cache_key(query, "bn", 72)
    print(f"\n   Current time window key: {current_key}")
    
    # Simulate next time window
    next_window = int(time.time() / 60 / 30) + 1
    next_key = create_query_cache_key(query, "bn", 72, next_window)
    print(f"   Next window key (30min): {next_key}")

def demo_search_improvements():
    """Demonstrate improved search and ranking"""
    print("\n\n🔍 SEARCH & RANKING IMPROVEMENTS DEMO")
    print("=" * 60)
    
    print("\n1. Enhanced BM25 Algorithm:")
    print("   Before: Basic fuzzy matching + token overlap")  
    print("   After: Added phrase matching + improved scoring\n")
    
    query = "Bangladesh economy growth"
    test_texts = [
        "Bangladesh economy shows strong growth this quarter",
        "Economic indicators suggest Bangladesh growth momentum", 
        "The economy of Bangladesh has been growing steadily",
        "Stock market updates from Dhaka today"
    ]
    
    for text in test_texts:
        score = bm25ish(query, text)
        print(f"   Text: '{text[:50]}...'")
        print(f"   BM25 Score: {score:.3f}\n")
    
    print("2. Source Diversity Improvements:")
    print("   Before: Max 5 sources, 1 per domain")
    print("   After: Max 8 sources, up to 2 per domain")
    print("   Before: Top 30 candidates before MMR")
    print("   After: Top 50 candidates for better diversity")
    
    print("\n3. Retrieval Parameters Enhanced:")
    print("   Before: 300 DB results, 500 char excerpts")
    print("   After: 500 DB results, 800 char excerpts")

def demo_summarization_improvements():
    """Demonstrate enhanced summarization"""
    print("\n\n📝 SUMMARIZATION IMPROVEMENTS DEMO")
    print("=" * 60)
    
    print("\n1. Response Length & Detail:")
    print("   Before: 6-10 sentences, 2000 tokens max, temperature=0.3")
    print("   After: 12-20 sentences, 4000 tokens max, temperature=0.5")
    
    print("\n2. Enhanced System Prompts:")
    print("   Before: Basic summarization with citations")
    print("   After: Comprehensive analysis with context, implications, perspectives")
    
    print("\n3. Content Quality:")  
    print("   Before: 'Write 6–10 sentences'")
    print("   After: 'Write a detailed 12–20 sentence analysis'")
    print("   Before: 'End with one sentence: Why it matters'")
    print("   After: 'End with 2-3 sentences explaining broader implications'")
    print("   Before: 'List 2–4 What to watch bullets'")
    print("   After: 'List 4–6 detailed What to watch bullets with actionable insights'")

def main():
    """Run all demos"""
    print("KhoborAgent Backend Improvements Demo")
    print("=" * 60)
    print("This demo shows the key improvements made to fix:")
    print("• Same responses for different queries")
    print("• Short, inaccurate answers")
    print("• Poor source diversity and retrieval")
    print("• Aggressive caching issues\n")
    
    demo_cache_improvements()
    demo_search_improvements() 
    demo_summarization_improvements()
    
    print("\n\n🎉 SUMMARY OF IMPROVEMENTS")
    print("=" * 60)
    print("✅ Fixed cache key collisions with unique query hashing")
    print("✅ Added time-based cache invalidation (30-min windows)")
    print("✅ Enhanced BM25 algorithm with phrase matching")
    print("✅ Increased source diversity (8 sources, 2 per domain)")
    print("✅ Expanded retrieval pipeline (500 DB results)")
    print("✅ Improved summarization (12-20 sentences, 4000 tokens)")
    print("✅ Enhanced prompts for comprehensive analysis")
    print("✅ Longer excerpts (800 chars) for better context")
    
    print("\n📊 Expected Results:")
    print("• Unique responses for each distinct query")
    print("• Longer, more detailed and accurate summaries")
    print("• Better source diversity and information quality")
    print("• Reduced cache collisions and fresher news")

if __name__ == "__main__":
    main()