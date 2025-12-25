"""
Standalone test - bypasses FastAPI server completely
"""

import asyncio
import json
import os
from dotenv import load_dotenv

# Load environment first
load_dotenv()

print("=" * 80)
print("STANDALONE PIPELINE TEST")
print("=" * 80)

# Check API key
api_key = os.getenv("OPENAI_API_KEY")
print(f"\n1. API Key Check:")
if api_key:
    print(f"   ✓ API key found: {api_key[:15]}...")
else:
    print(f"   ✗ API key NOT found!")
    print(f"   Please make sure .env file exists with OPENAI_API_KEY=sk-...")
    exit(1)

# Import after loading env
from models import TranscriptInput
from pipeline import TranscriptProcessor

# Load transcript
print(f"\n2. Loading transcript...")
with open('sample_transcript.json', 'r') as f:
    transcript_data = json.load(f)

transcript = TranscriptInput(**transcript_data)
print(f"   ✓ Loaded {len(transcript.segments)} segments")

# Process
async def test():
    print(f"\n3. Initializing processor...")
    processor = TranscriptProcessor()
    
    print(f"\n4. Processing transcript...")
    print(f"   (This will take ~3-5 seconds)")
    
    try:
        result = await processor.process_transcript(transcript)
        
        print(f"\n✓ SUCCESS!")
        print(f"\n5. Results:")
        print(f"   Total statements: {len(result.note_spans)}")
        
        # Show a few examples
        print(f"\n   Sample outputs:")
        for i, span in enumerate(result.note_spans[:3]):
            print(f"\n   [{span.section.upper()}]")
            print(f"   {span.text}")
            if span.citations:
                print(f"   Citations: {', '.join(span.citations)} (confidence: {span.confidence_score:.2f})")
        
        # Save output
        output_file = 'output_standalone_test.json'
        with open(output_file, 'w') as f:
            json.dump(result.model_dump(), f, indent=2)
        
        print(f"\n   Full output saved to: {output_file}")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

print(f"\n" + "=" * 80)
asyncio.run(test())
print("=" * 80)