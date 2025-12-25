"""
AidMi Transcript-to-SOAP-Note Pipeline
Main FastAPI application with hybrid RAG citation extraction
FIXED: Proper environment variable loading
"""

import os
from dotenv import load_dotenv

# CRITICAL: Load environment variables FIRST, before any other imports
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from typing import List, Dict, Optional
import logging

from models import TranscriptInput, SOAPNoteOutput, NoteSpan
from pipeline import TranscriptProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AidMi Transcript-to-Note API",
    description="Transform therapy session transcripts into structured SOAP notes with citations",
    version="1.0.0"
)

# Initialize processor (will be created once on startup)
processor: Optional[TranscriptProcessor] = None


@app.on_event("startup")
async def startup_event():
    """Initialize the transcript processor on startup"""
    global processor
    logger.info("Initializing Transcript Processor...")
    
    # Verify API key is loaded
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        logger.info(f"✓ OpenAI API key found: {api_key[:15]}...")
    else:
        logger.error("✗ OPENAI_API_KEY not found in environment!")
        logger.error("Please check your .env file")
    
    processor = TranscriptProcessor()
    logger.info(f"Processor ready! OpenAI configured: {processor.openai_configured}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AidMi Transcript-to-Note Pipeline",
        "version": "1.0.0"
    }


@app.post("/generate-note", response_model=SOAPNoteOutput)
async def generate_note(transcript: TranscriptInput):
    """
    Generate a structured SOAP note with citations from a therapy session transcript.
    
    Args:
        transcript: TranscriptInput object containing session_id, patient_id, and segments
        
    Returns:
        SOAPNoteOutput with structured note spans including citations
    """
    try:
        logger.info(f"Processing transcript: {transcript.session_id}")
        
        # Validate input
        if not transcript.segments or len(transcript.segments) == 0:
            raise HTTPException(status_code=400, detail="Transcript must contain at least one segment")
        
        # Process transcript through pipeline
        result = await processor.process_transcript(transcript)
        
        logger.info(f"Successfully generated note for session: {transcript.session_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing transcript {transcript.session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate note: {str(e)}")


@app.get("/health")
async def health_check():
    """Detailed health check"""
    api_key = os.getenv("OPENAI_API_KEY")
    return {
        "status": "healthy",
        "processor_initialized": processor is not None,
        "openai_configured": processor.openai_configured if processor else False,
        "env_file_exists": os.path.exists(".env"),
        "api_key_present": api_key is not None and len(api_key) > 0
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
