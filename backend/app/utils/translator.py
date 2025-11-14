import re
import logging
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)


class VietnameseTranslator:
    """Utility to detect and translate Vietnamese text to English"""
    
    # Vietnamese character pattern
    VIETNAMESE_PATTERN = re.compile(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', re.IGNORECASE)
    
    def __init__(self):
        self.translator = GoogleTranslator(source='vi', target='en')
    
    def is_vietnamese(self, text: str) -> bool:
        """Check if text contains Vietnamese characters"""
        if not text:
            return False
        return bool(self.VIETNAMESE_PATTERN.search(text))
    
    def translate(self, text: str) -> str:
        """
        Translate Vietnamese text to English.
        Returns original text if not Vietnamese or translation fails.
        """
        if not text or not text.strip():
            return text
        
        # Check if Vietnamese
        if not self.is_vietnamese(text):
            logger.info(f"[TRANSLATE] Text is not Vietnamese, skip: '{text}'")
            return text
        
        try:
            translated = self.translator.translate(text.strip())
            logger.info(f"[TRANSLATE] Vietnamese → English: '{text}' → '{translated}'")
            return translated
        except Exception as e:
            logger.warning(f"[TRANSLATE] Translation failed: {e}, using original text")
            return text


# Singleton instance
_translator_instance = None


def get_translator() -> VietnameseTranslator:
    """Get singleton translator instance"""
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = VietnameseTranslator()
    return _translator_instance
