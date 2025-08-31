"""
Comprehensive observability package for KhoborAgent

This package provides:
- Structured logging with request tracing
- Prometheus/OpenTelemetry metrics
- Performance monitoring
- Request lifecycle tracking
"""

from .logger import (
    StructuredLogger,
    get_logger,
    log_request_timing,
    request_context
)

from .metrics import (
    KhoborMetrics,
    get_metrics,
    record_request_metrics,
    record_stage_metrics
)

__all__ = [
    'StructuredLogger',
    'KhoborMetrics', 
    'get_logger',
    'get_metrics',
    'log_request_timing',
    'request_context',
    'record_request_metrics',
    'record_stage_metrics'
]