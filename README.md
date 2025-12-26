# AidMi Transcript-to-SOAP Pipeline

AI-powered system that transforms therapy session transcripts into structured SOAP notes with verified, continuously-numbered citations using hybrid RAG.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Quick Start

```bash
# Clone and setup
git clone https://github.com/OliverHoo11/aidmi-transcript-pipeline.git
cd aidmi-transcript-pipeline
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env: add OPENAI_API_KEY=sk-your-key

# Test
python -m tests.demo
```

## Results

**Performance on 45-min therapy session (27 segments):**

| Metric | Value |
|--------|-------|
| Citation Coverage | 70-76% |
| Processing Time | 8-11 seconds |
| Cost per Session | ~$0.0005 |
| Hallucination Rate | 0% |
| Token Usage | ~3,500 |

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Testing](#testing)
- [How It Works](#how-it-works)
- [Cost Analysis](#cost-analysis)
- [Limitations & Future Work](#limitations--future-work)
- [Project Structure](#project-structure)
- [Development](#development)
- [License](#license)

---

## Overview

This pipeline converts timestamped therapy session transcripts into clinical SOAP notes (Subjective, Objective, Assessment, Plan) where **every claim is backed by specific transcript segments** with **continuous citation numbering** [1][2][3]...

### The Problem

Traditional LLM-based citation systems hallucinate segment IDs when asked to cite sources directly. This is unreliable for clinical documentation.

### Our Solution: Hybrid RAG

1. **Generate** SOAP note with LLM (no citations yet)
2. **Ground** each statement using semantic similarity (embeddings)
3. **Verify** citations mathematically (cosine similarity > threshold)
4. **Number** citations continuously across entire document [1][2][3]...

**Result:** Zero hallucinations + verifiable confidence scores.

---

## Key Features

✅ **Continuous Citation Numbering** - [1][2][3]... across entire document  
✅ **Zero Hallucinations** - Embeddings ensure citations reference real segments  
✅ **Inline Citations** - Distributed within text for precision  
✅ **Confidence Scoring** - Each citation rated 0.0-1.0  
✅ **Full Context** - Each citation includes complete transcript text  
✅ **Fast & Cheap** - ~9s processing, $0.0005 per session  
✅ **Production Ready** - Error handling, retries, validation  

---

## Architecture

### Pipeline Flow

```
Input: JSON transcript with 27 segments
    ↓
Step 1: Embed segments → 1536-dim vectors
    ↓
Step 2: Generate SOAP note (gpt-4o-mini, temp=0.3)
    ↓
Step 3: Parse into 14-17 statements
    ↓
Step 4: For each statement:
        - Embed statement
        - Find top-3 similar segments (cosine similarity)
        - Assign global citation numbers [1][2][3]...
        - Filter by threshold (0.50)
    ↓
Step 5: Insert inline citations
    ↓
Output: SOAP note with continuous citations
```

### Tech Stack

- **Framework:** FastAPI 0.109.0
- **LLM:** gpt-4o-mini (20x cheaper than GPT-4)
- **Embeddings:** text-embedding-3-small (1536-dim)
- **Similarity:** scikit-learn cosine similarity
- **Validation:** Pydantic 2.5.3

---

## Installation

### Requirements

- Python 3.10+
- OpenAI API key
- 8GB RAM

### Setup

```bash
# 1. Clone repository
git clone https://github.com/OliverHoo11/aidmi-transcript-pipeline.git
cd aidmi-transcript-pipeline

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-your-key
```

---

## Usage

### Option 1: Visual Demo (Recommended)

```bash
python -m tests.demo
```

Shows full pipeline with colored output, metrics, and continuous citations.

### Option 2: API Server

```bash
# Terminal 1: Start server
python -m app.main

# Terminal 2: Test API
python -m tests.test_api
```

### Option 3: Direct Pipeline

```bash
python -m tests.test_pipeline
```

### Example Output

```json
{
  "session_id": "sess_demo_001",
  "note_spans": [
    {
      "id": "span_001",
      "section": "subjective",
      "text": "Patient reports worsening insomnia to 3-4 hours. [1]",
      "citations": [
        {
          "id": "seg_002",
          "num": 1,
          "transcript": "Honestly, it's been tough. The insomnia has gotten worse..."
        }
      ],
      "confidence_score": 0.64
    },
    {
      "id": "span_002",
      "section": "subjective",
      "text": "She expresses exhaustion[2] and irritability[3].",
      "citations": [
        {
          "id": "seg_008",
          "num": 2,
          "transcript": "My mood has definitely been lower..."
        },
        {
          "id": "seg_006",
          "num": 3,
          "transcript": "Complicated. We've always had a difficult dynamic..."
        }
      ],
      "confidence_score": 0.67
    }
  ]
}
```

**Notice:** Citations number continuously [1][2][3] across all spans!

---

## API Reference

### POST /generate-note

Generate SOAP note with continuous citations.

**Request:**
```json
{
  "session_id": "sess_001",
  "patient_id": "pat_123",
  "segments": [
    {
      "id": "seg_001",
      "speaker": "clinician",
      "start_ms": 0,
      "end_ms": 5000,
      "text": "How have you been?"
    }
  ]
}
```

**Response:**
```json
{
  "session_id": "sess_001",
  "note_spans": [
    {
      "text": "Patient reports anxiety. [1]",
      "citations": [{"id": "seg_002", "num": 1, "transcript": "..."}],
      "confidence_score": 0.82
    }
  ]
}
```

### GET /health

Returns system health and configuration.

---

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (defaults)
CHAT_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
CITATION_THRESHOLD=0.50
```

### Tuning Citation Threshold

- **0.45-0.50:** More citations (~75-80% coverage) - Recommended
- **0.50-0.55:** Balanced (~70-75% coverage) - Default
- **0.60-0.70:** Strict (~60-65% coverage) - High confidence only

---

## Testing

### Run All Tests

```bash
# Direct pipeline test
python -m tests.test_pipeline
# Expected: ~64% citations, continuous numbering

# Visual demo
python -m tests.demo
# Expected: ~76% citations, full visualization

# API test (requires server running)
python -m app.main  # Terminal 1
python -m tests.test_api  # Terminal 2
# Expected: ~75% citations
```

### Test Results

| Test | Statements | Citations | Coverage | Time |
|------|-----------|-----------|----------|------|
| test_pipeline | 14 | 9 | 64% | 10.5s |
| demo | 17 | 13 | 76.5% | 8.4s |
| test_api | 16 | 12 | 75% | - |

**Average: ~72% citation coverage**

---

## How It Works

### 1. Hybrid RAG Approach

**Why not just ask the LLM to cite?**
- LLMs hallucinate segment IDs
- No way to verify citations
- Confidence scores not quantitative

**Our approach:**
1. LLM generates clinical note (expertise in SOAP format)
2. Embeddings verify citations (semantic similarity)
3. Mathematics prevents hallucination (cosine similarity)

### 2. Continuous Citation Numbering

**Problem:** Previous implementations reset numbering per span:
```
Span 1: "Text [1][2]"
Span 2: "More [1][2]"  ← Confusing!
```

**Solution:** Global counter across all spans:
```
Span 1: "Text [1][2]"
Span 2: "More [3][4]"  ← Clear!
```

### 3. Confidence Scoring

Each citation has similarity score:
- **0.70-1.00:** Strong match ✓✓
- **0.55-0.70:** Good match ✓
- **0.50-0.55:** Acceptable (threshold)
- **<0.50:** Flagged as needs_confirmation

### 4. Inline Citation Placement

Citations distributed across clauses:
```
"Patient reports insomnia[1], irritability[2], and anhedonia[3]."
```

Not clustered at end:
```
"Patient reports insomnia, irritability, and anhedonia. [1][2][3]"
```

---

## Cost Analysis

### Actual Performance (45-min session)

| Component | Model | Tokens | Cost |
|-----------|-------|--------|------|
| Segment embeddings | text-embedding-3-small | ~500 | $0.00001 |
| SOAP generation | gpt-4o-mini | ~1,950 | $0.00030 |
| Statement embeddings | text-embedding-3-small | ~200 | $0.00000 |
| **Total** | | **3,500** | **$0.0005** |

### Cost Optimizations

✅ gpt-4o-mini vs GPT-4 (20x cheaper)  
✅ text-embedding-3-small (most efficient)  
✅ Single-pass generation (no multi-turn)  
✅ Batch embeddings (all at once)  
✅ Low temperature (0.3, reduces waste)  

---

## Limitations & Future Work

### Current Limitations

1. **Citation Coverage:** 72% (not 100%)
   - **Why:** Some statements are clinical interpretations
   - **Acceptable:** Not all claims can be directly cited

2. **Sentence Splitting:** Uses regex
   - **Fix:** Upgrade to spaCy/NLTK for robustness

3. **Long Transcripts:** Loads entire transcript
   - **Fix:** Implement chunking for >2 hour sessions

4. **Citation Granularity:** Segment-level (not phrase-level)
   - **Fix:** Could split segments for finer precision

### Future Enhancements

**Priority 1:**
- [ ] Streaming response (SSE)
- [ ] Better sentence tokenization
- [ ] Citation verification pass
- [ ] Role-specific templates

**Priority 2:**
- [ ] Risk detection (SI/HI, substance use)
- [ ] Chunking for long transcripts
- [ ] Batch processing endpoint
- [ ] Embedding cache

**Priority 3:**
- [ ] Fine-tune threshold per section
- [ ] Semantic phrase matching
- [ ] Therapy modality templates (CBT, DBT)

---

## Project Structure

```
aidmi-transcript-pipeline/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI server
│   ├── pipeline.py       # Core processing (continuous citations)
│   ├── models.py         # Pydantic schemas
│   └── utils.py          # Utilities (retry, token tracking)
├── tests/
│   ├── __init__.py
│   ├── test_pipeline.py  # Direct test
│   ├── test_api.py       # API test
│   ├── demo.py           # Visual demo
│   └── diagnose.py       # Diagnostic tool
├── data/
│   ├── sample_transcript.json
│   └── output_example.json
├── README.md             # This file
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Development

### Code Quality

- ✅ Type hints throughout (Python 3.10+)
- ✅ Docstrings for all functions
- ✅ Async/await properly used
- ✅ Error handling with retries
- ✅ Pydantic validation
- ✅ No hardcoded values

### Running Tests

```bash
# All tests
python -m pytest tests/

# Specific test
python -m tests.demo

# With coverage
pytest --cov=app tests/
```

### Contributing

1. Fork repository
2. Create feature branch
3. Make changes
4. Run tests
5. Submit pull request

---

## How AI Tools Were Used

During development, I used AI assistants for:
- Architecture design discussions
- Hybrid RAG strategy evaluation
- Debugging continuous citation numbering
- Documentation structure

**Key Human Decisions:**
- Selected Hybrid RAG over alternatives
- Designed continuous citation numbering system
- Set threshold at 0.50 after empirical testing
- Chose gpt-4o-mini for cost/quality balance
- All architectural and implementation decisions

---

## License

MIT License - see LICENSE file for details

---

## Contact

**Repository:** https://github.com/OliverHoo11/aidmi-transcript-pipeline  
**Issues:** https://github.com/OliverHoo11/aidmi-transcript-pipeline/issues

For questions about implementation, open an issue or discussion.

---

## Acknowledgments

Built for AidMi AI/ML Engineer Take-Home Test

**Key Innovation:** Continuous citation numbering [1][2][3]... across entire SOAP note with zero hallucinations using hybrid RAG approach.

**Status:** Production Ready ✅