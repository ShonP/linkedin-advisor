"""LinkedIn dark-mode post preview image generator using Playwright."""

from __future__ import annotations

import tempfile
import uuid
from html import escape
from pathlib import Path

_PREVIEWS_DIR = Path("data/previews")

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=600">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #1B1F23; display: flex; justify-content: center; padding: 24px; font-family: -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; }}
  .card {{ background: #1E2328; border: 1px solid #333840; border-radius: 8px; width: 552px; overflow: hidden; }}
  .header {{ display: flex; align-items: flex-start; padding: 16px 16px 0; gap: 10px; }}
  .avatar {{ width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #0A66C2, #004182); display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 16px; flex-shrink: 0; letter-spacing: 1px; }}
  .meta {{ flex: 1; min-width: 0; }}
  .name {{ color: #FFFFFF; font-size: 15px; font-weight: 600; line-height: 1.3; }}
  .headline {{ color: #A8A29E; font-size: 13px; line-height: 1.4; margin-block-start: 2px; }}
  .time {{ color: #A8A29E; font-size: 12px; margin-block-start: 2px; }}
  .body {{ padding: 12px 16px 16px; color: #E8E6E3; font-size: 14px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; unicode-bidi: plaintext; direction: auto; }}
  .body .hook {{ font-weight: 600; display: block; margin-block-end: 8px; font-size: 15px; color: #F5F5F5; }}
  .separator {{ height: 1px; background: #333840; margin: 0 16px; }}
  .actions {{ display: flex; justify-content: space-around; padding: 8px 16px; }}
  .action {{ display: flex; align-items: center; gap: 6px; color: #A8A29E; font-size: 13px; font-weight: 600; padding: 8px 12px; border-radius: 4px; }}
  .action svg {{ width: 20px; height: 20px; fill: #A8A29E; }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div class="avatar">{initials}</div>
    <div class="meta">
      <div class="name">{author}</div>
      <div class="headline">Senior AI Engineer</div>
      <div class="time">עכשיו · 🌐</div>
    </div>
  </div>
  <div class="body">
    <span class="hook">{hook}</span>
    {body}
  </div>
  <div class="separator"></div>
  <div class="actions">
    <div class="action"><svg viewBox="0 0 24 24"><path d="M19.46 11l-3.91-3.91a7 7 0 0 0-1.69-1.19 1 1 0 0 0-1.16.39c-.47.8-.2 1.84.6 2.32a5 5 0 0 1 1.21.85l3.91 3.91a1 1 0 0 0 1.42 0 1 1 0 0 0 0-1.42z"/></svg> אהבתי</div>
    <div class="action"><svg viewBox="0 0 24 24"><path d="M7 9h10v1H7zm0 4h7v-1H7zm0-8h10V4H7zm11.5-2h-13A1.5 1.5 0 0 0 4 4.5v10A1.5 1.5 0 0 0 5.5 16H9l3 3 3-3h3.5a1.5 1.5 0 0 0 1.5-1.5v-10A1.5 1.5 0 0 0 18.5 3z"/></svg> תגובה</div>
    <div class="action"><svg viewBox="0 0 24 24"><path d="M13.96 5H6C4.9 5 4 5.9 4 7v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V9.04L13.96 5zM14 14H8v-1h6v1zm2-3H8V9.98h8V11z"/></svg> שיתוף</div>
    <div class="action"><svg viewBox="0 0 24 24"><path d="M21 3L0 10l7.66 4.26L14 8l-6.26 6.34L12 21l9-18z"/></svg> שלח</div>
  </div>
</div>
</body>
</html>
"""


async def generate_preview_image(post_text: str, author: str = "Shon Pazarker") -> Path:
    """Render a LinkedIn dark-mode preview of the post and return the PNG path."""
    from playwright.async_api import async_playwright

    parts = post_text.split("\n", 1)
    hook = escape(parts[0])
    body = escape(parts[1]) if len(parts) > 1 else ""

    initials = "".join(w[0].upper() for w in author.split()[:2])
    html = _HTML_TEMPLATE.format(
        initials=initials,
        author=escape(author),
        hook=hook,
        body=body,
    )

    _PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    preview_path = _PREVIEWS_DIR / f"{uuid.uuid4().hex[:12]}.png"

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        f.write(html)
        html_path = f.name

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 600, "height": 100})
            await page.goto(f"file://{html_path}")
            card = page.locator(".card")
            await card.screenshot(path=str(preview_path))
            await browser.close()
    finally:
        Path(html_path).unlink(missing_ok=True)

    return preview_path
