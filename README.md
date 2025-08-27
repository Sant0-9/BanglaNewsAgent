# KhoborAgent

A minimal backend for RSS news aggregation with keyword ranking, summary generation with inline citations, and translation to Bangla.

## Quick Start

```bash
# Setup environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # set required environment variables

# Start API server (optional)
uvicorn apps.api.main:app --reload --port 8000

# Use CLI directly (no server needed)
python scripts/ask.py "বিটকয়েনের সর্বশেষ কী"
```

## API Usage

The API provides a single endpoint for news queries:

**POST /ask**
```json
{
  "query": "semiconductor export controls",
  "lang": "bn",
  "window_hours": 72
}
```

**Response:**
```json
{
  "answer_bn": "সেমিকন্ডাক্টর রপ্তানি নিয়ন্ত্রণ... [1][2]",
  "answer_en": "Semiconductor export controls... [1][2]",
  "sources": [
    {"name": "Reuters", "url": "...", "published_at": "..."},
    {"name": "BBC World", "url": "...", "published_at": "..."}
  ],
  "metrics": {"source_count": 3, "updated_ct": "..."},
  "flags": {"disagreement": false, "single_source": false}
}
```

## CLI Usage

Direct command-line usage without running a server:

```bash
python scripts/ask.py "সেমিকন্ডাক্টর এক্সপোর্ট কন্ট্রোল"
python scripts/ask.py "climate change latest news"
python scripts/ask.py "বিটকয়েনের সর্বশেষ খবর"
```

Output includes:
- Bangla summary with inline citations [1][2]
- Numbered source list with publication dates and URLs
- Flags for source disagreements or single-source claims

## Features

- **RSS Ingestion**: 18 curated feeds (global + Bangladesh)
- **Smart Ranking**: Keyword relevance + time decay scoring
- **Processing**: Model-based summarization and translation
- **Citation Integrity**: Inline source references [1][2][3]
- **Source Diversity**: Domain-based deduplication
- **Bilingual Output**: English and Bangla summaries
- **JSON Caching**: Disk-based article persistence

## Demo (one command)

```bash
pnpm run demo   # or: npm run demo
# Opens http://localhost:3000 and pre-warms two queries
```

This command will:
- Set up Python environment and install dependencies
- Start FastAPI backend on port 8000
- Start Next.js frontend on port 3000
- Open your browser to the web app
- Pre-warm the API with sample queries for instant streaming

**Troubleshooting:**
- Check http://localhost:8000/healthz
- If CORS errors, confirm CORSMiddleware is enabled
- If UI shows nothing, verify Network tab requests hit localhost:8000