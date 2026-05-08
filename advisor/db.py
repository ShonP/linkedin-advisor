"""SQLite database for managing social post drafts, copy analyses, proposals, and Reddit safety."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from advisor.db_schema import DB_SCHEMA, DRAFT_ADDED_COLUMNS
from advisor.models.copy import CopyAnalysis
from advisor.models.post import PostDraft
from advisor.models.proposal import ContentProposal
from advisor.models.reddit import RedditPost
from advisor.models.twitter import TwitterPost

_DB_PATH = Path("data/posts.db")


class PostsDB:
    def __init__(self, db_path: Path | None = None) -> None:
        self._path = db_path or _DB_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(DB_SCHEMA)
        self._migrate_drafts()

    def _migrate_drafts(self) -> None:
        existing = {r["name"] for r in self._conn.execute("PRAGMA table_info(drafts)").fetchall()}
        for col, ddl in DRAFT_ADDED_COLUMNS.items():
            if col not in existing:
                self._conn.execute(f"ALTER TABLE drafts ADD COLUMN {col} {ddl}")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def save_draft(
        self,
        draft: PostDraft,
        *,
        reddit: RedditPost | None = None,
        twitter: TwitterPost | None = None,
        proposal_reasoning: str = "",
        confidence: float = 0.0,
    ) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO drafts
               (id, hook, body, category, source_json, image_suggestion, best_time,
                status, created_at, platform, reddit_subreddit, reddit_flair, reddit_post_type,
                twitter_thread_json, twitter_hashtags_json, proposal_reasoning, confidence_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                draft.id, draft.hook, draft.body, draft.category,
                draft.source.model_dump_json(),
                draft.image_suggestion, draft.best_time,
                draft.created_at or datetime.now(UTC).isoformat(),
                draft.platform,
                reddit.subreddit if reddit else "",
                reddit.flair if reddit else "",
                reddit.post_type if reddit else "",
                json.dumps(twitter.thread) if twitter else "",
                json.dumps(twitter.hashtags) if twitter else "",
                proposal_reasoning,
                confidence,
            ),
        )
        self._conn.commit()

    def approve(self, post_id: str) -> bool:
        return self._set_status(post_id, "approved")

    def reject(self, post_id: str) -> bool:
        return self._set_status(post_id, "rejected")

    def _set_status(self, post_id: str, status: str) -> bool:
        now = datetime.now(UTC).isoformat()
        cur = self._conn.execute(
            "UPDATE drafts SET status = ?, decided_at = ? WHERE id = ?",
            (status, now, post_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def _row_to_draft(self, row: sqlite3.Row) -> dict[str, object]:
        return {
            "id": row["id"], "hook": row["hook"], "body": row["body"],
            "category": row["category"], "source": json.loads(row["source_json"]),
            "image_suggestion": row["image_suggestion"], "best_time": row["best_time"],
            "status": row["status"], "created_at": row["created_at"], "decided_at": row["decided_at"],
            "platform": row["platform"] or "linkedin",
            "reddit_subreddit": row["reddit_subreddit"] or "",
            "reddit_flair": row["reddit_flair"] or "",
            "reddit_post_type": row["reddit_post_type"] or "",
            "twitter_thread": json.loads(row["twitter_thread_json"] or "[]"),
            "twitter_hashtags": json.loads(row["twitter_hashtags_json"] or "[]"),
            "proposal_reasoning": row["proposal_reasoning"] or "",
            "confidence_score": row["confidence_score"] or 0.0,
        }

    def list_by_status(self, status: str, platform: str = "") -> list[dict[str, object]]:
        if platform:
            rows = self._conn.execute(
                "SELECT * FROM drafts WHERE status = ? AND platform = ? ORDER BY created_at DESC",
                (status, platform),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM drafts WHERE status = ? ORDER BY created_at DESC", (status,)
            ).fetchall()
        return [self._row_to_draft(r) for r in rows]

    def list_pending(self) -> list[dict[str, object]]:
        return self.list_by_status("pending")

    def list_approved(self) -> list[dict[str, object]]:
        return self.list_by_status("approved")

    def list_rejected(self) -> list[dict[str, object]]:
        return self.list_by_status("rejected")

    def update_draft_content(self, post_id: str, hook: str, body: str) -> bool:
        cur = self._conn.execute(
            "UPDATE drafts SET hook = ?, body = ?, status = 'pending', decided_at = '' WHERE id = ?",
            (hook, body, post_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def get_post(self, post_id: str) -> dict[str, object] | None:
        row = self._conn.execute("SELECT * FROM drafts WHERE id = ?", (post_id,)).fetchone()
        return self._row_to_draft(row) if row else None

    def get_post_full(self, post_id: str) -> dict[str, object] | None:
        row = self._conn.execute("SELECT * FROM drafts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            return None
        data = self._row_to_draft(row)
        data["body_length"] = len(str(data["body"]))
        return data

    def stats(self) -> dict[str, int]:
        rows = self._conn.execute("SELECT status, COUNT(*) as cnt FROM drafts GROUP BY status").fetchall()
        result = {"pending": 0, "approved": 0, "rejected": 0, "total": 0}
        for row in rows:
            result[row["status"]] = row["cnt"]
            result["total"] += row["cnt"]
        return result

    def save_copy_analysis(self, analysis: CopyAnalysis, analysis_id: str) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO copy_analyses
               (id, niche, platforms, analysis_json, created_at) VALUES (?, ?, ?, ?, ?)""",
            (
                analysis_id, analysis.niche, ",".join(analysis.platforms),
                analysis.model_dump_json(),
                analysis.created_at or datetime.now(UTC).isoformat(),
            ),
        )
        self._conn.commit()

    def list_copy_analyses(self, limit: int = 20) -> list[dict[str, object]]:
        rows = self._conn.execute(
            "SELECT id, niche, platforms, created_at FROM copy_analyses ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_copy_analysis(self, analysis_id: str) -> dict[str, object] | None:
        row = self._conn.execute(
            "SELECT * FROM copy_analyses WHERE id = ?", (analysis_id,)
        ).fetchone()
        if not row:
            return None
        return {**dict(row), "analysis": json.loads(row["analysis_json"])}

    def save_proposal(self, p: ContentProposal) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO proposals
               (id, platform, headline, angle, reasoning, confidence,
                suggested_subreddit, source_summary, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (
                p.id, p.platform, p.headline, p.angle, p.reasoning, p.confidence,
                p.suggested_subreddit, p.source_summary,
                p.created_at or datetime.now(UTC).isoformat(),
            ),
        )
        self._conn.commit()

    def list_proposals(self, status: str = "pending") -> list[dict[str, object]]:
        rows = self._conn.execute(
            "SELECT * FROM proposals WHERE status = ? ORDER BY confidence DESC, created_at DESC",
            (status,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_reddit_safety(self, subreddit: str) -> dict[str, object] | None:
        row = self._conn.execute(
            "SELECT * FROM reddit_safety WHERE subreddit = ?", (subreddit,)
        ).fetchone()
        return dict(row) if row else None

    def record_reddit_post(self, subreddit: str) -> None:
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """INSERT INTO reddit_safety (subreddit, posts_count, last_post_at)
               VALUES (?, 1, ?)
               ON CONFLICT(subreddit) DO UPDATE SET
                   posts_count = posts_count + 1,
                   last_post_at = excluded.last_post_at""",
            (subreddit, now),
        )
        self._conn.commit()
