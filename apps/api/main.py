from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import sys
import os
from pathlib import Path

# Add packages and services to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from packages.router.intent import classify
from packages.handlers import weather, markets, sports, lookup, news

app = FastAPI(
    title="KhoborAgent API",
    description="Multi-intent query API supporting news, weather, markets, sports, and lookup",
    version="2.0.0"
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    query: str = Field(..., description="Query for various intents (news, weather, markets, sports, lookup)")
    lang: str = Field(default="bn", description="Response language (en/bn)")

class SourceInfo(BaseModel):
    name: str
    url: str
    published_at: Optional[str]

class AskResponse(BaseModel):
    answer_bn: str
    sources: List[SourceInfo]
    metrics: Dict[str, Any]
    flags: Dict[str, bool]
    router_info: str

def resolve_handler(intent: str):
    """Resolve intent to appropriate handler function"""
    handler_map = {
        "weather": weather.handle,
        "markets": markets.handle,
        "sports": sports.handle,
        "lookup": lookup.handle,
        "news": news.handle
    }
    return handler_map.get(intent, news.handle)  # Default to news

@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "KhoborAgent API"
    }

@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """
    Process queries using intent classification and specialized handlers
    
    Flow:
    1. Classify query intent and extract slots
    2. Resolve appropriate handler for intent
    3. Call handler with query, slots, and language
    4. Return standardized response with metrics
    """
    try:
        # Step 1: Classify intent
        clf = classify(request.query)
        
        # Dev log
        print(f"[router] intent={clf['intent']} conf={clf['confidence']:.2f} slots={clf['slots']}")
        
        # Step 2: Resolve handler
        handler = resolve_handler(clf["intent"])
        
        # Step 3: Call handler
        resp = await handler(request.query, clf["slots"], lang=request.lang or "bn")
        
        # Step 4: Always include intent and confidence in metrics
        resp["metrics"]["intent"] = clf["intent"]
        resp["metrics"]["confidence"] = clf["confidence"]
        
        # Step 5: Build response
        sources = []
        for source_info in resp.get("sources", []):
            sources.append(SourceInfo(
                name=source_info.get("name", "Unknown"),
                url=source_info.get("url", ""),
                published_at=source_info.get("published_at")
            ))
        
        # Create router info display
        router_info = f"Routed to: {clf['intent'].title()} ({clf['confidence']:.2f})"
        
        response = AskResponse(
            answer_bn=resp["answer_bn"],
            sources=sources,
            metrics=resp["metrics"],
            flags=resp["flags"],
            router_info=router_info
        )
        
        print(f"Response generated successfully for intent={clf['intent']}")
        return response
        
    except Exception as e:
        # Clean error with official sources for weather/markets
        intent = clf.get("intent", "unknown") if 'clf' in locals() else "unknown"
        
        error_msg = "সেবায় সাময়িক সমস্যা হয়েছে।"
        error_sources = []
        
        if intent == "weather":
            error_sources = [{
                "name": "OpenWeatherMap",
                "url": "https://openweathermap.org/",
                "published_at": datetime.now(timezone.utc).isoformat()
            }]
        elif intent == "markets":
            error_sources = [{
                "name": "Alpha Vantage",
                "url": "https://www.alphavantage.co/",
                "published_at": datetime.now(timezone.utc).isoformat()
            }]
        
        print(f"Error processing request for intent={intent}: {e}")
        
        # Return clean error response
        return AskResponse(
            answer_bn=error_msg,
            sources=[SourceInfo(**src) for src in error_sources],
            metrics={
                "intent": intent,
                "confidence": 0.0,
                "latency_ms": 0,
                "source_count": len(error_sources),
                "updated_ct": datetime.now(timezone.utc).isoformat()
            },
            flags={
                "single_source": len(error_sources) <= 1,
                "disagreement": False
            },
            router_info=f"Routed to: {intent.title()} (0.00)"
        )

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "KhoborAgent API",
        "version": "2.0.0",
        "description": "Multi-intent query API supporting news, weather, markets, sports, and lookup",
        "intents": ["news", "weather", "markets", "sports", "lookup"],
        "endpoints": {
            "POST /ask": "Submit query and get intent-routed response",
            "GET /healthz": "Health check endpoint",
            "GET /": "This information endpoint"
        },
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)