"""Check the rendered pages, assets, publication rules, and social image URLs."""
from __future__ import annotations

import argparse
from collections import Counter
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import re
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
        self.body_text = []
        self.in_body = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "body":
            self.in_body = True
        if tag in {"a", "link"} and attrs.get("href"):
            self.urls.append(attrs["href"])
        if tag in {"img", "script", "source"} and attrs.get("src"):
            self.urls.append(attrs["src"])
        if tag == "meta" and attrs.get("property", attrs.get("name")) in {"og:image", "twitter:image"}:
            self.social_images.append(attrs.get("content", ""))

    def handle_endtag(self, tag):
        if tag == "body":
            self.in_body = False

    def handle_data(self, data):
        if self.in_body:
            self.body_text.append(data)


class EntryTitles(HTMLParser):
    """Read rendered entry headings without placeholder labels or anchor links."""

    void_tags = set("area base br col embed hr img input link meta param source track wbr".split())

    def __init__(self):
        super().__init__()
        self.titles = []
        self.parts = None
        self.ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        classes = set(dict(attrs).get("class", "").split())
        if tag == "h3" and classes & {"entry-title", "card-title"}:
            self.parts = []
        elif self.parts is not None:
            if tag not in self.void_tags:
                if self.ignored_depth or classes & {"placeholder-tag", "anchorjs-link"}:
                    self.ignored_depth += 1

    def handle_endtag(self, tag):
        if tag in self.void_tags:
            return
        if self.ignored_depth:
            self.ignored_depth -= 1
        elif tag == "h3" and self.parts is not None:
            self.titles.append(" ".join("".join(self.parts).split()))
            self.parts = None

    def handle_data(self, data):
        if self.parts is not None and not self.ignored_depth:
            self.parts.append(data)


def entry_title(source):
    # The listing templates allow inline HTML in titles.
    parser = EntryTitles()
    parser.feed(f'<h3 class="entry-title">{source}</h3>')
    return parser.titles[0]


def post_output_path(source, post):
    output_file = post.get("output-file")
    formats = post.get("format")
    if isinstance(formats, dict) and isinstance(formats.get("html"), dict):
        output_file = formats["html"].get("output-file", output_file)
    if output_file:
        if Path(output_file).suffix != ".html":
            output_file += ".html"
        return source.relative_to(ROOT).parent / output_file
    return source.relative_to(ROOT).with_suffix(".html")


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


def is_blog_page(site, page, url, site_host):
    target = local_target(site, page, url, site_host)
    if target is None:
        return False
    target = target.resolve()
    return target.is_relative_to(site / "writing") and target != site / "writing/index.xml"


