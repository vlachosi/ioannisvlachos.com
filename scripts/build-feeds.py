"""Build public Research, Code and combined RSS feeds after Quarto renders.

The Blog keeps Quarto's existing RSS address and full article content. Other
announcements use explicit dates and IDs rather than file or build timestamps.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import datetime as dt
from email.utils import format_datetime, parsedate_to_datetime
import os
from pathlib import Path
import re
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

import yaml


ROOT = Path(__file__).resolve().parents[1]
UTC = dt.timezone.utc
ANNOUNCEMENT_TIMEZONE = ZoneInfo("Australia/Melbourne")
LIMIT = 50
ATOM = "http://www.w3.org/2005/Atom"
DC = "http://purl.org/dc/elements/1.1/"
for prefix, namespace in (
    ("atom", ATOM),
    ("dc", DC),
    ("content", "http://purl.org/rss/1.0/modules/content/"),
    ("media", "http://search.yahoo.com/mrss/"),
):
    ET.register_namespace(prefix, namespace)


class FeedError(ValueError):
    """An actionable problem with a feed source or rendered Blog feed."""


def load_yaml(path):
    try:
        return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise FeedError(f"{path}: {error}") from error


def announcement_date(value, label):
    if isinstance(value, dt.datetime):
        raise FeedError(f"{label}: use a date in YYYY-MM-DD format")
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            pass
    raise FeedError(f"{label}: use a valid date in YYYY-MM-DD format")


def rss_date(value, timezone=UTC):
    moment = dt.datetime.combine(value, dt.time(), timezone).astimezone(UTC)
    return format_datetime(moment, usegmt=True)


def canonical_url(value, site_url):
    """Compare Quarto's /index.html and trailing-slash post addresses equally."""
    parsed = urlsplit(urljoin(site_url, value))
    path = unquote(parsed.path)
    if path.endswith("/index.html"):
        path = path[:-len("index.html")]
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def public_posts(root, site_url):
    posts = {}
    for path in sorted((root / "writing/posts").rglob("index.qmd")):
        text = path.read_text(encoding="utf-8")
        front = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.S)
        if not front:
            raise FeedError(f"{path}: YAML front matter is required")
        try:
            metadata = yaml.safe_load(front.group(1))
        except yaml.YAMLError as error:
            raise FeedError(f"{path}: invalid front matter: {error}") from error
        if not isinstance(metadata, dict):
            raise FeedError(f"{path}: expected front matter fields")
        if metadata.get("draft") or metadata.get("placeholder"):
            continue
        date = announcement_date(metadata.get("date"), f"{path} > date")
        output_file = metadata.get("output-file")
        formats = metadata.get("format")
        if isinstance(formats, dict) and isinstance(formats.get("html"), dict):
            # Format-specific options override the document-level setting.
            output_file = formats["html"].get("output-file", output_file)
        if output_file:
            # Quarto appends its output extension if it is absent or differs.
            if Path(output_file).suffix != ".html":
                output_file += ".html"
            relative = (path.relative_to(root).parent / output_file).as_posix()
        else:
            relative = path.relative_to(root).with_suffix(".html").as_posix()
        posts[canonical_url(relative, site_url)] = date
    return posts


def blog_items(root, output_dir, site_url):
    path = output_dir / "writing/index.xml"
    try:
        document = ET.parse(path)
    except (OSError, ET.ParseError) as error:
        raise FeedError(f"{path}: cannot read the rendered Blog RSS feed: {error}") from error
    if document.getroot().tag != "rss" or document.find("channel") is None:
        raise FeedError(f"{path}: expected an RSS channel")
    public = public_posts(root, site_url)
    items = []
    for original in document.findall("channel/item"):
        link = original.findtext("link", "")
        date = public.get(canonical_url(link, site_url)) if link else None
        if date is None:
            continue
        item = deepcopy(original)
        # Quarto owns Blog publication timestamps; preserve them exactly.
        published = item.find("pubDate")
        if published is None:
            published = ET.SubElement(item, "pubDate")
            published.text = rss_date(date)
        if item.find("guid") is None:
            ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = link
        items.append((date, item))
    return items


def collection_items(root, kind, site_url, today):
    section, filename, label = {
        "research": ("research", "papers.yml", "Research"),
        "code": ("projects", "projects.yml", "Code"),
    }[kind]
    records = load_yaml(root / section / filename) or []
    items = []
    used_ids = set()
    for record in records:
        if record.get("draft") or record.get("placeholder"):
            continue
        announcement = record.get("feed")
        if announcement is None or announcement == {}:
            continue
        if not isinstance(announcement, dict):
            raise FeedError(f"{label} > {record.get('title')}: feed must contain id and date")
        if not announcement.get("id") and not announcement.get("date"):
            continue
        identifier = announcement.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier):
            raise FeedError(f"{label} > {record.get('title')}: enter a stable feed ID using lowercase words separated by hyphens")
        if identifier in used_ids:
            raise FeedError(f"{label}: duplicate feed ID {identifier!r}")
        used_ids.add(identifier)
        date = announcement_date(announcement.get("date"), f"{label} > {record.get('title')} > feed date")
        if date > today:
            continue
        link = urljoin(site_url, f"{section}/#{kind}-{identifier}")
        item = ET.Element("item")
        ET.SubElement(item, "title").text = record["title"]
        ET.SubElement(item, "link").text = link
        ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = link
        ET.SubElement(item, "pubDate").text = rss_date(date, ANNOUNCEMENT_TIMEZONE)
        ET.SubElement(item, "description").text = record.get("abstract") or record.get("description") or ""
        ET.SubElement(item, "category").text = label
        if record.get("authors"):
            ET.SubElement(item, f"{{{DC}}}creator").text = record["authors"]
        items.append((date, item))
    return items


