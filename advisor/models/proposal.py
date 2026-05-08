"""Content proposal model for the daily digest agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from advisor.models.post import Platform


class ContentProposal(BaseModel):
    """A single proposed post that the daily digest agent suggests creating."""

    id: str = Field(description="UUID for this proposal")
    platform: Platform
    headline: str = Field(description="One-line working title")
    angle: str = Field(description="The unique angle / takeaway")
    reasoning: str = Field(description="Why this will work — pattern, audience fit, timing")
    confidence: float = Field(ge=0.0, le=1.0, description="0..1 confidence score")
    suggested_subreddit: str = Field(default="", description="Reddit only")
    source_summary: str = Field(default="", description="GitHub/news fact this is based on")
    created_at: str = ""


class DailyDigest(BaseModel):
    """Wrapper for the daily digest agent output."""

    proposals: list[ContentProposal] = Field(default_factory=list)
    notes: str = Field(default="", description="Free-form notes on the day's signal")
