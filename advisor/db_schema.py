"""Database schema and migration constants for PostsDB."""

from __future__ import annotations

DB_SCHEMA = """\
CREATE TABLE IF NOT EXISTS drafts (
    id TEXT PRIMARY KEY,
    hook TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT NOT NULL,
    source_json TEXT NOT NULL,
    image_suggestion TEXT DEFAULT '',
    best_time TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    decided_at TEXT DEFAULT '',
    platform TEXT DEFAULT 'linkedin',
    reddit_subreddit TEXT DEFAULT '',
    reddit_flair TEXT DEFAULT '',
    reddit_post_type TEXT DEFAULT '',
    twitter_thread_json TEXT DEFAULT '',
    twitter_hashtags_json TEXT DEFAULT '',
    proposal_reasoning TEXT DEFAULT '',
    confidence_score REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS copy_analyses (
    id TEXT PRIMARY KEY,
    niche TEXT NOT NULL,
    platforms TEXT NOT NULL,
    analysis_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proposals (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    headline TEXT NOT NULL,
    angle TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    confidence REAL NOT NULL,
    suggested_subreddit TEXT DEFAULT '',
    source_summary TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reddit_safety (
    subreddit TEXT PRIMARY KEY,
    posts_count INTEGER DEFAULT 0,
    last_post_at TEXT DEFAULT '',
    karma_estimate INTEGER DEFAULT 0,
    account_created_at TEXT DEFAULT ''
);
"""

DRAFT_ADDED_COLUMNS = {
    "platform": "TEXT DEFAULT 'linkedin'",
    "reddit_subreddit": "TEXT DEFAULT ''",
    "reddit_flair": "TEXT DEFAULT ''",
    "reddit_post_type": "TEXT DEFAULT ''",
    "twitter_thread_json": "TEXT DEFAULT ''",
    "twitter_hashtags_json": "TEXT DEFAULT ''",
    "proposal_reasoning": "TEXT DEFAULT ''",
    "confidence_score": "REAL DEFAULT 0.0",
}
