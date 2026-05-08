"""Copy-analysis models: patterns, examples, and tone guidelines per platform."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from advisor.models.post import Platform


class PostExample(BaseModel):
    """A successful post observed in the wild."""

    platform: Platform
    author: str = ""
    url: str = ""
    snippet: str = Field(description="First ~300 chars of the post body")
    engagement: str = Field(default="", description="e.g. '12k upvotes', '450 likes'")


class Pattern(BaseModel):
    """A recurring structural or stylistic pattern."""

    name: str = Field(description="Short label, e.g. 'curiosity_gap_hook'")
    description: str
    example: str = Field(default="", description="Concrete example string from observed posts")


class ToneGuideline(BaseModel):
    """Per-platform tone, voice, and structural rules."""

    platform: Platform
    voice: str
    structure: str
    do: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    hashtag_strategy: str = ""


HookCategory = Literal["curiosity_gap", "bold_claim", "story", "question", "metric", "contrarian"]


class CopyAnalysis(BaseModel):
    """Aggregated learnings from successful posts in a niche."""

    niche: str
    platforms: list[Platform]
    patterns: list[Pattern]
    examples: list[PostExample]
    tones: list[ToneGuideline]
    top_hook_categories: list[HookCategory] = Field(default_factory=list)
    summary: str = Field(default="", description="One-paragraph executive summary")
    created_at: str = ""


class CopyAnalysisResponse(BaseModel):
    analysis: CopyAnalysis
