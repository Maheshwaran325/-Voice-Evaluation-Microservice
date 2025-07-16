from typing import Dict, Any
import google.generativeai as genai
from config import Config  # Import your Config class

class FeedbackGenerator:
    def __init__(self):
        # Configure the Gemini API with your key
        genai.configure(api_key=Config.GEMINI_API_KEY)
        # Initialize the generative model
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')  # You can choose other models like 'gemini-1.5-flash' if available and suitable

    def generate_feedback(self, 
                          pronunciation: Dict[str, Any], 
                          pacing: Dict[str, Any], 
                          pauses: Dict[str, Any]) -> str:
        """Generate comprehensive feedback summary using Gemini API"""
        
        # Helper function to safely format floats or return fallback
        def safe_format(value: Any, format_spec: str = '.2f', fallback: str = 'N/A') -> str:
            if isinstance(value, (int, float)):
                return f"{value:{format_spec}}"
            return str(value) if value is not None else fallback  # Convert to str safely

        # Prepare the input for the Gemini model
        prompt = f"""
        Generate detailed, constructive, and encouraging feedback for a speaker based on the following analysis of their audio.
        Focus on improving their public speaking skills.

        **Pronunciation Analysis:**
        - Mispronounced words: {pronunciation.get('mispronounced_words', 'None')}
        - Overall pronunciation score: {self._format_pronunciation_score(pronunciation.get('overall_pronunciation_score'))}

        **Pacing Analysis:**
        - Words per minute (WPM): {safe_format(pacing.get('pacing_wpm'), format_spec='', fallback='N/A')}  # No decimal for WPM, assuming integer
        - Pacing assessment: {pacing.get('pacing_assessment', 'N/A')}

        **Pause Analysis:**
        - Total pause duration: {safe_format(pauses.get('total_pause_duration_sec'), '.2f', 'N/A')} seconds
        - Average pause duration: {safe_format(pauses.get('average_pause_duration_sec'), '.2f', 'N/A')} seconds
        - Pause count: {safe_format(pauses.get('pause_count'), '', 'N/A')}  # Assuming integer, no decimal
        - Longest pause duration: {safe_format(pauses.get('longest_pause_duration_sec'), '.2f', 'N/A')} seconds

        **Instructions for Feedback:**
        1. Start with a positive encouraging statement.
        2. Provide specific feedback on pronunciation, pacing, and pauses.
        3. For pronunciation, list specific words if mispronounced and suggest ways to improve.
        4. For pacing, comment on the WPM and suggest if they need to speed up or slow down.
        5. For pauses, suggest reducing long pauses or using them effectively.
        6. End with a concluding encouraging remark.
        7. Keep the feedback concise but informative, around 3-5 sentences.
        """
        
        try:
            # Generate content using the Gemini model
            response = self.model.generate_content(prompt)
            # Access the generated text
            feedback = response.text
            return feedback
        except Exception as e:
            # Improved logging: Include more context for debugging
            print(f"Error generating feedback with Gemini API: {e}. Prompt data: pronunciation={pronunciation}, pacing={pacing}, pauses={pauses}")
            return "Could not generate detailed feedback at this moment. Please try again later."

    def _format_pronunciation_score(self, score: Any) -> str:
        """Helper method to safely format the pronunciation score."""
        if isinstance(score, (int, float)):
            return f"{score * 100:.2f}%"
        return "N/A"
