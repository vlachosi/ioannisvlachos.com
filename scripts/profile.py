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
    "google_scholar": "Google Scholar",
    "ssrn": "SSRN",
    "repec": "RePEc",
    "arxiv": "arXiv",
    "researchgate": "ResearchGate",
    "semantic_scholar": "Semantic Scholar",
    "scopus": "Scopus",
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
RESEARCH_PROFILES = ("orcid", "google_scholar", "ssrn", "repec", "arxiv", "researchgate", "semantic_scholar", "scopus")
HOME_PROFILES = ("orcid", "google_scholar", "ssrn")
RESEARCH_ICONS = {"orcid": ORCID_ICON, "ssrn": SSRN_ICON}
for key, filename in {
    "google_scholar": "google-scholar.svg",
    "semantic_scholar": "semantic-scholar.svg",
    "scopus": "scopus.svg",
    "arxiv": "arxiv.svg",
    "repec": "ideas-repec.svg",
    "researchgate": "researchgate.svg",
}.items():
    RESEARCH_ICONS[key] = (
        Path(__file__).resolve().parents[1] / "assets/vendor/academicons" / filename
    ).read_text(encoding="utf-8").strip()


def _profile_button(key: str, links: dict, *, icon: bool = False, icon_only: bool = False) -> str:
    """Only configured profiles are shown; icon-only buttons retain a name."""
    if key not in links:
        return ""
    label = LINK_LABELS[key]
    visible_label = "Scholar" if key == "google_scholar" else label
    symbol = RESEARCH_ICONS[key] if icon or icon_only else ""
    content = symbol + ("" if icon_only else f'<span class="profile-label">{visible_label}</span>')
    icon_class = ' class="id-icon-only"' if icon_only else ""
    return f'<li><a{icon_class} href="{escape(links[key], quote=True)}" aria-label="{label} profile">{content}</a></li>'


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
    if key in RESEARCH_PROFILES and key != "orcid":
        return "Profile"
    if key in {"bluesky", "x"}:
        return "@" + path.rsplit("/", 1)[-1]
    return path or LINK_LABELS[key]


