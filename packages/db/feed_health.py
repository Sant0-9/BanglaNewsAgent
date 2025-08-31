import os
import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import uuid

import psycopg2
from psycopg2.extras import RealDictCursor

from packages.db.repo import get_db_config

@dataclass
class FeedHealthMetrics:
    """Feed health metrics data structure"""
    feed_url: str
    feed_name: str
    last_success: Optional[datetime]
    last_attempt: Optional[datetime]
    success_count: int
    error_count: int
    avg_latency_ms: float
    health_score: float
    is_enabled: bool
    error_details: Optional[str]
    
    @property
    def uptime_percentage(self) -> float:
        """Calculate uptime percentage from success/error counts"""
        total = self.success_count + self.error_count
        if total == 0:
            return 100.0
        return (self.success_count / total) * 100.0
    
    @property
    def hours_since_success(self) -> float:
        """Hours since last successful fetch"""
        if not self.last_success:
            return float('inf')
        return (datetime.now(timezone.utc) - self.last_success).total_seconds() / 3600.0
    
    def should_disable(self) -> bool:
        """Determine if feed should be automatically disabled"""
        # Disable if health score is very low
        if self.health_score < 0.3:
            return True
        
        # Disable if no success in last 24 hours and multiple recent errors
        if self.hours_since_success > 24 and self.error_count > 5:
            return True
            
        # Disable if uptime is very poor
        if self.uptime_percentage < 20.0 and (self.success_count + self.error_count) > 10:
            return True
            
        return False
    
    def should_deprioritize(self) -> bool:
        """Determine if feed should be deprioritized"""
        # Deprioritize if health score is moderate
        if 0.3 <= self.health_score < 0.7:
            return True
        
        # Deprioritize if uptime is moderate
        if 50.0 <= self.uptime_percentage < 80.0:
            return True
            
        # Deprioritize if slow but not broken
        if self.avg_latency_ms > 10000:  # > 10 seconds
            return True
            
        return False


def init_feed_health_db():
    """Initialize feed health monitoring tables"""
    db_config = get_db_config()
    
    with psycopg2.connect(**db_config) as conn:
        with conn.cursor() as cur:
            # Create feed health table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feed_health (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    feed_url TEXT NOT NULL UNIQUE,
                    feed_name TEXT NOT NULL,
                    last_success TIMESTAMPTZ,
                    last_attempt TIMESTAMPTZ,
                    success_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    total_latency_ms BIGINT DEFAULT 0,
                    avg_latency_ms FLOAT DEFAULT 0.0,
                    health_score FLOAT DEFAULT 1.0,
                    is_enabled BOOLEAN DEFAULT TRUE,
                    error_details TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            # Create index for fast lookups
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_feed_health_url ON feed_health(feed_url);
                CREATE INDEX IF NOT EXISTS idx_feed_health_enabled ON feed_health(is_enabled);
                CREATE INDEX IF NOT EXISTS idx_feed_health_score ON feed_health(health_score DESC);
            """)
            
            # Create feed health history for detailed tracking
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feed_health_history (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    feed_url TEXT NOT NULL,
                    attempt_time TIMESTAMPTZ DEFAULT NOW(),
                    success BOOLEAN NOT NULL,
                    latency_ms INTEGER,
                    error_message TEXT,
                    articles_fetched INTEGER DEFAULT 0
                );
            """)
            
            # Index for history queries
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_feed_health_history_url_time 
                ON feed_health_history(feed_url, attempt_time DESC);
            """)
            
        conn.commit()


def record_feed_attempt(feed_url: str, feed_name: str, success: bool, 
                       latency_ms: int, error_message: Optional[str] = None, 
                       articles_fetched: int = 0):
    """Record a feed fetch attempt and update health metrics"""
    db_config = get_db_config()
    
    with psycopg2.connect(**db_config) as conn:
        with conn.cursor() as cur:
            # Insert history record
            cur.execute("""
                INSERT INTO feed_health_history 
                (feed_url, success, latency_ms, error_message, articles_fetched)
                VALUES (%s, %s, %s, %s, %s)
            """, (feed_url, success, latency_ms, error_message, articles_fetched))
            
            # Update or insert main health record
            if success:
                cur.execute("""
                    INSERT INTO feed_health 
                    (feed_url, feed_name, last_success, last_attempt, success_count, total_latency_ms)
                    VALUES (%s, %s, NOW(), NOW(), 1, %s)
                    ON CONFLICT (feed_url) DO UPDATE SET
                        feed_name = EXCLUDED.feed_name,
                        last_success = NOW(),
                        last_attempt = NOW(),
                        success_count = feed_health.success_count + 1,
                        total_latency_ms = feed_health.total_latency_ms + %s,
                        updated_at = NOW()
                """, (feed_url, feed_name, latency_ms, latency_ms))
            else:
                cur.execute("""
                    INSERT INTO feed_health 
                    (feed_url, feed_name, last_attempt, error_count, error_details)
                    VALUES (%s, %s, NOW(), 1, %s)
                    ON CONFLICT (feed_url) DO UPDATE SET
                        feed_name = EXCLUDED.feed_name,
                        last_attempt = NOW(),
                        error_count = feed_health.error_count + 1,
                        error_details = %s,
                        updated_at = NOW()
                """, (feed_url, feed_name, error_message, error_message))
            
            # Calculate and update health metrics
            _update_health_metrics(cur, feed_url)
            
        conn.commit()


def _update_health_metrics(cur, feed_url: str):
    """Update calculated health metrics for a feed"""
    # Get current metrics
    cur.execute("""
        SELECT success_count, error_count, total_latency_ms, last_success
        FROM feed_health 
        WHERE feed_url = %s
    """, (feed_url,))
    
    result = cur.fetchone()
    if not result:
        return
    
    success_count, error_count, total_latency_ms, last_success = result
    
    # Calculate average latency
    avg_latency_ms = 0.0
    if success_count > 0:
        avg_latency_ms = total_latency_ms / success_count
    
    # Calculate health score (0.0 to 1.0)
    total_attempts = success_count + error_count
    if total_attempts == 0:
        health_score = 1.0
    else:
        # Base score from success rate
        success_rate = success_count / total_attempts
        
        # Penalize for high latency (exponential decay)
        latency_penalty = 1.0
        if avg_latency_ms > 1000:  # 1 second
            latency_penalty = max(0.1, 1.0 - (avg_latency_ms - 1000) / 20000)
        
        # Penalize for staleness
        staleness_penalty = 1.0
        if last_success:
            hours_old = (datetime.now(timezone.utc) - last_success).total_seconds() / 3600.0
            if hours_old > 2:  # More than 2 hours
                staleness_penalty = max(0.1, 1.0 - (hours_old - 2) / 24)
        else:
            staleness_penalty = 0.3  # Never succeeded
        
        # Combined health score
        health_score = success_rate * latency_penalty * staleness_penalty
    
    # Determine if feed should be disabled
    is_enabled = health_score >= 0.3 and (not last_success or 
                                         (datetime.now(timezone.utc) - last_success).total_seconds() < 86400)
    
    # Update metrics
    cur.execute("""
        UPDATE feed_health 
        SET avg_latency_ms = %s, 
            health_score = %s, 
            is_enabled = %s,
            updated_at = NOW()
        WHERE feed_url = %s
    """, (avg_latency_ms, health_score, is_enabled, feed_url))


def get_feed_health_metrics() -> List[FeedHealthMetrics]:
    """Get health metrics for all feeds"""
    db_config = get_db_config()
    
    with psycopg2.connect(**db_config) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT feed_url, feed_name, last_success, last_attempt,
                       success_count, error_count, avg_latency_ms, health_score,
                       is_enabled, error_details
                FROM feed_health
                ORDER BY health_score DESC
            """)
            
            results = []
            for row in cur.fetchall():
                results.append(FeedHealthMetrics(
                    feed_url=row['feed_url'],
                    feed_name=row['feed_name'],
                    last_success=row['last_success'],
                    last_attempt=row['last_attempt'],
                    success_count=row['success_count'],
                    error_count=row['error_count'],
                    avg_latency_ms=row['avg_latency_ms'],
                    health_score=row['health_score'],
                    is_enabled=row['is_enabled'],
                    error_details=row['error_details']
                ))
            
            return results


