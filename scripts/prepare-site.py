"""Validate editable content and prepare ignored files consumed by Quarto.

Run directly or through Quarto's project pre-render hook. Source content is never
rewritten. PyYAML is the only external build dependency.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"published", "working", "progress", "thesis"}
COLLECTIONS = {
    "papers": "research/papers.yml",
    "projects": "projects/projects.yml",
    "talks": "talks/talks.yml",
    "teaching": "teaching/teaching.yml",
}


class ContentError(ValueError):
    """An actionable content error, suitable for a build log."""


def load_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ContentError(f"{path}: {error}") from error


def text(value, label, *, required=False):
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        raise ContentError(f"{label}: enter {'a non-empty' if required else 'a'} text value")
    return value


def valid_date(value, label, *, required=False):
    if value in (None, "") and not required:
        return ""
    if isinstance(value, dt.datetime):
        raise ContentError(f"{label}: use a date in YYYY-MM-DD format")
    if isinstance(value, dt.date):
        return value.isoformat()
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ContentError(f"{label}: use a date in YYYY-MM-DD format")
    try:
        dt.date.fromisoformat(value)
    except ValueError as error:
        raise ContentError(f"{label}: {error}") from error
    return value


def valid_url(value, label):
    value = text(value, label)
    if not value:
        return
    # Content links may be HTTPS, email, a root/local path, or a fragment.
    if re.match(r"^(https?://|mailto:|/[^/]?|#)", value):
        return
    if ":" not in value and not value.startswith("//") and not any(c in value for c in "\r\n"):
        return
    raise ContentError(f"{label}: use an http(s), mailto, or local link")


def validate_profile(profile):
    if not isinstance(profile, dict):
        raise ContentError("_data/profile.yml: expected a settings object")
    text(profile.get("name"), "Profile > Name", required=True)
    for key in ("role", "affiliation", "bio", "rig", "email"):
        text(profile.get(key), f"Profile > {key}")
    email = profile.get("email") or ""
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ContentError("Profile > Email: enter an email address or leave blank")
    links = profile.get("links")
    if links is None:
        links = {}
    if not isinstance(links, dict):
        raise ContentError("Profile > Links: expected named links")
    for name, value in links.items():
        valid_url(value, f"Profile > Links > {name}")
    sections = profile.get("sections")
    if sections is None:
        sections = {}
    if not isinstance(sections, dict):
        raise ContentError("Profile > Sections: expected visibility switches")
    for name, value in sections.items():
        if not isinstance(value, bool):
            raise ContentError(f"Profile > Sections > {name}: expected true or false")


def validate_entries(entries, kind):
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        raise ContentError(f"{COLLECTIONS[kind]}: expected a list of entries")
    for index, item in enumerate(entries):
        where = f"{kind} entry {index + 1}"
        if not isinstance(item, dict):
            raise ContentError(f"{where}: expected an object")
        title = text(item.get("title"), f"{where} > title", required=True)
        where = f'{kind} > "{title}"'
        if kind == "papers" and (not isinstance(item.get("status"), str) or item["status"] not in STATUSES):
            raise ContentError(f"{where} > status: choose published, working, progress, or thesis")
        for key in ("authors", "venue", "abstract", "kind", "description", "when", "where"):
            if key in item:
                text(item[key], f"{where} > {key}")
        for key in ("placeholder", "draft", "featured"):
            if key in item and item[key] is not None and not isinstance(item[key], bool):
                raise ContentError(f"{where} > {key}: expected true or false")
        for key in ("year", "order"):
            if item.get(key) is not None and (isinstance(item[key], bool) or not isinstance(item[key], (int, float))):
                raise ContentError(f"{where} > {key}: expected a number")
        if item.get("tags") is not None:
            if not isinstance(item["tags"], list) or not all(isinstance(tag, str) for tag in item["tags"]):
                raise ContentError(f"{where} > tags: expected a list of text values")
        valid_url(item.get("href"), f"{where} > main link")
        links = item.get("links")
        if links is None:
            links = []
        if not isinstance(links, list):
            raise ContentError(f"{where} > links: expected a list of label/URL objects")
        for link in links:
            if not isinstance(link, dict):
                raise ContentError(f"{where} > links: expected label/URL objects")
            text(link.get("label"), f"{where} > link label", required=True)
            text(link.get("url"), f"{where} > link URL", required=True)
            valid_url(link["url"], f"{where} > link URL")
    return entries


def validate_posts(root):
    for path in sorted((root / "writing/posts").rglob("index.qmd")):
        source = path.read_text(encoding="utf-8")
        match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", source, re.S)
        where = str(path.relative_to(root))
        if not match:
            raise ContentError(f"{where}: YAML front matter is required")
        try:
            meta = yaml.safe_load(match.group(1))
        except yaml.YAMLError as error:
            raise ContentError(f"{where}: invalid front matter: {error}") from error
        if not isinstance(meta, dict):
            raise ContentError(f"{where}: expected front matter fields")
        text(meta.get("title"), f"{where} > title", required=True)
        text(meta.get("description"), f"{where} > description", required=True)
        valid_date(meta.get("date"), f"{where} > date", required=True)
        if not isinstance(meta.get("draft"), bool):
            raise ContentError(f"{where} > draft: explicitly choose true (draft) or false (published)")
        categories = meta.get("categories")
        if categories is None:
            categories = []
        if not isinstance(categories, list) or not all(isinstance(x, str) for x in categories):
            raise ContentError(f"{where} > categories: expected a list of text values")
        if meta.get("image"):
            text(meta.get("image-alt"), f"{where} > image-alt", required=True)
            image = text(meta["image"], f"{where} > image")
            if not re.match(r"^https?://", image):
                image_path = (root / image.lstrip("/")) if image.startswith("/") else (path.parent / image)
                if not image_path.is_file():
                    raise ContentError(f"{where} > image: file does not exist: {image}")
        if not source[match.end():].strip():
            raise ContentError(f"{where}: the article body is empty")


def selected_cv(root, record):
    # Pages CMS serializes a form whose optional fields were all cleared as an
    # empty YAML file. That represents no selected CV, not invalid content.
    if record is None:
        record = {}
    if not isinstance(record, dict):
        raise ContentError("_data/cv.yml: expected PDF selection settings")
    source = text(record.get("source"), "CV > Current CV PDF").strip()
    updated = valid_date(record.get("updated"), "CV > Last updated")
    if not source:
        return None, updated
    relative = Path(source)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] != "_cv-uploads":
        raise ContentError("CV > Current CV PDF: select a file from _cv-uploads")
    path = (root / relative).resolve()
    upload_root = (root / "_cv-uploads").resolve()
    if not path.is_relative_to(upload_root) or not path.is_file() or path.suffix.lower() != ".pdf":
        raise ContentError(f"CV > Current CV PDF: PDF file not found in _cv-uploads: {source}")
    data = path.read_bytes()
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
        raise ContentError(f"CV > Current CV PDF: {source} does not have a valid PDF header/end marker")
    if len(data) > 25 * 1024 * 1024:
        raise ContentError("CV > Current CV PDF: use a PDF smaller than 25 MiB")
    return path, updated


def write_changed(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_cv(root, source, updated):
    target = root / "cv/vlachos-cv.pdf"
    state_file = root / "_generated/cv-state.json"
    previous = {}
    if state_file.is_file():
        previous = json.loads(state_file.read_text(encoding="utf-8"))
    if target.exists():
        managed = previous.get("sha256") == digest(target)
        matches = source is not None and digest(source) == digest(target)
        if not managed and not matches:
            raise ContentError("cv/vlachos-cv.pdf contains an unmanaged file. Move it into _cv-uploads and select it in _data/cv.yml before rebuilding; it was preserved.")
    if source:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or digest(source) != digest(target):
            shutil.copyfile(source, target)
        write_changed(state_file, json.dumps({"sha256": digest(target)}) + "\n")
        date_html = ""
        if updated:
            date = dt.date.fromisoformat(updated)
            label = f"{date.day} {date.strftime('%B')} {date.year}"
            date_html = f'<span class="cv-updated">Updated <time datetime="{updated}">{label}</time></span>'
        output = (
            '<div class="cv-actions"><a class="btn-line" href="vlachos-cv.pdf" download data-cv-download>'
            '<i class="bi bi-file-earmark-pdf" aria-hidden="true"></i> Download PDF</a>'
            + date_html + '</div>\n'
            '<p class="cv-status" data-cv-status role="status" aria-live="polite" hidden></p>\n'
            '<div class="cv-viewer" data-cv-viewer="vlachos-cv.pdf" aria-label="CV preview"></div>\n'
        )
    else:
        if target.exists():
            target.unlink()
        write_changed(state_file, "{}\n")
        output = '<p class="cv-status">My CV will be available here soon.</p>\n'
        # A prior selected CV must not linger in an incremental output directory.
        output_dir = os.environ.get("QUARTO_PROJECT_OUTPUT_DIR")
        if output_dir:
            stale = Path(output_dir) / "cv/vlachos-cv.pdf"
            if stale.is_file() and previous.get("sha256") == digest(stale):
                stale.unlink()
    write_changed(root / "cv/_cv-status.html", output)


def prepare(root=ROOT, *, check_only=False, drafts=None):
    profile = load_yaml(root / "_data/profile.yml")
    validate_profile(profile)
    records = {
        kind: validate_entries(load_yaml(root / name), kind)
        for kind, name in COLLECTIONS.items()
    }
    validate_posts(root)
    source, updated = selected_cv(root, load_yaml(root / "_data/cv.yml"))
    if check_only:
        return
    from profile import render_profile

    generated = root / "_generated"
    generated.mkdir(exist_ok=True)
    metadata = render_profile(profile, generated, repo_root=root)
    write_changed(generated / "site.yml", yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False))
    if drafts is None:
        drafts = "drafts" in os.environ.get("QUARTO_PROFILE", "").split(",")
    for kind, entries in records.items():
        visible = entries if drafts else [
            item for item in entries if not item.get("draft") and not item.get("placeholder")
        ]
        if kind in {"papers", "projects"}:
            visible = [dict(item, order=100 if item.get("order") is None else item["order"], featured=bool(item.get("featured"))) for item in visible]
        write_changed(generated / f"{kind}.yml", yaml.safe_dump(visible, allow_unicode=True, sort_keys=False))
    prepare_cv(root, source, updated)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate content without writing generated files")
    args = parser.parse_args()
    try:
        prepare(check_only=args.check)
    except ContentError as error:
        print(f"Content error: {error}", file=sys.stderr)
        sys.exit(1)
    print("Content validated." if args.check else "Content validated; profile and CV prepared.")
