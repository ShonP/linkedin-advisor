"""SQLite database for managing LinkedIn post drafts and decisions."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from advisor.models.post import PostDraft

_DB_PATH = Path("data/posts.db")

_SCHEMA = """\
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
    decided_at TEXT DEFAULT ''
);
"""


class PostsDB:
    def __init__(self, db_path: Path | None = None) -> None:
        self._path = db_path or _DB_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def save_draft(self, draft: PostDraft) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO drafts
               (id, hook, body, category, source_json, image_suggestion, best_time, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (
                draft.id,
                draft.hook,
                draft.body,
                draft.category,
                draft.source.model_dump_json(),
                draft.image_suggestion,
                draft.best_time,
                draft.created_at or datetime.now(UTC).isoformat(),
            ),
        )
        self._conn.commit()

    def approve(self, post_id: str) -> bool:
        now = datetime.now(UTC).isoformat()
        cur = self._conn.execute(
            "UPDATE drafts SET status = 'approved', decided_at = ? WHERE id = ?",
            (now, post_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def reject(self, post_id: str) -> bool:
        now = datetime.now(UTC).isoformat()
        cur = self._conn.execute(
            "UPDATE drafts SET status = 'rejected', decided_at = ? WHERE id = ?",
            (now, post_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def _row_to_draft(self, row: sqlite3.Row) -> dict[str, object]:
        return {
            "id": row["id"],
            "hook": row["hook"],
            "body": row["body"],
            "category": row["category"],
            "source": json.loads(row["source_json"]),
            "image_suggestion": row["image_suggestion"],
            "best_time": row["best_time"],
            "status": row["status"],
            "created_at": row["created_at"],
            "decided_at": row["decided_at"],
        }

    def list_by_status(self, status: str) -> list[dict[str, object]]:
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

    def get_post(self, post_id: str) -> dict[str, object] | None:
        row = self._conn.execute("SELECT * FROM drafts WHERE id = ?", (post_id,)).fetchone()
        return self._row_to_draft(row) if row else None

    def stats(self) -> dict[str, int]:
        rows = self._conn.execute("SELECT status, COUNT(*) as cnt FROM drafts GROUP BY status").fetchall()
        result = {"pending": 0, "approved": 0, "rejected": 0, "total": 0}
        for row in rows:
            result[row["status"]] = row["cnt"]
            result["total"] += row["cnt"]
        return result
