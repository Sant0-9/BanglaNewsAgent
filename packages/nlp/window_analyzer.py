import re
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timezone, timedelta


class WindowAnalyzer:
    """Analyzes queries to determine optimal time windows and story context."""
    
    # Time-sensitive keywords
    IMMEDIATE_KEYWORDS = {
        # English
        "today", "now", "latest", "breaking", "current", "just", "recent", "this morning", "tonight",
        "moments ago", "currently", "right now", "as of now", "live", "ongoing",
        # Bangla
        "আজ", "এখন", "এখনই", "তাজা", "সাম্প্রতিক", "বর্তমানে", "চলমান", "সদ্য", "এই মুহূর্তে",
        "আজকের", "এইমাত্র", "এক্ষুনি", "এখনো"
    }
    
    WEEKLY_KEYWORDS = {
        # English
        "this week", "weekly", "past week", "last week", "over the week", "recent developments",
        "recent news", "what happened", "catch up", "summary", "overview",
        # Bangla  
        "এই সপ্তাহে", "সাপ্তাহিক", "গত সপ্তাহে", "সাম্প্রতিক ঘটনা", "সাম্প্রতিক সংবাদ",
        "কী ঘটেছে", "সারসংক্ষেপ", "সংক্ষিপ্ত বিবরণ"
    }
    
    BACKGROUND_KEYWORDS = {
        # English
        "background", "context", "what led to", "how did", "history", "origins", "started",
        "began", "timeline", "story so far", "full story", "complete picture", "explain",
        "why did", "what caused", "root cause", "series of events",
        # Bangla
        "পটভূমি", "প্রসঙ্গ", "কীভাবে শুরু", "ইতিহাস", "উৎপত্তি", "শুরু হয়েছিল", "কারণ",
        "সম্পূর্ণ ঘটনা", "পূর্ণ চিত্র", "ব্যাখ্যা", "কেন হয়েছে", "মূল কারণ", "ঘটনাক্রম"
    }
    
    # Story keywords that suggest continuing narratives
    STORY_INDICATORS = {
        # Politics & Government
        "election", "campaign", "parliament", "government", "minister", "prime minister", "president",
        "নির্বাচন", "প্রচারণা", "সংসদ", "সরকার", "মন্ত্রী", "প্রধানমন্ত্রী", "রাষ্ট্রপতি",
        
        # Economy & Markets  
        "economy", "inflation", "gdp", "budget", "stock market", "currency", "trade",
        "অর্থনীতি", "মুদ্রাস্ফীতি", "জিডিপি", "বাজেট", "শেয়ার বাজার", "মুদ্রা", "বাণিজ্য",
        
        # International Relations
        "diplomatic", "treaty", "summit", "visit", "relations", "border", "dispute",
        "কূটনৈতিক", "চুক্তি", "শীর্ষ বৈঠক", "সফর", "সম্পর্ক", "সীমান্ত", "বিরোধ",
        
        # Legal & Justice
        "court", "trial", "case", "verdict", "investigation", "charges", "lawsuit",
        "আদালত", "বিচার", "মামলা", "রায়", "তদন্ত", "অভিযোগ", "মোকদ্দমা",
        
        # Crisis & Disasters
        "crisis", "disaster", "flood", "cyclone", "fire", "accident", "rescue",
        "সংকট", "দুর্যোগ", "বন্যা", "ঘূর্ণিঝড়", "আগুন", "দুর্ঘটনা", "উদ্ধার"
    }
    
    def __init__(self):
        # Compile regex patterns for efficiency
        self.immediate_pattern = self._compile_keyword_pattern(self.IMMEDIATE_KEYWORDS)
        self.weekly_pattern = self._compile_keyword_pattern(self.WEEKLY_KEYWORDS)
        self.background_pattern = self._compile_keyword_pattern(self.BACKGROUND_KEYWORDS)
        self.story_pattern = self._compile_keyword_pattern(self.STORY_INDICATORS)
    
    def _compile_keyword_pattern(self, keywords: set) -> re.Pattern:
        """Compile keywords into a single regex pattern."""
        # Sort by length (longest first) to avoid partial matches
        sorted_keywords = sorted(keywords, key=len, reverse=True)
        # Escape special regex characters and create word boundaries
        escaped = [re.escape(kw) for kw in sorted_keywords]
        pattern = r'\b(?:' + '|'.join(escaped) + r')\b'
        return re.compile(pattern, re.IGNORECASE)
    
    def analyze_time_window(self, query: str, user_provided_window: Optional[int] = None) -> Dict[str, any]:
        """
        Analyze query to determine optimal time window.
        
        Returns:
        {
            'window_hours': int,
            'reasoning': str,
            'is_immediate': bool,
            'needs_background': bool,
            'story_detected': bool
        }
        """
        query_lower = query.lower().strip()
        
        # If user explicitly provided window, respect it but still analyze for other flags
        if user_provided_window is not None:
            return {
                'window_hours': user_provided_window,
                'reasoning': 'user_specified',
                'is_immediate': bool(self.immediate_pattern.search(query)),
                'needs_background': bool(self.background_pattern.search(query)),
                'story_detected': bool(self.story_pattern.search(query))
            }
        
        # Check for immediate/breaking news requests (24h)
        if self.immediate_pattern.search(query):
            return {
                'window_hours': 24,
                'reasoning': 'immediate_keywords_detected',
                'is_immediate': True,
                'needs_background': False,
                'story_detected': bool(self.story_pattern.search(query))
            }
        
        # Check for background/context requests (30 days for background + 24h for recent)
        if self.background_pattern.search(query):
            return {
                'window_hours': 720,  # 30 days
                'reasoning': 'background_context_requested',
                'is_immediate': False,
                'needs_background': True,
                'story_detected': bool(self.story_pattern.search(query))
            }
        
        # Check for weekly summary requests (7 days)  
        if self.weekly_pattern.search(query):
            return {
                'window_hours': 168,  # 7 days
                'reasoning': 'weekly_summary_detected',
                'is_immediate': False,
                'needs_background': False,
                'story_detected': bool(self.story_pattern.search(query))
            }
        
        # Default: General news queries (7 days)
        return {
            'window_hours': 168,  # 7 days
            'reasoning': 'default_general_news',
            'is_immediate': False,
            'needs_background': False,
            'story_detected': bool(self.story_pattern.search(query))
        }
    
    def generate_story_id(self, query: str, evidence: List[Dict]) -> Optional[str]:
        """
        Generate a story cluster ID for continuing narratives.
        Uses key entities and topics to create consistent identifiers.
        """
        if not evidence:
            return None
        
        # Extract key terms from query and evidence
        key_terms = set()
        
        # Add significant words from query (filter out common words)
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
            "by", "from", "as", "is", "was", "are", "were", "be", "been", "have", "has", "had",
            "do", "does", "did", "will", "would", "could", "should", "may", "might", "can",
            "what", "when", "where", "who", "why", "how", "this", "that", "these", "those",
            "এ", "এই", "ও", "তে", "এর", "করে", "হয়", "হয়েছে", "আছে", "ছিল", "থেকে", "জন্য"
        }
        
        query_words = [word.lower() for word in re.findall(r'\b\w+\b', query) if len(word) > 3]
        key_terms.update([word for word in query_words if word not in stop_words])
        
        # Extract key terms from article titles
        for item in evidence[:3]:  # Use top 3 articles
            title = item.get('title', '')
            title_words = [word.lower() for word in re.findall(r'\b\w+\b', title) if len(word) > 3]
            key_terms.update([word for word in title_words if word not in stop_words])
        
        if not key_terms:
            return None
        
        # Create stable ID from sorted key terms
        sorted_terms = sorted(list(key_terms))[:5]  # Max 5 terms for ID
        story_id = "_".join(sorted_terms)
        
        # Clean and truncate
        story_id = re.sub(r'[^a-z0-9_]', '', story_id.lower())
        return story_id[:50]  # Max 50 characters
    
    def should_use_region_filter(self, query: str) -> bool:
        """Determine if regional filtering (BD) should be applied."""
        
        # Bangladesh-specific indicators
        bd_indicators = {
            "bangladesh", "dhaka", "chittagong", "sylhet", "rajshahi", "khulna", "barisal", "rangpur",
            "বাংলাদেশ", "ঢাকা", "চট্টগ্রাম", "সিলেট", "রাজশাহী", "খুলনা", "বরিশাল", "রংপুর",
            "taka", "bdt", "hasina", "khaleda", "awami league", "bnp", "jatiya party",
            "টাকা", "হাসিনা", "খালেদা", "আওয়ামী লীগ", "বিএনপি", "জাতীয় পার্টি"
        }
        
        # Global topic indicators (don't use region filter)
        global_indicators = {
            "usa", "america", "china", "russia", "europe", "fifa", "olympics", "un", "who",
            "আমেরিকা", "চীন", "রাশিয়া", "ইউরোপ", "ফিফা", "অলিম্পিক", "জাতিসংঘ"
        }
        
        query_lower = query.lower()
        
        # Check for global indicators first
        if any(indicator in query_lower for indicator in global_indicators):
            return False
        
        # Check for Bangladesh indicators
        if any(indicator in query_lower for indicator in bd_indicators):
            return True
        
        # Default: Use region filter for general queries
        return True


# Create singleton instance
window_analyzer = WindowAnalyzer()


def analyze_query_window(query: str, user_window: Optional[int] = None) -> Dict[str, any]:
    """Convenience function for query window analysis."""
    return window_analyzer.analyze_time_window(query, user_window)


def get_story_id(query: str, evidence: List[Dict]) -> Optional[str]:
    """Convenience function for story ID generation."""
    return window_analyzer.generate_story_id(query, evidence)


def should_filter_by_region(query: str) -> bool:
    """Convenience function for region filtering decision."""
    return window_analyzer.should_use_region_filter(query)