"""
Conversation Persistence Layer

Handles storage and retrieval of conversation threads using Redis
for fast access and PostgreSQL for long-term storage.
"""
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from packages.memory.conversation import ConversationThread, ConversationManager


class ConversationPersistence:
    """Handles conversation storage with Redis cache and PostgreSQL backup."""
    
    def __init__(self):
        self.redis_client = None
        self.postgres_available = False
        self._setup_storage()
    
    def _setup_storage(self):
        """Initialize storage backends."""
        try:
            # Try to initialize Redis
            import redis
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=2,  # Use different DB for conversations
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            self.redis_client.ping()
            print("[MEMORY] Redis connection established")
        except Exception as e:
            print(f"[MEMORY] Redis not available: {e}")
            self.redis_client = None
        
        try:
            # Check if PostgreSQL is available for long-term storage
            from packages.db.repo import session_scope
            with session_scope() as session:
                session.execute("SELECT 1")
            self.postgres_available = True
            print("[MEMORY] PostgreSQL available for conversation storage")
        except Exception as e:
            print(f"[MEMORY] PostgreSQL not available for conversations: {e}")
            self.postgres_available = False
    
    async def save_conversation(self, thread: ConversationThread) -> bool:
        """Save conversation thread to storage."""
        data = thread.to_dict()
        
        # Save to Redis for fast access
        if self.redis_client:
            try:
                key = f"conversation:{thread.conversation_id}"
                # Set TTL to 7 days
                ttl = 7 * 24 * 3600  # 7 days in seconds
                
                self.redis_client.setex(
                    key, 
                    ttl,
                    json.dumps(data, ensure_ascii=False)
                )
                
                # Also store in a conversations index
                index_key = "conversations:active"
                self.redis_client.sadd(index_key, thread.conversation_id)
                self.redis_client.expire(index_key, ttl)
                
                return True
                
            except Exception as e:
                print(f"[MEMORY] Failed to save to Redis: {e}")
        
        # Fallback to PostgreSQL (if available)
        if self.postgres_available:
            return await self._save_to_postgres(thread)
        
        return False
    
    async def load_conversation(self, conversation_id: str) -> Optional[ConversationThread]:
        """Load conversation thread from storage."""
        
        # Try Redis first
        if self.redis_client:
            try:
                key = f"conversation:{conversation_id}"
                data_str = self.redis_client.get(key)
                
                if data_str:
                    data = json.loads(data_str)
                    return ConversationThread.from_dict(data)
                    
            except Exception as e:
                print(f"[MEMORY] Failed to load from Redis: {e}")
        
        # Try PostgreSQL fallback
        if self.postgres_available:
            return await self._load_from_postgres(conversation_id)
        
        return None
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation from storage."""
        deleted = False
        
        # Remove from Redis
        if self.redis_client:
            try:
                key = f"conversation:{conversation_id}"
                self.redis_client.delete(key)
                
                # Remove from index
                index_key = "conversations:active"
                self.redis_client.srem(index_key, conversation_id)
                deleted = True
                
            except Exception as e:
                print(f"[MEMORY] Failed to delete from Redis: {e}")
        
        # Remove from PostgreSQL
        if self.postgres_available:
            postgres_deleted = await self._delete_from_postgres(conversation_id)
            deleted = deleted or postgres_deleted
        
        return deleted
    
    async def list_conversations(
        self, 
        limit: int = 50,
        user_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List recent conversations."""
        conversations = []
        
        if self.redis_client:
            try:
                index_key = "conversations:active"
                conv_ids = self.redis_client.smembers(index_key)
                
                for conv_id in list(conv_ids)[:limit]:
                    key = f"conversation:{conv_id}"
                    data_str = self.redis_client.get(key)
                    
                    if data_str:
                        try:
                            data = json.loads(data_str)
                            conversations.append({
                                "conversation_id": data["conversation_id"],
                                "mode": data["mode"],
                                "user_lang": data["user_lang"],
                                "created_at": data["created_at"],
                                "last_activity": data["last_activity"],
                                "total_turns": len(data["turns"]),
                                "has_summary": data["summary"] is not None
                            })
                        except Exception as e:
                            print(f"[MEMORY] Error parsing conversation {conv_id}: {e}")
            
            except Exception as e:
                print(f"[MEMORY] Failed to list from Redis: {e}")
        
        # Sort by last activity
        conversations.sort(key=lambda x: x["last_activity"], reverse=True)
        return conversations[:limit]
    
    async def cleanup_old_conversations(self, max_age_days: int = 30) -> int:
        """Clean up conversations older than max_age_days."""
        cleaned = 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        
        if self.redis_client:
            try:
                index_key = "conversations:active"
                conv_ids = self.redis_client.smembers(index_key)
                
                for conv_id in conv_ids:
                    key = f"conversation:{conv_id}"
                    data_str = self.redis_client.get(key)
                    
                    if not data_str:
                        # Already expired, remove from index
                        self.redis_client.srem(index_key, conv_id)
                        cleaned += 1
                        continue
                    
                    try:
                        data = json.loads(data_str)
                        last_activity = datetime.fromisoformat(data["last_activity"])
                        
                        if last_activity < cutoff:
                            self.redis_client.delete(key)
                            self.redis_client.srem(index_key, conv_id)
                            cleaned += 1
                            
                    except Exception as e:
                        print(f"[MEMORY] Error cleaning conversation {conv_id}: {e}")
                        # Remove problematic entry
                        self.redis_client.delete(key)
                        self.redis_client.srem(index_key, conv_id)
                        cleaned += 1
                        
            except Exception as e:
                print(f"[MEMORY] Error during cleanup: {e}")
        
        return cleaned
    
    async def _save_to_postgres(self, thread: ConversationThread) -> bool:
        """Save conversation to PostgreSQL (for long-term storage)."""
        try:
            from packages.db.repo import session_scope, text
            
            data = thread.to_dict()
            
            with session_scope() as session:
                # Create conversations table if not exists
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        conversation_id TEXT PRIMARY KEY,
                        data JSONB NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
                
                # Upsert conversation
                session.execute(text("""
                    INSERT INTO conversations (conversation_id, data, created_at, updated_at)
                    VALUES (:conv_id, :data, :created_at, NOW())
                    ON CONFLICT (conversation_id) 
                    DO UPDATE SET 
                        data = EXCLUDED.data,
                        updated_at = NOW()
                """), {
                    "conv_id": thread.conversation_id,
                    "data": json.dumps(data, ensure_ascii=False),
                    "created_at": thread.created_at
                })
                
            return True
            
        except Exception as e:
            print(f"[MEMORY] Failed to save to PostgreSQL: {e}")
            return False
    
    async def _load_from_postgres(self, conversation_id: str) -> Optional[ConversationThread]:
        """Load conversation from PostgreSQL."""
        try:
            from packages.db.repo import session_scope, text
            
            with session_scope() as session:
                result = session.execute(text("""
                    SELECT data FROM conversations 
                    WHERE conversation_id = :conv_id
                """), {"conv_id": conversation_id})
                
                row = result.fetchone()
                if row:
                    data = json.loads(row[0])
                    return ConversationThread.from_dict(data)
                    
        except Exception as e:
            print(f"[MEMORY] Failed to load from PostgreSQL: {e}")
        
        return None
    
    async def _delete_from_postgres(self, conversation_id: str) -> bool:
        """Delete conversation from PostgreSQL."""
        try:
            from packages.db.repo import session_scope, text
            
            with session_scope() as session:
                result = session.execute(text("""
                    DELETE FROM conversations 
                    WHERE conversation_id = :conv_id
                """), {"conv_id": conversation_id})
                
                return result.rowcount > 0
                
        except Exception as e:
            print(f"[MEMORY] Failed to delete from PostgreSQL: {e}")
            return False


