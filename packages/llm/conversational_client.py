"""
Conversational LLM Client

Enhanced OpenAI client that integrates conversation memory for
coherent multi-turn conversations with proper context management.
"""
import asyncio
import json
from typing import Dict, List, Optional, Any, AsyncGenerator, Tuple
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from packages.llm.openai_client import OpenAIClient
from packages.memory.conversation import ConversationMode, ConversationThread, conversation_manager
from packages.memory.persistence import persistent_conversation_manager


class ConversationalLLMClient:
    """LLM client with conversation memory integration."""
    
    def __init__(self):
        self.client = OpenAIClient()
        self.conversation_manager = persistent_conversation_manager
    
    async def generate_with_memory(
        self,
        query: str,
        evidence: List[Dict[str, Any]],
        conversation_id: Optional[str] = None,
        lang: str = "bn",
        intent: str = "news",
        stream: bool = False,
        **kwargs
    ) -> Tuple[Dict[str, Any], str]:
        """
        Generate response with conversation memory integration.
        
        Returns:
            (response_data, conversation_id)
        """
        
        # Map intent to conversation mode
        mode_mapping = {
            "news": ConversationMode.NEWS,
            "markets": ConversationMode.MARKETS,
            "sports": ConversationMode.SPORTS,
            "weather": ConversationMode.WEATHER,
            "lookup": ConversationMode.GENERAL,
        }
        mode = mode_mapping.get(intent, ConversationMode.GENERAL)
        
        # Get or create conversation thread
        thread, is_new = await self.conversation_manager.get_or_create_thread_async(
            conversation_id=conversation_id,
            mode=mode,
            user_lang=lang
        )
        
        # Get conversation context
        conv_context = thread.get_conversation_context()
        
        # Build messages with memory context
        messages = self._build_messages_with_memory(
            query=query,
            evidence=evidence,
            conv_context=conv_context,
            lang=lang
        )
        
        # Generate response (streaming not implemented yet)
        return await self._generate_complete_with_memory(
            messages=messages,
            thread=thread,
            query=query,
            evidence=evidence,
            intent=intent,
            **kwargs
        )
    
    def _build_messages_with_memory(
        self,
        query: str,
        evidence: List[Dict[str, Any]],
        conv_context: Dict[str, Any],
        lang: str
    ) -> List[Dict[str, str]]:
        """Build message array with conversation context."""
        
        messages = []
        
        # System message with conversation context
        system_msg = conv_context["system_message"]
        
        # Add context information if available
        if conv_context.get("recent_turns"):
            system_msg += "\n\nRecent conversation context:"
            for turn in conv_context["recent_turns"][-3:]:  # Last 3 turns
                timestamp = turn["timestamp"][:16].replace("T", " ")  # Simplified timestamp
                system_msg += f"\nUser ({timestamp}): {turn['user'][:100]}"
                system_msg += f"\nAssistant: {turn['assistant'][:100]}"
                if len(turn['assistant']) > 100:
                    system_msg += "..."
        
        messages.append({"role": "system", "content": system_msg})
        
        # Current query with evidence
        user_content = f"Query: {query}"
        
        if evidence:
            user_content += "\n\nAvailable evidence:"
            for i, item in enumerate(evidence[:6], 1):  # Limit evidence to prevent token overflow
                outlet = item.get("outlet", "Unknown")
                title = item.get("title", "Untitled")
                timestamp = item.get("published_display", item.get("published_at", ""))
                excerpt = item.get("excerpt", "")[:200]  # Limit excerpt length
                
                user_content += f"\n[{i}] {outlet}: {title}"
                if timestamp:
                    user_content += f" ({timestamp})"
                if excerpt:
                    user_content += f"\n    {excerpt}..."
        
        messages.append({"role": "user", "content": user_content})
        
        return messages
    
    async def _generate_complete_with_memory(
        self,
        messages: List[Dict[str, str]],
        thread: ConversationThread,
        query: str,
        evidence: List[Dict[str, Any]],
        intent: str,
        **kwargs
    ) -> Tuple[Dict[str, Any], str]:
        """Generate complete response with memory integration."""
        
        try:
            # For now, use a simpler approach with the existing summarize functions
            from packages.llm.openai_client import summarize_bn_first
            
            # Convert evidence to the format expected by summarize_bn_first
            evidence_items = []
            for item in evidence:
                evidence_items.append({
                    "outlet": item.get("outlet", item.get("name", "Unknown")),
                    "title": query,  # Use the query as title for context
                    "summary": f"Context: {query}",
                    "url": item.get("url", ""),
                    "published_at": item.get("published_at", "")
                })
            
            # Use the existing summarization pipeline
            summary_result = await summarize_bn_first(evidence_items)
            assistant_message = summary_result.get("summary_bn", "") or summary_result.get("summary_en", "")
            
            if not assistant_message:
                assistant_message = f"I understand you're asking about: {query}. Let me help you with that based on the available information."
            
            # Prepare sources for memory
            sources = [
                {
                    "name": item.get("outlet", "Unknown"),
                    "url": item.get("url", ""),
                    "published_at": item.get("published_at", "")
                }
                for item in evidence
            ]
            
            # Add turn to conversation memory
            await self.conversation_manager.add_turn_with_persistence(
                conversation_id=thread.conversation_id,
                user_message=query,
                assistant_message=assistant_message,
                intent=intent,
                sources=sources,
                metadata={
                    "model_used": kwargs.get("model", "gpt-4o-mini"),
                    "evidence_count": len(evidence),
                    "response_tokens": len(assistant_message.split()) if assistant_message else 0
                }
            )
            
            # Build response
            response_data = {
                "answer_bn": assistant_message if lang == "bn" else assistant_message,
                "answer_en": assistant_message if lang == "en" else assistant_message,
                "sources": sources,
                "conversation_id": thread.conversation_id,
                "memory_context": {
                    "total_turns": len(thread.turns),
                    "has_summary": thread.summary is not None,
                    "mode": thread.mode.value
                }
            }
            
            return response_data, thread.conversation_id
            
        except Exception as e:
            print(f"[CONV_LLM] Error generating response: {e}")
            
            # Still add turn to memory with error info
            await self.conversation_manager.add_turn_with_persistence(
                conversation_id=thread.conversation_id,
                user_message=query,
                assistant_message=f"Error: {str(e)}",
                intent=intent,
                sources=[],
                metadata={"error": str(e)}
            )
            
            raise e
    
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> Optional[Dict[str, Any]]:
        """Get conversation history for a given conversation ID."""
        
        thread = await self.conversation_manager.persistence.load_conversation(conversation_id)
        if not thread:
            return None
        
        # Build history response
        turns = []
        for turn in thread.turns[-limit:]:
            turns.append({
                "turn_id": turn.turn_id,
                "timestamp": turn.timestamp.isoformat(),
                "user_message": turn.user_message,
                "assistant_message": turn.assistant_message,
                "intent": turn.intent,
                "sources_count": len(turn.sources)
            })
        
        return {
            "conversation_id": conversation_id,
            "mode": thread.mode.value,
            "user_lang": thread.user_lang,
            "created_at": thread.created_at.isoformat(),
            "last_activity": thread.last_activity.isoformat(),
            "total_turns": len(thread.turns),
            "summary": thread.summary.to_dict() if thread.summary else None,
            "recent_turns": turns,
            "user_context": thread.user_context
        }
    
    async def cleanup_old_conversations(self) -> Dict[str, int]:
        """Clean up old conversations and return stats."""
        
        # Cleanup in-memory threads
        self.conversation_manager.cleanup_old_threads()
        
        # Cleanup persistent storage
        cleaned_persistent = await self.conversation_manager.persistence.cleanup_old_conversations(
            max_age_days=7
        )
        
        return {
            "cleaned_persistent": cleaned_persistent,
            "active_threads": len(self.conversation_manager.active_threads)
        }


# Global conversational client instance
conversational_client = ConversationalLLMClient()