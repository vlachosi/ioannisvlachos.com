"""Regression checks for content entered through the browser editor.

All sample content and PDFs live in temporary directories. Run with
``python3 -m unittest discover -s tests`` from the repository root.
"""
from __future__ import annotations

import datetime as dt
from html.parser import HTMLParser
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import yaml


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare-site.py"
SPEC = importlib.util.spec_from_file_location("site_content", SCRIPT)
content = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(content)


def sample_pdf():
    """A tiny PDF fixture, never written into the site's source checkout."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] >>",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(b"xref\n0 4\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(data)


class Elements(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.elements = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class ContentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        environment = mock.patch.dict(os.environ, {"QUARTO_PROJECT_OUTPUT_DIR": ""})
        environment.start()
        self.addCleanup(environment.stop)

    def write(self, relative, source):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(source, bytes):
            path.write_bytes(source)
        else:
            path.write_text(source, encoding="utf-8")
        return path

    def post(self, metadata=None, body="An article with useful content."):
        if metadata is None:
            metadata = self.post_metadata()
        return self.write(
            "writing/posts/example/index.qmd",
            "---\n" + yaml.safe_dump(metadata) + "---\n\n" + body,
        )

    @staticmethod
    def post_metadata():
        return {
            "title": "Example article",
            "description": "A clear summary.",
            "date": "2026-10-03",
            "draft": True,
            "categories": ["Research", "Writing"],
        }

    def pdf(self, name="current.pdf", data=None):
        return self.write(f"_cv-uploads/{name}", sample_pdf() if data is None else data)

    def selected(self, source="_cv-uploads/current.pdf", updated="2026-10-03"):
        return content.selected_cv(self.root, {"source": source, "updated": updated})

    def test_research_accepts_supported_statuses_and_empty_collection(self):
        content.validate_entries([], "papers")
        for status in ("published", "working", "progress", "thesis"):
            with self.subTest(status=status):
                content.validate_entries([{"title": "A paper", "status": status}], "papers")

    def test_research_rejects_missing_unknown_and_non_text_statuses(self):
        for status in (None, "submitted", "", False, [], {}):
            with self.subTest(status=status):
                with self.assertRaisesRegex(content.ContentError, "status"):
                    content.validate_entries([{"title": "A paper", "status": status}], "papers")

    def test_research_rejects_wrong_field_types(self):
        bad_fields = [
            ("title", ""), ("title", ["Title"]), ("authors", ["An Author"]),
            ("abstract", {"text": "Abstract"}), ("year", True), ("order", "first"),
            ("draft", "false"), ("placeholder", "false"), ("featured", 1),
            ("tags", "economics"), ("tags", [17]),
            ("links", [{"label": "PDF", "url": "javascript:alert(1)"}]),
            ("links", [{"label": "", "url": "https://example.org/paper"}]),
        ]
        for field, value in bad_fields:
            with self.subTest(field=field, value=value):
                record = {"title": "A paper", "status": "working", field: value}
                with self.assertRaises(content.ContentError):
                    content.validate_entries([record], "papers")

    def test_research_rejects_malformed_collection_and_entry(self):
        for records in ({"title": "A paper"}, "A paper", ["A paper"]):
            with self.subTest(records=records):
                with self.assertRaises(content.ContentError):
                    content.validate_entries(records, "papers")

    def test_post_accepts_explicit_draft_and_published_metadata(self):
        for draft in (True, False):
            with self.subTest(draft=draft):
                metadata = self.post_metadata()
                metadata.update(draft=draft, date=dt.date(2026, 10, 3))
                self.post(metadata)
                content.validate_posts(self.root)

    def test_post_requires_title_description_date_and_explicit_draft(self):
        for field in ("title", "description", "date", "draft"):
            with self.subTest(field=field):
                metadata = self.post_metadata()
                del metadata[field]
                self.post(metadata)
                with self.assertRaisesRegex(content.ContentError, field):
                    content.validate_posts(self.root)

    def test_post_rejects_invalid_dates_categories_and_draft_types(self):
        bad_fields = [
            ("title", " "), ("description", ["Summary"]),
            ("date", "2026-02-30"), ("date", "3 October 2026"),
            ("date", dt.datetime(2026, 10, 3, 12)),
            ("draft", "false"), ("draft", 0), ("draft", None),
            ("categories", "research"), ("categories", [1]),
            ("categories", {"name": "research"}), ("categories", False),
            ("categories", 0), ("categories", ""),
        ]
        for field, value in bad_fields:
            with self.subTest(field=field, value=value):
                metadata = self.post_metadata()
                metadata[field] = value
                self.post(metadata)
                with self.assertRaisesRegex(content.ContentError, field):
                    content.validate_posts(self.root)

    def test_post_rejects_missing_or_invalid_front_matter_and_empty_body(self):
        for source in (
            "An article without metadata.",
            "---\ntitle: [broken\n---\nAn article.",
            "---\n- wrong\n- shape\n---\nAn article.",
        ):
            with self.subTest(source=source):
                self.write("writing/posts/example/index.qmd", source)
                with self.assertRaises(content.ContentError):
                    content.validate_posts(self.root)
        self.post(body="\n  ")
        with self.assertRaisesRegex(content.ContentError, "body"):
            content.validate_posts(self.root)

    def test_post_image_requires_alt_text_and_existing_local_file(self):
        metadata = self.post_metadata()
        metadata["image"] = "cover.png"
        self.post(metadata)
        with self.assertRaisesRegex(content.ContentError, "image-alt"):
            content.validate_posts(self.root)
        metadata["image-alt"] = "An explanatory chart."
        self.post(metadata)
        with self.assertRaisesRegex(content.ContentError, "image"):
            content.validate_posts(self.root)
        self.write("writing/posts/example/cover.png", b"fixture image")
        content.validate_posts(self.root)

    def test_cv_selection_may_be_empty_without_creating_a_file(self):
        for blank in (None, "", "  "):
            with self.subTest(blank=blank):
                self.assertEqual(self.selected(blank, None), (None, ""))
        self.assertFalse((self.root / "cv/vlachos-cv.pdf").exists())

    def test_cleared_cv_form_can_be_saved_as_empty_yaml(self):
        for source in ("", "# All optional fields were cleared.\n"):
            with self.subTest(source=source):
                path = self.write("_data/cv.yml", source)
                record = content.load_yaml(path)
                selected, updated = content.selected_cv(self.root, record)
                self.assertIsNone(selected)
                self.assertEqual(updated, "")
                content.prepare_cv(self.root, selected, updated)
                self.assertFalse((self.root / "cv/vlachos-cv.pdf").exists())
                document = Elements((self.root / "cv/_cv-status.html").read_text())
                self.assertFalse(any(tag == "a" for tag, _ in document.elements))

    def test_cv_selection_accepts_uploaded_pdf_and_yaml_date(self):
        source = self.pdf("Current CV.PDF")
        selected, updated = self.selected("_cv-uploads/Current CV.PDF", dt.date(2026, 10, 3))
        self.assertEqual(selected, source.resolve())
        self.assertEqual(updated, "2026-10-03")

    def test_cv_selection_rejects_unexpected_record_and_date_types(self):
        for record in ([], "_cv-uploads/current.pdf", {"source": 17}, {"updated": "yesterday"}):
            with self.subTest(record=record):
                with self.assertRaises(content.ContentError):
                    content.selected_cv(self.root, record)

    def test_cv_selection_rejects_absolute_traversal_and_non_upload_paths(self):
        self.pdf()
        for source in (
            "../current.pdf", "_cv-uploads/../current.pdf", "cv/vlachos-cv.pdf",
            "/_cv-uploads/current.pdf", str(self.root / "_cv-uploads/current.pdf"), ".",
        ):
            with self.subTest(source=source):
                with self.assertRaises(content.ContentError):
                    self.selected(source)

    def test_cv_selection_rejects_symlink_escaping_upload_directory(self):
        outside = self.write("outside.pdf", sample_pdf())
        link = self.root / "_cv-uploads/current.pdf"
        link.parent.mkdir()
        link.symlink_to(outside)
        with self.assertRaises(content.ContentError):
            self.selected()

    def test_cv_selection_rejects_missing_wrong_extension_and_bad_pdf_envelope(self):
        with self.assertRaises(content.ContentError):
            self.selected()
        self.pdf("current.txt")
        with self.assertRaises(content.ContentError):
            self.selected("_cv-uploads/current.txt")
        for data in (b"not a PDF\n%%EOF", b"%PDF-1.4\ntruncated", b"<!doctype html>error"):
            with self.subTest(data=data):
                self.pdf(data=data)
                with self.assertRaisesRegex(content.ContentError, "header/end"):
                    self.selected()

    def test_cv_selection_rejects_oversized_upload(self):
        self.pdf(data=b"%PDF-1.4\n" + b" " * (25 * 1024 * 1024) + b"\n%%EOF")
        with self.assertRaisesRegex(content.ContentError, "25 MiB"):
            self.selected()

    def test_cv_generation_preserves_source_and_has_static_enabled_download(self):
        source = self.pdf()
        original = source.read_bytes()
        content.prepare_cv(self.root, source, "2026-10-03")
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual((self.root / "cv/vlachos-cv.pdf").read_bytes(), original)
        document = Elements((self.root / "cv/_cv-status.html").read_text())
        downloads = [attrs for tag, attrs in document.elements if tag == "a" and "download" in attrs]
        self.assertEqual(len(downloads), 1)
        self.assertEqual(downloads[0]["href"], "vlachos-cv.pdf")
        self.assertNotEqual(downloads[0].get("aria-disabled"), "true")
        self.assertNotIn("is-disabled", downloads[0].get("class", "").split())
        self.assertNotIn("hidden", downloads[0])
        self.assertTrue(any(tag == "time" and attrs.get("datetime") == "2026-10-03"
                            for tag, attrs in document.elements))
        self.assertTrue(any(attrs.get("role") == "status" and attrs.get("aria-live") == "polite"
                            for _, attrs in document.elements))
        # Repeating a build must leave the source and public URL stable.
        content.prepare_cv(self.root, source, "2026-10-03")
        self.assertEqual((self.root / "cv/vlachos-cv.pdf").read_bytes(), original)

    def test_cv_generation_replaces_only_managed_canonical_pdf(self):
        first = self.pdf("first.pdf")
        second = self.pdf("second.pdf", sample_pdf() + b"\n% revised fixture\n")
        content.prepare_cv(self.root, first, "")
        content.prepare_cv(self.root, second, "")
        self.assertEqual((self.root / "cv/vlachos-cv.pdf").read_bytes(), second.read_bytes())
        self.assertTrue(first.exists())

    def test_clearing_cv_removes_managed_files_and_download_markup(self):
        source = self.pdf()
        content.prepare_cv(self.root, source, "")
        deployed = self.write("_site/cv/vlachos-cv.pdf", source.read_bytes())
        with mock.patch.dict(os.environ, {"QUARTO_PROJECT_OUTPUT_DIR": str(self.root / "_site")}):
            content.prepare_cv(self.root, None, "")
        self.assertFalse((self.root / "cv/vlachos-cv.pdf").exists())
        self.assertFalse(deployed.exists())
        self.assertTrue(source.exists(), "Clearing a selection must preserve the uploaded source")
        document = Elements((self.root / "cv/_cv-status.html").read_text())
        self.assertFalse(any(tag == "a" for tag, _ in document.elements))
        self.assertFalse(any("data-cv-viewer" in attrs for _, attrs in document.elements))
        content.prepare_cv(self.root, None, "")

    def test_cv_generation_and_clearing_preserve_unmanaged_canonical_file(self):
        target = self.write("cv/vlachos-cv.pdf", b"user's preexisting file")
        source = self.pdf()
        for selected in (None, source):
            with self.subTest(selected=selected):
                with self.assertRaisesRegex(content.ContentError, "unmanaged"):
                    content.prepare_cv(self.root, selected, "")
                self.assertEqual(target.read_bytes(), b"user's preexisting file")

    def test_cv_clearing_preserves_a_modified_managed_file(self):
        source = self.pdf()
        content.prepare_cv(self.root, source, "")
        target = self.write("cv/vlachos-cv.pdf", b"user changed this after generation")
        with self.assertRaisesRegex(content.ContentError, "unmanaged"):
            content.prepare_cv(self.root, None, "")
        self.assertEqual(target.read_bytes(), b"user changed this after generation")

    def test_cv_clearing_preserves_unrelated_file_in_output_directory(self):
        source = self.pdf()
        content.prepare_cv(self.root, source, "")
        deployed = self.write("_site/cv/vlachos-cv.pdf", b"an unrelated output file")
        with mock.patch.dict(os.environ, {"QUARTO_PROJECT_OUTPUT_DIR": str(self.root / "_site")}):
            content.prepare_cv(self.root, None, "")
        self.assertEqual(deployed.read_bytes(), b"an unrelated output file")


if __name__ == "__main__":
    unittest.main()
