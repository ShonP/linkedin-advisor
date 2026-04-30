"""Generate LinkedIn dark-mode preview images with optional embedded diagram."""

from __future__ import annotations

import base64
import hashlib
import html as html_mod
from pathlib import Path

from html2image import Html2Image

_PREVIEWS_DIR = Path("data/previews")

_CSS = """
body { margin:0; padding:0; background:#1B1F23; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }
.card { width:560px; background:#1E2328; border-radius:8px; border:1px solid #333; margin:20px auto; overflow:hidden; }
.header { display:flex; align-items:center; padding:16px 16px 0; }
.avatar { width:48px; height:48px; border-radius:50%; background:#0a66c2; color:white; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:18px; flex-shrink:0; }
.info { margin-left:12px; }
.name { color:#E8E6E3; font-weight:600; font-size:15px; }
.headline { color:#A8A29E; font-size:12px; margin-top:2px; }
.time { color:#A8A29E; font-size:12px; margin-top:2px; }
.body { padding:12px 16px; color:#E8E6E3; font-size:14px; line-height:1.5; direction:rtl; unicode-bidi:plaintext; white-space:pre-wrap; word-wrap:break-word; }
.post-image { width:100%; }
.post-image img { width:100%; display:block; }
.actions { display:flex; justify-content:space-around; padding:8px 16px 12px; border-top:1px solid #333; color:#A8A29E; font-size:13px; }
.action { display:flex; align-items:center; gap:4px; }
"""

_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div class="card">
  <div class="header">
    <div class="avatar">SP</div>
    <div class="info">
      <div class="name">{author}</div>
      <div class="headline">Senior AI Engineer | Production LLM Systems</div>
      <div class="time">1h • 🌐</div>
    </div>
  </div>
  <div class="body">{body}</div>
  {image_section}
  <div class="actions">
    <div class="action">👍 Like</div>
    <div class="action">💬 Comment</div>
    <div class="action">🔄 Repost</div>
    <div class="action">📤 Send</div>
  </div>
</div>
</body></html>"""


def generate_preview_image(
    post_text: str,
    author: str = "Shon Pazarker",
    diagram_path: str | Path | None = None,
) -> Path:
    """Render a LinkedIn dark-mode post preview as PNG, optionally with embedded diagram."""
    _PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)

    body_html = html_mod.escape(post_text)

    # Embed diagram as base64 if provided
    image_section = ""
    if diagram_path:
        dp = Path(diagram_path)
        if dp.exists():
            b64 = base64.b64encode(dp.read_bytes()).decode()
            ext = dp.suffix.lstrip(".")
            mime = "image/png" if ext == "png" else f"image/{ext}"
            image_section = f'<div class="post-image"><img src="data:{mime};base64,{b64}"/></div>'

    full_html = _TEMPLATE.format(
        css=_CSS,
        author=html_mod.escape(author),
        body=body_html,
        image_section=image_section,
    )

    file_id = hashlib.md5((post_text + str(diagram_path)).encode()).hexdigest()[:12]
    filename = f"{file_id}.png"

    height = 1800 if diagram_path else 1400
    hti = Html2Image(output_path=str(_PREVIEWS_DIR), size=(620, height))
    hti.screenshot(html_str=full_html, save_as=filename)

    path = _PREVIEWS_DIR / filename
    try:
        from PIL import Image
        img = Image.open(path)
        bbox = img.getbbox()
        if bbox:
            img = img.crop((0, 0, bbox[2], bbox[3] + 10))
            img.save(path)
    except ImportError:
        pass

    return path
