import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from contextlib import contextmanager
from functools import wraps
import logging
from pathlib import Path

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class StructuredLogger:
    """Structured logger for KhoborAgent with request tracing"""
    
    def __init__(self, name: str = "khoboragent"):
        self.logger = logging.getLogger(name)
        self.request_id = None
        self.stage_timings = {}
        self.stage_start_times = {}
    
    def set_request_id(self, request_id: Optional[str] = None) -> str:
        """Set request ID for tracing"""
        if request_id is None:
            request_id = str(uuid.uuid4())
        self.request_id = request_id
        self.stage_timings = {}
        self.stage_start_times = {}
        return request_id
    
    def log_structured(self, level: str, event: str, **kwargs):
        """Log structured data with request context"""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "request_id": self.request_id,
            **kwargs
        }
        
        # Add stage timing if available
        if self.request_id in self.stage_timings:
            log_data["stage_timings"] = self.stage_timings[self.request_id]
        
        log_message = json.dumps(log_data, ensure_ascii=False, default=str)
        
        if level.upper() == "INFO":
            self.logger.info(log_message)
        elif level.upper() == "ERROR":
            self.logger.error(log_message)
        elif level.upper() == "WARNING":
            self.logger.warning(log_message)
        elif level.upper() == "DEBUG":
            self.logger.debug(log_message)
    
    @contextmanager
    def stage_timer(self, stage_name: str):
        """Context manager to time a stage"""
        start_time = time.time()
        self.stage_start_times[stage_name] = start_time
        
        try:
            yield
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            if self.request_id not in self.stage_timings:
                self.stage_timings[self.request_id] = {}
            
            self.stage_timings[self.request_id][stage_name] = {
                "duration_ms": round(duration_ms, 2),
                "start_time": datetime.fromtimestamp(start_time, timezone.utc).isoformat(),
                "end_time": datetime.fromtimestamp(end_time, timezone.utc).isoformat()
            }
    
    def log_request_start(self, query: str, intent: str, **kwargs):
        """Log request initiation"""
        self.log_structured("INFO", "request_start", 
                          query=query[:200],  # Truncate for privacy
                          intent=intent,
                          **kwargs)
    
    def log_request_end(self, success: bool, response_size: int = 0, **kwargs):
        """Log request completion"""
        total_time = sum(
            timing["duration_ms"] 
            for timing in self.stage_timings.get(self.request_id, {}).values()
        )
        
        self.log_structured("INFO", "request_end",
                          success=success,
                          total_duration_ms=round(total_time, 2),
                          response_size_bytes=response_size,
                          stage_count=len(self.stage_timings.get(self.request_id, {})),
                          **kwargs)
    
    def log_stage_result(self, stage: str, success: bool, **kwargs):
        """Log stage completion with results"""
        stage_timing = self.stage_timings.get(self.request_id, {}).get(stage, {})
        
        self.log_structured("INFO", f"stage_{stage}_complete",
                          stage=stage,
                          success=success,
                          duration_ms=stage_timing.get("duration_ms", 0),
                          **kwargs)
    
    def log_fetch_stage(self, providers_hit: List[str], cache_status: str, 
                       results_count: int, **kwargs):
        """Log fetch stage specifics"""
        self.log_stage_result("fetch", 
                            success=results_count > 0,
                            providers_hit=providers_hit,
                            cache_status=cache_status,
                            results_count=results_count,
                            **kwargs)
    
    def log_dedupe_stage(self, input_count: int, output_count: int, 
                        duplicates_removed: int, **kwargs):
        """Log deduplication stage"""
        self.log_stage_result("dedupe",
                            success=True,
                            input_count=input_count,
                            output_count=output_count,
                            duplicates_removed=duplicates_removed,
                            deduplication_rate=round(duplicates_removed / max(input_count, 1), 3),
                            **kwargs)
    
    def log_rerank_stage(self, rerank_method: str, items_reranked: int, **kwargs):
        """Log reranking stage"""
        self.log_stage_result("rerank",
                            success=items_reranked > 0,
                            rerank_method=rerank_method,
                            items_reranked=items_reranked,
                            **kwargs)
    
    def log_summarize_stage(self, llm_model: str, input_tokens: int, 
                          output_tokens: int, was_refused: bool, **kwargs):
        """Log summarization stage"""
        self.log_stage_result("summarize",
                            success=not was_refused,
                            llm_model=llm_model,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            total_tokens=input_tokens + output_tokens,
                            was_refused=was_refused,
                            **kwargs)
    
    def log_per_answer_metrics(self, conversation_id: Optional[str], language: str,
                              retrieval_scores: List[float], k_hits: int, 
                              tool_calls: List[Dict[str, Any]], token_usage: Dict[str, int],
                              total_latency_ms: float, answer_type: str, 
                              refusal_reason: Optional[str] = None,
                              gate_triggered: Optional[str] = None, **kwargs):
        """
        Log comprehensive per-answer metrics as required:
        - conversation_id, language, retrieval scores, K hits
        - tool calls, token usage, total latency
        - refusal vs answer classification
        """
        self.log_structured("INFO", "answer_complete",
                          # Core identifiers
                          conversation_id=conversation_id,
                          language=language,
                          
                          # Retrieval metrics
                          retrieval_scores=retrieval_scores[:10] if retrieval_scores else [],  # Top 10 scores
                          k_hits=k_hits,
                          avg_retrieval_score=sum(retrieval_scores) / len(retrieval_scores) if retrieval_scores else 0.0,
                          max_retrieval_score=max(retrieval_scores) if retrieval_scores else 0.0,
                          min_retrieval_score=min(retrieval_scores) if retrieval_scores else 0.0,
                          
                          # External tool usage
                          tool_calls=tool_calls,
                          tool_call_count=len(tool_calls),
                          
                          # Token usage
                          prompt_tokens=token_usage.get('prompt_tokens', 0),
                          completion_tokens=token_usage.get('completion_tokens', 0),
                          total_tokens=token_usage.get('total_tokens', 0),
                          
                          # Performance
                          total_latency_ms=total_latency_ms,
                          
                          # Answer classification
                          answer_type=answer_type,  # "answer" or "refusal"
                          refusal_reason=refusal_reason,
                          gate_triggered=gate_triggered,
                          
                          # Context
                          has_sources=k_hits > 0,
                          **kwargs)
    
    def log_retrieval_details(self, query: str, chunks: List[Dict[str, Any]], 
                             scores: List[float], **kwargs):
        """Log detailed retrieval information for debugging"""
        top_chunks = []
        for i, (chunk, score) in enumerate(zip(chunks[:5], scores[:5])):  # Top 5 for debug
            top_chunks.append({
                'rank': i + 1,
                'score': round(score, 4),
                'title': chunk.get('title', 'Untitled')[:100],
                'source': chunk.get('source', 'Unknown'),
                'url': chunk.get('url', ''),
                'published_at': chunk.get('published_at', '')
            })
        
        self.log_structured("DEBUG", "retrieval_details",
                          query=query[:200],
                          total_chunks=len(chunks),
                          top_chunks=top_chunks,
                          score_distribution={
                              'min': min(scores) if scores else 0,
                              'max': max(scores) if scores else 0,
                              'avg': sum(scores) / len(scores) if scores else 0,
                              'median': sorted(scores)[len(scores)//2] if scores else 0
                          },
                          **kwargs)
    
    def log_confidence_calculation(self, level: str, score: float, 
                                 source_analysis: Dict[str, Any], **kwargs):
        """Log confidence calculation results"""
        self.log_structured("INFO", "confidence_calculated",
                          confidence_level=level,
                          confidence_score=score,
                          reputable_sources=source_analysis.get('reputable_sources', 0),
                          recent_sources=source_analysis.get('recent_sources', 0),
                          total_sources=source_analysis.get('total_sources', 0),
                          **kwargs)
    
    def log_quality_check(self, check_type: str, passed: bool, reason: str = "", **kwargs):
        """Log quality guardrail checks"""
        self.log_structured("INFO", "quality_check",
                          check_type=check_type,
                          passed=passed,
                          reason=reason,
                          **kwargs)
    
    def log_refusal(self, reason: str, stage: str, **kwargs):
        """Log request refusal with details"""
        self.log_structured("WARNING", "request_refused",
                          refusal_reason=reason,
                          refusal_stage=stage,
                          **kwargs)
    
    def log_error(self, error: Exception, stage: str, **kwargs):
        """Log error with context"""
        self.log_structured("ERROR", "error_occurred",
                          error_type=type(error).__name__,
                          error_message=str(error),
                          error_stage=stage,
                          **kwargs)
    
    def get_stage_summary(self) -> Dict[str, Any]:
        """Get summary of all stage timings for current request"""
        if not self.request_id or self.request_id not in self.stage_timings:
            return {}
        
        timings = self.stage_timings[self.request_id]
        total_time = sum(timing["duration_ms"] for timing in timings.values())
        
        return {
            "request_id": self.request_id,
            "total_duration_ms": round(total_time, 2),
            "stage_count": len(timings),
            "stages": timings,
            "slowest_stage": max(timings.items(), key=lambda x: x[1]["duration_ms"])[0] if timings else None
        }

# Global logger instance
_global_logger = None

def get_logger(name: str = "khoboragent") -> StructuredLogger:
    """Get global structured logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger(name)
    return _global_logger

def log_request_timing(stage_name: str):
    """Decorator to automatically time and log function execution"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            with logger.stage_timer(stage_name):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

# Context manager for request tracing
@contextmanager
def request_context(request_id: Optional[str] = None, query: str = "", intent: str = ""):
    """Context manager to handle full request lifecycle"""
    logger = get_logger()
    actual_request_id = logger.set_request_id(request_id)
    
    try:
        if query:
            logger.log_request_start(query, intent)
        yield actual_request_id
        logger.log_request_end(success=True)
    except Exception as e:
        logger.log_request_end(success=False, error=str(e))
        logger.log_error(e, "request_context")
        raise