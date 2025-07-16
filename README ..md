
# Voice Evaluation Microservice

## Project Description
The Voice Evaluation Microservice is a Python-based application built with FastAPI and Celery that processes audio files to provide comprehensive voice analysis. It leverages external APIs like AssemblyAI for transcription and Google Gemini API for generating detailed feedback. The service offers functionalities such as transcription, pronunciation analysis, pacing analysis, and pause analysis, culminating in a natural language feedback report. Audio processing is handled asynchronously using Celery background tasks to ensure responsiveness.

## Features
-   **Audio Transcription:** Utilizes AssemblyAI to accurately transcribe spoken content from audio files.
-   **Pronunciation Analysis:** Evaluates the pronunciation of words, identifying mispronounced words and providing a score.
-   **Pacing Analysis:** Assesses the speaking rate (words per minute) and categorizes it as slow, optimal, or fast.
-   **Pause Analysis:** Identifies and quantifies pauses within the speech.
-   **Intelligent Feedback Generation:** Generates comprehensive text-based feedback using Google Gemini API based on the analysis results (pronunciation, pacing, pauses).
-   **Asynchronous Processing:** Employs Celery for background audio processing, preventing timeouts and enhancing user experience.
-   **RESTful API:** Provides clear API endpoints for audio uploads, task status checks, and health monitoring.
-   **Web Interface (Basic):** Includes a simple `index.html` for easy file uploads and result display.
-   **Robust Error Handling:** Includes mechanisms for file validation, API errors, and graceful handling of background task failures.

## Technologies Used
-   **FastAPI:** For building the asynchronous API endpoints.
-   **Celery:** For managing and executing background tasks (audio processing).
-   **Redis:** (Configurable) As the message broker and result backend for Celery.
-   **AssemblyAI API:** For high-accuracy audio transcription.
-   **Google Gemini API:** For generating AI-powered feedback.
-   **Python-dotenv:** For managing environment variables.
-   **HTTPX:** For making asynchronous HTTP requests.

## Setup & Run Instructions

### Prerequisites
-   Python 3.9+
-   Redis (or another Celery-compatible broker/backend like RabbitMQ)
-   An AssemblyAI API Key
-   A Google Gemini API Key

### 1. Clone the repository
```bash
git clone <your-repository-url>
cd VoiceTTS
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Variables
Create a `.env` file in the root directory of the project and add the following environment variables:

```
ASSEMBLYAI_API_KEY="YOUR_ASSEMBLYAI_API_KEY"
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
CELERY_BROKER_URL="redis://localhost:6379/0" # Or your Redis/RabbitMQ URL
CELERY_RESULT_BACKEND="redis://localhost:6379/0" # Or your Redis/RabbitMQ URL
```
Replace `"YOUR_ASSEMBLYAI_API_KEY"` and `"YOUR_GEMINI_API_KEY"` with your actual API keys. The Celery URLs should point to your Redis or other message broker instances.

### 5. Run the Application

#### a. Start the Redis Server
Ensure your Redis server is running. If you're running it locally, you might start it via:
```bash
redis-server
```

#### b. Start the Celery Worker
In a new terminal, from the project root, start the Celery worker:
```bash
celery -A main.celery_app worker --loglevel=info
```
or
```bash
celery -A main.celery_app worker --loglevel=info -P solo
```

#### c. Start the FastAPI Application
In another terminal, from the project root, start the FastAPI application using Uvicorn:
```bash
uvicorn main:app --reload --port 8000
```
The API will be accessible at `http://localhost:8000`.

## Usage

### Through the Web Interface
Open `index.html` in your web browser (you can simply open the file directly or serve it with a simple HTTP server).
1.  Click "Choose File" and select an audio file (`.wav` or `.mp3`).
2.  Click "Upload and Evaluate".
3.  The page will display the processing status and then the final JSON response from the API.

### Via API Endpoints (e.g., using Postman, curl, or your own client)

