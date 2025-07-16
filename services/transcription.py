import asyncio
import httpx
import logging
from typing import Dict, Any
from config import Config
import os
import time

class TranscriptionService:
    def __init__(self):
        self.api_key = Config.ASSEMBLYAI_API_KEY
        self.base_url = "https://api.assemblyai.com/v2"
        self.max_retries = 3
        self.audio_mime_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".flac": "audio/flac",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
        }
        

    async def upload_file_with_retry(self, file_path: str, mime_type: str) -> str:
        """Upload file with retry logic for network errors"""
        for attempt in range(self.max_retries):
            try:
                return await self.upload_file(file_path, mime_type)
            except httpx.ReadError as e:
                if attempt == self.max_retries - 1:
                    raise Exception(f"File upload failed after {self.max_retries} attempts: {str(e)}")
                
                wait_time = 2 ** attempt
                logging.warning(f"Upload attempt {attempt + 1} failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            except Exception as e:
                raise e
        
    async def upload_file(self, file_path: str, mime_type: str) -> str:
        """Upload audio file to AssemblyAI with enhanced error handling"""
        if not self.api_key:
            raise Exception("AssemblyAI API key not configured")
        
        headers = {"authorization": self.api_key}
        
        try:
            # Validate file exists and get size
            if not os.path.exists(file_path):
                raise Exception(f"File not found: {file_path}")
            
            file_size = os.path.getsize(file_path)
            logging.info(f"Uploading file: {file_path} ({file_size} bytes)")

            # Determine correct MIME type
            file_extension = os.path.splitext(file_path)[1].lower()
            effective_mime_type = self.audio_mime_types.get(file_extension, mime_type)
            if effective_mime_type != mime_type:
                logging.info(f"Overriding guessed MIME type {mime_type} with {effective_mime_type} for extension {file_extension}")
            
            # Create client with longer timeout and connection limits
            timeout = httpx.Timeout(
                connect=30.0,  
                read=120.0,    
                write=120.0,   
                pool=300.0     
            )
            
            limits = httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5
            )
            
            async with httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                follow_redirects=True
            ) as client:
                with open(file_path, "rb") as f:
                    files_payload = {"file": (os.path.basename(file_path), f, mime_type)}

                    response = await client.post(
                    f"{self.base_url}/upload",
                    files=files_payload, 
                    headers=headers
                    )

                    if response.status_code == 401:
                        raise Exception("Invalid AssemblyAI API key")
                    elif response.status_code == 413:
                        raise Exception("File too large for AssemblyAI")
                    elif response.status_code == 429:
                        raise Exception("Rate limit exceeded - please try again later")
                    elif response.status_code not in [200, 201]:
                        error_text = response.text if response.content else "Unknown error"
                        raise Exception(f"Upload failed: {response.status_code} - {error_text}")
                    
                    result = response.json()
                    upload_url = result.get("upload_url")
                    
                    if not upload_url:
                        raise Exception("No upload URL returned from AssemblyAI")
                    
                    logging.info(f"File uploaded successfully: {upload_url}")
                    return upload_url
                    
        except httpx.ReadError as e:
            logging.error(f"Network read error during upload: {e}")
            raise e  # Re-raise to trigger retry logic
        except httpx.TimeoutException as e:
            logging.error(f"Upload timeout: {e}")
            raise Exception("Upload timeout - try with a smaller file or check your connection")
        except Exception as e:
            logging.error(f"Error during file upload: {e}", exc_info=True)
            raise Exception(f"File upload error: {str(e)}")

    async def transcribe_audio(self, audio_url: str) -> Dict[str, Any]:
        """Submit audio for transcription and poll for the result."""
        if not self.api_key:
            raise Exception("AssemblyAI API key not configured")

        headers = {
            "authorization": self.api_key,
            "content-type": "application/json"
        }
        
        json_data = {"audio_url": audio_url}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Submit the transcription job
                response = await client.post(
                    f"{self.base_url}/transcript",
                    headers=headers,
                    json=json_data
                )
                
                if response.status_code != 200:
                    error_text = response.text if response.content else "Unknown error"
                    raise Exception(f"Failed to submit transcription job: {response.status_code} - {error_text}")

                transcript_id = response.json().get("id")
                if not transcript_id:
                    raise Exception("Failed to get transcript ID from submission response.")
                
                logging.info(f"Transcription job submitted successfully. Transcript ID: {transcript_id}")

                # Poll for the final result using the existing polling method
                return await self._poll_transcript(transcript_id, headers)

        except httpx.TimeoutException:
            raise Exception("Timeout when submitting transcription job.")
        except Exception as e:
            logging.error(f"Error during transcription submission or polling: {e}", exc_info=True)
            raise Exception(f"Transcription process failed: {str(e)}")

    async def _poll_transcript(self, transcript_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Poll transcript status with timeout protection"""
        max_attempts = 60  # Maximum 60 attempts (1 minute)
        attempt = 0
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while attempt < max_attempts:
                try:
                    response = await client.get(
                        f"{self.base_url}/transcript/{transcript_id}",
                        headers=headers
                    )
                    
                    if response.status_code != 200:
                        raise Exception(f"Polling failed: {response.status_code} - {response.text}")
                    
                    result = response.json()
                    status = result.get("status")
                    
                    if status == "completed":
                        return result
                    elif status == "error":
                        error_msg = result.get("error", "Unknown transcription error")
                        raise Exception(f"Transcription failed: {error_msg}")
                    elif status in ["queued", "processing"]:
                        await asyncio.sleep(1)
                        attempt += 1
                    else:
                        raise Exception(f"Unknown status: {status}")
                        
                except httpx.TimeoutException:
                    raise Exception("Polling timeout - transcription taking too long")
                except Exception as e:
                    if "Transcription failed:" in str(e):
                        raise e
                    raise Exception(f"Polling error: {str(e)}")
            
            raise Exception("Transcription timeout - process took too long")


    def parse_transcription_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AssemblyAI result into our format"""
        words = []
        for word_data in result.get("words", []):
            words.append({
                "word": word_data["text"],
                "start": word_data["start"] / 1000.0,  # Convert to seconds
                "end": word_data["end"] / 1000.0,
                "confidence": word_data["confidence"]
            })
        
        return {
            "transcript": result["text"],
            "words": words,
            "audio_duration_sec": result.get("audio_duration", 0) / 1000.0
        }
