"""FastAPI server for the LinkedIn content advisor."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from advisor.db import PostsDB

app = FastAPI(title="LinkedIn Content Advisor", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_WEB_DIR = Path(__file__).parent.parent / "web"


def _get_db() -> PostsDB:
    return PostsDB()


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html_path = _WEB_DIR / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Web UI not found")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/posts")
async def list_posts(status: str = "pending") -> list[dict]:
    db = _get_db()
    try:
        if status == "all":
            return db.list_pending() + db.list_approved() + db.list_rejected()
        return db.list_by_status(status)
    finally:
        db.close()


@app.post("/api/posts/{post_id}/approve")
async def approve_post(post_id: str) -> dict[str, str]:
    db = _get_db()
    try:
        if not db.approve(post_id):
            raise HTTPException(status_code=404, detail="Post not found")
        return {"status": "approved", "id": post_id}
    finally:
        db.close()


@app.post("/api/posts/{post_id}/reject")
async def reject_post(post_id: str) -> dict[str, str]:
    db = _get_db()
    try:
        if not db.reject(post_id):
            raise HTTPException(status_code=404, detail="Post not found")
        return {"status": "rejected", "id": post_id}
    finally:
        db.close()


@app.get("/api/stats")
async def get_stats() -> dict[str, int]:
    db = _get_db()
    try:
        return db.stats()
    finally:
        db.close()
