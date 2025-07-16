from pydantic import BaseModel
from typing import List, Optional

class WordMetadata(BaseModel):
    word: str
    start: float
    end: float
    confidence: float

class TranscriptionResponse(BaseModel):
    transcript: str
    words: List[WordMetadata]
    audio_duration_sec: float

class MispronuncedWord(BaseModel):
    word: str
    start: float
    confidence: float

class PronunciationResponse(BaseModel):
    pronunciation_score: int
    mispronounced_words: List[MispronuncedWord]

class PacingResponse(BaseModel):
    pacing_wpm: int
    pacing_feedback: str

class PauseResponse(BaseModel):
    pause_count: int
    total_pause_time_sec: float
    pause_feedback: str

class VoiceEvaluationResponse(BaseModel):
    transcription: TranscriptionResponse
    pronunciation: PronunciationResponse
    pacing: PacingResponse
    pauses: PauseResponse
    text_feedback: str
