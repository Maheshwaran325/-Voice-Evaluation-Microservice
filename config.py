from dotenv import load_dotenv
import os

load_dotenv()

# Configuration class for the application
class Config:
    ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
    
    if ASSEMBLYAI_API_KEY is None:
        raise ValueError("ASSEMBLYAI_API_KEY environment variable is required")

    # Network configuration
    UPLOAD_TIMEOUT = 150  # 5 minutes
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # Base delay for exponential backoff
    
    # File size limits
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB (AssemblyAI limit)

    # Configuration settings
    UPLOAD_DIR = "uploads"
    ALLOWED_EXTENSIONS = {".wav", ".mp3"}
    
    # Analysis thresholds
    PRONUNCIATION_THRESHOLD = 0.85
    SLOW_WPM_THRESHOLD = 90
    FAST_WPM_THRESHOLD = 150
    PAUSE_THRESHOLD = 0.5  # seconds

    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

       # Gemini API Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    if GEMINI_API_KEY is None:
        raise ValueError("GEMINI_API_KEY environment variable is required for feedback generation")
