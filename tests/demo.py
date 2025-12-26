"""
Comprehensive demo script showing pipeline in action with detailed logging
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from app.models import TranscriptInput
from app.pipeline import TranscriptProcessor


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.END}\n")


def print_section(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.CYAN}{'-' * len(text)}{Colors.END}")


def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


async def run_demo():
    """Run comprehensive demo of the pipeline"""
    
    print_header("AidMi Transcript-to-Note Pipeline Demo")
    
    # Load sample transcript
    print_section("1. Loading Sample Transcript")
    
    try:
        with open('data/sample_transcript.json', 'r') as f:
            transcript_data = json.load(f)
        
        transcript = TranscriptInput(**transcript_data)
        
        print_success(f"Loaded transcript: {transcript.session_id}")
        print_info(f"Patient ID: {transcript.patient_id}")
        print_info(f"Clinician role: {transcript.clinician_role}")
        print_info(f"Session date: {transcript.session_date}")
        print_info(f"Duration: {transcript.duration_minutes} minutes")
        print_info(f"Total segments: {len(transcript.segments)}")
        
        # Show sample segments
        print("\n  Sample segments:")
        for i, seg in enumerate(transcript.segments[:3]):
            time_str = f"{seg.start_ms//1000//60:02d}:{seg.start_ms//1000%60:02d}"
            print(f"    [{time_str}] {Colors.BOLD}{seg.speaker}{Colors.END}: {seg.text[:60]}...")
        print(f"    ... ({len(transcript.segments) - 3} more segments)")
        
    except FileNotFoundError:
        print_warning("sample_transcript.json not found!")
        return
    except Exception as e:
        print_warning(f"Error loading transcript: {e}")
        return
    
    # Initialize processor
    print_section("2. Initializing Pipeline")
    
    # Check API key before creating processor
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print_warning("OpenAI API key not configured!")
        print_info("Please set OPENAI_API_KEY in your .env file")
        print_info("Example: echo 'OPENAI_API_KEY=sk-...' > .env")
        return
    
    print_success(f"API key loaded: {api_key[:15]}...")
    
    processor = TranscriptProcessor()
    
    print_success("Processor initialized")
    print_info(f"Chat model: {processor.chat_model}")
    print_info(f"Embedding model: {processor.embedding_model}")
    print_info(f"Citation threshold: {processor.citation_threshold}")
    
    # Process transcript
    print_section("3. Processing Transcript")
    
    print_info("Step 1: Embedding transcript segments...")
    start_time = datetime.now()
    
    try:
        result = await processor.process_transcript(transcript)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print_success(f"Processing complete! ({duration:.2f}s)")
        
    except Exception as e:
        print_warning(f"Error processing transcript: {e}")
        return
    
    # Display results
    print_section("4. Generated SOAP Note with Citations")
    
    sections = {'subjective': [], 'objective': [], 'assessment': [], 'plan': []}
    
    for span in result.note_spans:
        sections[span.section].append(span)
    
    section_names = {
        'subjective': 'SUBJECTIVE (Patient Reports)',
        'objective': 'OBJECTIVE (Clinical Observations)',
        'assessment': 'ASSESSMENT (Clinical Analysis)',
        'plan': 'PLAN (Treatment Recommendations)'
    }
    
    for section_key, section_title in section_names.items():
        spans = sections[section_key]
        if spans:
            print(f"\n{Colors.BOLD}{section_title}{Colors.END}")
            print(f"{'-' * 80}")
            
            for span in spans:
                print(f"\n{span.text}")
                
                if span.citations:
                    confidence_color = Colors.GREEN if span.confidence_score >= 0.80 else Colors.YELLOW
                    citation_ids = ', '.join([c.id for c in span.citations])
                    print(f"  {confidence_color}└─ Citations: {citation_ids}{Colors.END}", end='')
                    print(f" {confidence_color}(confidence: {span.confidence_score:.2f}){Colors.END}")
                    
                    # Show cited segment preview with citation numbers
                    for citation in span.citations[:2]:  # Show first 2 citations
                        preview = citation.transcript[:60] + "..." if len(citation.transcript) > 60 else citation.transcript
                        print(f"     {Colors.CYAN}↳ [{citation.num}] {citation.id}: \"{preview}\"{Colors.END}")
                
                if span.needs_confirmation:
                    print(f"  {Colors.RED}└─ ⚠️  NEEDS CONFIRMATION (no strong transcript support){Colors.END}")
    
    # Statistics
    print_section("5. Quality Metrics")
    
    total_spans = len(result.note_spans)
    with_citations = sum(1 for span in result.note_spans if span.citations)
    needs_confirmation = sum(1 for span in result.note_spans if span.needs_confirmation)
    avg_confidence = sum(span.confidence_score or 0 for span in result.note_spans) / total_spans
    avg_citations_per_span = sum(len(span.citations) for span in result.note_spans) / total_spans
    
    print_info(f"Total statements: {total_spans}")
    print_info(f"With citations: {with_citations} ({with_citations/total_spans*100:.1f}%)")
    print_info(f"Needs confirmation: {needs_confirmation} ({needs_confirmation/total_spans*100:.1f}%)")
    print_info(f"Average confidence: {avg_confidence:.2f}")
    print_info(f"Average citations per statement: {avg_citations_per_span:.1f}")
    
    # Token usage
    if 'token_usage' in result.metadata:
        print_section("6. Token Usage & Cost Estimate")
        
        tokens = result.metadata['token_usage']
        total_tokens = tokens.get('total_tokens', 0)
        
        print_info(f"Prompt tokens: {tokens.get('prompt_tokens', 0):,}")
        print_info(f"Completion tokens: {tokens.get('completion_tokens', 0):,}")
        print_info(f"Embedding tokens: {tokens.get('embedding_tokens', 0):,}")
        print_info(f"Total tokens: {total_tokens:,}")
        
        # Cost estimate (approximate)
        # gpt-4o-mini: $0.15 per 1M input tokens, $0.60 per 1M output tokens
        # text-embedding-3-small: $0.02 per 1M tokens
        prompt_cost = tokens.get('prompt_tokens', 0) * 0.15 / 1_000_000
        completion_cost = tokens.get('completion_tokens', 0) * 0.60 / 1_000_000
        embedding_cost = tokens.get('embedding_tokens', 0) * 0.02 / 1_000_000
        total_cost = prompt_cost + completion_cost + embedding_cost
        
        print_info(f"Estimated cost: ${total_cost:.4f}")
    
    # Save output
    print_section("7. Saving Output")
    
    output_path = f'output_demo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    with open(output_path, 'w') as f:
        json.dump(result.model_dump(), f, indent=2)
    
    print_success(f"Full output saved to: {output_path}")
    
    # Show citation distribution
    print_section("8. Citation Analysis")
    
    print("\nCitation confidence distribution:")
    confidence_ranges = {
        '0.90-1.00 (Excellent)': 0,
        '0.80-0.89 (Very Good)': 0,
        '0.70-0.79 (Good)': 0,
        '0.60-0.69 (Fair)': 0,
        '0.00-0.59 (Weak)': 0
    }
    
    for span in result.note_spans:
        score = span.confidence_score or 0
        if score >= 0.90:
            confidence_ranges['0.90-1.00 (Excellent)'] += 1
        elif score >= 0.80:
            confidence_ranges['0.80-0.89 (Very Good)'] += 1
        elif score >= 0.70:
            confidence_ranges['0.70-0.79 (Good)'] += 1
        elif score >= 0.60:
            confidence_ranges['0.60-0.69 (Fair)'] += 1
        else:
            confidence_ranges['0.00-0.59 (Weak)'] += 1
    
    for range_name, count in confidence_ranges.items():
        bar_length = int(count * 40 / total_spans) if total_spans > 0 else 0
        bar = '█' * bar_length
        print(f"  {range_name:20} {bar} {count}")
    
    # Final summary
    print_header("Demo Complete!")
    
    print(f"\n{Colors.GREEN}✓ Successfully processed {len(transcript.segments)} segments")
    print(f"✓ Generated {total_spans} clinical statements")
    print(f"✓ Average confidence score: {avg_confidence:.2f}")
    print(f"✓ Processing time: {duration:.2f}s{Colors.END}\n")
    
    print(f"{Colors.CYAN}Next steps:{Colors.END}")
    print(f"  1. Review output file: {output_path}")
    print(f"  2. Try the API: python main.py (then python test_api_client.py)")
    print(f"  3. Read documentation: README.md and ARCHITECTURE.md")
    print(f"  4. Adjust threshold in .env if needed\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
