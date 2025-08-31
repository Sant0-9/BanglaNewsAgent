#!/usr/bin/env python3
"""
Test script for retrieval guardrails and insufficient context handling.
"""
import asyncio
import sys
from pathlib import Path
import json

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent))

from packages.nlp.hybrid_retrieve import hybrid_retrieve_with_guardrails
from packages.handlers.enhanced_news import enhanced_handle
from packages.db import repo as db_repo


async def test_insufficient_context_scenarios():
    """Test various insufficient context scenarios."""
    
    print("🧪 Testing Retrieval Guardrails & Insufficient Context Handling")
    print("=" * 70)
    
    test_cases = [
        {
            "name": "Non-existent topic",
            "query": "zebrafish quantum computing algorithms in Bangladesh",
            "lang": "bn",
            "expected": "insufficient_context"
        },
        {
            "name": "Very vague query", 
            "query": "news",
            "lang": "bn",
            "expected": "insufficient_context"
        },
        {
            "name": "Volatile fact - Stock price",
            "query": "NVIDIA stock price today",
            "lang": "en",
            "expected": "tool_routing"
        },
        {
            "name": "Sports score query",
            "query": "Bangladesh cricket match score today", 
            "lang": "bn",
            "expected": "tool_routing"
        },
        {
            "name": "Valid news query",
            "query": "latest news about Bangladesh politics",
            "lang": "bn", 
            "expected": "proceed_with_answer"
        },
        {
            "name": "Currency query",
            "query": "USD to BDT exchange rate",
            "lang": "en",
            "expected": "tool_routing"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print(f"Query: {test_case['query']}")
        print(f"Language: {test_case['lang']}")
        print(f"Expected: {test_case['expected']}")
        print("-" * 50)
        
        try:
            # Test hybrid retrieval
            retrieval_result = await hybrid_retrieve_with_guardrails(
                query=test_case['query'],
                category=None,
                repo=db_repo,
                lang=test_case['lang'],
                intent="news",
                window_hours=72
            )
            
            quality = retrieval_result['quality']
            routing = retrieval_result['routing'] 
            evidence = retrieval_result['evidence']
            guardrails = retrieval_result['guardrails']
            
            print(f"✓ Evidence found: {len(evidence)} items")
            print(f"✓ Quality sufficient: {quality['sufficient']}")
            print(f"✓ Best score: {quality['best_score']:.3f}")
            print(f"✓ Quality score: {quality['quality_score']:.3f}")
            print(f"✓ Language matches: {quality['language_matches']}")
            print(f"✓ Route to tool: {routing['route_to_tool']} ({routing.get('tool', 'none')})")
            print(f"✓ Guardrails applied: {', '.join(guardrails['applied']) if guardrails['applied'] else 'none'}")
            
            # Determine actual result type
            if routing['route_to_tool']:
                actual_result = "tool_routing"
            elif not quality['sufficient']:
                actual_result = "insufficient_context"
            else:
                actual_result = "proceed_with_answer"
            
            print(f"✓ Actual result: {actual_result}")
            
            # Check if matches expectation
            matches = actual_result == test_case['expected']
            print(f"{'✅ PASS' if matches else '❌ FAIL'}: Expected {test_case['expected']}, got {actual_result}")
            
            results.append({
                "test": test_case['name'],
                "query": test_case['query'],
                "expected": test_case['expected'],
                "actual": actual_result,
                "pass": matches,
                "quality": quality,
                "routing": routing,
                "evidence_count": len(evidence)
            })
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append({
                "test": test_case['name'], 
                "query": test_case['query'],
                "expected": test_case['expected'],
                "actual": "error",
                "pass": False,
                "error": str(e)
            })
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results if r.get('pass', False))
    total = len(results)
    
    print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    
    for result in results:
        status = "✅ PASS" if result.get('pass') else "❌ FAIL"
        print(f"{status} {result['test']}: {result['expected']} -> {result['actual']}")
    
    return results


async def test_enhanced_news_handler():
    """Test the enhanced news handler end-to-end."""
    
    print("\n🧪 Testing Enhanced News Handler")
    print("=" * 70)
    
    test_queries = [
        {"query": "nonexistent topic xyz123", "lang": "bn"},
        {"query": "NVIDIA stock price", "lang": "en"}, 
        {"query": "latest Bangladesh news", "lang": "bn"}
    ]
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n🔍 Handler Test {i}: {test['query']}")
        
        try:
            result = await enhanced_handle(
                query=test['query'],
                slots={},
                lang=test['lang'],
                intent="news"
            )
            
            print(f"✓ Answer (first 100 chars): {result.get('answer_bn', '')[:100]}...")
            print(f"✓ Sources: {len(result.get('sources', []))}")
            print(f"✓ Flags: {result.get('flags', {})}")
            print(f"✓ Has insufficient_context: {'insufficient_context' in result}")
            print(f"✓ Has error: {'error' in result}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")


if __name__ == "__main__":
    print("Testing Retrieval Guardrails System")
    print("This will test insufficient context detection, tool routing, and guardrails.")
    
    try:
        # Run retrieval tests
        retrieval_results = asyncio.run(test_insufficient_context_scenarios())
        
        # Run handler tests  
        asyncio.run(test_enhanced_news_handler())
        
        print("\n✅ All tests completed!")
        
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)