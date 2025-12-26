"""
Diagnostic script to check why citations are so low
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import asyncio
import json
import os
from dotenv import load_dotenv
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

from app.models import TranscriptInput
from app.pipeline import TranscriptProcessor

async def diagnose():
    print("=" * 80)
    print("CITATION DIAGNOSTIC")
    print("=" * 80)
    
    # Load transcript
    with open('data/sample_transcript.json', 'r') as f:
        transcript_data = json.load(f)
    
    transcript = TranscriptInput(**transcript_data)
    processor = TranscriptProcessor()
    
    # Initialize the client
    processor._ensure_client()
    
    print(f"\nCurrent threshold: {processor.citation_threshold}")
    print(f"Embedding model: {processor.embedding_model}")
    
    # Get embeddings
    print(f"\nEmbedding {len(transcript.segments)} segments...")
    segment_embeddings = await processor._embed_segments(transcript.segments)
    
    # Generate note
    print(f"Generating SOAP note...")
    soap_note = await processor._generate_soap_note(transcript)
    statements = processor._parse_soap_note(soap_note)
    
    print(f"\nGenerated {len(statements)} statements")
    print(f"\nChecking similarity scores for each statement:\n")
    
    # Embed statements
    statement_texts = [s['text'] for s in statements]
    statement_embeddings = await processor._embed_texts(statement_texts)
    
    # For each statement, show top 3 matches
    for idx, (statement, stmt_embedding) in enumerate(zip(statements, statement_embeddings)):
        print(f"\n{idx+1}. [{statement['section'].upper()}]")
        print(f"   Statement: {statement['text'][:80]}...")
        
        # Calculate similarities
        similarities = cosine_similarity(
            stmt_embedding.reshape(1, -1),
            segment_embeddings
        )[0]
        
        # Get top 3
        top_3_indices = np.argsort(similarities)[-3:][::-1]
        top_3_scores = similarities[top_3_indices]
        
        print(f"\n   Top 3 matching segments:")
        for seg_idx, score in zip(top_3_indices, top_3_scores):
            seg = transcript.segments[seg_idx]
            indicator = "✓" if score >= processor.citation_threshold else "✗"
            print(f"   {indicator} {seg.id}: {score:.3f} - {seg.text[:60]}...")
        
        if top_3_scores[0] < processor.citation_threshold:
            print(f"   ⚠️  Best match ({top_3_scores[0]:.3f}) is below threshold ({processor.citation_threshold})")
    
    # Statistics
    print("\n" + "=" * 80)
    print("SIMILARITY STATISTICS")
    print("=" * 80)
    
    all_max_scores = []
    for stmt_embedding in statement_embeddings:
        similarities = cosine_similarity(
            stmt_embedding.reshape(1, -1),
            segment_embeddings
        )[0]
        all_max_scores.append(similarities.max())
    
    all_max_scores = np.array(all_max_scores)
    
    print(f"\nMax similarity scores distribution:")
    print(f"  Mean: {all_max_scores.mean():.3f}")
    print(f"  Median: {np.median(all_max_scores):.3f}")
    print(f"  Min: {all_max_scores.min():.3f}")
    print(f"  Max: {all_max_scores.max():.3f}")
    print(f"\nScores above threshold (0.70): {(all_max_scores >= 0.70).sum()}/{len(all_max_scores)}")
    print(f"Scores above 0.65: {(all_max_scores >= 0.65).sum()}/{len(all_max_scores)}")
    print(f"Scores above 0.60: {(all_max_scores >= 0.60).sum()}/{len(all_max_scores)}")
    print(f"Scores above 0.55: {(all_max_scores >= 0.55).sum()}/{len(all_max_scores)}")
    
    print(f"\nRECOMMENDATION:")
    if all_max_scores.mean() < 0.60:
        print(f"  ⚠️  Average similarity is very low ({all_max_scores.mean():.3f})")
        print(f"  The SOAP note language may be too different from transcript")
        print(f"  Recommended threshold: 0.50-0.55")
    elif all_max_scores.mean() < 0.65:
        print(f"  Average similarity is moderate ({all_max_scores.mean():.3f})")
        print(f"  Recommended threshold: 0.55-0.60")
    else:
        print(f"  Average similarity is good ({all_max_scores.mean():.3f})")
        print(f"  Current threshold (0.70) might be appropriate")

if __name__ == "__main__":
    asyncio.run(diagnose())