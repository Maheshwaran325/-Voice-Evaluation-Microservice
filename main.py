import asyncio
import os
import uuid
import mimetypes
import logging
import httpx
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from celery import Celery, Task

from config import Config
from models import VoiceEvaluationResponse
from services.transcription import TranscriptionService
from services.pronunciation import PronunciationAnalyzer
from services.pacing import PacingAnalyzer
from services.pause_analysis import PauseAnalyzer
from services.feedback_generator import FeedbackGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(title="Voice Evaluation Microservice", version="1.0.0")

# Initialize Celery
celery_app = Celery(
    "voice_evaluation",
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND
)

# Initialize services (these will be used by the Celery task)
transcription_service = TranscriptionService()
pronunciation_analyzer = PronunciationAnalyzer()
pacing_analyzer = PacingAnalyzer()
pause_analyzer = PauseAnalyzer()
feedback_generator = FeedbackGenerator()

# Create upload directory
os.makedirs(Config.UPLOAD_DIR, exist_ok=True)

class ContextTask(Task):
    """
    Celery task that automatically pushes a FastAPI app context.
    This is useful if your services rely on FastAPI's dependency injection
    or other app-specific contexts. For this specific case, it might not
    be strictly necessary as services are initialized globally, but it's
    good practice for more complex apps.
    """
    def __call__(self, *args, **kwargs):
        # You might need to adjust this depending on how your services
        # are truly instantiated and if they require any FastAPI app context.
        # For now, we'll just call the original run method.
        return self.run(*args, **kwargs)

celery_app.Task = ContextTask

# Define the Celery task for audio processing
@celery_app.task(name="process_audio_task")
def process_audio_task(file_path: str, file_name: str, mime_type: str) -> dict:
    """
    Celery task to handle the actual audio transcription and evaluation.
    This runs in a separate worker process.
    """
    request_id = str(uuid.uuid4())[:8]
    logging.info(f"[{request_id}] Starting background processing for file: {file_name}")

    try:
        # Upload to AssemblyAI
        upload_url = asyncio.run(transcription_service.upload_file_with_retry(file_path, mime_type))
        
        # Transcribe audio
        transcription_result = asyncio.run(transcription_service.transcribe_audio(upload_url))
        parsed_result = transcription_service.parse_transcription_result(transcription_result)
        
        # Analyze pronunciation
        pronunciation_result = pronunciation_analyzer.analyze_pronunciation(parsed_result["words"])
        
        # Analyze pacing
        pacing_result = pacing_analyzer.analyze_pacing(
            parsed_result["words"], 
            parsed_result["audio_duration_sec"]
        )
        
        # Analyze pauses
        pause_result = pause_analyzer.analyze_pauses(parsed_result["words"])
        
        # Generate feedback
        text_feedback = feedback_generator.generate_feedback(
            pronunciation_result, 
            pacing_result, 
            pause_result
        )
        
        # Prepare response
        response_data = VoiceEvaluationResponse(
            transcription=parsed_result,
            pronunciation=pronunciation_result,
            pacing=pacing_result,
            pauses=pause_result,
            text_feedback=text_feedback
        ).model_dump() # Use model_dump() for Pydantic v2+ to convert to dict
        
        logging.info(f"[{request_id}] Finished background processing for file: {file_name}")
        return response_data
            
    except Exception as e:
        logging.error(f"[{request_id}] Background processing error for {file_name}: {str(e)}")
        # Re-raise the exception or return an error state if you want to capture it in Celery result backend
        raise
    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/transcribe", response_model=dict) # Response model changed to dict for task_id
async def transcribe_and_evaluate(file: UploadFile = File(...)):
    """
    Receives audio file, saves it, and enqueues processing as a background task.
    Returns a task ID.
    """
    request_id = str(uuid.uuid4())[:8]
    logging.info(f"[{request_id}] Received request for file: {file.filename}")
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in Config.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Allowed: {Config.ALLOWED_EXTENSIONS}"
            )
        
        # Save uploaded file
        file_id = str(uuid.uuid4())
        file_path = f"{Config.UPLOAD_DIR}/{file_id}{file_extension}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            if len(content) == 0:
                raise HTTPException(status_code=400, detail="Empty file")
            if len(content) > Config.MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="File too large")
            buffer.write(content)
        
        # Improved MIME type validation
        VALID_MIME_TYPES = ["audio/wav", "audio/mpeg", "audio/x-wav"]
        mime_type, _ = mimetypes.guess_type(file.filename)

        if not mime_type or mime_type not in VALID_MIME_TYPES:
            # Clean up the file if MIME type is invalid
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=400, detail="Invalid or unsupported audio format")

        # Enqueue the task
        task = process_audio_task.delay(file_path, file.filename, mime_type)
        
        logging.info(f"[{request_id}] Enqueued task {task.id} for file: {file.filename}")
        return {"message": "Processing started", "task_id": task.id}
            
    except HTTPException as e:
        # Propagate known HTTP exceptions
        raise e
    except Exception as e:
        logging.error(f"[{request_id}] Error enqueuing task: {str(e)}") 
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(e)}")

@app.get("/status/{task_id}", response_model=dict)
async def get_task_status(task_id: str):
    """
    Check the status of a background processing task.
    """
    task = celery_app.AsyncResult(task_id)
    
    if task.state == "PENDING":
        response = {
            "status": "PENDING",
            "message": "Task is pending or not found"
        }
    elif task.state == "PROGRESS":
        response = {
            "status": "PROGRESS",
            "message": "Task is in progress",
            "info": task.info # Can include progress updates from the task
        }
    elif task.state == "SUCCESS":
        response = {
            "status": "SUCCESS",
            "result": task.result
        }
    elif task.state == "FAILURE":
        response = {
            "status": "FAILURE",
            "message": str(task.info), # task.info contains the exception
            "traceback": task.traceback
        }
    else:
        response = {
            "status": task.state,
            "message": "Unknown state"
        }
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Voice Evaluation Microservice is running"}

@app.get("/health/assemblyai")
async def assemblyai_health_check():
    """Check AssemblyAI service connectivity"""
    try:
        headers = {"authorization": Config.ASSEMBLYAI_API_KEY}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.assemblyai.com/v2/transcript",
                headers=headers
            )
            
            if response.status_code == 401:
                return {"status": "error", "message": "Invalid API key"}
            elif response.status_code == 429:
                return {"status": "warning", "message": "Rate limited"}
            elif response.status_code in [200, 404]: 
                return {"status": "healthy", "message": "AssemblyAI is reachable"}
            else:
                return {"status": "error", "message": f"Unexpected status: {response.status_code}"}
                
    except httpx.ReadError:
        return {"status": "error", "message": "Network connectivity issue"}
    except httpx.TimeoutException:
        return {"status": "error", "message": "Connection timeout"}
    except Exception as e:
        return {"status": "error", "message": f"Health check failed: {str(e)}"}


# Add this test endpoint to your main.py
@app.get("/test-api-key")
async def test_api_key():
    """Test AssemblyAI API key validity"""
    headers = {"authorization": f"Bearer {Config.ASSEMBLYAI_API_KEY}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.assemblyai.com/v2/transcript",
            headers=headers
        )
        
        return {
            "status_code": response.status_code,
            "valid": response.status_code != 401,
            "message": "API key is valid" if response.status_code != 401 else "Invalid API key"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)