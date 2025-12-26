"""
Core transcript processing pipeline with hybrid RAG citation extraction
FIXED VERSION: Lower default threshold (0.50) and working token tracking
"""

import os
import json
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from openai import AsyncOpenAI
import asyncio
from sklearn.metrics.pairwise import cosine_similarity

from app.models import TranscriptInput, SOAPNoteOutput, NoteSpan, TranscriptSegment, Citation
from app.utils import retry_with_backoff, validate_segment_ids, TokenCounter

logger = logging.getLogger(__name__)


class TranscriptProcessor:
    """Main processor for converting transcripts to SOAP notes with citations"""
    
    def __init__(self):
        """Initialize the processor with OpenAI client"""
        # Don't check for API key here - it will be loaded by main.py
        self.api_key = None
        self.client = None
        self.openai_configured = False
            
        # Configuration - Read from environment with better defaults
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.chat_model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
        # Default to 0.50 for good citation coverage (tested empirically)
        self.citation_threshold = float(os.getenv("CITATION_THRESHOLD", "0.50"))
        self.max_retries = 3
        
        # Token tracking
        self.token_counter = TokenCounter()
        
        logger.info(f"Initialized with threshold: {self.citation_threshold}")
    
    def _ensure_client(self):
        """Lazy initialization of OpenAI client"""
        if self.client is None:
            self.api_key = os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise Exception("OpenAI API key not configured")
            self.client = AsyncOpenAI(api_key=self.api_key)
            self.openai_configured = True
            logger.info("OpenAI client initialized")
        
    async def process_transcript(self, transcript: TranscriptInput) -> SOAPNoteOutput:
        """
        Main pipeline: transcript -> SOAP note with verified citations
        
        Steps:
        1. Embed all transcript segments
        2. Generate SOAP note using LLM
        3. Parse note into individual statements
        4. For each statement, find supporting segments using embeddings (RAG)
        5. Verify and score citations
        """
        # Initialize client on first use
        self._ensure_client()
        
        # Reset token counter for this session
        self.token_counter.reset()
        
        logger.info(f"Step 1: Embedding {len(transcript.segments)} transcript segments...")
        segment_embeddings = await self._embed_segments(transcript.segments)
        
        logger.info("Step 2: Generating SOAP note with LLM...")
        soap_note = await self._generate_soap_note(transcript)
        
        logger.info("Step 3: Parsing SOAP note into statements...")
        statements = self._parse_soap_note(soap_note)
        
        logger.info("Step 4: Extracting citations using RAG approach...")
        note_spans = await self._extract_citations_rag(
            statements, 
            transcript.segments, 
            segment_embeddings
        )
        
        logger.info("Step 5: Finalizing output...")
        
        # Get token summary
        token_summary = self.token_counter.get_summary()
        
        output = SOAPNoteOutput(
            session_id=transcript.session_id,
            note_spans=note_spans,
            metadata={
                "total_segments": len(transcript.segments),
                "total_statements": len(note_spans),
                "model_used": self.chat_model,
                "embedding_model": self.embedding_model,
                "citation_threshold": self.citation_threshold,
                "token_usage": token_summary
            }
        )
        
        return output
    
    async def _embed_segments(self, segments: List[TranscriptSegment]) -> np.ndarray:
        """
        Embed all transcript segments for semantic search
        
        Returns:
            numpy array of shape (n_segments, embedding_dim)
        """
        texts = [f"{seg.speaker}: {seg.text}" for seg in segments]
        
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            embeddings = np.array([item.embedding for item in response.data])
            
            # Track token usage
            if hasattr(response, 'usage') and response.usage:
                self.token_counter.add_embedding(response.usage.total_tokens)
            
            logger.info(f"Created embeddings with shape: {embeddings.shape}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error creating embeddings: {e}")
            raise
    
    async def _generate_soap_note(self, transcript: TranscriptInput) -> Dict:
        """
        Generate SOAP note using LLM with structured output
        
        Returns:
            Dict with keys: subjective, objective, assessment, plan
        """
        # Prepare transcript text
        transcript_text = self._format_transcript_for_llm(transcript.segments)
        
        # Create prompt for SOAP note generation
        system_prompt = """You are an expert clinical documentation assistant specializing in behavioral health.
Your task is to generate a professional SOAP note from a therapy session transcript.

SOAP Format:
- Subjective: Patient's reported experiences, feelings, and concerns in their own words
- Objective: Observable behaviors, affect, and clinical observations
- Assessment: Clinical interpretation, diagnosis considerations, progress evaluation
- Plan: Treatment interventions, homework, follow-up items

Guidelines:
- Be concise and clinically appropriate
- Use professional clinical language
- Focus on clinically relevant information
- Each section should be 2-4 sentences
- Stick to what's in the transcript - don't infer beyond what's stated
"""
        
        user_prompt = f"""Generate a SOAP note from this therapy session transcript:

{transcript_text}

Return ONLY a valid JSON object with this structure:
{{
  "subjective": "...",
  "objective": "...",
  "assessment": "...",
  "plan": "..."
}}"""
        
        try:
            # Use JSON mode for structured output
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # Lower temperature for consistency
                max_tokens=1000
            )
            
            # Track token usage
            if hasattr(response, 'usage') and response.usage:
                self.token_counter.add_completion(
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )
            
            soap_note = json.loads(response.choices[0].message.content)
            logger.info("Successfully generated SOAP note")
            return soap_note
            
        except Exception as e:
            logger.error(f"Error generating SOAP note: {e}")
            # Retry logic
            if hasattr(self, '_retry_count') and self._retry_count < self.max_retries:
                self._retry_count += 1
                logger.info(f"Retrying... ({self._retry_count}/{self.max_retries})")
                await asyncio.sleep(1)
                return await self._generate_soap_note(transcript)
            else:
                self._retry_count = 0
                raise
    
    def _parse_soap_note(self, soap_note: Dict) -> List[Dict]:
        """
        Parse SOAP note into individual statements
        
        Returns:
            List of dicts with keys: section, text
        """
        statements = []
        
        for section in ['subjective', 'objective', 'assessment', 'plan']:
            if section not in soap_note:
                continue
                
            text = soap_note[section]
            
            # Split into sentences (simple approach - can be improved)
            sentences = self._split_into_sentences(text)
            
            for sentence in sentences:
                if sentence.strip():
                    statements.append({
                        'section': section,
                        'text': sentence.strip()
                    })
        
        logger.info(f"Parsed {len(statements)} statements from SOAP note")
        return statements
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences (simple rule-based approach)
        """
        import re
        # Split on period, exclamation, question mark followed by space or end
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    async def _extract_citations_rag(
        self, 
        statements: List[Dict], 
        segments: List[TranscriptSegment],
        segment_embeddings: np.ndarray
    ) -> List[NoteSpan]:
        """
        Extract citations using RAG approach with embeddings
        Now includes inline citation numbers WITHIN the sentence text
        
        For each statement:
        1. Embed the statement
        2. Find top-k most similar segments using cosine similarity
        3. For each citation, find best matching phrase in statement
        4. Insert citation numbers inline: "text [1] more text [2]"
        5. Include full transcript text for each citation
        """
        note_spans = []
        
        # Embed all statements at once for efficiency
        statement_texts = [s['text'] for s in statements]
        statement_embeddings = await self._embed_texts(statement_texts)
        
        # GLOBAL citation counter - continues across all spans
        global_citation_num = 1
        
        # For each statement, find similar segments
        for idx, (statement, stmt_embedding) in enumerate(zip(statements, statement_embeddings)):
            # Calculate cosine similarity between statement and all segments
            similarities = cosine_similarity(
                stmt_embedding.reshape(1, -1),
                segment_embeddings
            )[0]
            
            # Get top-k most similar segments
            top_k = 3  # Consider top 3 segments
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            top_scores = similarities[top_indices]
            
            # Filter by threshold and collect citations
            citation_list = []
            max_score = 0.0
            
            for seg_idx, score in zip(top_indices, top_scores):
                if score >= self.citation_threshold:
                    segment = segments[seg_idx]
                    citation_list.append({
                        'id': segment.id,
                        'num': global_citation_num,  # Use global counter
                        'transcript': segment.text,
                        'score': float(score)
                    })
                    max_score = max(max_score, score)
                    global_citation_num += 1  # Increment global counter
            
            # Determine if needs confirmation
            needs_confirmation = len(citation_list) == 0 or max_score < self.citation_threshold
            
            # Add inline citation numbers within the sentence
            text_with_citations = await self._insert_inline_citations(
                statement['text'], 
                citation_list,
                segments
            )
            
            # Create Citation objects (without score)
            citations = [
                Citation(
                    id=c['id'],
                    num=c['num'],
                    transcript=c['transcript']
                )
                for c in citation_list
            ]
            
            # Create note span
            note_span = NoteSpan(
                id=f"span_{idx+1:03d}",
                section=statement['section'],
                text=text_with_citations,
                citations=citations,
                needs_confirmation=needs_confirmation,
                confidence_score=float(max_score) if citation_list else 0.0
            )
            
            note_spans.append(note_span)
            
            logger.debug(
                f"Statement: '{statement['text'][:50]}...' -> "
                f"Citations: {[c['id'] for c in citation_list]}, Score: {max_score:.3f}, "
                f"Needs confirmation: {needs_confirmation}"
            )
        
        return note_spans
    
    async def _insert_inline_citations(
        self,
        text: str,
        citation_list: List[Dict],
        segments: List[TranscriptSegment]
    ) -> str:
        """
        Insert citation numbers inline within the sentence based on semantic relevance
        
        Strategy:
        - Always try to distribute citations inline for maximum precision
        - Split statement into phrases (by comma, 'and', etc.)
        - Insert citations after relevant phrases
        - If single phrase, add at end
        """
        if not citation_list:
            return text
        
        # Try to distribute citations inline based on text structure
        import re
        
        # Split on: comma, semicolon, 'and', 'but', 'or'
        clauses = re.split(r'(,\s+|;\s+|\s+and\s+|\s+but\s+|\s+or\s+)', text)
        
        # Count substantive clauses (not separators)
        substantive_clauses = [c for i, c in enumerate(clauses) if i % 2 == 0 and c.strip()]
        
        # If we have multiple clauses, distribute citations inline
        if len(substantive_clauses) >= len(citation_list):
            result_parts = []
            citation_idx = 0
            
            for i, clause in enumerate(clauses):
                result_parts.append(clause)
                
                # Add citation after substantive clauses (even indices)
                if i % 2 == 0 and citation_idx < len(citation_list) and clause.strip():
                    result_parts.append(f"[{citation_list[citation_idx]['num']}]")
                    citation_idx += 1
            
            # Add any remaining citations at end
            while citation_idx < len(citation_list):
                result_parts.append(f"[{citation_list[citation_idx]['num']}]")
                citation_idx += 1
            
            return ''.join(result_parts)
        
        # Fallback: single clause or not enough phrases - add all at end
        citation_nums = ''.join([f"[{c['num']}]" for c in citation_list])
        return f"{text} {citation_nums}"

    
    async def _embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed a list of texts"""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            embeddings = np.array([item.embedding for item in response.data])
            
            # Track token usage
            if hasattr(response, 'usage') and response.usage:
                self.token_counter.add_embedding(response.usage.total_tokens)
            
            return embeddings
        except Exception as e:
            logger.error(f"Error embedding texts: {e}")
            raise
    
    def _format_transcript_for_llm(self, segments: List[TranscriptSegment]) -> str:
        """Format transcript segments into readable text for LLM"""
        lines = []
        for seg in segments:
            timestamp = self._format_timestamp(seg.start_ms)
            lines.append(f"[{timestamp}] {seg.speaker.upper()}: {seg.text}")
        return "\n".join(lines)
    
    def _format_timestamp(self, ms: int) -> str:
        """Convert milliseconds to MM:SS format"""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"