#### 1. Upload and Transcribe Audio
-   **Endpoint:** `POST /transcribe`
-   **Description:** Receives an audio file, saves it, and enqueues it for background processing. Returns a `task_id`.
-   **Request:** `multipart/form-data` with a file named `file`.
-   **Example (using `curl`):**
    ```bash
    curl -X POST "http://localhost:8000/transcribe" \
         -H "accept: application/json" \
         -H "Content-Type: multipart/form-data" \
         -F "file=@/path/to/your/audio.wav;type=audio/wav"
    ```
-   **Response (Success):**
    ```json
    {
      "message": "Processing started",
      "task_id": "your-celery-task-id"
    }
    ```
-   **Response (Error):**
    ```json
    {
      "detail": "Unsupported file format. Allowed: ['.wav', '.mp3']"
    }
    ```

#### 2. Check Task Status
-   **Endpoint:** `GET /status/{task_id}`
-   **Description:** Checks the current status of an audio processing task using its `task_id`.
-   **Example (using `curl`):**
    ```bash
    curl -X GET "http://localhost:8000/status/your-celery-task-id" \
         -H "accept: application/json"
    ```
-   **Response Examples:**
    -   **Pending:**
        ```json
        {
          "status": "PENDING",
          "message": "Task is pending or not found"
        }
        ```
    -   **Success:**
        ```json
        {
          "status": "SUCCESS",
          "result": {
            "transcription": {
              // ... transcription details ...
            },
            "pronunciation": {
              // ... pronunciation analysis ...
            },
            "pacing": {
              // ... pacing analysis ...
            },
            "pauses": {
              // ... pause analysis ...
            },
            "text_feedback": "..."
          }
        }
        ```
    -   **Failure:**
        ```json
        {
          "status": "FAILURE",
          "message": "Error message from the task",
          "traceback": "..."
        }
        ```

#### 3. Health Checks
-   **Endpoint:** `GET /health`
-   **Description:** Checks if the FastAPI application is running.
-   **Response:**
    ```json
    {
      "status": "healthy",
      "message": "Voice Evaluation Microservice is running"
    }
    ```
-   **Endpoint:** `GET /health/assemblyai`
-   **Description:** Checks connectivity and API key validity with AssemblyAI.
-   **Response Examples:**
    ```json
    {
      "status": "healthy",
      "message": "AssemblyAI is reachable"
    }
    ```
    ```json
    {
      "status": "error",
      "message": "Invalid API key"
    }
    ```

#### 4. Test API Key
-   **Endpoint:** `GET /test-api-key`
-   **Description:** A simple endpoint to test the validity of the AssemblyAI API key configured in `config.py`.

## Sample Audio Files Used
The `uploads/` directory contains sample audio files that can be used for testing the service. These are:
- `20095e63-db5b-40ac-a1fc-e3e79d0eec40.mp3`
- `5132ae46-fd2c-4d53-899a-dfeae3e553d0.mp3`
- `d481457b-9c83-4881-9fee-635df5f83402.mp3`
- `sample.mp3`
- `sample.wav`


## Assumptions and Notes
-   This project assumes you have a running Redis instance for Celery to function correctly.
-   Ensure your AssemblyAI and Google Gemini API keys are correctly configured in the `.env` file.
-   The `uploads/` directory is used for temporary storage of audio files. These files are removed after processing by the Celery task.
-   The `index.html` provides a basic web interface for demonstration purposes. For a production environment, you would typically build a more robust frontend application.
-   The `config.py` file contains thresholds for pronunciation, pacing, and pause analysis, which can be adjusted to suit specific requirements.

## Project Structure

```
VoiceTTS/
├── config.py             # Configuration settings and environment variables
├── main.py               # Main FastAPI application, API endpoints, and Celery task definition
├── services/             # Directory containing modular analysis services
│   ├── __init__.py
│   ├── feedback_generator.py # Generates feedback using Gemini API
│   ├── pacing.py             # Analyzes speaking pace
│   ├── pause_analysis.py     # Analyzes pauses in speech
│   ├── pronunciation.py      # Analyzes pronunciation
│   └── transcription.py      # Handles AssemblyAI transcription
├── uploads/              # Directory for temporary storage of uploaded audio files
├── .env                  # Environment variables (create this file)
├── requirements.txt      # Python dependencies (if generated)
└── venv/                 # Python virtual environment
```
