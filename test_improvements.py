#!/usr/bin/env python3
"""
Test script to validate KhoborAgent backend improvements
"""
import sys
import time
from pathlib import Path

# Add packages to path
sys.path.append(str(Path(__file__).parent))

from packages.util.cache import create_query_cache_key, get
from packages.util.cache import set as cache_set

def test_cache_uniqueness():
    """Test that cache keys are unique for different queries"""
    print("Testing cache key uniqueness...")
    
    queries = [
        "Bangladesh economy news",
        "Bangladesh economic news", 
        "What is happening in Bangladesh economy",
        "Bangladesh economy today",
        "Recent Bangladesh economic developments"
    ]
    
    cache_keys = []
    for query in queries:
        key = create_query_cache_key(query, "bn", 72)
        cache_keys.append(key)
        print(f"Query: '{query}' -> Key: {key}")
    
    # Check uniqueness
    unique_keys = len(set(cache_keys))
    print(f"Total queries: {len(queries)}")
    print(f"Unique cache keys: {unique_keys}")
    
    if unique_keys == len(queries):
        print("✅ PASS: All cache keys are unique")
    else:
        print("❌ FAIL: Some cache keys are duplicated")
        
    return unique_keys == len(queries)

def test_cache_time_sensitivity():
    """Test that cache keys change over time"""
    print("\nTesting cache time sensitivity...")
    
    query = "Test query for time sensitivity"
    
    # Get key at current time
    key1 = create_query_cache_key(query, "bn", 72)
    
    # Get key at different timestamp (simulate 31 minutes later)
    current_time_minutes = int(time.time() / 60)
    future_timestamp = current_time_minutes // 30 + 1  # Next 30-minute window
    key2 = create_query_cache_key(query, "bn", 72, future_timestamp)
    
    print(f"Key at time T: {key1}")
    print(f"Key at time T+30min: {key2}")
    
    if key1 != key2:
        print("✅ PASS: Cache keys change over time windows")
        return True
    else:
        print("❌ FAIL: Cache keys don't change over time")
        return False

def test_cache_functionality():
    """Test basic cache get/set functionality"""
    print("\nTesting cache functionality...")
    
    test_key = "test:key:123"
    test_value = {"answer": "Test response", "sources": []}
    
    # Set value
    cache_set(test_key, test_value, ttl_seconds=60)
    
    # Get value
    retrieved = get(test_key)
    
    if retrieved == test_value:
        print("✅ PASS: Cache set/get working correctly")
        return True
    else:
        print("❌ FAIL: Cache set/get not working")
        print(f"Expected: {test_value}")
        print(f"Got: {retrieved}")
        return False

def main():
    """Run all tests"""
    print("KhoborAgent Backend Improvement Tests")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(test_cache_uniqueness())
    results.append(test_cache_time_sensitivity())
    results.append(test_cache_functionality())
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Improvements are working correctly!")
    else:
        print("⚠️  Some tests failed - Check implementation")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)