from typing import List, Dict, Any
from config import Config

class PauseAnalyzer:
    def __init__(self):
        self.pause_threshold = Config.PAUSE_THRESHOLD
    
    def analyze_pauses(self, words: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze pause patterns between words"""
        if len(words) < 2:
            return {
                "pause_count": 0,
                "total_pause_time_sec": 0.0,
                "pause_feedback": "Insufficient data for pause analysis."
            }
        
        pauses = []
        for i in range(1, len(words)):
            pause_duration = words[i]["start"] - words[i-1]["end"]
            if pause_duration > self.pause_threshold:
                pauses.append(pause_duration)
        
        pause_count = len(pauses)
        total_pause_time = sum(pauses)
        
        # Generate feedback
        if pause_count == 0:
            feedback = "Great! Your speech flows smoothly without long pauses."
        elif pause_count <= 2:
            feedback = "Good fluency with minimal pauses."
        elif pause_count <= 4:
            feedback = "Try to reduce long pauses to improve fluency."
        else:
            feedback = "Your speech has many long pauses. Practice speaking more continuously."
        
        return {
            "pause_count": pause_count,
            "total_pause_time_sec": round(total_pause_time, 2),
            "pause_feedback": feedback
        }
