import json
import logging
from typing import List, Tuple
import google.generativeai as genai
from app.core.config import settings
from app.services.gemini.reset_api_key import APIKeyManager

logger = logging.getLogger(__name__)


class QueryAugmentor:
    """Use Gemini to generate augmented queries for video search"""
    
    def __init__(self):
        if not settings.GEMINI_API_KEYS:
            raise ValueError("GEMINI_API_KEYS must be set in ENV")
        
        self.key_manager = APIKeyManager("settings.GEMINI_API_KEYS")
        self.model_name = "gemini-2.0-flash-lite"
    
    def _get_client(self):
        """Get Gemini client with next available API key"""
        api_key = self.key_manager.get_next_key()
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(self.model_name)
    
    def augment_query(self, original_query: str) -> Tuple[str, str]:
        """
        Generate 2 augmented queries from original query.
        Returns: (query1, query2)
        Falls back to original query if generation fails.
        """
        if not original_query or not original_query.strip():
            logger.warning("[QUERY AUG] Empty query, returning original")
            return (original_query, original_query)
        
        prompt = f"""Generate 2 alternative search queries for video retrieval based on this original query.
The alternative queries should:
1. Use different wording but maintain the same semantic meaning
2. Be suitable for video search (describe visual content, actions, objects, scenes)
3. Be concise (5-15 words each)

Original query: "{original_query}"

Return ONLY a JSON object in this exact format:
{{"q1": "first alternative query", "q2": "second alternative query"}}

Do not include any explanation or additional text."""

        try:
            model = self._get_client()
            response = model.generate_content(prompt)
            
            # Parse JSON from response
            text = response.text.strip()
            
            # Remove markdown code blocks if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            result = json.loads(text)
            q1 = result.get("q1", original_query).strip()
            q2 = result.get("q2", original_query).strip()
            
            logger.info(f"[QUERY AUG] Original: '{original_query}'")
            logger.info(f"[QUERY AUG] Q1: '{q1}'")
            logger.info(f"[QUERY AUG] Q2: '{q2}'")
            
            return (q1, q2)
            
        except json.JSONDecodeError as e:
            logger.error(f"[QUERY AUG] JSON parse error: {e}, response: {response.text if 'response' in locals() else 'N/A'}")
            return (original_query, original_query)
            
        except Exception as e:
            logger.error(f"[QUERY AUG] Generation failed: {e}")
            return (original_query, original_query)


# Singleton instance
_augmentor_instance = None


def get_query_augmentor() -> QueryAugmentor:
    """Get singleton query augmentor instance"""
    global _augmentor_instance
    if _augmentor_instance is None:
        _augmentor_instance = QueryAugmentor()
    return _augmentor_instance
