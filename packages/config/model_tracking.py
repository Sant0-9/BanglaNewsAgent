"""
Model Version Tracking and Safety Module

Prevents mixed-version embedding vectors by tracking model changes
and forcing reindex when embedding model or chunker configuration changes.
"""
import os
import json
import hashlib
from typing import Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone
from .embedding import config as embedding_config

# File to track model state
MODEL_STATE_FILE = Path("model_state.json")

class ModelTracker:
    """Tracks model changes and ensures embedding consistency."""
    
    def __init__(self):
        self.state_file = MODEL_STATE_FILE
        
    def _get_current_model_signature(self) -> Dict[str, any]:
        """Get current model configuration signature."""
        # Chunker configuration hash (would include chunk size, overlap, etc.)
        chunker_config = {
            "chunk_size": int(os.getenv("CHUNK_SIZE", "1000")),
            "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "200")),
            "chunker_type": os.getenv("CHUNKER_TYPE", "recursive"),
        }
        
        # Create a hash of chunker configuration
        chunker_hash = hashlib.md5(
            json.dumps(chunker_config, sort_keys=True).encode()
        ).hexdigest()
        
        return {
            "embedding_model": embedding_config.model_name,
            "embedding_dimension": embedding_config.dimension,
            "chunker_config": chunker_config,
            "chunker_hash": chunker_hash,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "version": "1.0"
        }
    
    def _load_tracked_state(self) -> Optional[Dict[str, any]]:
        """Load the previously tracked model state."""
        if not self.state_file.exists():
            return None
            
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[MODEL_TRACKER] Error loading model state: {e}")
            return None
    
    def _save_tracked_state(self, state: Dict[str, any]) -> None:
        """Save the current model state."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            print(f"[MODEL_TRACKER] Saved model state: {state['embedding_model']}")
        except IOError as e:
            print(f"[MODEL_TRACKER] Error saving model state: {e}")
    
    def check_model_consistency(self) -> Tuple[bool, Dict[str, any]]:
        """
        Check if model configuration has changed.
        
        Returns:
            Tuple of (is_consistent, status_info)
        """
        current_sig = self._get_current_model_signature()
        tracked_state = self._load_tracked_state()
        
        if tracked_state is None:
            # No previous state - this is a fresh install
            self._save_tracked_state(current_sig)
            return True, {
                "status": "initialized",
                "reason": "No previous model state found - initializing tracking",
                "current_model": current_sig["embedding_model"],
                "current_dimension": current_sig["embedding_dimension"],
                "reindex_required": False
            }
        
        # Check for embedding model changes
        embedding_changed = (
            tracked_state["embedding_model"] != current_sig["embedding_model"] or
            tracked_state["embedding_dimension"] != current_sig["embedding_dimension"]
        )
        
        # Check for chunker configuration changes
        chunker_changed = (
            tracked_state.get("chunker_hash", "") != current_sig["chunker_hash"]
        )
        
        if embedding_changed or chunker_changed:
            # Configuration has changed - reindex required
            changes = []
            if embedding_changed:
                changes.append(f"embedding model: {tracked_state['embedding_model']} → {current_sig['embedding_model']}")
            if chunker_changed:
                changes.append("chunker configuration changed")
                
            return False, {
                "status": "inconsistent",
                "reason": f"Configuration changed: {', '.join(changes)}",
                "previous_model": tracked_state["embedding_model"],
                "current_model": current_sig["embedding_model"],
                "previous_dimension": tracked_state["embedding_dimension"],
                "current_dimension": current_sig["embedding_dimension"],
                "changes": changes,
                "reindex_required": True
            }
        
        # Configuration is consistent
        return True, {
            "status": "consistent",
            "reason": "Model configuration matches tracked state",
            "current_model": current_sig["embedding_model"],
            "current_dimension": current_sig["embedding_dimension"],
            "reindex_required": False,
            "last_updated": tracked_state.get("last_updated", "unknown")
        }
    
    def force_reindex_and_update(self) -> Dict[str, any]:
        """
        Force a reindex and update the tracked state.
        This should be called after successfully completing a reindex.
        """
        from ..db.repo import reset_embedding_index
        
        print("[MODEL_TRACKER] Starting forced reindex due to model changes")
        
        try:
            # Perform the reindex
            reset_result = reset_embedding_index()
            
            # Update tracked state on successful reindex
            current_sig = self._get_current_model_signature()
            self._save_tracked_state(current_sig)
            
            return {
                "status": "success",
                "reindex_result": reset_result,
                "new_state": current_sig,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def get_model_info(self) -> Dict[str, any]:
        """Get comprehensive model information."""
        current_sig = self._get_current_model_signature()
        tracked_state = self._load_tracked_state()
        is_consistent, status_info = self.check_model_consistency()
        
        return {
            "current_configuration": current_sig,
            "tracked_state": tracked_state,
            "consistency_check": status_info,
            "is_consistent": is_consistent,
            "model_state_file": str(self.state_file),
            "file_exists": self.state_file.exists()
        }

# Global model tracker instance
model_tracker = ModelTracker()

def ensure_model_consistency() -> bool:
    """
    Ensure model consistency, blocking execution if reindex is required.
    
    Returns True if consistent, False if reindex is required.
    """
    is_consistent, status_info = model_tracker.check_model_consistency()
    
    if not is_consistent:
        print(f"[MODEL_SAFETY] {status_info['reason']}")
        print("[MODEL_SAFETY] Reindex required before proceeding")
        return False
    
    return True

def force_reindex_on_model_change() -> Dict[str, any]:
    """Force reindex when model configuration has changed."""
    return model_tracker.force_reindex_and_update()