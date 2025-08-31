"""
Embedding Configuration Module

Single source of truth for all embedding-related configuration.
Validates model compatibility and dimensional consistency.
"""
import os
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Model dimension mapping for OpenAI embedding models
MODEL_DIMENSIONS = {
    "text-embedding-3-large": 3072,
    "text-embedding-3-small": 1536,
    "text-embedding-ada-002": 1536,
}

# Environment configuration
# Support separate env vars for store/query while enforcing unification
EMBED_STORE_ENV = os.getenv("OPENAI_EMBED_MODEL_STORE")
EMBED_QUERY_ENV = os.getenv("OPENAI_EMBED_MODEL_QUERY")
EMBED_LEGACY_ENV = os.getenv("OPENAI_EMBED_MODEL")

# Default to text-embedding-3-large as single source of truth
DEFAULT_MODEL = "text-embedding-3-large"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

class EmbeddingConfig:
    """Centralized embedding configuration with validation."""
    
    def __init__(self):
        # Resolve model with store/query unification
        chosen_store = EMBED_STORE_ENV or EMBED_LEGACY_ENV or DEFAULT_MODEL
        chosen_query = EMBED_QUERY_ENV or EMBED_LEGACY_ENV or DEFAULT_MODEL

        # Enforce unification: both must be identical
        if chosen_store != chosen_query:
            raise ValueError(
                "Embedding models for store and query must match. "
                f"Got STORE='{chosen_store}', QUERY='{chosen_query}'. "
                "Set both to 'text-embedding-3-large' via OPENAI_EMBED_MODEL_STORE and OPENAI_EMBED_MODEL_QUERY."
            )

        self._model = chosen_store
        self._api_key = OPENAI_API_KEY
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate the embedding configuration."""
        # API key is required for embedding calls, but not for DB schema usage.
        # Avoid raising here so migrations/init can run without a key.
        if not self._api_key:
            # Soft warning; runtime embedding calls will fail if key is missing
            print("[EMBEDDING] Warning: OPENAI_API_KEY is not set. Embedding calls will fail until configured.")
        
        if self._model not in MODEL_DIMENSIONS:
            available_models = ", ".join(MODEL_DIMENSIONS.keys())
            raise ValueError(
                f"Unsupported embedding model: {self._model}. "
                f"Available models: {available_models}"
            )
    
    @property
    def model_name(self) -> str:
        """Get the configured embedding model name."""
        return self._model
    
    @property
    def dimension(self) -> int:
        """Get the embedding dimension for the configured model."""
        return MODEL_DIMENSIONS[self._model]
    
    @property
    def api_key(self) -> str:
        """Get the OpenAI API key."""
        return self._api_key
    
    @property
    def base_url(self) -> str:
        """Get the OpenAI embeddings API base URL."""
        return "https://api.openai.com/v1/embeddings"
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get the HTTP headers for API requests."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
    
    def validate_dimension(self, vector_dim: int) -> bool:
        """Validate that a vector dimension matches the configured model."""
        return vector_dim == self.dimension
    
    def model_info(self) -> Dict[str, any]:
        """Get comprehensive model information."""
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "api_base": self.base_url,
            "supported_models": list(MODEL_DIMENSIONS.keys()),
            "store_model": self.model_name,
            "query_model": self.model_name,
        }

# Global configuration instance
config = EmbeddingConfig()

# Export key values for easy access
MODEL_NAME = config.model_name
EMBEDDING_DIM = config.dimension
API_KEY = config.api_key
BASE_URL = config.base_url
HEADERS = config.headers

def get_model_dimension(model_name: str) -> Optional[int]:
    """Get the dimension for a specific model name."""
    return MODEL_DIMENSIONS.get(model_name)

def validate_model_compatibility(model_name: str, dimension: int) -> bool:
    """Validate that a model name and dimension are compatible."""
    expected_dim = MODEL_DIMENSIONS.get(model_name)
    return expected_dim is not None and expected_dim == dimension