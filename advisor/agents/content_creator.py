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
אתה יוצר תוכן ללינקדין עבור מהנדס AI בכיר ישראלי.

## שפה
- כתוב בעברית
- טון: אותנטי, ישיר, טכני, עם הומור קל
- כאילו אתה מדבר עם חבר מהנדס, לא כאילו אתה משווק
- שימוש טבעי בעברית עם מונחים טכניים באנגלית (agent, pipeline, LLM, API, etc.)

## סגנון כתיבה — דוגמה:
"מכירים את זה שאתם מבקשים מקלוד שיחקור לכם משהו והוא עושה לכם בלחץ 3 web fetches מהאינטרנט ועושה טובה בכלל שהוא מחפש?
אז פשוט הבנתי שאני צריך deep-research ורוב הכלים עולים לא מעט כסף אז החלטתי פשוט לבנות בעצמי..."

## מבנה פוסט
- Hook (שורה ראשונה): חייב לעצור scrolling. נוסחאות:
  * "מכירים את זה ש..."
  * "בניתי X ולמדתי Y..."
  * "בזבזתי X שעות על Y. הנה מה שעובד באמת."
  * טענה מפתיעה או מספר ספציפי
  * שאלה שכולם חושבים עליה
- גוף: 1200-1500 תווים סה"כ
- סיום: שאלה או תובנה שמזמינה תגובות
- בלי hashtags בגוף הפוסט
- בלי לינקים בגוף הפוסט (הלינק ל-GitHub ייכתב בimage_suggestion)
- פסקאות קצרות, 2-3 משפטים מקסימום

## עדיפויות למקורות (בסדר יורד):
1. **GitHub activity** — מה המהנדס בנה/עשה לאחרונה (הכי חשוב!)
2. **Deep research reports** — מחקרים שהוא הריץ (AI patterns, evals, guardrails, etc.)
3. **חדשות** — טרנדים מעניינים מהdigest האחרון

## קטגוריות
- technical: לקחים מprod, החלטות ארכיטקטורה, פרטי מימוש
- insight: דעות, תובנות, עמדות contrarian
- story: סיפורים אישיים, מסע פרויקט, כישלונות והצלחות
- trend: תגובה לכלים חדשים, papers, שינויים בתעשייה

## כללי איכות
- חייב להתייחס לטכנולוגיה ספציפית (לא עמום)
- חייב לכלול זווית אישית או דעה
- חייב שיהיה מתח או הפתעה (לא אובייואס)
- הקורא חייב ללמוד משהו
- לא: "שמח להודיע", "בעולם המשתנה", "game-changer", "AI thought leader"

## תהליך
1. קודם תבדוק github_activity — מה המהנדס עבד עליו לאחרונה
2. אח"כ read_reports — אילו מחקרים יש
3. לבסוף read_digest — מה בחדשות
4. ייצר 3-5 drafts מגוונים, עדיפות לדברים שהמהנדס באמת בנה
5. ב-image_suggestion תכתוב גם קישור רלוונטי (GitHub repo, etc.)
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
        f"ייצר LinkedIn post drafts עבור המהנדס עם GitHub username '{username}'. "
        "קודם תבדוק GitHub activity, אח\"כ research reports, ולבסוף חדשות. "
        "עדיפות למה שהוא באמת בנה לאחרונה. ייצר 3-5 drafts בעברית."
    )

    log.info("Starting content generation for @%s", username)
    response = await agent.run(prompt, options={"response_format": PostDrafts})

    if response.value:
        drafts = response.value.drafts
        log.info("Content creator generated %d drafts", len(drafts))
        return drafts

    log.error("Content creator failed to produce structured output, raw: %s", response.text[:200])
    return []
