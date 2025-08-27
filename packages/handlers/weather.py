"""
Weather handler for weather-related queries
"""
import asyncio
import httpx
import os
from typing import Dict, Any
from datetime import datetime


class WeatherClient:
    """Stub weather API client"""
    
    def __init__(self):
        self.api_key = os.getenv("WEATHER_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/2.5"
    
    async def get_weather(self, location: str) -> Dict[str, Any]:
        """Get current weather for location (stub implementation)"""
        if not self.api_key:
            return {
                "location": location,
                "temperature": 28,
                "condition": "Partly Cloudy",
                "humidity": 65,
                "wind_speed": 12,
                "source": "OpenWeatherMap"
            }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                params = {
                    "q": location,
                    "appid": self.api_key,
                    "units": "metric"
                }
                response = await client.get(f"{self.base_url}/weather", params=params)
                response.raise_for_status()
                data = response.json()
                
                return {
                    "location": data["name"],
                    "temperature": round(data["main"]["temp"]),
                    "condition": data["weather"][0]["description"].title(),
                    "humidity": data["main"]["humidity"],
                    "wind_speed": round(data["wind"]["speed"] * 3.6),  # Convert to km/h
                    "source": "OpenWeatherMap"
                }
        except Exception:
            # Fallback to stub data
            return {
                "location": location,
                "temperature": 28,
                "condition": "Partly Cloudy", 
                "humidity": 65,
                "wind_speed": 12,
                "source": "OpenWeatherMap (stub)"
            }


async def handle(query: str, slots: dict, lang: str = "bn") -> dict:
    """
    Handle weather queries
    
    Returns:
    {
      "answer_bn": "...",
      "sources": [{"name":"...", "url":"...", "published_at":"..."}],
      "flags": {"single_source": bool, "disagreement": bool},
      "metrics": {"latency_ms": int, "source_count": int, "updated_ct": "..."}
    }
    """
    start_time = datetime.now()
    
    # Get location from slots or default to Dhaka
    location = slots.get("location", "Dhaka")
    
    # Initialize weather client
    weather_client = WeatherClient()
    
    try:
        # Get weather data
        weather_data = await weather_client.get_weather(location)
        
        # Format Bangla answer
        temp = weather_data["temperature"]
        condition = weather_data["condition"]
        humidity = weather_data["humidity"]
        wind_speed = weather_data["wind_speed"]
        
        if (lang or "bn").lower() == "en":
            answer_text = (f"Current weather in {weather_data['location']}: "
                           f"temperature {temp}°C, condition {condition}, "
                           f"humidity {humidity}%, wind speed {wind_speed} km/h.")
        else:
            answer_text = (f"{weather_data['location']}-এর বর্তমান আবহাওয়া: তাপমাত্রা {temp}°সে, "
                           f"অবস্থা {condition}, আর্দ্রতা {humidity}%, বাতাসের গতি {wind_speed} কিমি/ঘণ্টা।")
        
        # Create source info
        sources = [{
            "name": weather_data["source"],
            "url": "https://openweathermap.org/",
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
            "answer_bn": f"{location}-এর আবহাওয়ার তথ্য পেতে সমস্যা হয়েছে। ত্রুটি: {str(e)}",
            "sources": [],
            "flags": {"single_source": False, "disagreement": False},
            "metrics": {
                "latency_ms": latency_ms,
                "source_count": 0,
                "updated_ct": end_time.isoformat()
            }
        }