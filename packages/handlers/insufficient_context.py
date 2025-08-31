"""
Insufficient Context Handler

Provides structured responses when retrieval guardrails determine
that context is insufficient for reliable answer generation.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import re


class InsufficientContextHandler:
    """Handles insufficient context scenarios with helpful alternatives."""
    
    def __init__(self):
        self.suggestion_templates = {
            "search": {
                "bn": "আরো নির্দিষ্ট অনুসন্ধানের জন্য কিওয়ার্ড ব্যবহার করুন বা অন্য কোন বিষয়ে জানতে চান তা স্পষ্ট করে বলুন।",
                "en": "Try using more specific keywords or clarify what exactly you'd like to know about."
            },
            "tools": {
                "bn": "রিয়েল-টাইম তথ্যের জন্য আবহাওয়া, বাজার বা খেলার স্কোর অনুসন্ধান করুন।",
                "en": "For real-time information, try searching for weather, market data, or sports scores."
            },
            "browse": {
                "bn": "সর্বশেষ খবর দেখতে আমাদের সংবাদ বিভাগ ব্রাউজ করুন।",
                "en": "Browse our news section to see the latest updates."
            },
            "rephrase": {
                "bn": "আপনার প্রশ্নটি ভিন্নভাবে বা সহজ ভাষায় জিজ্ঞাসা করে দেখুন।",
                "en": "Try rephrasing your question in a different way or simpler terms."
            }
        }
    
    def generate_insufficient_context_response(
        self,
        query: str,
        quality_assessment: Dict[str, Any],
        routing_info: Dict[str, Any],
        lang: str = "bn",
        intent: str = "news"
    ) -> Dict[str, Any]:
        """
        Generate a structured response for insufficient context scenarios.
        
        Args:
            query: Original user query
            quality_assessment: Context quality assessment from retrieval
            routing_info: Tool routing information
            lang: Target language
            intent: Query intent
            
        Returns:
            Structured response with alternatives and suggestions
        """
        
        # Main insufficient context messages
        main_messages = {
            "bn": "আপনার অনুসন্ধানের জন্য পর্যাপ্ত তথ্য পাওয়া যায়নি।",
            "en": "Insufficient information found for your query."
        }
        
        # Specific reason messages based on quality assessment
        reason_messages = self._get_reason_message(quality_assessment, lang)
        
        # Generate contextual suggestions
        suggestions = self._generate_suggestions(
            query, quality_assessment, routing_info, lang, intent
        )
        
        # Create response structure
        response = {
            "type": "insufficient_context",
            "message": main_messages[lang],
            "reason": reason_messages,
            "query": query,
            "suggestions": suggestions,
            "alternatives": self._get_alternatives(query, lang, intent),
            "metadata": {
                "quality_score": quality_assessment.get("quality_score", 0.0),
                "candidate_count": quality_assessment.get("candidate_count", 0),
                "best_score": quality_assessment.get("best_score", 0.0),
                "language_matches": quality_assessment.get("language_matches", 0),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        return response
    
    def _get_reason_message(
        self, 
        quality_assessment: Dict[str, Any], 
        lang: str
    ) -> Dict[str, str]:
        """Generate specific reason message based on quality assessment."""
        
        reason = quality_assessment.get("reason", "")
        candidate_count = quality_assessment.get("candidate_count", 0)
        best_score = quality_assessment.get("best_score", 0.0)
        language_matches = quality_assessment.get("language_matches", 0)
        
        # Detailed reason messages
        if candidate_count == 0:
            return {
                "bn": "আপনার অনুসন্ধানের সাথে মিলে এমন কোনো তথ্য খুঁজে পাওয়া যায়নি।",
                "en": "No information matching your search criteria was found."
            }
        elif candidate_count < 3:
            return {
                "bn": f"খুব কম তথ্য পাওয়া গেছে ({candidate_count} টি ফলাফল)। আরো নির্দিষ্ট অনুসন্ধান প্রয়োজন।",
                "en": f"Very few results found ({candidate_count} results). More specific search needed."
            }
        elif best_score < 0.4:
            return {
                "bn": "পাওয়া তথ্যগুলো আপনার অনুসন্ধানের সাথে পর্যাপ্ত মিল নেই।",
                "en": "The available information doesn't closely match your search query."
            }
        elif language_matches == 0:
            lang_name = "বাংলা" if lang == "bn" else "English"
            return {
                "bn": f"আপনার পছন্দের ভাষায় ({lang_name}) কোনো উপযুক্ত তথ্য পাওয়া যায়নি।",
                "en": f"No suitable information found in your preferred language ({lang_name})."
            }
        else:
            return {
                "bn": "পাওয়া তথ্যের গুণমান নির্ভরযোগ্য উত্তর প্রদানের জন্য যথেষ্ট নয়।",
                "en": "The quality of available information isn't sufficient for a reliable answer."
            }
    
    def _generate_suggestions(
        self,
        query: str,
        quality_assessment: Dict[str, Any],
        routing_info: Dict[str, Any],
        lang: str,
        intent: str
    ) -> List[Dict[str, str]]:
        """Generate contextual suggestions based on the query and assessment."""
        
        suggestions = []
        
        # Suggestion 1: Search refinement
        suggestions.append({
            "type": "search_refinement",
            "title": "অনুসন্ধান উন্নত করুন" if lang == "bn" else "Refine your search",
            "description": self.suggestion_templates["search"][lang],
            "action": "refine_search"
        })
        
        # Suggestion 2: Tool routing if applicable
        if routing_info.get("route_to_tool"):
            tool_name = routing_info.get("tool", "unknown")
            tool_desc_bn = {
                "markets": "আর্থিক তথ্য",
                "sports": "খেলার তথ্য", 
                "weather": "আবহাওয়া তথ্য"
            }.get(tool_name, "রিয়েল-টাইম তথ্য")
            
            tool_desc_en = {
                "markets": "financial information",
                "sports": "sports information",
                "weather": "weather information"
            }.get(tool_name, "real-time information")
            
            suggestions.append({
                "type": "tool_query",
                "title": f"{tool_desc_bn} জানুন" if lang == "bn" else f"Try {tool_desc_en}",
                "description": f"আপ-টু-ডেট {tool_desc_bn} পেতে আমাদের {tool_name} সার্ভিস ব্যবহার করুন।" if lang == "bn" else f"Use our {tool_name} service for up-to-date {tool_desc_en}.",
                "action": f"route_to_{tool_name}",
                "tool": tool_name
            })
        
        # Suggestion 3: Browse alternatives
        if intent == "news":
            suggestions.append({
                "type": "browse_news",
                "title": "সর্বশেষ খবর দেখুন" if lang == "bn" else "Browse latest news",
                "description": self.suggestion_templates["browse"][lang],
                "action": "browse_recent_news"
            })
        
        # Suggestion 4: Rephrase query
        suggestions.append({
            "type": "rephrase",
            "title": "প্রশ্ন পরিবর্তন করুন" if lang == "bn" else "Rephrase your question", 
            "description": self.suggestion_templates["rephrase"][lang],
            "action": "rephrase_query"
        })
        
        return suggestions
    
    def _get_alternatives(
        self, 
        query: str, 
        lang: str, 
        intent: str
    ) -> List[Dict[str, str]]:
        """Generate alternative query suggestions."""
        
        alternatives = []
        
        # Extract key terms from query
        key_terms = self._extract_key_terms(query, lang)
        
        if not key_terms:
            return alternatives
        
        # Generate alternative queries based on intent
        if intent == "news":
            alt_queries = self._generate_news_alternatives(key_terms, lang)
        elif intent == "markets":
            alt_queries = self._generate_markets_alternatives(key_terms, lang)
        elif intent == "sports":
            alt_queries = self._generate_sports_alternatives(key_terms, lang)
        else:
            alt_queries = self._generate_general_alternatives(key_terms, lang)
        
        for alt_query in alt_queries[:3]:  # Limit to top 3 alternatives
            alternatives.append({
                "query": alt_query,
                "description": f"'{alt_query}' অনুসন্ধান করুন" if lang == "bn" else f"Search for '{alt_query}'"
            })
        
        return alternatives
    
    def _extract_key_terms(self, query: str, lang: str) -> List[str]:
        """Extract key terms from the query for generating alternatives."""
        
        # Remove common stop words
        stop_words = {
            "bn": {"এ", "এই", "ও", "তে", "এর", "করে", "হয়", "হয়েছে", "আছে", "ছিল", "থেকে", "জন্য", "কি", "কী", "কেন", "কিভাবে"},
            "en": {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "what", "when", "where", "who", "why", "how"}
        }
        
        # Tokenize
        if lang == "bn":
            # Simple Bangla tokenization
            tokens = re.findall(r'[\u0980-\u09FF]+|[a-zA-Z]+', query)
        else:
            tokens = re.findall(r'\b\w+\b', query.lower())
        
        # Filter stop words and short terms
        key_terms = [
            token for token in tokens 
            if token.lower() not in stop_words.get(lang, set()) and len(token) > 2
        ]
        
        return key_terms[:5]  # Return top 5 key terms
    
    def _generate_news_alternatives(self, key_terms: List[str], lang: str) -> List[str]:
        """Generate news-specific alternative queries."""
        if not key_terms:
            return []
        
        alternatives = []
        main_term = key_terms[0]
        
        if lang == "bn":
            alternatives.extend([
                f"{main_term} সম্পর্কে সর্বশেষ খবর",
                f"{main_term} নিয়ে আজকের খবর",
                f"{main_term} সংবাদ"
            ])
        else:
            alternatives.extend([
                f"latest news about {main_term}",
                f"{main_term} news today",
                f"recent {main_term} updates"
            ])
        
        return alternatives
    
    def _generate_markets_alternatives(self, key_terms: List[str], lang: str) -> List[str]:
        """Generate markets-specific alternative queries."""
        if not key_terms:
            return []
        
        alternatives = []
        main_term = key_terms[0]
        
        if lang == "bn":
            alternatives.extend([
                f"{main_term} শেয়ারের দাম",
                f"{main_term} বাজার মূল্য",
                f"{main_term} স্টক"
            ])
        else:
            alternatives.extend([
                f"{main_term} stock price",
                f"{main_term} market value", 
                f"{main_term} share price"
            ])
        
        return alternatives
    
    def _generate_sports_alternatives(self, key_terms: List[str], lang: str) -> List[str]:
        """Generate sports-specific alternative queries.""" 
        if not key_terms:
            return []
        
        alternatives = []
        main_term = key_terms[0]
        
        if lang == "bn":
            alternatives.extend([
                f"{main_term} খেলার ফলাফল",
                f"{main_term} স্কোর",
                f"{main_term} ম্যাচ"
            ])
        else:
            alternatives.extend([
                f"{main_term} game result",
                f"{main_term} score",
                f"{main_term} match"
            ])
        
        return alternatives
    
    def _generate_general_alternatives(self, key_terms: List[str], lang: str) -> List[str]:
        """Generate general alternative queries."""
        if not key_terms:
            return []
        
        alternatives = []
        main_term = key_terms[0]
        
        if len(key_terms) > 1:
            second_term = key_terms[1]
            if lang == "bn":
                alternatives.extend([
                    f"{main_term} {second_term}",
                    f"{main_term} সম্পর্কে তথ্য",
                    f"{main_term} কী"
                ])
            else:
                alternatives.extend([
                    f"{main_term} {second_term}",
                    f"information about {main_term}",
                    f"what is {main_term}"
                ])
        
        return alternatives


# Global instance
insufficient_context_handler = InsufficientContextHandler()