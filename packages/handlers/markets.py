"""
Markets handler for stock/financial queries
"""
import asyncio
import httpx
import os
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add packages to path 
sys.path.append(str(Path(__file__).parent.parent))


class QuotesClient:
    """Stub quotes API client"""
    
    def __init__(self):
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.base_url = "https://www.alphavantage.co/query"
    
    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Get stock quote (stub implementation)"""
        if not self.api_key:
            raise RuntimeError("Alpha Vantage API key not configured")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": ticker,
                    "apikey": self.api_key
                }
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                quote = data.get("Global Quote", {})
                if not quote:
                    raise ValueError("No quote data found")
                
                return {
                    "ticker": quote.get("01. symbol", ticker),
                    "price": float(quote.get("05. price", 0)),
                    "change": float(quote.get("09. change", 0)),
                    "change_percent": float(quote.get("10. change percent", "0%").rstrip('%')),
                    "volume": int(quote.get("06. volume", 0)),
                    "source": "Alpha Vantage"
                }
        except Exception as e:
            raise RuntimeError(f"Quote fetch failed: {e}")


async def handle(query: str, slots: dict, lang: str = "bn") -> dict:
    """
    Handle markets queries
    
    If ticker found: call quotes API
    Else: fallback to news intent with same query
    
    Returns:
    {
      "answer_bn": "...",
      "sources": [{"name":"...", "url":"...", "published_at":"..."}],
      "flags": {"single_source": bool, "disagreement": bool},
      "metrics": {"latency_ms": int, "source_count": int, "updated_ct": "..."}
    }
    """
    start_time = datetime.now()
    
    # Check if ticker is found in slots
    ticker = slots.get("ticker")
    
    if ticker:
        # Handle as stock quote request
        quotes_client = QuotesClient()
        from packages.util.rate_limiter import api_manager
        
        try:
            # Get quote data with rate limiting and short TTL cache
            wrapped = await api_manager.call_with_protection(
                api_type="markets",
                api_function=quotes_client.get_quote,
                cache_key_params={"ticker": ticker.upper()},
                retry_count=1,
                retry_delay=0.5,
                ticker=ticker.upper(),
            )
            if "_error" in wrapped:
                raise RuntimeError(wrapped["_error"])  # Surface concise error
            quote_data = wrapped
            
            # Format Bangla answer
            price = quote_data["price"]
            change = quote_data["change"]
            change_percent = quote_data["change_percent"]
            volume = quote_data["volume"]
            
            # Format change indicator
            change_text = "বেড়েছে" if change >= 0 else "কমেছে"
            change_sign = "+" if change >= 0 else ""
            
            if (lang or "bn").lower() == "en":
                answer_text = (f"Current price of {quote_data['ticker']} is ${price:.2f}, "
                               f"{change_sign}{change:.2f} ({change_sign}{change_percent:.2f}%) {('up' if change >= 0 else 'down')} from yesterday. "
                               f"Volume: {volume:,} shares.")
            else:
                answer_text = (f"{quote_data['ticker']} শেয়ারের বর্তমান দাম ${price:.2f}, "
                               f"গতকালের তুলনায় {change_sign}{change:.2f} ({change_sign}{change_percent:.2f}%) {change_text}। "
                               f"লেনদেনের পরিমাণ: {volume:,} শেয়ার।")
            
            # Create source info
            sources = [{
                "name": quote_data["source"],
                "url": "https://www.alphavantage.co/",
                "published_at": datetime.now().isoformat()
            }]
            
            # Calculate metrics
            end_time = datetime.now()
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                "answer_bn": answer_text,
                "sources": sources,
                "flags": {"single_source": True, "disagreement": False},
                "metrics": {
                    "latency_ms": latency_ms,
                    "source_count": 1,
                    "updated_ct": end_time.isoformat()
                }
            }
            
        except Exception as e:
            # Error fallback
            end_time = datetime.now()
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                "answer_bn": (
                    f"{ticker} শেয়ারের তথ্য পেতে সমস্যা হয়েছে। ত্রুটি: {str(e)}"
                    if (lang or "bn").lower() != "en"
                    else f"Failed to fetch {ticker} stock quote: {str(e)}"
                ),
                "sources": [],
                "flags": {"single_source": False, "disagreement": False},
                "metrics": {
                    "latency_ms": latency_ms,
                    "source_count": 0,
                    "updated_ct": end_time.isoformat()
                }
            }
    
    else:
        # No ticker found, return markets-specific not available message
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return {
            "answer_bn": (
                "Please specify a stock ticker symbol (e.g., AAPL, MSFT)."
                if (lang or "bn").lower() == "en"
                else "নির্দিষ্ট শেয়ারের টিকার খুঁজে পাওয়া যায়নি। অনুগ্রহ করে শেয়ারের টিকার সিম্বল উল্লেখ করুন (যেমন: AAPL, MSFT)।"
            ),
            "sources": [{
                "name": "Alpha Vantage",
                "url": "https://www.alphavantage.co/",
                "published_at": datetime.now().isoformat()
            }],
            "flags": {"single_source": True, "disagreement": False},
            "metrics": {
                "latency_ms": latency_ms,
                "source_count": 1,
                "updated_ct": end_time.isoformat()
            }
        }