def get_healthy_feeds() -> List[Dict[str, Any]]:
    """Get list of healthy feeds for ingestion"""
    db_config = get_db_config()
    
    with psycopg2.connect(**db_config) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT fh.feed_url, fh.feed_name, fh.health_score, fh.avg_latency_ms,
                       fh.is_enabled
                FROM feed_health fh
                WHERE fh.is_enabled = TRUE AND fh.health_score > 0.3
                ORDER BY fh.health_score DESC
            """)
            
            return [dict(row) for row in cur.fetchall()]


def disable_unhealthy_feeds():
    """Automatically disable feeds that meet criteria for disabling"""
    metrics = get_feed_health_metrics()
    disabled_feeds = []
    
    db_config = get_db_config()
    with psycopg2.connect(**db_config) as conn:
        with conn.cursor() as cur:
            for metric in metrics:
                if metric.should_disable() and metric.is_enabled:
                    cur.execute("""
                        UPDATE feed_health 
                        SET is_enabled = FALSE, updated_at = NOW()
                        WHERE feed_url = %s
                    """, (metric.feed_url,))
                    
                    disabled_feeds.append({
                        'feed_name': metric.feed_name,
                        'feed_url': metric.feed_url,
                        'health_score': metric.health_score,
                        'uptime': metric.uptime_percentage,
                        'hours_since_success': metric.hours_since_success
                    })
                    
                    print(f"[HEALTH] Disabled unhealthy feed: {metric.feed_name} "
                          f"(score: {metric.health_score:.2f}, uptime: {metric.uptime_percentage:.1f}%)")
        
        conn.commit()
    
    return disabled_feeds


def get_feed_timeout(feed_url: str) -> int:
    """Get adaptive timeout for a feed based on its historical performance"""
    db_config = get_db_config()
    
    try:
        with psycopg2.connect(**db_config) as conn:
            with conn.cursor() as cur:
                # Get average latency and success rate for this feed
                cur.execute("""
                    SELECT avg_latency_ms, health_score, success_count + error_count as total_attempts
                    FROM feed_health 
                    WHERE feed_url = %s
                """, (feed_url,))
                
                result = cur.fetchone()
                if not result or result[2] < 5:  # Less than 5 attempts
                    return 10000  # Default 10 seconds for new feeds
                
                avg_latency_ms, health_score, total_attempts = result
                
                # Adaptive timeout: base + margin based on historical performance
                if health_score > 0.8:  # Very healthy feeds
                    return min(15000, int(avg_latency_ms * 2 + 5000))  # 2x avg + 5s margin, max 15s
                elif health_score > 0.5:  # Moderately healthy
                    return min(25000, int(avg_latency_ms * 2.5 + 8000))  # 2.5x avg + 8s margin, max 25s
                else:  # Struggling feeds
                    return min(30000, int(avg_latency_ms * 3 + 10000))  # 3x avg + 10s margin, max 30s
                    
    except Exception as e:
        print(f"[HEALTH] Error getting timeout for {feed_url}: {e}")
        return 10000  # Default fallback