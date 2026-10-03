"""Render shared profile data into Quarto includes and metadata.

Called by prepare-site.py before Quarto renders. Generated includes are local
build inputs; _data/profile.yml remains the only editable identity record.
"""

from datetime import date
from html import escape
import json
from pathlib import Path
from urllib.parse import urlparse

import yaml


LINK_LABELS = {
    "orcid": "ORCID",
    "ssrn": "SSRN",
    "github": "GitHub",
    "linkedin": "LinkedIn",
    "bluesky": "Bluesky",
    "x": "X",
}
LINK_ICONS = {
    "github": "github",
    "linkedin": "linkedin",
    "bluesky": "bluesky",
    "x": "twitter-x",
}
ORCID_ICON = '<svg class="orcid-icon" viewBox="0 0 256 256" aria-hidden="true"><circle cx="128" cy="128" r="128" fill="#A6CE39"/><g fill="#fff"><rect x="70" y="102" width="18" height="84" rx="1"/><circle cx="79" cy="79" r="11.5"/><path d="M108 102h44c26 0 46 18.5 46 42s-20 42-46 42h-44zM126 118v52h25c17 0 29-11 29-26s-12-26-29-26z"/></g></svg>'
SSRN_ICON = '<svg class="ssrn-icon" viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="6" fill="#2A63AB"/><rect x="4" y="4" width="56" height="56" rx="3" fill="none" stroke="#fff" stroke-opacity="0.55" stroke-width="1.5"/><text x="32" y="40" text-anchor="middle" font-family="Petrona, Georgia, serif" font-size="20" font-weight="700" fill="#fff" letter-spacing="-0.5">SSRN</text></svg>'


def _write_changed(path: Path, content: str) -> None:
    # Unchanged includes must keep their timestamps during live preview.
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def _display_link(key: str, url: str) -> str:
    """Use the public handle in the About page's compact link list."""
    path = urlparse(url).path.strip("/")
    if key == "ssrn":
        return "Author page"
    if key in {"bluesky", "x"}:
        return "@" + path.rsplit("/", 1)[-1]
    return path or LINK_LABELS[key]


