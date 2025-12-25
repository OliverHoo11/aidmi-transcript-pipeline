"""
Pydantic models for API input/output validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class TranscriptSegment(BaseModel):
    """Individual segment of a therapy session transcript"""
    id: str = Field(..., description="Unique segment identifier")
    speaker: str = Field(..., description="Speaker role: 'clinician' or 'patient'")
    start_ms: int = Field(..., description="Start time in milliseconds")
    end_ms: int = Field(..., description="End time in milliseconds")
    text: str = Field(..., description="Transcript text for this segment")


class TranscriptInput(BaseModel):
    """Input format for therapy session transcript"""
    session_id: str = Field(..., description="Unique session identifier")
    patient_id: str = Field(..., description="Patient identifier")
    clinician_role: Optional[str] = Field(default="therapist", description="Role of clinician")
    session_date: Optional[str] = Field(default=None, description="Date of session")
    duration_minutes: Optional[int] = Field(default=None, description="Session duration")
    segments: List[TranscriptSegment] = Field(..., description="List of transcript segments")


class Citation(BaseModel):
    """Individual citation with segment reference"""
    id: str = Field(..., description="Segment ID (e.g., 'seg_002')")
    num: int = Field(..., description="Citation number for inline reference (e.g., [1])")
    transcript: str = Field(..., description="Full transcript text from this segment")


class NoteSpan(BaseModel):
    """Individual span/sentence in the SOAP note with citations"""
    id: str = Field(..., description="Unique span identifier")
    section: str = Field(..., description="SOAP section: subjective, objective, assessment, or plan")
    text: str = Field(..., description="The actual note text with inline citation numbers [1][2]")
    citations: List[Citation] = Field(default_factory=list, description="List of citations with full transcript")
    needs_confirmation: bool = Field(default=False, description="True if claim lacks transcript support")
    confidence_score: Optional[float] = Field(default=None, description="Confidence score for citations (0-1)")


class SOAPNoteOutput(BaseModel):
    """Output format with structured SOAP note and citations"""
    session_id: str = Field(..., description="Session identifier from input")
    note_spans: List[NoteSpan] = Field(..., description="List of note spans with citations")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata about generation")