class PersistentConversationManager(ConversationManager):
    """Conversation manager with automatic persistence."""
    
    def __init__(self):
        super().__init__()
        self.persistence = ConversationPersistence()
    
    async def get_or_create_thread_async(
        self,
        conversation_id: Optional[str] = None,
        mode = None,  # Import type issue, will fix in actual usage
        user_lang: str = "bn"
    ):
        """Async version that loads from storage if needed."""
        if conversation_id and conversation_id not in self.active_threads:
            # Try to load from storage
            thread = await self.persistence.load_conversation(conversation_id)
            if thread:
                self.active_threads[conversation_id] = thread
                return thread, False
        
        # Use sync method for existing logic
        from packages.memory.conversation import ConversationMode
        mode = mode or ConversationMode.GENERAL
        return self.get_or_create_thread(conversation_id, mode, user_lang)
    
    async def save_thread(self, conversation_id: str) -> bool:
        """Save conversation thread to persistent storage."""
        if conversation_id in self.active_threads:
            thread = self.active_threads[conversation_id]
            return await self.persistence.save_conversation(thread)
        return False
    
    async def add_turn_with_persistence(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
        intent: Optional[str] = None,
        sources: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None,
        auto_save: bool = True
    ) -> str:
        """Add turn and optionally auto-save to storage."""
        turn_id = self.add_turn(
            conversation_id=conversation_id,
            user_message=user_message,
            assistant_message=assistant_message,
            intent=intent,
            sources=sources,
            metadata=metadata
        )
        
        if auto_save:
            await self.save_thread(conversation_id)
        
        return turn_id


# Global persistent conversation manager
persistent_conversation_manager = PersistentConversationManager()