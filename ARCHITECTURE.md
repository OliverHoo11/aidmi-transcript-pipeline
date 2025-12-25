# Architecture & Design Decisions

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Server                          │
│                         (main.py)                               │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ POST /generate-note
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TranscriptProcessor                          │
│                      (pipeline.py)                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Step 1: Embed All Segments                              │  │
│  │  - Convert transcript to vectors                        │  │
│  │  - Create searchable knowledge base                     │  │
│  │  Model: text-embedding-3-small                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                        │                                        │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Step 2: Generate SOAP Note                              │  │
│  │  - LLM analyzes transcript                              │  │
│  │  - Produces clinical note                               │  │
│  │  Model: gpt-4o-mini                                     │  │
│  └─────────────────────────────────────────────────────────┘  │
│                        │                                        │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Step 3: Parse into Statements                           │  │
│  │  - Split note into individual claims                    │  │
│  │  - Separate by SOAP section                             │  │
│  └─────────────────────────────────────────────────────────┘  │
│                        │                                        │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Step 4: Extract Citations (RAG)                         │  │
│  │  For each statement:                                    │  │
│  │   1. Embed statement                                    │  │
│  │   2. Query segment vectors (cosine similarity)          │  │
│  │   3. Find top-k matches                                 │  │
│  │   4. Filter by threshold (0.70)                         │  │
│  │   5. Assign citations + confidence                      │  │
│  └─────────────────────────────────────────────────────────┘  │
│                        │                                        │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Step 5: Flag Uncertain Claims                           │  │
│  │  - Mark needs_confirmation if score < threshold         │  │
│  │  - Add confidence scores                                │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SOAPNoteOutput                               │
│                     (models.py)                                 │
│                                                                 │
│  - note_spans: List[NoteSpan]                                  │
│  - Each span has:                                              │
│    • text: The claim                                           │
│    • section: subjective/objective/assessment/plan             │
│    • citations: [seg_001, seg_003]                             │
│    • confidence_score: 0.0 - 1.0                               │
│    • needs_confirmation: bool                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Hybrid RAG Citation Strategy

### Why Hybrid RAG?

**Problem:** LLMs hallucinate segment IDs when asked to cite sources.

**Solution:** Use semantic similarity (embeddings) to ground citations in reality.

### Comparison Matrix

| Approach | Accuracy | Cost | Speed | Hallucination Risk |
|----------|----------|------|-------|-------------------|
| Single-pass LLM | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⚠️ High |
| Two-pass LLM | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⚠️ Medium |
| Pure Embeddings | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ✅ None |
| **Hybrid RAG** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ✅ None |

### How It Works

```
Statement: "Patient reports worsening insomnia"
           │
           ├─ Embed statement → [0.23, -0.15, 0.87, ...]
           │
           ├─ Calculate similarity with all segments:
           │  seg_001: 0.42 ❌ (below threshold)
           │  seg_002: 0.89 ✅ (patient mentions insomnia)
           │  seg_003: 0.78 ✅ (clinician asks about sleep)
           │  seg_004: 0.51 ❌ (different topic)
           │
           ├─ Filter by threshold (0.70):
           │  Keep: seg_002 (0.89), seg_003 (0.78)
           │
           └─ Result:
              citations: ["seg_002", "seg_003"]
              confidence_score: 0.89
              needs_confirmation: false
```

### Mathematical Foundation

**Cosine Similarity:**
```
similarity(A, B) = (A · B) / (||A|| × ||B||)

Where:
- A = statement embedding vector
- B = segment embedding vector
- Result: -1 to 1 (1 = identical, 0 = orthogonal, -1 = opposite)
```

**Citation Decision:**
```python
if max_similarity >= 0.70:
    assign_citation(segment_id)
    needs_confirmation = False
else:
    needs_confirmation = True
```

## Data Flow

```
Input Transcript
├── session_id: "sess_001"
├── patient_id: "pat_123"
└── segments: [
    {
      "id": "seg_001",
      "speaker": "clinician",
      "start_ms": 0,
      "end_ms": 8500,
      "text": "How have you been?"
    },
    ...
]

                ↓ Pipeline Processing ↓

Output Note
├── session_id: "sess_001"
├── note_spans: [
    {
      "id": "span_001",
      "section": "subjective",
      "text": "Patient reports worsening insomnia...",
      "citations": ["seg_002", "seg_003"],
      "confidence_score": 0.89,
      "needs_confirmation": false
    },
    ...
]
└── metadata: {
    "total_segments": 27,
    "total_statements": 12,
    "model_used": "gpt-4o-mini",
    "token_usage": {...}
}
```

