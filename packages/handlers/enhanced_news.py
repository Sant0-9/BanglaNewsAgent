"""
Enhanced News Handler with Retrieval Guardrails

Implements hybrid retrieval, context gating, and proper citation handling
for reliable news delivery without hallucinations.
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from packages.llm.openai_client import summarize_bn_first
from packages.nlp.hybrid_retrieve import hybrid_retrieve_with_guardrails
from packages.router.tool_routing import volatile_router, ToolType
from packages.handlers.insufficient_context import insufficient_context_handler
from packages.db import repo as db_repo


async def enhanced_handle(
    query: str, 
    slots: dict, 
    lang: str = "bn",
    intent: str = "news"
) -> dict:
    """
    Enhanced news handler with retrieval guardrails and tool routing.
    
    Returns structured response with proper error handling and citations.
    """
    start_time = datetime.now(timezone.utc)
    
    try:
        # 1) Hybrid retrieval with guardrails
        retrieval_result = await hybrid_retrieve_with_guardrails(
            query=query,
            category=None,  # No category filter for general news
            repo=db_repo,
            lang=lang,
            intent=intent,
            window_hours=72
        )
        
        evidence = retrieval_result['evidence']
        quality = retrieval_result['quality']
        routing = retrieval_result['routing']
        guardrails = retrieval_result['guardrails']
        citations_required = retrieval_result['citations_required']
        
        # 2) Check if tool routing is recommended for volatile facts
        if routing.get('route_to_tool') and routing.get('tool'):
            print(f"[NEWS] Volatile fact detected, routing to {routing['tool']} tool")
            
            # Route to appropriate tool
            tool_type = ToolType(routing['tool'])
            
            # Get handler function (would import based on tool)
            if tool_type == ToolType.MARKETS:
                from packages.handlers import markets
                handler_func = markets.handle
            elif tool_type == ToolType.SPORTS:
                from packages.handlers import sports  
                handler_func = sports.handle
            else:
                # Fallback to news handler for other tool types
                handler_func = None
            
            if handler_func:
                tool_result = await volatile_router.route_to_tool(
                    query=query,
                    tool_type=tool_type,
                    handler_func=handler_func,
                    lang=lang,
                    slots=slots
                )
                
                if tool_result.success:
                    # Return tool result with routing metadata
                    result_data = tool_result.data
                    if isinstance(result_data, dict):
                        result_data['routing_info'] = {
                            'routed_to_tool': True,
                            'tool_name': tool_type.value,
                            'execution_time_ms': tool_result.execution_time_ms,
                            'reason': routing['reason']
                        }
                        return result_data
                
                # Tool failed - return error without LLM fabrication
                failure_msg = volatile_router.get_failure_message(tool_result, query, lang)
                end_time = datetime.now(timezone.utc)
                
                return {
                    "answer_bn": failure_msg['message_bn'] if lang == 'bn' else failure_msg['message_en'],
                    "answer_en": failure_msg['message_en'],
                    "sources": [],
                    "flags": {"single_source": False, "disagreement": False, "tool_failure": True},
                    "metrics": {
                        "latency_ms": int((end_time - start_time).total_seconds() * 1000),
                        "source_count": 0,
                        "updated_ct": end_time.isoformat(),
                        "tool_execution_time_ms": tool_result.execution_time_ms,
                        "tool_failure_type": failure_msg['failure_type']
                    },
                    "error": {
                        "type": "tool_failure",
                        "tool": tool_type.value,
                        "retry_suggested": failure_msg['retry_suggested'],
                        "message": failure_msg[f'message_{lang}']
                    }
                }
        
        # 3) Context gating - check if we have sufficient context
        if not quality['sufficient']:
            print(f"[NEWS] Insufficient context: {quality['reason']}")
            
            # Generate structured insufficient context response
            insufficient_response = insufficient_context_handler.generate_insufficient_context_response(
                query=query,
                quality_assessment=quality,
                routing_info=routing,
                lang=lang,
                intent=intent
            )
            
            end_time = datetime.now(timezone.utc)
            
            # Convert to standard response format
            if lang == 'bn':
                answer_text = f"{insufficient_response['message']} {insufficient_response['reason']['bn']}"
            else:
                answer_text = f"{insufficient_response['message']} {insufficient_response['reason']['en']}"
            
            return {
                "answer_bn": answer_text,
                "answer_en": insufficient_response['reason']['en'],
                "sources": [],
                "flags": {"single_source": False, "disagreement": False, "insufficient_context": True},
                "metrics": {
                    "latency_ms": int((end_time - start_time).total_seconds() * 1000),
                    "source_count": quality['candidate_count'],
                    "updated_ct": end_time.isoformat(),
                    "quality_score": quality['quality_score'],
                    "best_score": quality['best_score']
                },
                "insufficient_context": insufficient_response,
                "guardrails_applied": guardrails['applied']
            }
        
        # 4) Proceed with answer generation - we have sufficient context
        print(f"[NEWS] Processing {len(evidence)} sources with quality score {quality['quality_score']:.3f}")
        
        if not evidence:
            end_time = datetime.now(timezone.utc)
            return {
                "answer_bn": "বর্তমানে এই বিষয়ে কোনো সংবাদ পাওয়া যাচ্ছে না।",
                "answer_en": "No news currently available on this topic.",
                "sources": [],
                "flags": {"single_source": False, "disagreement": False},
                "metrics": {
                    "latency_ms": int((end_time - start_time).total_seconds() * 1000),
                    "source_count": 0,
                    "updated_ct": end_time.isoformat()
                }
            }
        
        # 5) Generate summary with enhanced citation handling
        summary_result = await summarize_bn_first(
            query=query,
            evidence=evidence,
            lang=lang,
            require_citations=citations_required
        )
        
        # 6) Build enhanced sources with timestamps (required for News mode)
        sources = []
        for item in evidence:
            source_entry = {
                "name": item.get("outlet", "Unknown"),
                "url": item.get("url", ""),
                "published_at": item.get("published_at", ""),
            }
            
            # Add citation for News mode
            if citations_required and "citation" in item:
                source_entry["citation"] = item["citation"]
            
            # Add language detection info
            if "language_detected" in item:
                source_entry["language"] = item["language_detected"]["language"]
                source_entry["language_confidence"] = item["language_detected"]["confidence"]
            
            sources.append(source_entry)
        
        # 7) Detect content flags
        source_domains = {item.get("outlet", "Unknown") for item in evidence}
        single_source = len(source_domains) == 1
        
        # Simple disagreement detection (could be enhanced)
        disagreement = len(evidence) > 3 and len(source_domains) > 2
        
        end_time = datetime.now(timezone.utc)
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # 8) Build final response
        response = {
            "answer_bn": summary_result.get("answer_bn", "তথ্য প্রক্রিয়াকরণে সমস্যা হয়েছে।"),
            "answer_en": summary_result.get("answer_en", "Error processing information."),
            "sources": sources,
            "flags": {
                "single_source": single_source,
                "disagreement": disagreement,
                "citations_required": citations_required,
                "language_filtered": guardrails.get('lang_filter', False)
            },
            "metrics": {
                "latency_ms": latency_ms,
                "source_count": len(evidence),
                "updated_ct": end_time.isoformat(),
                "quality_score": quality['quality_score'],
                "best_score": quality['best_score'],
                "language_matches": quality['language_matches'],
                "processing_time_ms": guardrails.get('processing_time_ms', 0)
            },
            "guardrails_applied": guardrails['applied'],
            "retrieval_stats": retrieval_result.get('stats', {})
        }
        
        return response
        
    except Exception as e:
        print(f"[NEWS] Error in enhanced_handle: {e}")
        end_time = datetime.now(timezone.utc)
        
        return {
            "answer_bn": f"তথ্য প্রক্রিয়াকরণে ত্রুটি: {str(e)}",
            "answer_en": f"Error processing information: {str(e)}",
            "sources": [],
            "flags": {"single_source": False, "disagreement": False, "processing_error": True},
            "metrics": {
                "latency_ms": int((end_time - start_time).total_seconds() * 1000),
                "source_count": 0,
                "updated_ct": end_time.isoformat()
            },
            "error": {
                "type": "processing_error",
                "message": str(e)
            }
        }


# Backward compatibility function
async def handle(query: str, slots: dict, lang: str = "bn") -> dict:
    """Wrapper for backward compatibility."""
    return await enhanced_handle(query, slots, lang, intent="news")