def render_profile(profile: dict, generated_dir: Path, repo_root: Path | None = None) -> dict:
    """Write generated includes and return configuration for Quarto to merge."""
    generated_dir = Path(generated_dir)
    repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]
    generated_dir.mkdir(parents=True, exist_ok=True)
    sections = profile.get("sections") or {}
    blog_enabled = sections.get("blog", True)
    name = str(profile["name"])
    role = str(profile.get("role") or "")
    affiliation = str(profile.get("affiliation") or "")
    bio = str(profile.get("bio") or "").strip()
    about_extra = str(profile.get("about_extra") or "").strip()
    email = str(profile.get("email") or "").strip()
    links = {key: str(url).strip() for key, url in (profile.get("links") or {}).items() if key in LINK_LABELS and url and str(url).strip()}
    position = " at ".join(part for part in [role, affiliation] if part)
    description = ", ".join(part for part in [name, position] if part) + "."
    role_html = " at<br>".join(escape(part) for part in [role, affiliation] if part)

    academic_links = [_profile_button(key, links, icon=True, icon_only=(key == "orcid")) for key in HOME_PROFILES if key in links]
    social_links = []
    for key, icon in LINK_ICONS.items():
        if key in links:
            social_links.append(f'<li><a href="{escape(links[key], quote=True)}" aria-label="{LINK_LABELS[key]}"><i class="bi bi-{icon}" aria-hidden="true"></i></a></li>')
    if email:
        social_links.append(f'<li data-email-slot><a href="mailto:{escape(email, quote=True)}" aria-label="Email" title="{escape(email, quote=True)}"><i class="bi bi-envelope" aria-hidden="true"></i></a></li>')
    profile_groups = []
    if academic_links:
        profile_groups.append('<ul class="id-links academic-links" aria-label="Academic profiles">' + "\n".join(academic_links) + '</ul>')
    if social_links:
        profile_groups.append('<ul class="id-links" aria-label="Social profiles and email">' + "\n".join(social_links) + '</ul>')
    home_html = [
        '<div class="hero__text">',
        f'<h1 class="hero__name" id="hero-name">{escape(name)}</h1>',
        '<div class="hero__identity">',
        f'<p class="hero__role">{role_html}</p>' if role_html else "",
        '<div class="hero__profiles">' + "\n".join(profile_groups) + '</div>' if profile_groups else "",
        '</div>',
    ]
    home = "```{=html}\n" + "\n".join(home_html) + "\n```\n\n"
    home += '::: {.hero__about}\n' + bio + '\n\n[More about me →](about.qmd){.more}\n:::\n\n'
    home += '```{=html}\n</div>\n```\n'
    _write_changed(generated_dir / "home-profile.qmd", home)
    research_buttons = [_profile_button(key, links, icon=True) for key in RESEARCH_PROFILES if key in links]
    research_links = '<ul class="id-links research-profiles" aria-label="Research profiles">\n' + "\n".join(research_buttons) + '\n</ul>\n' if research_buttons else ""
    _write_changed(generated_dir / "research-profiles.html", research_links)
    about_bio = "\n\n".join(part for part in (bio, about_extra) if part)
    _write_changed(generated_dir / "bio.qmd", about_bio + "\n")

    elsewhere = []
    if email:
        elsewhere.append(f'<li><span class="label">Email</span><span data-email-slot><a href="mailto:{escape(email, quote=True)}">{escape(email)}</a></span></li>')
    for key, label in LINK_LABELS.items():
        if key not in links:
            continue
        visible_label = "Scholar" if key == "google_scholar" else label
        value = f'<a href="{escape(links[key], quote=True)}">{escape(_display_link(key, links[key]))}</a>'
        elsewhere.append(f'<li><span class="label">{visible_label}</span>{value}</li>')
    _write_changed(generated_dir / "elsewhere.html", '<ul class="elsewhere">\n' + "\n".join(elsewhere) + '\n</ul>\n' if elsewhere else "")

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
    # Quarto recreates listing containers from metadata, even when their body
    # markup is hidden. Omit the Blog listing itself as well as its column.
    home_listings = [{
        "id": "home-research", "contents": "/_generated/papers.yml",
        "template": "templates/home.ejs", "sort": "order",
        "include": {"featured": True}, "max-items": 2,
        "template-params": {"kind": "research", "empty": "Papers will appear here."},
    }]
    if blog_enabled:
        home_listings.append({
            "id": "home-blog", "contents": "writing/posts",
            "template": "templates/home.ejs", "sort": "date desc", "max-items": 3,
            "template-params": {"kind": "writing", "empty": "Nothing published yet. The first post is on its way."},
        })
    home_listings.append({
        "id": "home-projects", "contents": "/_generated/projects.yml",
        "template": "templates/home.ejs", "sort": "order",
        "include": {"featured": True}, "max-items": 2,
        "template-params": {"kind": "projects", "empty": "Code will appear here."},
    })
    _write_changed(generated_dir / "home.yml", yaml.safe_dump({
        "pagetitle": name, "description": description, "listing": home_listings,
    }, allow_unicode=True, sort_keys=False))

    subscriptions = [("all", "All updates", "/index.xml", (
        "New blog posts, research announcements and code." if blog_enabled
        else "Research announcements and code."
    ))]
    if blog_enabled:
        subscriptions.append(("blog", "Blog", "/writing/index.xml", "Posts on research, financial markets, statistics and code."))
    subscriptions.extend([
        ("research", "Research", "/research/index.xml", "Announcements of papers and other research outputs."),
        ("code", "Code", "/projects/index.xml", "New packages, replication code and templates."),
    ])
    options = ['<div class="subscription-options">']
    discovery = []
    for key, label, url, summary in subscriptions:
        options.append(f'''<section class="subscription-option" aria-labelledby="subscribe-{key}">
  <h2 id="subscribe-{key}">{label}</h2>
  <p>{summary}</p>
  <div class="subscription-actions">
    <a class="btn-line" href="{url}" type="application/rss+xml" aria-label="Open feed: {label}"><i class="bi bi-rss" aria-hidden="true"></i> Open feed</a>
    <button class="btn-line" type="button" data-copy-feed="feed-{key}" data-feed-label="{label}" aria-label="Copy link: {label} feed" hidden><i class="bi bi-copy" aria-hidden="true"></i> <span data-copy-label>Copy link</span></button>
  </div>
  <a class="feed-address" id="feed-{key}" href="{url}" type="application/rss+xml">https://ioannisvlachos.com{url}</a>
</section>''')
        discovery.append(f'<link rel="alternate" type="application/rss+xml" title="{escape(name, quote=True)} — {label}" href="{url}">')
    options.append('</div>')
    _write_changed(generated_dir / "subscriptions.html", "\n".join(options) + "\n")
    _write_changed(generated_dir / "subscribe.yml", yaml.safe_dump({
        "include-in-header": {"text": "\n".join(discovery)},
    }, allow_unicode=True, sort_keys=False))

    navigation = [
        {"text": "About", "href": "about.qmd"},
        {"text": "Research", "href": "research/index.qmd"},
        {"text": "Code", "href": "projects/index.qmd"},
    ]
    for section, label in [("teaching", "Teaching"), ("talks", "Talks")]:
        if sections.get(section):
            navigation.append({"text": label, "href": f"{section}/index.qmd"})
    if blog_enabled:
        navigation.append({"text": "Blog", "href": "writing/index.qmd"})
    navigation.append({"text": "CV", "href": "cv/index.qmd"})

    return {
        "blog-enabled": blog_enabled,
        "has-contact-links": bool(elsewhere),
        "project": {"render": ["*.qmd"] + [f"!{section}/" for section in ["talks", "teaching"] if not sections.get(section)] + ([] if blog_enabled else ["!writing/"])},
        "website": {
            "title": name,
            "description": description,
            "navbar": {"title": name, "right": navigation},
            "twitter-card": {"creator": _display_link("x", links["x"]) if "x" in links else ""},
            "page-footer": {
                "left": f"© {date.today().year} {name}",
                "center": [{"text": LINK_LABELS[key], "href": links[key]} for key in LINK_ICONS if key in links],
            },
        },
        "format": {
            "html": {
                "include-in-header": str((generated_dir / "head.html").relative_to(repo_root)),
                "include-after-body": str((generated_dir / "after-body.html").relative_to(repo_root)),
            },
        },
    }