def feed_xml(name, label, description, site_url, feed_path, page_path, items, language="en-AU"):
    unique = {}
    for _, item in items:
        identifier = item.findtext("guid") or item.findtext("link")
        if not identifier:
            raise FeedError("Every RSS item needs a stable GUID or link")
        try:
            published = parsedate_to_datetime(item.findtext("pubDate", ""))
            if published.tzinfo is None:
                raise ValueError("a timezone is required")
            published = published.astimezone(UTC)
        except (TypeError, ValueError) as error:
            raise FeedError(f"RSS item {identifier}: invalid publication date: {error}") from error
        if identifier not in unique or published > unique[identifier][0]:
            unique[identifier] = (published, item)
    ordered = sorted(unique.values(), key=lambda pair: (-pair[0].timestamp(), pair[1].findtext("guid", "")))[:LIMIT]
    document = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(document, "channel")
    ET.SubElement(channel, "title").text = f"{name} — {label}"
    ET.SubElement(channel, "link").text = urljoin(site_url, page_path)
    ET.SubElement(channel, f"{{{ATOM}}}link", {
        "href": urljoin(site_url, feed_path), "rel": "self", "type": "application/rss+xml",
    })
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, "language").text = language
    if ordered:
        ET.SubElement(channel, "lastBuildDate").text = format_datetime(ordered[0][0], usegmt=True)
    for _, item in ordered:
        channel.append(deepcopy(item))
    ET.indent(document, space="  ")
    return ET.tostring(document, encoding="utf-8", xml_declaration=True) + b"\n", len(ordered)


def build_feeds(root=ROOT, output_dir=None, *, today=None, require_blog=True):
    root = Path(root)
    config = load_yaml(root / "_quarto.yml")
    profile = load_yaml(root / "_data/profile.yml")
    site_url = config["website"]["site-url"].rstrip("/") + "/"
    if urlsplit(site_url).scheme not in {"http", "https"}:
        raise FeedError("website.site-url must be an absolute HTTP(S) URL")
    if output_dir is None:
        output_dir = os.environ.get("QUARTO_PROJECT_OUTPUT_DIR") or config["project"].get("output-dir", "_site")
    output_dir = Path(output_dir)
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    today = today or dt.datetime.now(ANNOUNCEMENT_TIMEZONE).date()
    research = collection_items(root, "research", site_url, today)
    code = collection_items(root, "code", site_url, today)
    specifications = [
        ("research/index.xml", "Research", "Research announcements and new papers.", "research/", research),
        ("projects/index.xml", "Code", "New packages, replication code and templates.", "projects/", code),
    ]
    blog_enabled = (profile.get("sections") or {}).get("blog", True)
    blog_path = output_dir / "writing/index.xml"
    if not blog_enabled:
        # Retain the subscription URL without publishing hidden or stale posts.
        # The Blog page itself is absent, so link the channel to Subscribe.
        specifications.extend([
            ("writing/index.xml", "Blog", "Posts on research, financial markets, statistics and code.", "subscribe.html", []),
            ("index.xml", "All updates", "Research announcements and code.", "subscribe.html", research + code),
        ])
    elif blog_path.is_file():
        blog = blog_items(root, output_dir, site_url)
        specifications.append(("index.xml", "All updates", "New blog posts, research announcements and code.", "subscribe.html", blog + research + code))
    elif require_blog:
        raise FeedError("The Blog RSS feed is missing. Render writing/index.qmd or run a full quarto render before building All updates.")
    else:
        # A partial render must not leave a stale combined feed behind.
        (output_dir / "index.xml").unlink(missing_ok=True)
    results = {}
    for relative, label, description, page, items in specifications:
        contents, count = feed_xml(profile["name"], label, description, site_url, relative, page, items, config.get("lang", "en-AU"))
        path = output_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != contents:
            path.write_bytes(contents)
        results[relative] = count
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Rendered output directory (defaults to Quarto's output directory)")
    args = parser.parse_args()
    # Quarto sets RENDER_ALL for full builds; a standalone invocation is also strict.
    partial = "QUARTO_PROJECT_OUTPUT_DIR" in os.environ and os.environ.get("QUARTO_PROJECT_RENDER_ALL") != "1"
    try:
        results = build_feeds(output_dir=args.output_dir, require_blog=not partial)
    except FeedError as error:
        parser.exit(1, f"RSS feed error: {error}\n")
    print("RSS feeds prepared: " + ", ".join(f"{name} ({count} items)" for name, count in results.items()))
    if "index.xml" not in results:
        print("All updates skipped for this partial render: render writing/index.qmd or the full site to create its Blog source.")


if __name__ == "__main__":
    main()
