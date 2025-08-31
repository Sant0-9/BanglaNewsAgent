import time
from typing import Dict, Any, Optional, List
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta
import threading
from contextlib import contextmanager

# Try to import Prometheus client, fallback to internal metrics
try:
    from prometheus_client import Counter as PrometheusCounter
    from prometheus_client import Histogram, Gauge, Summary
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("[METRICS] Prometheus client not available, using internal metrics")

# Try to import OpenTelemetry, fallback gracefully
try:
    from opentelemetry import trace, metrics as otel_metrics
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    print("[METRICS] OpenTelemetry not available, using fallback metrics")

class KhoborMetrics:
    """Comprehensive metrics system for KhoborAgent with Prometheus/OpenTelemetry support"""
    
    def __init__(self):
        self.start_time = time.time()
        self._lock = threading.Lock()
        
        # Internal metrics storage (fallback)
        self.counters = defaultdict(int)
        self.histograms = defaultdict(list)
        self.gauges = defaultdict(float)
        self.request_times = []
        
        # Initialize Prometheus metrics if available
        if PROMETHEUS_AVAILABLE:
            self._init_prometheus_metrics()
        
        # Initialize OpenTelemetry if available
        if OPENTELEMETRY_AVAILABLE:
            self._init_opentelemetry_metrics()
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics"""
        # Request counters
        self.prom_requests_total = PrometheusCounter(
            'khoboragent_requests_total',
            'Total number of requests',
            ['intent', 'status', 'confidence_level']
        )
        
        self.prom_stage_duration = Histogram(
            'khoboragent_stage_duration_seconds',
            'Duration of processing stages',
            ['stage', 'success'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float('inf')]
        )
        
        self.prom_response_time = Histogram(
            'khoboragent_response_time_seconds', 
            'Total response time',
            ['intent', 'success'],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 30.0, 60.0, float('inf')]
        )
        
        self.prom_sources_count = Histogram(
            'khoboragent_sources_count',
            'Number of sources used',
            ['intent'],
            buckets=[1, 2, 3, 5, 10, 20, 50, 100, float('inf')]
        )
        
        # Gauge metrics
        self.prom_active_requests = Gauge(
            'khoboragent_active_requests',
            'Currently active requests'
        )
        
        self.prom_cache_hit_ratio = Gauge(
            'khoboragent_cache_hit_ratio',
            'Cache hit ratio'
        )
        
        # Provider metrics
        self.prom_provider_requests = PrometheusCounter(
            'khoboragent_provider_requests_total',
            'Requests to external providers',
            ['provider', 'status']
        )
        
        # Quality metrics
        self.prom_quality_checks = PrometheusCounter(
            'khoboragent_quality_checks_total',
            'Quality check results',
            ['check_type', 'result']
        )
        
        self.prom_refusals = PrometheusCounter(
            'khoboragent_refusals_total',
            'Request refusals by reason',
            ['reason', 'stage']
        )
        
        # ML metrics
        self.prom_ml_classifications = PrometheusCounter(
            'khoboragent_ml_classifications_total',
            'ML model classifications',
            ['model_type', 'primary_intent', 'is_multi_intent']
        )
        
        # Token usage
        self.prom_tokens_used = PrometheusCounter(
            'khoboragent_tokens_total',
            'Total tokens used',
            ['model', 'type']  # type: input/output
        )
    
    def _init_opentelemetry_metrics(self):
        """Initialize OpenTelemetry metrics"""
        # This would be configured based on your observability platform
        # For now, we'll prepare the structure
        self.otel_meter = None
        if hasattr(otel_metrics, 'get_meter'):
            self.otel_meter = otel_metrics.get_meter("khoboragent")
    
    def record_request(self, intent: str, success: bool, duration_seconds: float, 
                      confidence_level: str = "unknown"):
        """Record a complete request"""
        with self._lock:
            # Internal metrics
            status = "success" if success else "error"
            self.counters[f"requests.{intent}.{status}"] += 1
            self.request_times.append(duration_seconds)
            
            # Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                self.prom_requests_total.labels(
                    intent=intent, 
                    status=status,
                    confidence_level=confidence_level
                ).inc()
                
                self.prom_response_time.labels(
                    intent=intent,
                    success=str(success)
                ).observe(duration_seconds)
    
    def record_stage_timing(self, stage: str, success: bool, duration_seconds: float):
        """Record stage processing time"""
        with self._lock:
            # Internal metrics
            key = f"stage.{stage}.{success}"
            self.histograms[key].append(duration_seconds)
            
            # Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                self.prom_stage_duration.labels(
                    stage=stage,
                    success=str(success)
                ).observe(duration_seconds)
    
    def record_sources_used(self, intent: str, source_count: int):
        """Record number of sources used"""
        with self._lock:
            # Internal metrics
            self.histograms[f"sources.{intent}"].append(source_count)
            
            # Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                self.prom_sources_count.labels(intent=intent).observe(source_count)
    
    def record_provider_request(self, provider: str, success: bool):
        """Record external provider request"""
        with self._lock:
            status = "success" if success else "error"
            self.counters[f"provider.{provider}.{status}"] += 1
            
            if PROMETHEUS_AVAILABLE:
                self.prom_provider_requests.labels(
                    provider=provider,
                    status=status
                ).inc()
    
    def record_quality_check(self, check_type: str, passed: bool):
        """Record quality check result"""
        with self._lock:
            result = "pass" if passed else "fail"
            self.counters[f"quality.{check_type}.{result}"] += 1
            
            if PROMETHEUS_AVAILABLE:
                self.prom_quality_checks.labels(
                    check_type=check_type,
                    result=result
                ).inc()
    
    def record_refusal(self, reason: str, stage: str):
        """Record request refusal"""
        with self._lock:
            self.counters[f"refusal.{reason}.{stage}"] += 1
            
            if PROMETHEUS_AVAILABLE:
                self.prom_refusals.labels(
                    reason=reason,
                    stage=stage
                ).inc()
    
    def record_ml_classification(self, model_type: str, primary_intent: str, 
                               is_multi_intent: bool):
        """Record ML classification"""
        with self._lock:
            self.counters[f"ml.{model_type}.{primary_intent}"] += 1
            
            if PROMETHEUS_AVAILABLE:
                self.prom_ml_classifications.labels(
                    model_type=model_type,
                    primary_intent=primary_intent,
                    is_multi_intent=str(is_multi_intent)
                ).inc()
    
    def record_token_usage(self, model: str, input_tokens: int, output_tokens: int):
        """Record token usage"""
        with self._lock:
            self.counters[f"tokens.{model}.input"] += input_tokens
            self.counters[f"tokens.{model}.output"] += output_tokens
            
            if PROMETHEUS_AVAILABLE:
                self.prom_tokens_used.labels(model=model, type="input").inc(input_tokens)
                self.prom_tokens_used.labels(model=model, type="output").inc(output_tokens)
    
    def set_active_requests(self, count: int):
        """Set current active request count"""
        with self._lock:
            self.gauges["active_requests"] = count
            
            if PROMETHEUS_AVAILABLE:
                self.prom_active_requests.set(count)
    
    def set_cache_hit_ratio(self, ratio: float):
        """Set cache hit ratio (0.0 to 1.0)"""
        with self._lock:
            self.gauges["cache_hit_ratio"] = ratio
            
            if PROMETHEUS_AVAILABLE:
                self.prom_cache_hit_ratio.set(ratio)
    
    @contextmanager
    def request_tracker(self, intent: str = "unknown"):
        """Context manager to track request timing"""
        start_time = time.time()
        self.set_active_requests(self.gauges["active_requests"] + 1)
        
        success = True
        confidence_level = "unknown"
        
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            duration = time.time() - start_time
            self.record_request(intent, success, duration, confidence_level)
            self.set_active_requests(max(0, self.gauges["active_requests"] - 1))
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        if not PROMETHEUS_AVAILABLE:
            return "# Prometheus not available\n"
        
        return generate_latest().decode('utf-8')
    
    def get_internal_metrics(self) -> Dict[str, Any]:
        """Get internal metrics summary"""
        with self._lock:
            uptime_seconds = time.time() - self.start_time
            
            # Calculate percentiles for request times
            request_times_sorted = sorted(self.request_times)
            n = len(request_times_sorted)
            
            percentiles = {}
            if n > 0:
                percentiles = {
                    "p50": request_times_sorted[int(n * 0.5)],
                    "p90": request_times_sorted[int(n * 0.9)],
                    "p95": request_times_sorted[int(n * 0.95)],
                    "p99": request_times_sorted[int(n * 0.99)] if n >= 100 else request_times_sorted[-1]
                }
            
            return {
                "uptime_seconds": uptime_seconds,
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "request_count": len(self.request_times),
                "response_time_percentiles": percentiles,
                "avg_response_time": sum(self.request_times) / max(len(self.request_times), 1),
                "histogram_summary": {
                    key: {
                        "count": len(values),
                        "avg": sum(values) / max(len(values), 1),
                        "min": min(values) if values else 0,
                        "max": max(values) if values else 0
                    }
                    for key, values in self.histograms.items()
                }
            }
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get health check metrics"""
        with self._lock:
            total_requests = sum(
                count for key, count in self.counters.items() 
                if key.startswith("requests.")
            )
            
            success_requests = sum(
                count for key, count in self.counters.items()
                if key.startswith("requests.") and ".success" in key
            )
            
            error_rate = 1.0 - (success_requests / max(total_requests, 1))
            
            # Recent request times (last 100)
            recent_times = self.request_times[-100:] if len(self.request_times) > 100 else self.request_times
            avg_response_time = sum(recent_times) / max(len(recent_times), 1)
            
            return {
                "healthy": error_rate < 0.1 and avg_response_time < 10.0,
                "error_rate": error_rate,
                "avg_response_time_seconds": avg_response_time,
                "active_requests": self.gauges.get("active_requests", 0),
                "total_requests": total_requests,
                "cache_hit_ratio": self.gauges.get("cache_hit_ratio", 0.0)
            }

# Global metrics instance
_global_metrics = None

def get_metrics() -> KhoborMetrics:
    """Get global metrics instance"""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = KhoborMetrics()
    return _global_metrics

def record_request_metrics(intent: str, success: bool, duration_seconds: float,
                         confidence_level: str = "unknown"):
    """Convenience function to record request metrics"""
    metrics = get_metrics()
    metrics.record_request(intent, success, duration_seconds, confidence_level)

def record_stage_metrics(stage: str, success: bool, duration_seconds: float):
    """Convenience function to record stage metrics"""
    metrics = get_metrics()
    metrics.record_stage_timing(stage, success, duration_seconds)