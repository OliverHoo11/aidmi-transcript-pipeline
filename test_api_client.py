"""
API Client test script
Tests the FastAPI endpoint
"""

import requests
import json
from pathlib import Path


def test_api():
    """Test the /generate-note API endpoint"""
    
    # API endpoint
    base_url = "http://localhost:8000"
    
    # Load sample transcript
    with open('sample_transcript.json', 'r') as f:
        transcript_data = json.load(f)
    
    print(f"Testing API at {base_url}")
    print(f"Session ID: {transcript_data['session_id']}")
    print("-" * 80)
    
    # Test health check first
    try:
        health_response = requests.get(f"{base_url}/health")
        health_response.raise_for_status()
        print("✓ Health check passed")
        print(f"  {health_response.json()}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return
    
    # Send POST request to generate note
    print("\nGenerating SOAP note...")
    try:
        response = requests.post(
            f"{base_url}/generate-note",
            json=transcript_data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        result = response.json()
        
        print("\n" + "=" * 80)
        print("API RESPONSE - SOAP NOTE WITH CITATIONS")
        print("=" * 80)
        
        # Display results
        sections = {'subjective': [], 'objective': [], 'assessment': [], 'plan': []}
        
        for span in result['note_spans']:
            sections[span['section']].append(span)
        
        for section_name, spans in sections.items():
            if spans:
                print(f"\n{section_name.upper()}:")
                print("-" * 80)
                for span in spans:
                    print(f"\n{span['text']}")
                    if span['citations']:
                        citation_ids = ', '.join([c['id'] for c in span['citations']])
                        print(f"  └─ Citations: {citation_ids} "
                              f"(confidence: {span.get('confidence_score', 0):.2f})")
                        # Show citation details
                        for citation in span['citations'][:2]:  # Show first 2
                            preview = citation['transcript'][:60] + "..." if len(citation['transcript']) > 60 else citation['transcript']
                            print(f"     ↳ [{citation['num']}] {citation['id']}: \"{preview}\"")
                    if span['needs_confirmation']:
                        print(f"  └─ ⚠️  NEEDS CONFIRMATION")
        
        # Save output
        output_path = 'output_api_test.json'
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        print("\n" + "=" * 80)
        print(f"Full response saved to: {output_path}")
        print("=" * 80)
        
        # Statistics
        metadata = result.get('metadata', {})
        print(f"\nMetadata:")
        print(f"  Model used: {metadata.get('model_used')}")
        print(f"  Total segments: {metadata.get('total_segments')}")
        print(f"  Total statements: {metadata.get('total_statements')}")
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ API request failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")


if __name__ == "__main__":
    test_api()
