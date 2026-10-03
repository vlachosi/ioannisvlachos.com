"""Generate the shared social card from the same profile used by the website.

Only a cache miss starts Chromium. The PNG's digest versions its URL while the
stable file path keeps earlier shared URLs valid after later content edits.
"""
from __future__ import annotations

import base64
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import struct
from urllib.parse import urlsplit

import yaml

SIZE = (1200, 630)
FONTS = {
    "petrona": "petrona-latin-wght-normal.woff2",
    "mono": "jetbrains-mono-latin-wght-normal.woff2",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_changed(path: Path, data: bytes) -> None:
    if not path.is_file() or path.read_bytes() != data:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def _png_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def _card_data(root: Path, profile: dict) -> dict:
    config = yaml.safe_load((root / "_quarto.yml").read_text(encoding="utf-8"))
    address = urlsplit(config["website"]["site-url"])
    if address.scheme not in {"http", "https"} or not address.netloc:
        raise ValueError("website.site-url must be an absolute HTTP(S) URL")
    palette_source = (root / "styles/light.scss").read_text(encoding="utf-8")
    palette = {}
    for key in ("paper", "ink", "muted", "accent"):
        match = re.search(r"\$" + key + r":\s*(#[0-9a-fA-F]{6})\s*;", palette_source)
        if not match:
            raise ValueError(f"Sharing image: expected a six-digit ${key} colour in styles/light.scss")
        palette[key] = match.group(1)
    return {
        "name": str(profile["name"]).strip(),
        "role": str(profile.get("role") or "").strip(),
        "affiliation": str(profile.get("affiliation") or "").strip(),
        "domain": (address.netloc + address.path).rstrip("/"),
        "palette": palette,
    }


def _document(template: str, data: dict, fonts: dict[str, bytes]) -> str:
    # Text is drawn on a canvas, never interpreted as HTML. Escape script
    # delimiters too, so even an unusual CMS name cannot end the JSON element.
    encoded = json.dumps(data, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    document = template
    for key, content in fonts.items():
        document = document.replace(f"__FONT_{key.upper()}__", base64.b64encode(content).decode("ascii"))
    return document.replace("__CARD_DATA__", encoded)


def _render(document: str) -> tuple[bytes, dict]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Exception as error:
            raise RuntimeError(
                "Sharing image renderer could not start. Install requirements.txt and run "
                "'python -m playwright install --with-deps chromium --only-shell'."
            ) from error
        try:
            context = browser.new_context(
                viewport={"width": SIZE[0], "height": SIZE[1]},
                device_scale_factor=1, locale="en-AU", color_scheme="light",
                reduced_motion="reduce",
            )
            # The template embeds its fonts and profile. Rendering never needs
            # a network service, a CMS login, or access to external resources.
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_content(document, wait_until="load")
            layout = page.evaluate("renderCard()")
            png = page.locator("canvas").screenshot(type="png", animations="disabled")
        finally:
            browser.close()
    if _png_size(png) != SIZE:
        raise RuntimeError("Sharing image renderer returned an unexpected PNG size")
    return png, layout


def generate_social_image(root: Path, profile: dict) -> dict:
    """Generate/cache the card, returning Quarto website image and alt metadata."""
    root = Path(root)
    data = _card_data(root, profile)
    template = (root / "templates/social-card.html").read_text(encoding="utf-8")
    fonts = {key: (root / "assets/fonts" / name).read_bytes() for key, name in FONTS.items()}
    inputs = {
        "data": data, "template": template, "size": SIZE,
        "fonts": {key: _sha(value) for key, value in fonts.items()},
        "playwright": version("playwright"), "generator": _sha(Path(__file__).read_bytes()),
    }
    input_digest = _sha(json.dumps(inputs, sort_keys=True).encode("utf-8"))
    output = root / "assets/generated/social-preview.png"
    cache_path = root / "_generated/social-image.json"
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        png = output.read_bytes()
        valid_cache = (
            cache.get("input_digest") == input_digest
            and cache.get("image_digest") == _sha(png)
            and _png_size(png) == SIZE
        )
    except (OSError, ValueError, TypeError, AttributeError):
        valid_cache = False
    if not valid_cache:
        png, layout = _render(_document(template, data, fonts))
        cache = {"input_digest": input_digest, "image_digest": _sha(png), "layout": layout}
        _write_changed(output, png)
        _write_changed(cache_path, (json.dumps(cache, indent=2) + "\n").encode("utf-8"))
    # Keep the image URL used by earlier versions of the website alive too.
    _write_changed(root / "assets/og.png", png)
    position = " at ".join(part for part in (data["role"], data["affiliation"]) if part)
    alt = ". ".join(part for part in (data["name"], position, data["domain"]) if part)
    return {
        "image": f"/assets/generated/social-preview.png?v={cache['image_digest'][:16]}",
        "image-alt": alt,
    }
