"""
Tool Routing for Volatile Facts

Handles routing to external tools for time-sensitive/volatile data
and manages tool failures without LLM fallback fabrication.
"""
import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone
from enum import Enum


class ToolType(Enum):
    MARKETS = "markets"
    SPORTS = "sports"
    WEATHER = "weather"
    NEWS = "news"
    LOOKUP = "lookup"


class ToolFailureType(Enum):
    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    API_ERROR = "api_error"
    PARSE_ERROR = "parse_error"
    RATE_LIMIT = "rate_limit"
    UNAVAILABLE = "unavailable"


class ToolResult:
    """Standardized tool result container."""
    
    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        failure_type: Optional[ToolFailureType] = None,
        tool_name: str = "unknown",
        execution_time_ms: float = 0.0,
        retry_suggested: bool = False
    ):
        self.success = success
        self.data = data
        self.error = error
        self.failure_type = failure_type
        self.tool_name = tool_name
        self.execution_time_ms = execution_time_ms
        self.retry_suggested = retry_suggested
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "failure_type": self.failure_type.value if self.failure_type else None,
            "tool_name": self.tool_name,
            "execution_time_ms": self.execution_time_ms,
            "retry_suggested": self.retry_suggested,
            "timestamp": self.timestamp.isoformat()
        }