def render_profile(profile: dict, generated_dir: Path, repo_root: Path | None = None) -> dict:
    """Write generated includes and return configuration for Quarto to merge."""
    generated_dir = Path(generated_dir)
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]
    generated_dir.mkdir(parents=True, exist_ok=True)
    name = str(profile["name"])
    role = str(profile.get("role") or "")
    affiliation = str(profile.get("affiliation") or "")
    bio = str(profile.get("bio") or "").strip()
    about_extra = str(profile.get("about_extra") or "").strip()
    email = str(profile.get("email") or "").strip()
    links = {key: str(url) for key, url in (profile.get("links") or {}).items() if key in LINK_LABELS and url}
    position = " at ".join(part for part in [role, affiliation] if part)
    description = ", ".join(part for part in [name, position] if part) + "."
    role_html = " at<br>".join(escape(part) for part in [role, affiliation] if part)

    academic_links = []
    for key, icon in [("orcid", ORCID_ICON), ("ssrn", SSRN_ICON)]:
        if key in links:
            label = "SSRN author page" if key == "ssrn" else "ORCID"
            title = label if key == "ssrn" else "ORCID " + _display_link(key, links[key])
            academic_links.append(f'<li><a href="{escape(links[key], quote=True)}" aria-label="{label}" title="{escape(title, quote=True)}">{icon} {LINK_LABELS[key]}</a></li>')
    social_links = []
    for key, icon in LINK_ICONS.items():
        if key in links:
            social_links.append(f'<li><a href="{escape(links[key], quote=True)}" aria-label="{LINK_LABELS[key]}"><i class="bi bi-{icon}" aria-hidden="true"></i></a></li>')
    social_links.append('<li data-email-slot><span class="id-placeholder" title="Email address to be added"><i class="bi bi-envelope" aria-hidden="true"></i><span class="sr-only">Email (placeholder)</span></span></li>')
    home_html = [
        '<div class="hero__text">',
        f'<h1 class="hero__name" id="hero-name">{escape(name)}</h1>',
        '<div class="hero__identity">',
        f'<p class="hero__role">{role_html}</p>' if role_html else "",
        '<ul class="id-links" aria-label="Academic profiles">' + "\n".join(academic_links) + '</ul>' if academic_links else "",
        '<ul class="id-links" aria-label="Social profiles and email">' + "\n".join(social_links) + '</ul>',
        '</div>',
    ]
    home = "```{=html}\n" + "\n".join(home_html) + "\n```\n\n"
    home += '::: {.hero__about}\n' + bio + '\n\n[More about me →](about.qmd){.more}\n:::\n\n'
    home += '```{=html}\n</div>\n```\n'
    _write_changed(generated_dir / "home-profile.qmd", home)
    about_bio = "\n\n".join(part for part in (bio, about_extra) if part)
    _write_changed(generated_dir / "bio.qmd", about_bio + "\n")

    elsewhere = ['<ul class="elsewhere">', '<li><span class="label">Email</span><span data-email-slot><span class="placeholder-tag" style="margin-left:0">placeholder</span></span></li>']
    for key, label in LINK_LABELS.items():
        if key in links:
            elsewhere.append(f'<li><span class="label">{label}</span><a href="{escape(links[key], quote=True)}">{escape(_display_link(key, links[key]))}</a></li>')
    elsewhere.append('</ul>')
    _write_changed(generated_dir / "elsewhere.html", "\n".join(elsewhere) + "\n")

    head = (repo_root / "_includes/head.html").read_text(encoding="utf-8")
    head += f'<meta name="author" content="{escape(name, quote=True)}">\n'
    for key in ["github", "bluesky"]:
        if key in links:
            head += f'<link rel="me" href="{escape(links[key], quote=True)}">\n'
    _write_changed(generated_dir / "head.html", head)

    # Escape HTML delimiters even inside JSON: </script> must never close the
    # data element. This address is public contact data, not a stored secret.
    contact_json = json.dumps({"email": email}, ensure_ascii=False)
    contact_json = contact_json.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    after_body = f'<script type="application/json" id="site-contact">{contact_json}</script>\n'
    after_body += (repo_root / "_includes/after-body.html").read_text(encoding="utf-8")
    _write_changed(generated_dir / "after-body.html", after_body)
    _write_changed(generated_dir / "home.yml", yaml.safe_dump({"pagetitle": name, "description": description}, allow_unicode=True, sort_keys=False))

    sections = profile.get("sections") or {}
    navigation = [
        {"text": "About", "href": "about.qmd"},
        {"text": "Research", "href": "research/index.qmd"},
        {"text": "Writing", "href": "writing/index.qmd"},
        {"text": "Projects", "href": "projects/index.qmd"},
    ]
    for section, label in [("talks", "Talks"), ("teaching", "Teaching")]:
        if sections.get(section):
            navigation.append({"text": label, "href": f"{section}/index.qmd"})
    navigation.append({"text": "CV", "href": "cv/index.qmd"})

    return {
        "project": {"render": ["*.qmd"] + [f"!{section}/" for section in ["talks", "teaching"] if not sections.get(section)]},
        "website": {
            "title": name,
            "description": description,
            "navbar": {"title": name, "right": navigation},
            "twitter-card": {"creator": _display_link("x", links["x"]) if "x" in links else ""},
            "page-footer": {
                "left": f"© {date.today().year} {name}",
                "center": [{"text": label, "href": links[key]} for key, label in LINK_LABELS.items() if key in links],
            },
        },
        "format": {
            "html": {
                "include-in-header": str((generated_dir / "head.html").relative_to(repo_root)),
                "include-after-body": str((generated_dir / "after-body.html").relative_to(repo_root)),
            },
        },
    }
