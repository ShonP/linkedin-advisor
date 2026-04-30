"""Tool: generate images via Azure OpenAI gpt-image-2."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import httpx

from advisor.config import get_settings
from advisor.log import log

_IMAGES_DIR = Path("data/images")


def generate_image(prompt: str, filename: str = "", size: str = "1536x1024") -> Path | None:
    """Generate an image using gpt-image-2 deployment endpoint."""
    settings = get_settings()
    _IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    if not filename:
        h = hashlib.md5(prompt.encode()).hexdigest()[:12]
        filename = f"img-{h}.png"

    endpoint = settings.azure_image_endpoint
    if not endpoint:
        log.error("AZURE_IMAGE_ENDPOINT not set")
        return None

    try:
        resp = httpx.post(
            endpoint,
            headers={"api-key": settings.azure_api_key, "Content-Type": "application/json"},
            json={"prompt": prompt, "n": 1, "size": size},
            timeout=300,
        )
        resp.raise_for_status()
        data = resp.json()
        b64 = data["data"][0]["b64_json"]
        img_bytes = base64.b64decode(b64)

        path = _IMAGES_DIR / filename
        path.write_bytes(img_bytes)
        log.info("Generated image: %s (%d bytes)", path, len(img_bytes))
        return path
    except Exception as e:
        log.error("Image generation failed: %s", e)
        return None
