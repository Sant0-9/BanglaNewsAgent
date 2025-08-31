#!/usr/bin/env python3
"""
Integration test for B11-B14 enhancements to KhoborAgent

Tests:
- B11: ML intent classification with rule fallback
- B12: Trustworthy confidence scoring
- B13: Comprehensive logging and metrics
- B14: Quality guardrails and hallucination checks
"""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

# Test imports
from packages.router.ml_intent import classify as ml_classify, get_classification_stats
from packages.quality.confidence_scorer import calculate_trustworthy_confidence
from packages.quality.guardrails import check_quality_and_refuse_if_needed
from packages.observability import get_logger, get_metrics, request_context

def test_b11_ml_intent_classification():
    """Test B11: ML intent classification with rule fallback"""
    print("=== Testing B11: ML Intent Classification ===")
    
    test_queries = [
        ("আজকের তাজা খবর", "news"),
        ("Bitcoin price today", "markets"), 
        ("Bangladesh vs India cricket score", "sports"),
        ("weather forecast Dhaka", "weather"),
        ("who is Elon Musk", "lookup"),
        ("sports news and stock market update", "news")  # Multi-intent
    ]
    
    results = []
    for query, expected_intent in test_queries:
        result = ml_classify(query)
        
        print(f"Query: '{query}'")
        print(f"  Intent: {result['intent']} (expected: {expected_intent})")
        print(f"  Confidence: {result['confidence']:.3f}")
        print(f"  Method: {result.get('classification_method', 'unknown')}")
        print(f"  Slots: {result.get('slots', {})}")
        
        if 'is_multi_intent' in result:
            print(f"  Multi-intent: {result['is_multi_intent']}")
            if result['is_multi_intent']:
                print(f"  Active intents: {result.get('active_intents', [])}")
        
        results.append({
            "query": query,
            "result": result,
            "correct_intent": result['intent'] == expected_intent
        })
        print()
    
    # Get classification stats
    stats = get_classification_stats()
    print("Classification Statistics:")
    print(f"  Total classifications: {stats.get('total_classifications', 0)}")
    print(f"  ML usage ratio: {stats.get('ml_usage_ratio', 0.0):.3f}")
    print(f"  Fallback usage ratio: {stats.get('fallback_usage_ratio', 0.0):.3f}")
    print(f"  Avg processing time: {stats.get('avg_processing_time_ms', 0):.2f}ms")
    
    accuracy = sum(1 for r in results if r['correct_intent']) / len(results)
    print(f"\nAccuracy: {accuracy:.1%}")
    
    return results

