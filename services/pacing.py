from typing import List, Dict, Any
from config import Config

class PacingAnalyzer:
    def __init__(self):
        self.slow_threshold = Config.SLOW_WPM_THRESHOLD
        self.fast_threshold = Config.FAST_WPM_THRESHOLD
    
    def analyze_pacing(self, words: List[Dict[str, Any]], audio_duration: float) -> Dict[str, Any]:
        """Analyze speaking pace (WPM)"""
        if not words or audio_duration == 0:
            return {
                "pacing_wpm": 0,
                "pacing_feedback": "Unable to calculate pacing."
            }
        
        # Calculate WPM
        total_words = len(words)
        duration_minutes = audio_duration / 60.0
        wpm = round(total_words / duration_minutes)
        
        # Generate feedback
        if wpm < self.slow_threshold:
            feedback = "Your speaking pace is too slow. Try to speak a bit faster."
        elif wpm > self.fast_threshold:
            feedback = "Your speaking pace is too fast. Try to slow down a bit."
        else:
            feedback = "Your speaking pace is appropriate."
        
        return {
            "pacing_wpm": wpm,
            "pacing_feedback": feedback
        }
