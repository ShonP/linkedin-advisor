"""Reddit-specific post model."""

from __future__ import annotations

from pydantic import BaseModel, Field

from advisor.models.post import ContentSource


class RedditPost(BaseModel):
    """A discussion-style Reddit post.

    Reddit culture rule: 90% value, ≤10% self-promotion. Discussion / TIL /
    helpful answer formats are safe; show-and-tell only after karma is built.
    """

    id: str = Field(description="UUID for this draft")
    title: str = Field(description="Post title — clear, specific, no clickbait")
    body: str = Field(description="Markdown body. Authentic, value-first.")
    subreddit: str = Field(description="Target subreddit, e.g. 'programming'")
    flair: str = Field(default="", description="Optional post flair label")
    post_type: str = Field(
        default="discussion",
        description="One of: discussion, til, help, show-and-tell",
    )
    self_promo_level: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Self-promotion 0-10. Keep ≤1 for safety.",
    )
    source: ContentSource
    created_at: str = ""


class RedditPostResponse(BaseModel):
    post: RedditPost
