# KhoborAgent

A minimal backend for RSS news aggregation with PostgreSQL storage, pgvector similarity search, keyword ranking, summary generation with inline citations, and translation to Bangla.

## Quick Start

```bash
# Complete setup using Makefile
make dev

# Or manual setup:
# 1. Start database
make db-up

# 2. Install dependencies
make install

# 3. Run migrations
make db-migrate

# 4. Backfill existing JSON data (optional)
make db-backfill

# 5. Start API server
make api

# Use CLI directly (no server needed)
python scripts/ask.py "বিটকয়েনের সর্বশেষ কী"
```

## Database Setup

KhoborAgent uses PostgreSQL with pgvector for efficient similarity search:

```bash
# Start PostgreSQL with Docker
docker-compose -f docker-compose.db.yml up -d

# Run database migrations
alembic upgrade head

# Migrate existing JSON cache to database
python scripts/migrate_json_to_db.py

# Check database connection
make check-db
```

## API Usage

### Query Endpoint

**POST /ask** - Main query endpoint with intelligent routing
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

### Database API Endpoints

**GET /api/articles** - Get recent articles from database
```bash
curl "http://localhost:8000/api/articles?limit=10"
```

**GET /api/articles/search** - Search articles by keyword
```bash
curl "http://localhost:8000/api/articles/search?q=technology&limit=10"
```

**GET /api/articles/similar** - Find similar articles using vector search
```bash
curl "http://localhost:8000/api/articles/similar?q=artificial intelligence&limit=5"
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

- **PostgreSQL Storage**: Robust database with pgvector for similarity search
- **RSS Ingestion**: 18 curated feeds (global + Bangladesh) with automatic processing
- **Vector Search**: Semantic similarity search using OpenAI embeddings
- **Smart Ranking**: Keyword relevance + time decay scoring
- **Processing**: Model-based summarization and translation
- **Citation Integrity**: Inline source references [1][2][3]
- **Source Diversity**: Domain-based deduplication
- **Bilingual Output**: English and Bangla summaries
- **Query Logging**: All user queries and responses logged for analysis
- **JSON Fallback**: Backward compatibility with existing JSON cache

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

## Development Workflow

### Common Commands

```bash
# Full development setup
make dev

# Database management  
make db-up            # Start PostgreSQL
make db-down          # Stop PostgreSQL
make db-migrate       # Run migrations
make db-backfill      # Import JSON data
make db-reset         # Reset database (WARNING: destroys data)

# Development
make api              # Start API server
make test-ingest      # Test RSS ingestion
make check-db         # Verify database connection

# Migration management
make db-migrate-create MSG="Description"  # Create new migration
alembic upgrade head                      # Apply migrations
alembic downgrade -1                      # Rollback one migration
```

### Database Schema

The application uses these main tables:
- **articles**: News articles with metadata and summaries
- **article_vectors**: pgvector embeddings for similarity search
- **sources**: RSS feed source configuration  
- **query_logs**: User queries and responses for analytics

### Environment Variables

Copy `.env.example` to `.env` and configure:
- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: Required for embeddings and summarization
- `INGEST_INTERVAL_MIN`: RSS feed refresh interval

### Migration from JSON Cache

Existing JSON cache files are automatically migrated to PostgreSQL:

```bash
python scripts/migrate_json_to_db.py
```

The system maintains backward compatibility - if database is unavailable, it falls back to JSON cache files.