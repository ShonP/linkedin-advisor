"""Twitter/X-specific post model."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from advisor.models.post import ContentSource

TWEET_MAX = 280


class TwitterPost(BaseModel):
    """Single tweet or a thread.

    `text` is the lead tweet (≤280 chars). `thread` holds follow-up tweets
    when the post is a thread; empty list means single tweet.
    """

    id: str = Field(description="UUID for this draft")
    text: str = Field(description="Lead tweet, ≤280 chars")
    thread: list[str] = Field(default_factory=list, description="Follow-up tweets in order")
    hashtags: list[str] = Field(default_factory=list, description="Suggested hashtags without #")
    source: ContentSource
    created_at: str = ""

    @field_validator("text")
    @classmethod
    def _check_lead(cls, v: str) -> str:
        if len(v) > TWEET_MAX:
            raise ValueError(f"lead tweet exceeds {TWEET_MAX} chars: {len(v)}")
        return v

    @field_validator("thread")
    @classmethod
    def _check_thread(cls, v: list[str]) -> list[str]:
        for i, t in enumerate(v):
            if len(t) > TWEET_MAX:
                raise ValueError(f"thread[{i}] exceeds {TWEET_MAX} chars: {len(t)}")
        return v

    def is_thread(self) -> bool:
        return bool(self.thread)


class TwitterPostResponse(BaseModel):
    post: TwitterPost
