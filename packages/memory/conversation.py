"""
Conversation Memory System

Implements stable threading, context management, and mode-specific memory
for maintaining coherent multi-turn conversations.
"""
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sys
from pathlib import Path

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class ConversationMode(Enum):
    NEWS = "news"
    GENERAL = "general"
    MARKETS = "markets"
    SPORTS = "sports"
    WEATHER = "weather"


@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation."""
    turn_id: str
    user_message: str
    assistant_message: str
    intent: Optional[str]
    timestamp: datetime
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationTurn':
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass  
class ConversationSummary:
    """Compressed summary of conversation history."""
    summary_text: str
    key_facts: List[str]
    user_preferences: Dict[str, Any]
    topics_discussed: List[str]
    turns_summarized: int
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSummary':
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


class ConversationThread:
    """Manages a single conversation thread with memory."""
    
    # Configuration
    MAX_TURNS_IN_CONTEXT = 10  # Keep last N turns verbatim
    MAX_CONTEXT_TOKENS = 8000  # Approximate token limit
    SUMMARY_TRIGGER_TOKENS = 6000  # When to start summarizing
    
    def __init__(
        self, 
        conversation_id: str,
        mode: ConversationMode = ConversationMode.GENERAL,
        user_lang: str = "bn"
    ):
        self.conversation_id = conversation_id
        self.mode = mode
        self.user_lang = user_lang
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = self.created_at
        
        # Conversation state
        self.turns: List[ConversationTurn] = []
        self.summary: Optional[ConversationSummary] = None
        self.user_context: Dict[str, Any] = {
            "preferred_language": user_lang,
            "current_language": user_lang,  # Can be toggled mid-conversation
            "timezone": None,
            "interests": [],
            "mentioned_entities": [],
            "language_history": [{"language": user_lang, "timestamp": self.created_at.isoformat()}]
        }
        
        # Token tracking (rough estimates)
        self.estimated_tokens = 0
    
    def add_turn(
        self,
        user_message: str,
        assistant_message: str,
        intent: Optional[str] = None,
        sources: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Add a new turn to the conversation."""
        turn_id = str(uuid.uuid4())[:8]
        sources = sources or []
        metadata = metadata or {}
        
        turn = ConversationTurn(
            turn_id=turn_id,
            user_message=user_message,
            assistant_message=assistant_message,
            intent=intent,
            timestamp=datetime.now(timezone.utc),
            sources=sources,
            metadata=metadata
        )
        
        self.turns.append(turn)
        self.last_activity = turn.timestamp
        
        # Update user context
        self._update_user_context(user_message, intent, sources, metadata)
        
        # Estimate token usage (rough)
        turn_tokens = len(user_message.split()) + len(assistant_message.split())
        self.estimated_tokens += turn_tokens
        
        # Check if we need to summarize
        if (len(self.turns) > self.MAX_TURNS_IN_CONTEXT and 
            self.estimated_tokens > self.SUMMARY_TRIGGER_TOKENS):
            self._create_or_update_summary()
        
        return turn_id
    
    def toggle_language(self, new_language: str) -> bool:
        """
        Toggle the conversation language (BN↔EN)
        
        Args:
            new_language: New language to switch to ('bn' or 'en')
            
        Returns:
            True if language was changed, False if already in that language
        """
        current_lang = self.user_context.get("current_language", self.user_lang)
        
        if current_lang == new_language:
            return False  # Already in that language
            
        # Update current language
        self.user_context["current_language"] = new_language
        
        # Add to language history
        if "language_history" not in self.user_context:
            self.user_context["language_history"] = []
            
        self.user_context["language_history"].append({
            "language": new_language,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger": "user_toggle"
        })
        
        # Keep only last 10 language changes
        if len(self.user_context["language_history"]) > 10:
            self.user_context["language_history"] = self.user_context["language_history"][-10:]
            
        return True
    
    def get_current_language(self) -> str:
        """Get the current language for this conversation"""
        return self.user_context.get("current_language", self.user_lang)
    
    def get_conversation_context(self) -> Dict[str, Any]:
        """
        Get the full conversation context for the LLM.
        Includes system message, summary, and recent turns.
        """
        context = {
            "conversation_id": self.conversation_id,
            "mode": self.mode.value,
            "user_language": self.user_lang,
            "system_message": self._get_system_message(),
            "summary": self.summary.to_dict() if self.summary else None,
            "recent_turns": [],
            "user_context": self.user_context,
            "metadata": {
                "total_turns": len(self.turns),
                "estimated_tokens": self.estimated_tokens,
                "last_activity": self.last_activity.isoformat(),
                "created_at": self.created_at.isoformat()
            }
        }
        
        # Add recent turns (last N turns verbatim)
        recent_turns = self.turns[-self.MAX_TURNS_IN_CONTEXT:]
        for turn in recent_turns:
            context["recent_turns"].append({
                "user": turn.user_message,
                "assistant": turn.assistant_message,
                "intent": turn.intent,
                "timestamp": turn.timestamp.isoformat(),
                "sources_count": len(turn.sources)
            })
        
        return context
    
    def _update_user_context(
        self,
        user_message: str,
        intent: Optional[str],
        sources: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ):
        """Update user context with information from the current turn."""
        
        # Track mentioned entities (simple keyword extraction)
        entities = self._extract_entities(user_message)
        for entity in entities:
            if entity not in self.user_context["mentioned_entities"]:
                self.user_context["mentioned_entities"].append(entity)
        
        # Track interests based on intents
        if intent and intent not in self.user_context["interests"]:
            self.user_context["interests"].append(intent)
        
        # Keep only recent entities and interests
        if len(self.user_context["mentioned_entities"]) > 50:
            self.user_context["mentioned_entities"] = self.user_context["mentioned_entities"][-30:]
        if len(self.user_context["interests"]) > 10:
            self.user_context["interests"] = self.user_context["interests"][-5:]
    
    def _extract_entities(self, text: str) -> List[str]:
        """Simple entity extraction for user context."""
        import re
        
        # Extract capitalized words (likely proper nouns)
        entities = []
        
        # English entities
        english_entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entities.extend(english_entities)
        
        # Common entity patterns
        patterns = [
            r'\b(?:Bitcoin|BTC|Ethereum|ETH)\b',  # Crypto
            r'\b(?:NVIDIA|Apple|Tesla|Microsoft|Amazon|Google|Meta)\b',  # Stocks
            r'\b(?:Bangladesh|India|China|USA|UK)\b',  # Countries
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.extend(matches)
        
        return list(set(entities))[:10]  # Limit and deduplicate
    
    def _create_or_update_summary(self):
        """Create or update the conversation summary."""
        # Take the oldest turns that aren't already summarized
        turns_to_summarize = self.turns[:-self.MAX_TURNS_IN_CONTEXT]
        if not turns_to_summarize:
            return
        
        # Extract key information for summary
        key_facts = []
        topics = set()
        user_prefs = {}
        
        for turn in turns_to_summarize:
            # Extract facts from assistant messages
            if turn.sources:
                facts = [
                    f"Discussed {turn.intent or 'topic'} with {len(turn.sources)} sources"
                ]
                key_facts.extend(facts)
            
            # Track topics
            if turn.intent:
                topics.add(turn.intent)
        
        # Create summary text
        summary_parts = []
        if topics:
            summary_parts.append(f"Topics discussed: {', '.join(topics)}")
        if key_facts:
            summary_parts.append(f"Key information exchanged: {'; '.join(key_facts[:5])}")
        
        summary_text = ". ".join(summary_parts) if summary_parts else "General conversation"
        
        # Create or update summary
        self.summary = ConversationSummary(
            summary_text=summary_text,
            key_facts=key_facts[:10],
            user_preferences=dict(self.user_context),
            topics_discussed=list(topics),
            turns_summarized=len(turns_to_summarize),
            created_at=datetime.now(timezone.utc)
        )
        
        # Remove summarized turns to save memory
        self.turns = self.turns[-self.MAX_TURNS_IN_CONTEXT:]
        
        # Adjust token estimate
        self.estimated_tokens = self.estimated_tokens // 3  # Rough compression ratio
    
    def _get_system_message(self) -> str:
        """Get mode-specific system message."""
        
        base_context = f"""You are KhoborAgent, an AI assistant specialized in providing information to Bengali-speaking users. 

Current conversation context:
- Language: {self.user_lang}
- Mode: {self.mode.value}
- Active conversation thread: {self.conversation_id}"""

        if self.user_context.get("mentioned_entities"):
            entities = ", ".join(self.user_context["mentioned_entities"][:5])
            base_context += f"\n- Previously mentioned: {entities}"
        
        if self.summary:
            base_context += f"\n- Conversation summary: {self.summary.summary_text}"
        
        mode_specific = {
            ConversationMode.NEWS: """

NEWS MODE - DISCIPLINED FACT-CHECKING:
MANDATORY REFUSALS:
- Inadequate sources or low retrieval confidence: "Cannot verify claims with available sources. Please search for more recent information."
- Time-sensitive topics without current sources: "Cannot answer from memory on time-sensitive topics. Need current sources with timestamps."
- Contradictory sources: "Sources contain contradictions that cannot be resolved."

CITATION REQUIREMENTS:
- Every factual claim requires [n] citation
- Every number, date, quote needs source attribution
- Format: "According to [Source, Timestamp]: claim"
- NO speculation, NO memory for current events
- Refuse if sources are older than 48h for breaking news""",

            ConversationMode.MARKETS: """

MARKETS MODE - FINANCIAL DISCIPLINE:
MANDATORY REFUSALS:
- Market data without timestamps: "Cannot provide market information without current timestamps. Please search for recent market data."
- Investment advice requests: "Cannot provide investment advice. Only factual market information with disclaimers."
- Price speculation: "Cannot speculate on future prices. Only current data with source timestamps."

REQUIREMENTS:
- All market data must include timestamps and disclaimers
- Warn about delayed data and investment risks
- Cite financial data sources clearly with timestamps
- NO prediction, NO investment recommendations""",

            ConversationMode.SPORTS: """

SPORTS MODE:
- Provide sports information with match dates/times
- Include score sources and competition context
- Note when information may be preliminary
- Focus on factual match data and statistics""",

            ConversationMode.GENERAL: """

GENERAL MODE:
- Be helpful and conversational
- Maintain context from previous turns
- Acknowledge when you don't know something
- Ask clarifying questions when needed""",

            ConversationMode.WEATHER: """

WEATHER MODE - METEOROLOGICAL DISCIPLINE:
MANDATORY REFUSALS:
- Weather data without timestamps: "Cannot provide weather information without current timestamps. Please search for recent weather data."
- Forecast beyond source data: "Cannot predict weather beyond provided forecast data."

REQUIREMENTS:
- All weather data must include timestamps and location context
- Note data source and accuracy limitations explicitly
- Use appropriate units for user's region with source attribution
- NO speculation beyond provided forecasts"""
        }
        
        return base_context + mode_specific.get(self.mode, mode_specific[ConversationMode.GENERAL])
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize conversation thread to dictionary."""
        return {
            "conversation_id": self.conversation_id,
            "mode": self.mode.value,
            "user_lang": self.user_lang,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "turns": [turn.to_dict() for turn in self.turns],
            "summary": self.summary.to_dict() if self.summary else None,
            "user_context": self.user_context,
            "estimated_tokens": self.estimated_tokens
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationThread':
        """Deserialize conversation thread from dictionary."""
        thread = cls(
            conversation_id=data["conversation_id"],
            mode=ConversationMode(data["mode"]),
            user_lang=data["user_lang"]
        )
        
        thread.created_at = datetime.fromisoformat(data["created_at"])
        thread.last_activity = datetime.fromisoformat(data["last_activity"])
        thread.user_context = data["user_context"]
        thread.estimated_tokens = data["estimated_tokens"]
        
        # Restore turns
        thread.turns = [ConversationTurn.from_dict(turn_data) for turn_data in data["turns"]]
        
        # Restore summary
        if data["summary"]:
            thread.summary = ConversationSummary.from_dict(data["summary"])
        
        return thread


class ConversationManager:
    """Manages multiple conversation threads with persistence."""
    
    def __init__(self):
        self.active_threads: Dict[str, ConversationThread] = {}
        self.cleanup_interval = timedelta(hours=24)  # Clean old threads
    
    def get_or_create_thread(
        self,
        conversation_id: Optional[str] = None,
        mode: ConversationMode = ConversationMode.GENERAL,
        user_lang: str = "bn"
    ) -> Tuple[ConversationThread, bool]:
        """
        Get existing thread or create new one.
        Returns (thread, is_new).
        """
        if conversation_id and conversation_id in self.active_threads:
            thread = self.active_threads[conversation_id]
            # Update mode if changed
            if thread.mode != mode:
                thread.mode = mode
            return thread, False
        
        # Create new thread
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        thread = ConversationThread(
            conversation_id=conversation_id,
            mode=mode,
            user_lang=user_lang
        )
        
        self.active_threads[conversation_id] = thread
        return thread, True
    
    def add_turn(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
        intent: Optional[str] = None,
        sources: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Add turn to conversation thread."""
        if conversation_id not in self.active_threads:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        thread = self.active_threads[conversation_id]
        return thread.add_turn(
            user_message=user_message,
            assistant_message=assistant_message,
            intent=intent,
            sources=sources,
            metadata=metadata
        )
    
    def get_context_for_llm(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation context formatted for LLM."""
        if conversation_id not in self.active_threads:
            return None
        
        return self.active_threads[conversation_id].get_conversation_context()
    
    def cleanup_old_threads(self):
        """Remove inactive threads older than cleanup interval."""
        cutoff = datetime.now(timezone.utc) - self.cleanup_interval
        
        to_remove = []
        for conv_id, thread in self.active_threads.items():
            if thread.last_activity < cutoff:
                to_remove.append(conv_id)
        
        for conv_id in to_remove:
            del self.active_threads[conv_id]
        
        print(f"[MEMORY] Cleaned up {len(to_remove)} inactive conversations")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        if not self.active_threads:
            return {"active_threads": 0}
        
        total_turns = sum(len(thread.turns) for thread in self.active_threads.values())
        total_tokens = sum(thread.estimated_tokens for thread in self.active_threads.values())
        
        mode_distribution = {}
        for thread in self.active_threads.values():
            mode = thread.mode.value
            mode_distribution[mode] = mode_distribution.get(mode, 0) + 1
        
        return {
            "active_threads": len(self.active_threads),
            "total_turns": total_turns,
            "estimated_total_tokens": total_tokens,
            "average_turns_per_thread": total_turns / len(self.active_threads),
            "mode_distribution": mode_distribution,
            "threads_with_summaries": sum(1 for t in self.active_threads.values() if t.summary)
        }


# Global conversation manager instance
conversation_manager = ConversationManager()