class VolatileFactRouter:
    """Routes volatile fact queries to appropriate tools with failure handling."""
    
    # Tool timeout configurations (in seconds)
    TOOL_TIMEOUTS = {
        ToolType.MARKETS: 8.0,   # Financial APIs can be slower
        ToolType.SPORTS: 6.0,    # Sports APIs usually fast
        ToolType.WEATHER: 4.0,   # Weather APIs generally quick
        ToolType.NEWS: 10.0,     # News APIs may be slower
        ToolType.LOOKUP: 3.0     # Local lookup should be fast
    }
    
    # Retry configurations
    MAX_RETRIES = {
        ToolType.MARKETS: 2,     # Important for financial accuracy
        ToolType.SPORTS: 1,      # Sports data less critical for retries  
        ToolType.WEATHER: 1,     # Weather updates frequently anyway
        ToolType.NEWS: 1,        # News has fallback to local data
        ToolType.LOOKUP: 0       # Local lookup shouldn't need retries
    }
    
    def __init__(self):
        self.call_history: List[Dict[str, Any]] = []
    
    async def route_to_tool(
        self,
        query: str,
        tool_type: ToolType,
        handler_func: callable,
        lang: str = "bn",
        **kwargs
    ) -> ToolResult:
        """
        Route query to specified tool with comprehensive error handling.
        
        Args:
            query: User query
            tool_type: Target tool type
            handler_func: Tool handler function
            lang: Target language
            **kwargs: Additional arguments for handler
            
        Returns:
            ToolResult with success/failure information
        """
        start_time = time.time()
        timeout = self.TOOL_TIMEOUTS.get(tool_type, 5.0)
        max_retries = self.MAX_RETRIES.get(tool_type, 1)
        
        last_error = None
        last_failure_type = None
        
        for attempt in range(max_retries + 1):
            try:
                # Execute tool with timeout
                result = await asyncio.wait_for(
                    handler_func(query, lang=lang, **kwargs),
                    timeout=timeout
                )
                
                execution_time = (time.time() - start_time) * 1000
                
                # Log successful call
                self._log_call(
                    tool_type=tool_type.value,
                    query=query,
                    success=True,
                    execution_time_ms=execution_time,
                    attempt=attempt + 1
                )
                
                return ToolResult(
                    success=True,
                    data=result,
                    tool_name=tool_type.value,
                    execution_time_ms=execution_time
                )
                
            except asyncio.TimeoutError:
                last_error = f"Tool timeout after {timeout}s"
                last_failure_type = ToolFailureType.TIMEOUT
                execution_time = timeout * 1000  # Approximate
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                last_error = str(e)
                
                # Classify error type
                error_str = str(e).lower()
                if "timeout" in error_str or "timed out" in error_str:
                    last_failure_type = ToolFailureType.TIMEOUT
                elif "http" in error_str or "status" in error_str:
                    if "429" in error_str or "rate limit" in error_str:
                        last_failure_type = ToolFailureType.RATE_LIMIT
                    else:
                        last_failure_type = ToolFailureType.HTTP_ERROR
                elif "parse" in error_str or "json" in error_str or "decode" in error_str:
                    last_failure_type = ToolFailureType.PARSE_ERROR
                elif "api" in error_str or "key" in error_str:
                    last_failure_type = ToolFailureType.API_ERROR
                else:
                    last_failure_type = ToolFailureType.UNAVAILABLE
            
            # Log failed attempt
            self._log_call(
                tool_type=tool_type.value,
                query=query,
                success=False,
                execution_time_ms=execution_time,
                error=last_error,
                failure_type=last_failure_type.value if last_failure_type else None,
                attempt=attempt + 1
            )
            
            # Brief delay before retry (exponential backoff)
            if attempt < max_retries:
                await asyncio.sleep(min(2 ** attempt, 5.0))
        
        # All attempts failed
        total_execution_time = (time.time() - start_time) * 1000
        
        return ToolResult(
            success=False,
            error=last_error,
            failure_type=last_failure_type,
            tool_name=tool_type.value,
            execution_time_ms=total_execution_time,
            retry_suggested=self._should_suggest_retry(last_failure_type)
        )
    
    def _should_suggest_retry(self, failure_type: Optional[ToolFailureType]) -> bool:
        """Determine if retry should be suggested based on failure type."""
        if not failure_type:
            return False
        
        # Suggest retry for transient failures
        transient_failures = {
            ToolFailureType.TIMEOUT,
            ToolFailureType.HTTP_ERROR,
            ToolFailureType.UNAVAILABLE
        }
        
        # Don't suggest retry for persistent issues
        persistent_failures = {
            ToolFailureType.API_ERROR,
            ToolFailureType.RATE_LIMIT,
            ToolFailureType.PARSE_ERROR
        }
        
        return failure_type in transient_failures
    
    def _log_call(
        self,
        tool_type: str,
        query: str,
        success: bool,
        execution_time_ms: float,
        error: Optional[str] = None,
        failure_type: Optional[str] = None,
        attempt: int = 1
    ):
        """Log tool call for monitoring and debugging."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_type": tool_type,
            "query": query[:100] + "..." if len(query) > 100 else query,
            "success": success,
            "execution_time_ms": execution_time_ms,
            "attempt": attempt,
            "error": error,
            "failure_type": failure_type
        }
        
        self.call_history.append(log_entry)
        
        # Keep only last 100 calls to prevent memory bloat
        if len(self.call_history) > 100:
            self.call_history = self.call_history[-100:]
        
        # Print for development debugging
        status = "✓" if success else "✗"
        print(f"[TOOL] {status} {tool_type} ({execution_time_ms:.0f}ms) - {query[:50]}...")
        if not success:
            print(f"       Error: {error}")
    
    def get_failure_message(
        self,
        tool_result: ToolResult,
        query: str,
        lang: str = "bn"
    ) -> Dict[str, str]:
        """
        Generate user-friendly failure messages without LLM fabrication.
        """
        if tool_result.success:
            return {"error": False, "message_bn": "", "message_en": ""}
        
        failure_type = tool_result.failure_type
        tool_name = tool_result.tool_name
        
        # Bangla error messages
        messages_bn = {
            ToolFailureType.TIMEOUT: f"দুঃখিত, {tool_name} সেবা থেকে তথ্য আনতে সময় বেশি লাগছে। অনুগ্রহ করে পুনরায় চেষ্টা করুন।",
            ToolFailureType.HTTP_ERROR: f"{tool_name} সেবায় সাময়িক সমস্যা রয়েছে। কিছুক্ষণ পর আবার চেষ্টা করুন।",
            ToolFailureType.API_ERROR: f"{tool_name} এপিআই-তে সমস্যা হয়েছে। পরে আবার চেষ্টা করুন।",
            ToolFailureType.RATE_LIMIT: f"অনেকগুলো অনুরোধের কারণে {tool_name} সেবা সাময়িকভাবে সীমিত। অনুগ্রহ করে কিছুক্ষণ অপেক্ষা করুন।",
            ToolFailureType.PARSE_ERROR: f"{tool_name} থেকে প্রাপ্ত তথ্য প্রক্রিয়া করতে সমস্যা হয়েছে।",
            ToolFailureType.UNAVAILABLE: f"{tool_name} সেবা বর্তমানে উপলব্ধ নেই।"
        }
        
        # English error messages  
        messages_en = {
            ToolFailureType.TIMEOUT: f"Sorry, the {tool_name} service is taking too long to respond. Please try again.",
            ToolFailureType.HTTP_ERROR: f"The {tool_name} service is experiencing temporary issues. Please try again later.",
            ToolFailureType.API_ERROR: f"There's an issue with the {tool_name} API. Please try again later.", 
            ToolFailureType.RATE_LIMIT: f"Too many requests to {tool_name} service. Please wait a moment before trying again.",
            ToolFailureType.PARSE_ERROR: f"Unable to process the data received from {tool_name} service.",
            ToolFailureType.UNAVAILABLE: f"The {tool_name} service is currently unavailable."
        }
        
        # Default fallback messages
        default_bn = f"'{query}' সম্পর্কে তথ্য আনতে সমস্যা হয়েছে। অনুগ্রহ করে পুনরায় চেষ্টা করুন।"
        default_en = f"Unable to fetch information about '{query}'. Please try again."
        
        message_bn = messages_bn.get(failure_type, default_bn)
        message_en = messages_en.get(failure_type, default_en)
        
        # Add retry suggestion if applicable
        if tool_result.retry_suggested:
            retry_bn = " পুনরায় চেষ্টা করার পরামর্শ দেওয়া হচ্ছে।"
            retry_en = " Retry is recommended."
            message_bn += retry_bn
            message_en += retry_en
        
        return {
            "error": True,
            "message_bn": message_bn,
            "message_en": message_en,
            "failure_type": failure_type.value if failure_type else "unknown",
            "retry_suggested": tool_result.retry_suggested,
            "execution_time_ms": tool_result.execution_time_ms
        }
    
    def get_call_stats(self) -> Dict[str, Any]:
        """Get statistics about recent tool calls."""
        if not self.call_history:
            return {"total_calls": 0}
        
        total_calls = len(self.call_history)
        successful_calls = sum(1 for call in self.call_history if call["success"])
        
        # Calculate average response times by tool
        tool_stats = {}
        for call in self.call_history:
            tool = call["tool_type"]
            if tool not in tool_stats:
                tool_stats[tool] = {"calls": 0, "successes": 0, "total_time": 0}
            
            tool_stats[tool]["calls"] += 1
            tool_stats[tool]["total_time"] += call["execution_time_ms"]
            if call["success"]:
                tool_stats[tool]["successes"] += 1
        
        # Calculate averages
        for tool, stats in tool_stats.items():
            stats["success_rate"] = stats["successes"] / stats["calls"]
            stats["avg_response_time_ms"] = stats["total_time"] / stats["calls"]
        
        return {
            "total_calls": total_calls,
            "success_rate": successful_calls / total_calls,
            "tool_breakdown": tool_stats,
            "recent_failures": [
                {
                    "tool": call["tool_type"],
                    "error": call["error"],
                    "failure_type": call["failure_type"],
                    "timestamp": call["timestamp"]
                }
                for call in self.call_history[-10:]
                if not call["success"]
            ]
        }


# Global router instance
volatile_router = VolatileFactRouter()