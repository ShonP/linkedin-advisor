"""Pydantic models for LinkedIn post drafts and decisions."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ContentSource(BaseModel):
    type: str = Field(description="Source type: 'github', 'news', or 'research'")
    title: str
    url: str = ""
    summary: str = ""


class PostDraft(BaseModel):
    id: str = Field(description="UUID for this draft")
    hook: str = Field(description="Opening line — attention grabber")
    body: str = Field(description="Full post text, 1200-1500 characters")
    category: str = Field(description="One of: technical, insight, story, trend")
    source: ContentSource
    image_suggestion: str = Field(default="", description="What image or visual would enhance this post")
    best_time: str = Field(default="", description="Suggested posting time, e.g. 'Tuesday 9am EST'")
    created_at: str = ""


class PostDrafts(BaseModel):
    """Structured output wrapper for the content creator agent."""

    drafts: list[PostDraft]


class SingleDraftResponse(BaseModel):
    """Structured output wrapper for single draft generation."""

    draft: PostDraft


class PostDecision(BaseModel):
    post_id: str
    decision: str = Field(description="'approved' or 'rejected'")
    decided_at: str
