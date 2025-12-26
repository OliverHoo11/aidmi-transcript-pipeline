"""
Test script to run the pipeline with sample transcript
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import asyncio
import json
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.models import TranscriptInput
from app.pipeline import TranscriptProcessor


async def test_pipeline():
    """Test the pipeline with sample transcript"""
    
    # Load sample transcript
    with open('data/sample_transcript.json', 'r') as f:
        transcript_data = json.load(f)
    
    # Parse into Pydantic model
    transcript = TranscriptInput(**transcript_data)
    
    print(f"Loaded transcript: {transcript.session_id}")
    print(f"Number of segments: {len(transcript.segments)}")
    print("-" * 80)
    
    # Initialize processor
    processor = TranscriptProcessor()
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not configured!")
        print("Please set your OpenAI API key in the .env file")
        return
    
    # Process transcript
    print("Processing transcript...")
    result = await processor.process_transcript(transcript)
    
    # Display results
    print("\n" + "=" * 80)
    print("GENERATED SOAP NOTE WITH CITATIONS")
    print("=" * 80)
    
    sections = {'subjective': [], 'objective': [], 'assessment': [], 'plan': []}
    
    # Group by section
    for span in result.note_spans:
        sections[span.section].append(span)
    
    # Display each section
    for section_name, spans in sections.items():
        if spans:
            print(f"\n{section_name.upper()}:")
            print("-" * 80)
            for span in spans:
                print(f"\n{span.text}")
                if span.citations:
                    citation_ids = ', '.join([c.id for c in span.citations])
                    print(f"  └─ Citations: {citation_ids} (confidence: {span.confidence_score:.2f})")
                    # Show citation details
                    for citation in span.citations[:2]:  # Show first 2
                        preview = citation.transcript[:60] + "..." if len(citation.transcript) > 60 else citation.transcript
                        print(f"     ↳ [{citation.num}] {citation.id}: \"{preview}\"")
                if span.needs_confirmation:
                    print(f"  └─ ⚠️  NEEDS CONFIRMATION (no strong transcript support)")
    
    # Save output
    output_path = 'output_sample.json'
    with open(output_path, 'w') as f:
        json.dump(result.model_dump(), f, indent=2)
    
    print("\n" + "=" * 80)
    print(f"Full output saved to: {output_path}")
    print("=" * 80)
    
    # Statistics
    total_spans = len(result.note_spans)
    needs_confirmation = sum(1 for span in result.note_spans if span.needs_confirmation)
    avg_confidence = sum(span.confidence_score or 0 for span in result.note_spans) / total_spans
    
    print(f"\nStatistics:")
    print(f"  Total statements: {total_spans}")
    print(f"  Needs confirmation: {needs_confirmation} ({needs_confirmation/total_spans*100:.1f}%)")
    print(f"  Average confidence: {avg_confidence:.2f}")


if __name__ == "__main__":
    asyncio.run(test_pipeline())