def check_site(site, *, drafts=False):
    site = Path(site).resolve()
    config = yaml.safe_load((ROOT / "_quarto.yml").read_text())
    profile = yaml.safe_load((ROOT / "_data/profile.yml").read_text())
    sections = profile.get("sections") or {}
    blog_enabled = sections.get("blog", True)
    site_host = urlsplit(config["website"]["site-url"]).netloc
    errors = []
    required = ["index.html", "about.html", "research/index.html", "projects/index.html", "subscribe.html", "cv/index.html", "404.html"]
    if blog_enabled:
        required.append("writing/index.html")
    for page in required:
        file = site / page
        if not file.is_file():
            errors.append(f"Missing page: {page}")
        elif profile["name"] not in unescape(file.read_text()):
            errors.append(f"Missing profile identity: {page}")
    pages = list(site.rglob("*.html"))
    checked = 0
    for page in pages:
        if not blog_enabled and page.is_relative_to(site / "writing"):
            errors.append(f"Blog is disabled but HTML remains: {page.relative_to(site)} (run a clean build)")
        parser = References()
        parser.feed(page.read_text(encoding="utf-8"))
        for url in parser.urls + parser.social_images:
            target = local_target(site, page, url, site_host)
            if target is not None:
                checked += 1
                if not blog_enabled and is_blog_page(site, page, url, site_host):
                    errors.append(f"Blog is disabled but {page.relative_to(site)} links to it: {url} (run a clean build)")
                if not target.is_file():
                    errors.append(f"{page.relative_to(site)}: missing local target {url}")
    for filename in ("search.json", "sitemap.xml", "index.xml", "writing/index.xml", "research/index.xml", "projects/index.xml"):
        file = site / filename
        if not file.is_file():
            errors.append(f"Missing generated metadata: {filename}")
        else:
            data = file.read_text()
            try:
                metadata = json.loads(data) if filename.endswith(".json") else ET.fromstring(data)
            except (ValueError, ET.ParseError):
                errors.append(f"Invalid generated metadata: {filename}")
                continue
            if not blog_enabled:
                urls = []
                if filename == "search.json" and isinstance(metadata, list):
                    urls = [item.get(key, "") for item in metadata if isinstance(item, dict) for key in ("href", "objectID")]
                elif filename == "sitemap.xml":
                    urls = [element.text or "" for element in metadata.findall(".//{*}loc")]
                elif filename.endswith(".xml"):
                    items = metadata.findall("channel/item")
                    if filename == "writing/index.xml":
                        if metadata.tag != "rss" or metadata.find("channel") is None:
                            errors.append("Blog is disabled but writing/index.xml is not a valid empty RSS channel")
                        elif items:
                            errors.append("Blog is disabled but writing/index.xml contains posts (run a clean build)")
                    urls = [item.findtext(key, "") for item in items for key in ("link", "guid")]
                if any(isinstance(url, str) and is_blog_page(site, site / "index.html", url, site_host) for url in urls):
                    errors.append(f"Blog is disabled but {filename} contains Blog URLs (run a clean build)")
    publication_files = ["index.html", "writing/index.html", "search.json", "sitemap.xml", "writing/index.xml", "index.xml"]
    for source in (ROOT / "writing/posts").rglob("index.qmd") if blog_enabled else ():
        # Content validation runs first, so these front matter records are valid.
        front = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", source.read_text(), re.S)
        if not front:
            errors.append(f"{source.relative_to(ROOT)}: YAML front matter is required")
            continue
        post = yaml.safe_load(front.group(1))
        if not post.get("draft"):
            continue
        relative = source.parent.relative_to(ROOT).as_posix()
        for name in publication_files:
            file = site / name
            if file.is_file() and not drafts and relative in file.read_text():
                errors.append(f"Draft leaked into production {name}: {relative}")
        if drafts:
            rendered = site / post_output_path(source, post)
            parser = References()
            if rendered.is_file():
                parser.feed(rendered.read_text())
            # Production draft files are empty HTML stubs. Rendered titles can
            # contain Pandoc typography or be hidden by document-level options.
            if not "".join(parser.body_text).strip():
                errors.append(f"Draft preview is missing: {relative}")
    for kind, source_path, page_path in [
        ("research", "research/papers.yml", "research/index.html"),
        ("projects", "projects/projects.yml", "projects/index.html"),
    ]:
        records = yaml.safe_load((ROOT / source_path).read_text()) or []
        parser = EntryTitles()
        if (site / page_path).is_file():
            parser.feed((site / page_path).read_text())
        actual = Counter(parser.titles)
        expected = Counter()
        hidden = set()
        for record in records:
            visible = drafts or not (record.get("draft") or record.get("placeholder"))
            title = entry_title(record["title"])
            if visible:
                expected[title] += 1
            else:
                hidden.add(title)
        for title in expected - actual:
            errors.append(f"{kind}: expected entry missing: {title}")
        for title in actual - expected:
            reason = "unpublished entry leaked" if title in hidden else "unexpected or duplicate entry"
            errors.append(f"{kind}: {reason}: {title}")
    for section in ("talks", "teaching"):
        if bool(sections.get(section)) != (site / section / "index.html").is_file():
            errors.append(f"{section}: output does not match its visibility setting (try a clean build)")
    cv = yaml.safe_load((ROOT / "_data/cv.yml").read_text()) or {}
    if bool(cv.get("source")) != (site / "cv/vlachos-cv.pdf").is_file():
        errors.append("CV output does not match the selected PDF")
    for private_build_path in ("_cv-uploads", "_data", "_generated", "_site", "_site-preview"):
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
