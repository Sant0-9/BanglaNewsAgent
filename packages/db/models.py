import os
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    func,
    Boolean,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.types import UserDefinedType


Base = declarative_base()


class Vector(UserDefinedType):
    """Postgres pgvector type.

    Generates VECTOR(dim) in DDL. Values should be bound as strings in the
    pgvector input format, e.g. "[0.1, 0.2, 0.3]". This avoids requiring the
    python pgvector adapter while keeping DDL correct.
    """

    def __init__(self, dim: int):
        self.dim = dim

    def get_col_spec(self, dialect=None):  # type: ignore[override]
        return f"vector({int(self.dim)})"

    def bind_processor(self, dialect):  # type: ignore[override]
        # We pass strings already formatted as pgvector literals.
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):  # type: ignore[override]
        # Return the raw database value (driver returns list or string depending on adapter)
        def process(value):
            return value
        return process


class Article(Base):
    __tablename__ = "articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(2000), unique=True, nullable=False, index=True)
    title = Column(String(512), nullable=False)
    source = Column(String(128), nullable=False)
    source_category = Column(String(32), nullable=False)
    summary = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    inserted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    vector = relationship(
        "ArticleVector",
        back_populates="article",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined",
    )


class ArticleVector(Base):
    __tablename__ = "article_vectors"

    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    embedding = Column(Vector(1536), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    article = relationship("Article", back_populates="vector")


class Source(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False, unique=True)
    category = Column(String(32), nullable=False)
    url = Column(String(512), nullable=False)
    rss_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    source_articles = Column(Text, nullable=True)  # JSON string of article IDs
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