def test_b12_confidence_scoring():
    """Test B12: Trustworthy confidence scoring"""
    print("=== Testing B12: Confidence Scoring ===")
    
    # Test with high confidence scenario (3+ reputable sources, recent, no contradictions)
    high_confidence_evidence = [
        {
            "title": "Bangladesh Economy Shows Strong Growth",
            "excerpt": "GDP increased by 6.5% in Q3 according to government data",
            "outlet": "prothomalo.com",
            "published_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "url": "https://prothomalo.com/example"
        },
        {
            "title": "World Bank Confirms Bangladesh Growth",
            "excerpt": "Latest report shows GDP growth of 6.4% for third quarter",
            "outlet": "reuters.com", 
            "published_at": (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat(),
            "url": "https://reuters.com/example"
        },
        {
            "title": "IMF Reports Strong Bangladesh Performance",
            "excerpt": "Economic indicators show 6.6% GDP expansion",
            "outlet": "bloomberg.com",
            "published_at": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
            "url": "https://bloomberg.com/example"
        }
    ]
    
    # Test with medium confidence (2 sources)
    medium_confidence_evidence = high_confidence_evidence[:2]
    
    # Test with low confidence (1 source, old)
    low_confidence_evidence = [{
        "title": "Old Economic Report",
        "excerpt": "GDP data from last year",
        "outlet": "unknown-blog.com",
        "published_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        "url": "https://unknown-blog.com/example"
    }]
    
    test_cases = [
        ("High confidence", high_confidence_evidence, "high"),
        ("Medium confidence", medium_confidence_evidence, "medium"), 
        ("Low confidence", low_confidence_evidence, "low")
    ]
    
    results = []
    for case_name, evidence, expected_level in test_cases:
        confidence = calculate_trustworthy_confidence(evidence)
        
        print(f"{case_name}:")
        print(f"  Level: {confidence['level']} (expected: {expected_level})")
        print(f"  Score: {confidence['score']:.3f}")
        print(f"  Rationale: {confidence['rationale']}")
        print(f"  Sources: {confidence['source_analysis']['total_sources']}")
        print(f"  Reputable sources: {confidence['source_analysis']['reputable_sources']}")
        print(f"  Recent sources: {confidence['source_analysis']['recent_sources']}")
        print(f"  Contradictions: {confidence['contradiction_analysis']['has_contradictions']}")
        
        results.append({
            "case": case_name,
            "confidence": confidence,
            "correct_level": confidence['level'] == expected_level
        })
        print()
    
    accuracy = sum(1 for r in results if r['correct_level']) / len(results)
    print(f"Confidence Level Accuracy: {accuracy:.1%}")
    
    return results

def test_b13_observability():
    """Test B13: Logging and metrics"""
    print("=== Testing B13: Observability ===")
    
    logger = get_logger()
    metrics = get_metrics()
    
    # Test request context and timing
    with request_context(query="test query", intent="news") as request_id:
        print(f"Request ID: {request_id}")
        
        # Simulate various stages
        with logger.stage_timer("fetch"):
            time.sleep(0.1)
            logger.log_fetch_stage(
                providers_hit=["news_api", "rss_feeds"],
                cache_status="miss",
                results_count=15
            )
        
        with logger.stage_timer("dedupe"):
            time.sleep(0.05)
            logger.log_dedupe_stage(
                input_count=15,
                output_count=10,
                duplicates_removed=5
            )
        
        with logger.stage_timer("rerank"):
            time.sleep(0.02)
            logger.log_rerank_stage(
                rerank_method="semantic_similarity",
                items_reranked=10
            )
        
        with logger.stage_timer("summarize"):
            time.sleep(0.2)
            logger.log_summarize_stage(
                llm_model="gpt-4",
                input_tokens=1500,
                output_tokens=300,
                was_refused=False
            )
        
        # Test confidence logging
        logger.log_confidence_calculation(
            level="high",
            score=0.85,
            source_analysis={"reputable_sources": 3, "recent_sources": 3, "total_sources": 3}
        )
    
    # Get stage summary
    stage_summary = logger.get_stage_summary()
    print("Stage Summary:")
    print(f"  Total duration: {stage_summary.get('total_duration_ms', 0):.2f}ms")
    print(f"  Stage count: {stage_summary.get('stage_count', 0)}")
    print(f"  Slowest stage: {stage_summary.get('slowest_stage', 'none')}")
    
    # Test metrics
    metrics.record_request("news", True, 0.4, "high")
    metrics.record_provider_request("news_api", True)
    metrics.record_ml_classification("ml_classifier", "news", False)
    
    health_metrics = metrics.get_health_metrics()
    print("\nHealth Metrics:")
    print(f"  Healthy: {health_metrics['healthy']}")
    print(f"  Error rate: {health_metrics['error_rate']:.3f}")
    print(f"  Avg response time: {health_metrics['avg_response_time_seconds']:.3f}s")
    print(f"  Active requests: {health_metrics['active_requests']}")
    
    internal_metrics = metrics.get_internal_metrics()
    print(f"\nRequest count: {internal_metrics['request_count']}")
    print(f"Uptime: {internal_metrics['uptime_seconds']:.1f}s")
    
    return stage_summary, health_metrics

def test_b14_quality_guardrails():
    """Test B14: Quality guardrails and hallucination checks"""
    print("=== Testing B14: Quality Guardrails ===")
    
    # Test case 1: Good summary with numeric markers and multiple sources
    good_summary = "Bangladesh's GDP increased by 6.5% in Q3 2024, according to government data. The World Bank confirmed growth of 6.4% for the same period, while IMF reported 6.6% expansion."
    
    good_evidence = [
        {
            "title": "Bangladesh Economy Shows Strong Growth", 
            "excerpt": "GDP increased by 6.5% in Q3",
            "outlet": "prothomalo.com",
            "published_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        },
        {
            "title": "World Bank Confirms Growth",
            "excerpt": "Growth of 6.4% confirmed", 
            "outlet": "reuters.com",
            "published_at": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        },
        {
            "title": "IMF Economic Report",
            "excerpt": "6.6% expansion reported",
            "outlet": "bloomberg.com",
            "published_at": (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
        }
    ]
    
    # Test case 2: Bad summary without numeric markers
    bad_summary_no_markers = "Bangladesh's economy is doing well and growing significantly according to recent reports from various sources."
    
    # Test case 3: Non-trivial claims with only 1 source
    single_source_evidence = [good_evidence[0]]
    
    # Test case 4: Sources outside time window
    old_evidence = [
        {
            "title": "Old Economic Data",
            "excerpt": "Some old data",
            "outlet": "reuters.com", 
            "published_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        }
    ]
    
    test_cases = [
        ("Good: Multiple sources, markers, recent", good_summary, good_evidence, False),
        ("Bad: No numeric markers", bad_summary_no_markers, good_evidence, True),
        ("Bad: Single source for non-trivial", good_summary, single_source_evidence, True),
        ("Bad: Sources outside window", good_summary, old_evidence, True)
    ]
    
    results = []
    for case_name, summary, evidence, should_be_refused in test_cases:
        should_refuse, response = check_quality_and_refuse_if_needed(summary, evidence)
        
        print(f"{case_name}:")
        print(f"  Should refuse: {should_refuse} (expected: {should_be_refused})")
        
        if should_refuse:
            print(f"  Refusal reason: {response.get('refusal_reason', 'Unknown')}")
            print(f"  Confidence level: {response.get('confidence', {}).get('level', 'unknown')}")
        else:
            quality_checks = response.get('quality_checks', {})
            for check_name, check_result in quality_checks.items():
                print(f"  {check_name}: {'PASS' if check_result.passed else 'FAIL'} - {check_result.reason}")
        
        results.append({
            "case": case_name,
            "should_refuse": should_refuse,
            "expected_refuse": should_be_refused,
            "correct": should_refuse == should_be_refused
        })
        print()
    
    accuracy = sum(1 for r in results if r['correct']) / len(results)
    print(f"Quality Check Accuracy: {accuracy:.1%}")
    
    return results

def main():
    """Run all B11-B14 enhancement tests"""
    print("Testing B11-B14 Enhancements for KhoborAgent")
    print("=" * 50)
    
    # Test B11: ML Intent Classification
    b11_results = test_b11_ml_intent_classification()
    
    print("\n" + "=" * 50)
    
    # Test B12: Confidence Scoring  
    b12_results = test_b12_confidence_scoring()
    
    print("\n" + "=" * 50)
    
    # Test B13: Observability
    stage_summary, health_metrics = test_b13_observability()
    
    print("\n" + "=" * 50)
    
    # Test B14: Quality Guardrails
    b14_results = test_b14_quality_guardrails()
    
    # Overall summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    b11_accuracy = sum(1 for r in b11_results if r['correct_intent']) / len(b11_results)
    b12_accuracy = sum(1 for r in b12_results if r['correct_level']) / len(b12_results)  
    b14_accuracy = sum(1 for r in b14_results if r['correct']) / len(b14_results)
    
    print(f"B11 Intent Classification Accuracy: {b11_accuracy:.1%}")
    print(f"B12 Confidence Level Accuracy: {b12_accuracy:.1%}")
    print(f"B13 Observability: {'✓' if stage_summary and health_metrics else '✗'}")
    print(f"B14 Quality Guardrails Accuracy: {b14_accuracy:.1%}")
    
    overall_success = all([
        b11_accuracy >= 0.8,
        b12_accuracy >= 0.8,
        stage_summary and health_metrics,
        b14_accuracy >= 0.8
    ])
    
    print(f"\nOverall Success: {'✓ PASS' if overall_success else '✗ FAIL'}")
    
    if overall_success:
        print("\n🎉 All B11-B14 enhancements are working correctly!")
        print("\nImplemented features:")
        print("✅ B11: ML multi-label intent classification with rule fallback")
        print("✅ B12: Trustworthy confidence scoring (high/medium/low)")
        print("✅ B13: Comprehensive logging and metrics with request tracing")
        print("✅ B14: Quality guardrails preventing hallucinations and stale data")
    else:
        print("\n⚠️  Some enhancements need attention. Check the test output above.")

if __name__ == "__main__":
    main()