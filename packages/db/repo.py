import os
import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import create_engine, text, select, func
from sqlalchemy.sql import text as sql_text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from .models import Base, Article, ArticleVector, QueryLog

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/khobor")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Create pgvector extension, tables, and IVFFLAT index."""
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        Base.metadata.create_all(bind=conn)
        # Create vector index if not exists (IVFFLAT lists=100)
        conn.exec_driver_sql(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = 'idx_article_vectors_embedding_ivfflat'
                      AND n.nspname = 'public'
                ) THEN
                    CREATE INDEX idx_article_vectors_embedding_ivfflat
                    ON article_vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
                END IF;
            END
            $$;
            """
        )


def _vector_literal(vec: Sequence[float]) -> str:
    # Format as pgvector literal string: [v1, v2, ...]
    return "[" + ", ".join(f"{float(v):.8f}" for v in vec) + "]"


def upsert_article(article: dict) -> uuid.UUID:
    """Upsert article by URL. Returns article UUID.

    Expected keys: url, title, source, source_category, summary, published_at (ISO str or datetime)
    """
    with session_scope() as session:
        data = dict(article)
        # Normalize published_at
        published_at = data.get("published_at")
        if isinstance(published_at, str) and published_at:
            try:
                data["published_at"] = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except Exception:
                data["published_at"] = None
        elif not published_at:
            data["published_at"] = None

        insert_stmt = insert(Article).values(**{
            "url": data["url"],
            "title": data.get("title", "Untitled")[:512],
            "source": data.get("source", "Unknown")[:128],
            "source_category": data.get("source_category", "general")[:32],
            "summary": data.get("summary"),
            "published_at": data.get("published_at"),
        })
        
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[Article.url],
            set_={
                "title": insert_stmt.excluded.title,
                "source": insert_stmt.excluded.source,
                "source_category": insert_stmt.excluded.source_category,
                "summary": insert_stmt.excluded.summary,
                "published_at": insert_stmt.excluded.published_at,
            },
        ).returning(Article.id)

        result = session.execute(insert_stmt)
        article_id = result.scalar_one()
        return article_id


def upsert_embedding(article_id: uuid.UUID, vec: Sequence[float]) -> None:
    # Enforce 1536-dim vector to match schema
    if vec is None or len(vec) != 1536:
        raise ValueError(f"Embedding must be 1536-dim; got {0 if vec is None else len(vec)}")
    embedding_literal = _vector_literal(vec)
    with session_scope() as session:
        insert_stmt = insert(ArticleVector).values(
            article_id=article_id,
            embedding=embedding_literal,
        )
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[ArticleVector.article_id],
            set_={
                "embedding": insert_stmt.excluded.embedding,
                "updated_at": text("now() at time zone 'utc'")
            }
        )
        session.execute(insert_stmt)


def fetch_recent_candidates(window_hours: int = 72, limit: int = 800) -> List[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(window_hours))
    with session_scope() as session:
        stmt = (
            select(Article)
            .where(
                (Article.published_at == None) |  # include undated
                (Article.published_at >= cutoff)
            )
            .order_by(Article.inserted_at.desc())
            .limit(limit)
        )
        result = session.execute(stmt).scalars().all()
        # Expunge objects from session to avoid lazy loading issues
        for article in result:
            session.expunge(article)
        return result


def search_vectors(qvec: Sequence[float], window_hours: int = 72, limit: int = 300) -> List[Tuple[Article, float]]:
    """Search by cosine similarity over recent articles.

    Returns list of (Article, cosine_similarity)
    """
    q_literal = _vector_literal(qvec)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(window_hours))

    with session_scope() as session:
        # Use raw SQL with proper parameterization
        query = sql_text(f"""
            SELECT a.id, a.url, a.title, a.source, a.source_category, a.summary, a.published_at,
                   1 - (av.embedding <=> '{q_literal}'::vector) AS cos_sim
            FROM article_vectors av
            JOIN articles a ON a.id = av.article_id
            WHERE (a.published_at IS NULL OR a.published_at >= :cutoff)
            ORDER BY av.embedding <=> '{q_literal}'::vector
            LIMIT :limit
        """)
        rows = session.execute(query, {"cutoff": cutoff, "limit": int(limit)})
        results: List[Tuple[Article, float]] = []
        for row in rows:
            art = Article(
                id=row[0],
                url=row[1],
                title=row[2],
                source=row[3],
                source_category=row[4],
                summary=row[5],
                published_at=row[6],
            )
            results.append((art, float(row[7])))
        return results


def log_query(question: str, answer: str, source_article_ids: List[str] = None, response_time_ms: int = None) -> uuid.UUID:
    """Log user query and response to database."""
    with session_scope() as session:
        source_articles_json = json.dumps(source_article_ids) if source_article_ids else None
        
        query_log = QueryLog(
            question=question,
            answer=answer,
            source_articles=source_articles_json,
            response_time_ms=response_time_ms
        )
        session.add(query_log)
        session.flush()
        return query_log.id


def get_recent_articles(limit: int = 50) -> List[Article]:
    """Get recent articles for API endpoints."""
    with session_scope() as session:
        stmt = (
            select(Article)
            .order_by(Article.inserted_at.desc())
            .limit(limit)
        )
        result = session.execute(stmt).scalars().all()
        # Expunge objects from session to avoid lazy loading issues
        for article in result:
            session.expunge(article)
        return result


def search_articles_by_keyword(keyword: str, limit: int = 50) -> List[Article]:
    """Search articles by keyword in title or summary."""
    with session_scope() as session:
        keyword_pattern = f"%{keyword.lower()}%"
        stmt = (
            select(Article)
            .where(
                (func.lower(Article.title).contains(keyword_pattern)) |
                (func.lower(Article.summary).contains(keyword_pattern))
            )
            .order_by(Article.inserted_at.desc())
            .limit(limit)
        )
        result = session.execute(stmt).scalars().all()
        # Expunge objects from session to avoid lazy loading issues
        for article in result:
            session.expunge(article)
        return result
