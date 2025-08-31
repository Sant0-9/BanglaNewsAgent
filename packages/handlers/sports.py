"""
Sports handler for sports scores and match info
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent))


class SportsClient:
    """Stub sports API client (replace with real API)"""
    async def get_latest_score(self, team: str) -> Dict[str, Any]:
        # Stub data; integrate real provider here
        await asyncio.sleep(0.1)
        return {
            "team": team,
            "opponent": "Rivals",
            "score": "2-1",
            "status": "Final",
            "source": "StubSports",
        }


async def handle(query: str, slots: dict, lang: str = "bn") -> dict:
    """
    Handle sports queries (latest score / last match)
    """
    start_time = datetime.now()

    # Extract team if available; very simple heuristic
    team = slots.get("sport") or "Team"

    client = SportsClient()
    try:
        data = await client.get_latest_score(team)

        if (lang or "bn").lower() == "en":
            answer = (
                f"{data['team']} vs {data['opponent']}: {data['score']} ({data['status']})."
            )
        else:
            answer = (
                f"{data['team']} বনাম {data['opponent']}: {data['score']} ({data['status']})."
            )

        end_time = datetime.now()
        return {
            "answer_bn": answer,
            "sources": [
                {
                    "name": data["source"],
                    "url": "https://example.com/sports",
                    "published_at": end_time.isoformat(),
                }
            ],
            "flags": {"single_source": True, "disagreement": False},
            "metrics": {
                "latency_ms": int((end_time - start_time).total_seconds() * 1000),
                "source_count": 1,
                "updated_ct": end_time.isoformat(),
            },
        }
    except Exception as e:
        end_time = datetime.now()
        return {
            "answer_bn": (
                f"খেলার ফলাফল আনতে সমস্যা হয়েছে: {str(e)}"
                if (lang or "bn").lower() != "en"
                else f"Failed to fetch sports score: {str(e)}"
            ),
            "sources": [],
            "flags": {"single_source": False, "disagreement": False},
            "metrics": {
                "latency_ms": int((end_time - start_time).total_seconds() * 1000),
                "source_count": 0,
                "updated_ct": end_time.isoformat(),
            },
        }
