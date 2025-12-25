# Quick Start Guide

## 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Set Up API Key

```bash
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-your-key-here
```

## 3. Test the Pipeline

```bash
# Option A: Test pipeline directly (no server needed)
python test_pipeline.py

# Option B: Visual demo with detailed output
python demo.py

# Option C: Run API server
python main.py
# In another terminal:
python test_api_client.py
```

## Expected Output

After running `python demo.py`, you should see:

```
================================================================================
                     AidMi Transcript-to-Note Pipeline Demo
================================================================================

✓ API key loaded: sk-proj-U8LOpl...
✓ Processor initialized
✓ Processing complete! (8.44s)

SUBJECTIVE:
Sarah reports worsening insomnia to 3-4 hours per night. [1]
  └─ Citations: seg_002 (confidence: 0.64)
     ↳ [1] seg_002: "Hi. Honestly, it's been a really tough couple..."

She expresses feelings of exhaustion[1] and irritability[2]...
  └─ Citations: seg_008, seg_006 (confidence: 0.67)

[... more sections ...]

Quality Metrics:
  Total statements: 17
  With citations: 13 (76.5%)
  Needs confirmation: 4 (23.5%)
  Average confidence: 0.45

Token Usage:
  Total tokens: 3,567
  Estimated cost: $0.0005
```

**This is normal and expected!** The system achieves 70-76% citation coverage, which is excellent for clinical note generation. The remaining 24-30% are interpretive statements that lack direct transcript support.

## Troubleshooting

**Error: "OPENAI_API_KEY not configured"**
- Make sure you created `.env` file with your API key
- Check the file exists: `cat .env` (should show your key)
- Restart server after editing `.env`

**Error: "Module not found"**
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

**Low citation coverage (<60%)**
- Default threshold is 0.50 (good balance)
- Lower threshold: `CITATION_THRESHOLD=0.45` in `.env` (more citations, lower confidence)
- Higher threshold: `CITATION_THRESHOLD=0.60` (fewer citations, higher confidence)

**Server won't start**
- Check if port 8000 is free: `lsof -i :8000` (Unix) or `netstat -ano | findstr :8000` (Windows)
- Try different port: `uvicorn main:app --port 8001`

**API returns 500 error**
- Check server logs for error details
- Verify `.env` file is in same directory as `main.py`
- Restart server completely

## Understanding the Results

### Citation Coverage
- **70-76% is excellent** - Most claims are supported by transcript
- **24-30% needs confirmation** - These are clinical interpretations/summaries
- **Not all statements can be cited** - Some are synthesized from multiple segments

### Confidence Scores
- **0.70-1.00:** Strong match (excellent)
- **0.55-0.69:** Good match (reliable)
- **0.50-0.54:** Acceptable match (threshold)
- **<0.50:** Weak match (flagged as needs confirmation)

### Inline Citations
Citations appear as **[1][2][3]** within or after the text:
- Short statements: Citations at end → `"Text. [1][2]"`
- Long statements: Distributed inline → `"Text[1] more text[2]"`

## Next Steps

1. **Review output files:** `output_demo_*.json` or `output_sample.json`
2. **Explore API docs:** http://localhost:8000/docs (when server running)
3. **Tune threshold:** Adjust `CITATION_THRESHOLD` in `.env` if needed
4. **Read detailed docs:** See `README.md` and `ARCHITECTURE.md`

## Performance Benchmarks

Based on sample transcript (27 segments, 45-min session):

| Metric | Value |
|--------|-------|
| Processing time | 8-11 seconds |
| Token usage | ~3,500 tokens |
| Cost per session | ~$0.0005 |
| Citation coverage | 70-76% |
| Avg confidence | 0.45-0.59 |

## Quick Tests

**Verify everything works:**
```bash
# Test 1: Direct pipeline
python test_pipeline.py
# Expected: ~64% citations (9/14 statements)

# Test 2: Visual demo
python demo.py
# Expected: ~76% citations (13/17 statements)

# Test 3: API
python main.py  # Terminal 1
python test_api_client.py  # Terminal 2
# Expected: ~75% citations (12/16 statements)
```

All tests show slightly different results due to LLM variation - this is normal!