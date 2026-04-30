"""Content creator agent: generates LinkedIn post drafts with structured output."""

from __future__ import annotations

from agent_framework import Agent

from advisor.client import get_chat_client
from advisor.config import get_settings
from advisor.log import log
from advisor.middleware import caching, llm_call_logging, retry, tool_call_logging
from advisor.models.post import PostDraft, SingleDraftResponse
from advisor.tools.github_activity import github_activity
from advisor.tools.read_digest import read_digest
from advisor.tools.read_repo import read_repo
from advisor.tools.read_reports import read_reports

SYSTEM_PROMPT = """\
אתה יוצר תוכן ללינקדין עבור שון, מהנדס AI בכיר ישראלי.

## פרסונה
- role: Senior AI Engineer
- niche: Production LLM systems, AI agents, research tools
- audience: מהנדסי AI, CTOs, מפתחים בכירים
- voice: טכני, כנה, פרקטי, עם הומור קל
- avoid: hype, buzzwords, engagement bait, "שמח להודיע", "game-changer"

## שפה ושפת כתיבה
- עברית נקייה ופשוטה — הימנע ממילים באנגלית כשיש מקבילה טבעית בעברית
- "סוכן מחקר" ולא "research agent", "שאילתות חיפוש" ולא "search queries"
- מונחים טכניים באנגלית רק כשאין באמת חלופה (GitHub, API, LLM, RSS, README)
- משפטים קצרים. שורה אחת לכל רעיון. רווח בין פסקאות.
- לא buzzwords — תתאר מה קורה, לא את שם הclass
- "מפרק את השאלה לנושאים" ולא "OutlineAgent מפרק"
- "מריץ חיפוש במקביל" ולא "Supervisor dispatches parallel queries"

## סגנון דוגמה:
"מכירים את זה שאתם מבקשים מקלוד שיחקור לכם משהו והוא עושה לכם בלחץ 3 web fetches?
אז הבנתי שאני צריך deep-research ורוב הכלים עולים לא מעט כסף אז החלטתי פשוט לבנות בעצמי..."

## Hook Formulas (בחר אחד לפוסט):
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
- גוף: 800-1200 תווים סה"כ (כולל hook!) — זה חובה, לא יותר!
- פוסט קצר וחד עדיף על פוסט ארוך ומפורט
- מקסימום 6-8 פסקאות קצרות
- פסקאות קצרות (2-3 משפטים)
- סיום: שאלה שמזמינה תגובות
- בלי hashtags, בלי לינקים בגוף
- ב-image_suggestion: תיאור באנגלית בלבד של דיאגרמת ארכיטקטורה (MUST be in English for image generation)

## תהליך
1. github_activity — מה שון עבד עליו (עדיפות ראשונה!)
2. read_reports — מחקרים שהריץ
3. read_digest — חדשות אחרונות
4. ייצר draft אחד, הכי חזק, בעברית
"""

EDIT_SYSTEM_PROMPT = """\
אתה עורך תוכן ללינקדין. קיבלת פוסט קיים והוראות עריכה.
ערוך את הפוסט לפי ההוראות בדיוק. שמור על הסגנון, האורך, והמבנה של הפוסט המקורי.
אל תשנה את הנושא אלא אם ההוראות מבקשות זאת.
החזר את הפוסט המעודכן בפורמט המבוקש.
"""


async def generate_single_draft(topic: str = "") -> PostDraft | None:
    """Run the content creator agent and return a single PostDraft."""
    settings = get_settings()
    username = settings.github_username or "ShonP"

    agent = Agent(
        client=get_chat_client(),
        name="content-creator",
        instructions=SYSTEM_PROMPT,
        tools=[github_activity, read_repo, read_digest, read_reports],
        middleware=[tool_call_logging, caching, retry, llm_call_logging],
    )

    topic_line = f"הנושא: {topic}. " if topic else ""
    prompt = (
        f"ייצר LinkedIn post draft אחד עבור שון (GitHub: {username}). "
        f"{topic_line}"
        "קודם תבדוק GitHub activity, אח\"כ research reports, ולבסוף חדשות. "
        "עדיפות למה שהוא באמת בנה. ייצר draft אחד בעברית."
    )

    log.info("Starting single draft generation for @%s", username)
    response = await agent.run(prompt, options={"response_format": SingleDraftResponse})

    if response.value:
        log.info("Content creator generated draft: %s", response.value.draft.hook[:60])
        return response.value.draft

    log.error("Content creator failed, raw: %s", response.text[:200])
    return None


async def edit_post_draft(original_text: str, instructions: str) -> PostDraft | None:
    """Revise an existing draft based on edit instructions."""
    agent = Agent(
        client=get_chat_client(),
        name="content-editor",
        instructions=EDIT_SYSTEM_PROMPT,
        tools=[],
        middleware=[llm_call_logging],
    )

    prompt = f"הפוסט המקורי:\n\n{original_text}\n\nהוראות עריכה: {instructions}"

    log.info("Editing draft with instructions: %s", instructions[:80])
    response = await agent.run(prompt, options={"response_format": SingleDraftResponse})

    if response.value:
        log.info("Editor produced revised draft")
        return response.value.draft

    log.error("Edit failed, raw: %s", response.text[:200])
    return None
