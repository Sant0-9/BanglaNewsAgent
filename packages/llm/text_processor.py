import sys
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

# Ensure we can import shared utilities
sys.path.append(str(Path(__file__).parent.parent.parent))
from packages.util.normalize import truncate_text


def build_evidence_pack(selected_articles: List[Any]) -> List[Dict[str, Any]]:
    """Format articles into evidence pack structure with trimmed excerpts."""
    evidence_pack: List[Dict[str, Any]] = []

    for index, article in enumerate(selected_articles, start=1):
        excerpt = truncate_text(getattr(article, "summary", ""), max_length=500)
        evidence_pack.append(
            {
                "id": index,
                "outlet": getattr(article, "source", "Unknown"),
                "title": getattr(article, "title", "Untitled"),
                "published_at": getattr(article, "published_at", None),
                "excerpt": excerpt,
                "url": getattr(article, "url", ""),
            }
        )

    return evidence_pack


class TextProcessor:
    """Provider-agnostic processor with local translation helper."""

    async def translate_to_bangla(self, english_text: str) -> str:
        if not english_text:
            return ""
        # Replace periods with Bangla danda for a more localized feel
        return english_text.replace(".", "।")


class NewsProcessor:
    """Local, provider-agnostic processor for summarization and translation.

    This implementation avoids external providers. It creates a concise
    English roundup based on provided evidence and returns a Bangla field by
    mirroring the English content (so downstream code remains compatible).
    """

    def __init__(self) -> None:
        pass

    async def _format_summary_en(self, evidence_pack: List[Dict[str, Any]]) -> str:
        if not evidence_pack:
            return "No recent news articles available."

        # Convert/normalize dates for readability
        def fmt_date(iso_ts: Any) -> str:
            try:
                if not iso_ts:
                    return "Unknown date"
                dt = datetime.fromisoformat(str(iso_ts).replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                return str(iso_ts) if iso_ts else "Unknown date"

        lines: List[str] = []

        # Intro sentence
        unique_outlets = [e["outlet"] for e in evidence_pack if e.get("outlet")]
        unique_outlets = list(dict.fromkeys(unique_outlets))  # preserve order, dedupe
        if unique_outlets:
            lines.append(
                f"Roundup from {', '.join(unique_outlets[:3])}" + (" and others." if len(unique_outlets) > 3 else ".")
            )

        # Highlight key items with inline numeric citations [1][2] ...
        for e in evidence_pack[:5]:
            idx = e["id"]
            title = e.get("title", "Untitled")
            outlet = e.get("outlet", "Unknown")
            when = fmt_date(e.get("published_at"))
            lines.append(f"[{idx}] {title} — {outlet} ({when}).")

        # Why it matters
        lines.append("Why it matters: quick view across multiple sources.")

        # Optional watch items are listed separately by caller using return JSON
        return " \n".join(lines)

    async def summarize_evidence(self, selected_articles: List[Any]) -> Dict[str, Any]:
        if not selected_articles:
            return {
                "summary_en": "No recent news articles available.",
                "disagreement": False,
                "single_source": False,
                "watch": [],
            }

        evidence_pack = build_evidence_pack(selected_articles)

        summary_en = await self._format_summary_en(evidence_pack)

        # Basic heuristics
        single_source = len(evidence_pack) < 2
        disagreement = False  # Not detected locally without NLP; default to False
        watch = [
            "Follow for updates across outlets.",
            "Check for revisions as stories develop.",
        ]

        return {
            "summary_en": summary_en,
            "disagreement": disagreement,
            "single_source": single_source,
            "watch": watch,
        }

    async def translate_to_bangla(self, english_summary: str) -> Dict[str, Any]:
        # Provider-free placeholder: mirror English content to maintain pipeline.
        # Downstream UI expects 'summary_bn'.
        if not english_summary:
            return {"summary_bn": ""}

        # Replace periods with Bangla danda for a more localized feel
        bn_like = english_summary.replace(".", "।")
        return {"summary_bn": bn_like}

    async def process_news(self, selected_articles: List[Any]) -> Dict[str, Any]:
        try:
            summary_result = await self.summarize_evidence(selected_articles)
            english_summary = summary_result.get("summary_en", "")

            translation_result = await self.translate_to_bangla(english_summary)
            bangla_summary = translation_result.get("summary_bn", "")

            return {
                "summary_en": english_summary,
                "summary_bn": bangla_summary,
                "disagreement": summary_result.get("disagreement", False),
                "single_source": summary_result.get("single_source", False),
                "watch": summary_result.get("watch", []),
                "evidence_pack": build_evidence_pack(selected_articles),
            }
        except Exception as error:
            return {
                "summary_en": f"Error processing news: {str(error)}",
                "summary_bn": f"Error processing news: {str(error)}",
                "disagreement": False,
                "single_source": False,
                "watch": [],
                "evidence_pack": build_evidence_pack(selected_articles) if selected_articles else [],
            }
