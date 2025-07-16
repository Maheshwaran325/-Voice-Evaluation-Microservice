from typing import List, Dict, Any
from config import Config

class PronunciationAnalyzer:
    def __init__(self):
        self.threshold = Config.PRONUNCIATION_THRESHOLD
    
    def analyze_pronunciation(self, words: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze pronunciation based on confidence scores"""
        if not words:
            return {
                "pronunciation_score": 0,
                "mispronounced_words": []
            }
        
        # Calculate average confidence
        total_confidence = sum(word["confidence"] for word in words)
        avg_confidence = total_confidence / len(words)
        pronunciation_score = round(avg_confidence * 100)
        
        # Find mispronounced words
        mispronounced_words = []
        for word in words:
            if word["confidence"] < self.threshold:
                mispronounced_words.append({
                    "word": word["word"],
                    "start": word["start"],
                    "confidence": word["confidence"]
                })
        
        return {
            "pronunciation_score": pronunciation_score,
            "mispronounced_words": mispronounced_words
        }
