"""Check the rendered pages, assets, publication rules, and social image URLs."""
from __future__ import annotations

import argparse
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import sys
import xml.etree.ElementTree as ET
import json

import yaml

ROOT = Path(__file__).resolve().parents[1]


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.social_images = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"a", "link"} and attrs.get("href"):
            self.urls.append(attrs["href"])
        if tag in {"img", "script", "source"} and attrs.get("src"):
            self.urls.append(attrs["src"])
        if tag == "meta" and attrs.get("property", attrs.get("name")) in {"og:image", "twitter:image"}:
            self.social_images.append(attrs.get("content", ""))


def local_target(site, page, url, site_host):
    parsed = urlsplit(url)
    if parsed.scheme not in {"", "http", "https"}:
        return None
    if parsed.netloc and parsed.netloc != site_host:
        return None
    if not parsed.path:
        return page
    path = unquote(parsed.path)
    target = (site / path.lstrip("/")) if path.startswith("/") or parsed.netloc else (page.parent / path)
    if target.is_dir() or path.endswith("/"):
        target = target / "index.html"
    return target


def check_site(site, *, drafts=False):
    site = Path(site).resolve()
    config = yaml.safe_load((ROOT / "_quarto.yml").read_text())
    profile = yaml.safe_load((ROOT / "_data/profile.yml").read_text())
    site_host = urlsplit(config["website"]["site-url"]).netloc
    errors = []
    required = ["index.html", "about.html", "research/index.html", "projects/index.html", "writing/index.html", "cv/index.html", "404.html"]
    for page in required:
        file = site / page
        if not file.is_file():
            errors.append(f"Missing page: {page}")
        elif profile["name"] not in unescape(file.read_text()):
            errors.append(f"Missing profile identity: {page}")
    pages = list(site.rglob("*.html"))
    checked = 0
    for page in pages:
        parser = References()
        parser.feed(page.read_text(encoding="utf-8"))
        for url in parser.urls + parser.social_images:
            target = local_target(site, page, url, site_host)
            if target is not None:
                checked += 1
                if not target.is_file():
                    errors.append(f"{page.relative_to(site)}: missing local target {url}")
    for filename in ("search.json", "sitemap.xml", "writing/index.xml"):
        file = site / filename
        if not file.is_file():
            errors.append(f"Missing generated metadata: {filename}")
        else:
            data = file.read_text()
            try:
                json.loads(data) if filename.endswith(".json") else ET.fromstring(data)
            except (ValueError, ET.ParseError):
                errors.append(f"Invalid generated metadata: {filename}")
    publication_files = ["index.html", "writing/index.html", "search.json", "sitemap.xml", "writing/index.xml"]
    for source in (ROOT / "writing/posts").rglob("index.qmd"):
        # Content validation runs first, so these front matter records are valid.
        front = source.read_text().split("---", 2)[1]
        post = yaml.safe_load(front)
        if not post.get("draft"):
            continue
        relative = source.parent.relative_to(ROOT).as_posix()
        for name in publication_files:
            file = site / name
            if file.is_file() and not drafts and relative in file.read_text():
                errors.append(f"Draft leaked into production {name}: {relative}")
        rendered = site / relative / "index.html"
        if drafts and (not rendered.is_file() or escape(post["title"]) not in rendered.read_text()):
            errors.append(f"Draft preview is missing: {relative}")
    for kind, source_path, page_path in [
        ("research", "research/papers.yml", "research/index.html"),
        ("projects", "projects/projects.yml", "projects/index.html"),
    ]:
        records = yaml.safe_load((ROOT / source_path).read_text()) or []
        rendered = (site / page_path).read_text()
        for record in records:
            visible = drafts or not (record.get("draft") or record.get("placeholder"))
            title = escape(record["title"], quote=False)
            if visible and title not in rendered:
                errors.append(f"{kind}: expected entry missing: {record['title']}")
            if not visible and title in rendered:
                errors.append(f"{kind}: unpublished entry leaked: {record['title']}")
    sections = profile.get("sections") or {}
    for section in ("talks", "teaching"):
        if bool(sections.get(section)) != (site / section / "index.html").is_file():
            errors.append(f"{section}: output does not match its visibility setting (try a clean build)")
    cv = yaml.safe_load((ROOT / "_data/cv.yml").read_text()) or {}
    if bool(cv.get("source")) != (site / "cv/vlachos-cv.pdf").is_file():
        errors.append("CV output does not match the selected PDF")
    for private_build_path in ("_cv-uploads", "_data", "_generated"):
        if (site / private_build_path).exists():
            errors.append(f"Build/source directory was copied into the site: {private_build_path}")
    if errors:
        raise ValueError("\n".join(dict.fromkeys(errors)))
    print(f"PASS: {len(pages)} HTML pages, {checked} local references, metadata and {'draft' if drafts else 'production'} publication rules.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", nargs="?", default="_site")
    parser.add_argument("--drafts", action="store_true")
    args = parser.parse_args()
    try:
        check_site(args.site, drafts=args.drafts)
    except (ValueError, OSError) as error:
        print(f"Site check failed:\n{error}", file=sys.stderr)
        sys.exit(1)
