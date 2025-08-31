import asyncio
from typing import List, Sequence
import sys
from pathlib import Path

import httpx

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from packages.config.embedding import (
    config, 
    MODEL_NAME, 
    EMBEDDING_DIM, 
    BASE_URL, 
    HEADERS
)


def _pad_or_truncate(vecs: List[List[float]], dim: int) -> List[List[float]]:
    padded: List[List[float]] = []
    for v in vecs:
        if len(v) == dim:
            padded.append(v)
        elif len(v) > dim:
            padded.append(v[:dim])
        else:
            padded.append(v + [0.0] * (dim - len(v)))
    return padded


async def _embed_batch(texts: List[str], model: str, timeout: float = 15.0) -> List[List[float]]:
    # Always use unified model from config to prevent divergence
    model = MODEL_NAME
    payload = {"model": model, "input": texts}
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(BASE_URL, json=payload, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        vectors = [item["embedding"] for item in data.get("data", [])]
        return _pad_or_truncate(vectors, EMBEDDING_DIM)


async def embed_store(texts: List[str], batch_size: int = 64) -> List[List[float]]:
    """Embed texts for storage using the configured model."""
    if not texts:
        return []
    # Chunk into batches
    batches = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]
    results: List[List[float]] = []
    for batch in batches:
        vecs = await _embed_batch(batch, MODEL_NAME)
        results.extend(vecs)
    return results


async def embed_query(text: str) -> List[float]:
    """Embed query text using the configured model."""
    if not text:
        return []
    vecs = await _embed_batch([text], MODEL_NAME)
    return vecs[0] if vecs else []


def embed_text(text: str) -> List[float]:
    """Synchronous wrapper for embed_query"""
    if not text:
        return []
    
    try:
        # If we're in an event loop, create a new one in a thread
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, embed_query(text))
            return future.result()
    except RuntimeError:
        # No event loop running, safe to use asyncio.run
        return asyncio.run(embed_query(text))
