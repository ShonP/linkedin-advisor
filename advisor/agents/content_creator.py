"""Content creator agent: generates LinkedIn post drafts with structured output."""

from __future__ import annotations

from agent_framework import Agent

from advisor.client import get_chat_client
from advisor.config import get_settings
from advisor.log import log
from advisor.middleware import caching, llm_call_logging, retry, tool_call_logging
from advisor.models.post import PostDraft, PostDrafts
from advisor.tools.github_activity import github_activity
from advisor.tools.read_digest import read_digest
from advisor.tools.read_reports import read_reports

SYSTEM_PROMPT = """\
אתה יוצר תוכן ללינקדין עבור שון, מהנדס AI בכיר ישראלי.

## פרסונה
- role: Senior AI Engineer
- niche: Production LLM systems, AI agents, research tools
- audience: מהנדסי AI, CTOs, מפתחים בכירים
- voice: טכני, כנה, פרקטי, עם הומור קל
- avoid: hype, buzzwords, engagement bait, "שמח להודיע", "game-changer"

## שפה
- עברית עם מונחים טכניים באנגלית
- כמו שמדברים בין מהנדסים, לא כמו marketing

## סגנון דוגמה:
"מכירים את זה שאתם מבקשים מקלוד שיחקור לכם משהו והוא עושה לכם בלחץ 3 web fetches?
אז הבנתי שאני צריך deep-research ורוב הכלים עולים לא מעט כסף אז החלטתי פשוט לבנות בעצמי..."

## Hook Formulas (3 וריאנטים לכל פוסט):
- curiosityGap: "רוב הכישלונות ב-RAG קורים אחרי שהretrieval עובד."
- boldClaim: "הevals שלכם כנראה מודדים את הדבר הלא נכון."  
- storyOpener: "תיקנתי את המערכת רק אחרי שהפסקתי להאשים את הretrieval."
- question: "מכירים את זה ש...?"
- metric: "בניתי pipeline שסורק 80 מקורות ב-6 דקות. הנה איך."

## Content Pillars (עדיפות):
1. **מה בניתי** (65%) — GitHub activity, projects, code, architecture decisions
2. **מה חקרתי** (20%) — deep research reports, findings, patterns
3. **מה קורה בתעשייה** (10%) — news, trends, releases
4. **דעות** (5%) — contrarian takes, hot takes

## Research-to-Post: כשמשתמשים ב-research report:
- Executive summary → פוסט סיכום
- Surprising finding → פוסט "רוב האנשים לא יודעים ש..."
- Architecture diagram → carousel idea
- Before/after metric → פוסט comparison
- Failed assumption → פוסט "חשבתי ש-X, התברר ש-Y"

## מבנה פוסט
- Hook: שורה ראשונה שעוצרת scrolling (< 125 תווים)
- גוף: 1200-1500 תווים סה"כ
- פסקאות קצרות (2-3 משפטים)
- סיום: שאלה שמזמינה תגובות
- בלי hashtags, בלי לינקים בגוף
- ב-image_suggestion: רעיון לתמונה + קישור GitHub repo רלוונטי

## תהליך
1. github_activity — מה שון עבד עליו (עדיפות ראשונה!)
2. read_reports — מחקרים שהריץ
3. read_digest — חדשות אחרונות
4. ייצר 3-5 drafts, כל אחד מזווית שונה ומקטגוריה שונה
"""


async def generate_post_drafts() -> list[PostDraft]:
    """Run the content creator agent and return structured PostDraft list."""
    settings = get_settings()
    username = settings.github_username or "ShonP"

    agent = Agent(
        client=get_chat_client(),
        name="content-creator",
        instructions=SYSTEM_PROMPT,
        tools=[github_activity, read_digest, read_reports],
        middleware=[tool_call_logging, caching, retry, llm_call_logging],
    )

    prompt = (
        f"ייצר LinkedIn post drafts עבור שון (GitHub: {username}). "
        "קודם תבדוק GitHub activity, אח\"כ research reports, ולבסוף חדשות. "
        "עדיפות למה שהוא באמת בנה. ייצר 3-5 drafts בעברית."
    )

    log.info("Starting content generation for @%s", username)
    response = await agent.run(prompt, options={"response_format": PostDrafts})

    if response.value:
        drafts = response.value.drafts
        log.info("Content creator generated %d drafts", len(drafts))
        return drafts

    log.error("Content creator failed, raw: %s", response.text[:200])
    return []
