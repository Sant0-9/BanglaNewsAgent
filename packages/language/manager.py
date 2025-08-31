"""
Multi-level Language State Management

Handles language preferences at three levels:
1. Global preference (default in settings)
2. Per-conversation override (sticky for that thread)  
3. Per-message override (detected or explicit)
"""
import re
from typing import Dict, Optional, Literal, Tuple
from dataclasses import dataclass
from enum import Enum


class LanguageLevel(Enum):
    GLOBAL = "global"
    CONVERSATION = "conversation" 
    MESSAGE = "message"


@dataclass
class LanguageState:
    """Complete language state for a request"""
    ui_language: Literal['bn', 'en']
    input_language: Optional[Literal['bn', 'en']] = None
    output_language: Literal['bn', 'en'] = None
    retrieval_preference: Literal['bn', 'en'] = None
    source_level: LanguageLevel = LanguageLevel.GLOBAL
    
    def __post_init__(self):
        if self.output_language is None:
            self.output_language = self.ui_language
        if self.retrieval_preference is None:
            self.retrieval_preference = self.ui_language


class LanguageManager:
    """Manages language state at multiple levels"""
    
    def __init__(self, default_global_lang: str = "bn"):
        self.global_language = default_global_lang
        # Per-conversation language overrides
        self.conversation_languages: Dict[str, str] = {}
        # Language detection patterns
        self.bn_patterns = [
            r'[\u0980-\u09FF]',  # Bengali Unicode block
            r'(কী|কি|কে|কোন|কেন|কীভাবে|কোথায়|কখন)',  # Common Bengali question words
        ]
        self.en_patterns = [
            r'[a-zA-Z]{3,}',  # Words with 3+ Latin letters
            r'\b(what|who|where|when|why|how|the|and|is|are|was|were)\b',  # Common English words
        ]
    
    def detect_language(self, text: str) -> Optional[Literal['bn', 'en']]:
        """Detect language of input text"""
        if not text or len(text.strip()) < 2:
            return None
            
        text = text.strip()
        
        # Check for Bengali patterns
        bn_matches = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in self.bn_patterns)
        # Check for English patterns  
        en_matches = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in self.en_patterns)
        
        # Simple heuristic: more matches wins
        if bn_matches > en_matches and bn_matches > 0:
            return 'bn'
        elif en_matches > bn_matches and en_matches > 0:
            return 'en'
        
        # If inconclusive, check character composition
        bn_chars = len(re.findall(r'[\u0980-\u09FF]', text))
        latin_chars = len(re.findall(r'[a-zA-Z]', text))
        total_chars = len(re.sub(r'\s+', '', text))
        
        if total_chars > 0:
            bn_ratio = bn_chars / total_chars
            latin_ratio = latin_chars / total_chars
            
            if bn_ratio > 0.3:  # 30% Bengali characters
                return 'bn'
            elif latin_ratio > 0.5:  # 50% Latin characters
                return 'en'
        
        return None
    
    def get_language_state(
        self,
        conversation_id: Optional[str] = None,
        explicit_lang: Optional[str] = None,
        input_text: Optional[str] = None,
        detect_input: bool = True
    ) -> LanguageState:
        """
        Determine complete language state for a request
        
        Priority order:
        1. Explicit per-message override
        2. Per-conversation override  
        3. Global default
        """
        
        # Start with global default
        current_lang = self.global_language
        source_level = LanguageLevel.GLOBAL
        
        # Check for conversation-level override
        if conversation_id and conversation_id in self.conversation_languages:
            current_lang = self.conversation_languages[conversation_id]
            source_level = LanguageLevel.CONVERSATION
        
        # Check for explicit message-level override
        if explicit_lang and explicit_lang in ['bn', 'en']:
            current_lang = explicit_lang
            source_level = LanguageLevel.MESSAGE
        
        # Detect input language if requested
        input_language = None
        if detect_input and input_text:
            input_language = self.detect_language(input_text)
        
        return LanguageState(
            ui_language=current_lang,
            input_language=input_language,
            output_language=current_lang,
            retrieval_preference=current_lang,
            source_level=source_level
        )
    
    def set_global_language(self, language: Literal['bn', 'en']):
        """Set global default language"""
        self.global_language = language
    
    def set_conversation_language(self, conversation_id: str, language: Literal['bn', 'en']):
        """Set language override for specific conversation"""
        self.conversation_languages[conversation_id] = language
    
    def toggle_conversation_language(self, conversation_id: str) -> Literal['bn', 'en']:
        """Toggle language for a conversation (BN↔EN)"""
        current = self.conversation_languages.get(conversation_id, self.global_language)
        new_lang = 'en' if current == 'bn' else 'bn'
        self.conversation_languages[conversation_id] = new_lang
        return new_lang
    
    def clear_conversation_language(self, conversation_id: str):
        """Remove language override for conversation (fall back to global)"""
        self.conversation_languages.pop(conversation_id, None)
    
    def get_retrieval_tags(self, language_state: LanguageState) -> Tuple[str, Optional[str]]:
        """
        Get language tags for content retrieval
        
        Returns:
            (preferred_lang, fallback_lang)
        """
        preferred = language_state.retrieval_preference
        fallback = 'en' if preferred == 'bn' else 'bn'
        return preferred, fallback
    
    def should_translate_input(self, language_state: LanguageState, index_language: str = "en") -> bool:
        """
        Determine if input should be translated for indexing
        
        Args:
            language_state: Current language state
            index_language: Language used for the search index
        """
        if not language_state.input_language:
            return False
            
        # Translate if input language differs from index language
        return language_state.input_language != index_language
    
    def should_translate_output(self, language_state: LanguageState, content_language: str) -> bool:
        """
        Determine if output should be translated
        
        Args:
            language_state: Current language state  
            content_language: Language of the retrieved content
        """
        return content_language != language_state.output_language
    
    def get_ui_strings(self, language: str) -> Dict[str, str]:
        """Get UI strings for the specified language"""
        ui_strings = {
            'bn': {
                'searching': 'খোঁজা হচ্ছে...',
                'generating': 'উত্তর তৈরি হচ্ছে...',
                'error': 'সেবায় সাময়িক সমস্যা হয়েছে।',
                'no_results': 'কোন তথ্য পাওয়া যায়নি।',
                'regenerate': 'আবার তৈরি করুন',
                'toggle_language': 'ভাষা পরিবর্তন করুন',
                'language_toggled': 'ভাষা পরিবর্তন হয়েছে',
            },
            'en': {
                'searching': 'Searching...',
                'generating': 'Generating answer...',
                'error': 'Service temporarily unavailable.',
                'no_results': 'No information found.',
                'regenerate': 'Regenerate',
                'toggle_language': 'Toggle Language',
                'language_toggled': 'Language toggled',
            }
        }
        
        return ui_strings.get(language, ui_strings['en'])
    
    def cleanup_old_conversations(self, conversation_ids_to_keep: set):
        """Remove language overrides for conversations that no longer exist"""
        to_remove = []
        for conv_id in self.conversation_languages:
            if conv_id not in conversation_ids_to_keep:
                to_remove.append(conv_id)
        
        for conv_id in to_remove:
            del self.conversation_languages[conv_id]
        
        return len(to_remove)


# Global language manager instance
language_manager = LanguageManager(default_global_lang="bn")