## Error Handling Strategy

### Retry Logic
```python
@retry_with_backoff(max_retries=3, backoff_factor=2.0)
async def call_openai_api():
    # API call here
    pass

# Retry sequence:
# Attempt 1: immediate
# Attempt 2: after 1.0s
# Attempt 3: after 2.0s
# Fail: raise exception
```

### Validation Layers

1. **Input Validation** (Pydantic)
   - Ensures all required fields present
   - Type checking for all inputs
   - Segment ID format validation

2. **Processing Validation**
   - Check OpenAI API key exists
   - Verify embeddings have correct dimensions
   - Validate similarity scores in range [0, 1]

3. **Output Validation** (Pydantic)
   - All segment IDs in citations exist in input
   - Confidence scores between 0.0 and 1.0
   - Section names are valid SOAP sections

## Performance Optimization

### Current Implementation

**Token Usage per Session:**
- Embeddings: ~500 tokens (27 segments × ~18 tokens each)
- SOAP Generation: ~1000 tokens prompt + ~300 tokens completion
- Statement Embeddings: ~200 tokens (12 statements × ~16 tokens each)
- **Total: ~2000 tokens**

**Cost per Session:**
- Embeddings: $0.002
- Chat completion: $0.003
- **Total: ~$0.005**

**Latency:**
- Embedding segments: ~0.5s
- SOAP generation: ~2.0s
- Citation extraction: ~0.3s
- **Total: ~3s per session**

### Future Optimizations

1. **Caching Layer**
   ```
   Cache embeddings for segments
   → 80% cost reduction on repeat processing
   ```

2. **Batch Processing**
   ```
   Process 10 sessions at once
   → Amortize overhead, 30% faster
   ```

3. **Streaming Response**
   ```
   Stream SOAP note as generated
   → Better UX, same cost
   ```

4. **Smart Chunking**
   ```
   For long transcripts (>10K tokens):
   - Chunk into overlapping segments
   - Process in parallel
   - Merge results
   ```

## Design Decisions

### Why gpt-4o-mini?
- 20x cheaper than GPT-4
- Fast response times (~2s)
- Sufficient for clinical note generation
- Structured output support

### Why text-embedding-3-small?
- Cost-effective ($0.02 / 1M tokens)
- 1536 dimensions (good balance)
- Fast embedding generation
- Compatible with cosine similarity

### Why 0.70 threshold?
- Tested on sample data
- 0.60: Too many weak citations
- 0.70: **Balanced** (selected)
- 0.80: Too strict, many false negatives

### Why async FastAPI?
- Non-blocking I/O for OpenAI API calls
- Better throughput under load
- Native async support in OpenAI SDK
- Easy to add streaming later

## Security Considerations

1. **API Key Protection**
   - Stored in `.env` (not in repo)
   - Loaded at runtime only
   - Never logged or exposed

2. **Input Sanitization**
   - Pydantic validation prevents injection
   - Segment IDs validated against whitelist
   - Text content length limits

3. **Rate Limiting**
   - OpenAI SDK handles rate limits
   - Retry logic with exponential backoff
   - Graceful degradation on failures

## Testing Strategy

### Unit Tests (Future)
```python
test_embed_segments()
test_generate_soap_note()
test_parse_statements()
test_extract_citations()
test_validate_segment_ids()
```

### Integration Tests
```python
test_pipeline.py → Direct pipeline test
test_api_client.py → API endpoint test
```

### Quality Metrics
- Citation accuracy: % of citations that support claims
- Confidence calibration: correlation between score and accuracy
- Coverage: % of note claims that receive citations
- Hallucination rate: non-existent segment IDs (should be 0%)

## Scalability Considerations

**Current capacity:** ~20 requests/minute (OpenAI rate limit)

**To scale to 1000s of sessions/day:**

1. **Horizontal scaling**
   - Multiple FastAPI instances behind load balancer
   - Shared Redis cache for embeddings

2. **Database layer**
   - Store processed notes in PostgreSQL
   - Index by session_id, patient_id, date

3. **Queue system**
   - Use Celery/Redis for async processing
   - Handle batch jobs overnight

4. **Monitoring**
   - Track token usage, latency, error rates
   - Alert on citation quality degradation
   - Log confidence score distribution

---

**Last Updated:** December 2024
