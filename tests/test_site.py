"""Rendered-site checker regressions, using a minimal temporary website."""
from contextlib import redirect_stdout
from html import escape
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import yaml


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check-site.py"
SPEC = importlib.util.spec_from_file_location("site_checker", SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class SiteChecks(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.site = self.root / "_site"
        self.name = "Research & Teaching"
        self.write("_quarto.yml", yaml.safe_dump({"website": {"site-url": "https://example.org"}}))
        self.write("_data/profile.yml", yaml.safe_dump({"name": self.name}))
        self.write("_data/cv.yml", "")
        self.write("research/papers.yml", "[]\n")
        self.write("projects/projects.yml", "[]\n")
        for page in (
            "index.html", "about.html", "research/index.html", "projects/index.html",
            "writing/index.html", "subscribe.html", "cv/index.html", "404.html",
        ):
            self.write(f"_site/{page}", f"<!doctype html><html><body>{escape(self.name)}</body></html>")
        self.write("_site/search.json", "[]")
        self.write("_site/sitemap.xml", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>')
        for feed in ("index.xml", "writing/index.xml", "research/index.xml", "projects/index.xml"):
            self.write(f"_site/{feed}", '<rss version="2.0"><channel/></rss>')
        patch = mock.patch.object(checker, "ROOT", self.root)
        patch.start()
        self.addCleanup(patch.stop)

    def write(self, relative, source):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")

    def collection(self, kind, records, headings):
        filename, title_class = {
            "research": ("papers.yml", "entry-title"),
            "projects": ("projects.yml", "card-title"),
        }[kind]
        defaults = {"status": "working"} if kind == "research" else {"section": "packages"}
        self.write(f"{kind}/{filename}", yaml.safe_dump([dict(defaults, **record) for record in records]))
        entries = "".join(f'<li><h3 class="{title_class}">{title}</h3></li>' for title in headings)
        self.write(
            f"_site/{kind}/index.html",
            f"<!doctype html><html><body>{escape(self.name)}<nav>Research</nav><ul>{entries}</ul></body></html>",
        )

    def post(self, metadata):
        self.write(
            "writing/posts/example/index.qmd",
            "---\n" + yaml.safe_dump({
                "title": "Example article", "description": "A summary.",
                "date": "2026-10-03", "draft": True, **metadata,
            }, default_style='"') + "---\n\nArticle body.\n",
        )

    def disable_blog(self):
        self.write("_data/profile.yml", yaml.safe_dump({"name": self.name, "sections": {"blog": False}}))
        (self.site / "writing/index.html").unlink()

    def test_escaped_profile_name_is_recognized_in_rendered_pages(self):
        with redirect_stdout(io.StringIO()):
            checker.check_site(self.site)

    def test_missing_profile_identity_still_fails(self):
        self.write("_site/about.html", "<!doctype html><html><body>Different identity</body></html>")
        with self.assertRaisesRegex(ValueError, "Missing profile identity: about.html"):
            checker.check_site(self.site)

    def test_copied_production_resources_fail_even_without_nested_html(self):
        self.write("_site/_site/CNAME", "example.org\n")
        self.write("_site/_site/assets/og.png", "copied image resource")
        with self.assertRaisesRegex(ValueError, "Build/source directory was copied into the site: _site"):
            checker.check_site(self.site)

    def test_copied_preview_resources_fail_even_without_nested_html(self):
        self.write("_site/_site-preview/CNAME", "example.org\n")
        self.write("_site/_site-preview/assets/og.png", "copied image resource")
        with self.assertRaisesRegex(ValueError, "Build/source directory was copied into the site: _site-preview"):
            checker.check_site(self.site)

    def test_post_front_matter_delimiter_inside_quoted_title_is_valid(self):
        for draft in (False, True):
            with self.subTest(draft=draft):
                self.post({"title": "Some --- text", "draft": draft})
                self.write(
                    "_site/writing/posts/example/index.html",
                    '<html><body><h1 class="title">Some --- text</h1></body></html>',
                )
                with redirect_stdout(io.StringIO()):
                    checker.check_site(self.site, drafts=draft)

    def test_hidden_title_outside_collection_entries_is_not_a_leak(self):
        self.collection("research", [{"title": "Research", "status": "working", "draft": True}], [])
        with redirect_stdout(io.StringIO()):
            checker.check_site(self.site)

    def test_public_and_hidden_entries_may_share_title(self):
        for kind in ("research", "projects"):
            with self.subTest(kind=kind):
                self.collection(kind, [
                    {"title": "Shared title"},
                    {"title": "Shared title", "draft": True},
                ], ["Shared title"])
                with redirect_stdout(io.StringIO()):
                    checker.check_site(self.site)

    def test_duplicate_rendered_entry_titles_are_rejected(self):
        for kind in ("research", "projects"):
            with self.subTest(kind=kind):
                self.collection(kind, [{"title": "One public entry"}], ["One public entry", "One public entry"])
                with self.assertRaisesRegex(ValueError, "One public entry"):
                    checker.check_site(self.site)
                self.collection(kind, [], [])

    def test_hidden_collection_entry_is_rejected(self):
        for kind in ("research", "projects"):
            for hidden_flag in ("draft", "placeholder"):
                with self.subTest(kind=kind, hidden_flag=hidden_flag):
                    self.collection(kind, [{"title": "Hidden entry", hidden_flag: True}], ["Hidden entry"])
                    with self.assertRaisesRegex(ValueError, "Hidden entry"):
                        checker.check_site(self.site)
                    self.collection(kind, [], [])

    def test_placeholder_labels_and_heading_links_do_not_change_entry_title(self):
        for kind in ("research", "projects"):
            with self.subTest(kind=kind):
                self.collection(kind, [{"title": "Coming paper", "placeholder": True}], [
                    'Coming <em>paper</em><span class="placeholder-tag">placeholder</span>'
                    '<a class="anchorjs-link" href="#paper" aria-label="Anchor">#</a>',
                ])
                with redirect_stdout(io.StringIO()):
                    checker.check_site(self.site, drafts=True)

    def test_draft_custom_output_filenames_are_recognized(self):
        for metadata, filename in (
            ({"output-file": "custom.html"}, "custom.html"),
            ({"format": {"html": {"output-file": "custom"}}}, "custom.html"),
            ({"output-file": "ignored.html", "format": {"html": {"output-file": "notes.txt"}}}, "notes.txt.html"),
        ):
            with self.subTest(metadata=metadata):
                self.post(metadata)
                self.write(
                    f"_site/writing/posts/example/{filename}",
                    '<html><body><h1 class="title">Example article</h1></body></html>',
                )
                with redirect_stdout(io.StringIO()):
                    checker.check_site(self.site, drafts=True)
                (self.site / "writing/posts/example" / filename).unlink()

    def test_missing_draft_custom_output_is_rejected(self):
        for metadata in (
            {"output-file": "custom.html"},
            {"output-file": "index.html", "format": {"html": {"output-file": "custom.html"}}},
        ):
            with self.subTest(metadata=metadata):
                self.post(metadata)
                self.write(
                    "_site/writing/posts/example/index.html",
                    '<html><body><h1 class="title">Example article</h1></body></html>',
                )
                with self.assertRaisesRegex(ValueError, "Draft preview is missing"):
                    checker.check_site(self.site, drafts=True)

    def test_draft_preview_accepts_smart_punctuation(self):
        self.post({"title": 'A "quoted" draft'})
        self.write(
            "_site/writing/posts/example/index.html",
            '<html><body><h1 class="title">A “quoted” draft</h1><p>Article body.</p></body></html>',
        )
        with redirect_stdout(io.StringIO()):
            checker.check_site(self.site, drafts=True)

    def test_draft_preview_accepts_suppressed_title_block(self):
        self.post({"title-block-style": "none"})
        self.write(
            "_site/writing/posts/example/index.html",
            '<html><body><main><p>Article body.</p></main></body></html>',
        )
        with redirect_stdout(io.StringIO()):
            checker.check_site(self.site, drafts=True)

    def test_draft_preview_rejects_production_stub(self):
        self.post({})
        for source in (
            "<!doctype html><html><head></head><body></body></html>",
            "<html><head><title>Example article</title></head><body></body></html>",
            '<html><head><title>Example article</title></head><body><h1 class="title"> </h1></body></html>',
        ):
            with self.subTest(source=source):
                self.write("_site/writing/posts/example/index.html", source)
                with self.assertRaisesRegex(ValueError, "Draft preview is missing"):
                    checker.check_site(self.site, drafts=True)

    def test_enabled_blog_requires_index_and_draft_preview(self):
        self.post({})
        for sections in ({}, {"blog": True}):
            with self.subTest(sections=sections):
                self.write("_data/profile.yml", yaml.safe_dump({"name": self.name, "sections": sections}))
                with self.assertRaisesRegex(ValueError, "Draft preview is missing"):
                    checker.check_site(self.site, drafts=True)
                self.write("_site/writing/posts/example/index.html", "<html><body>Article body.</body></html>")
                with redirect_stdout(io.StringIO()):
                    checker.check_site(self.site, drafts=True)
                (self.site / "writing/index.html").unlink()
                with self.assertRaisesRegex(ValueError, "Missing page: writing/index.html"):
                    checker.check_site(self.site)
                self.write("_site/writing/index.html", f"<html><body>{escape(self.name)}</body></html>")
                (self.site / "writing/posts/example/index.html").unlink()

    def test_disabled_blog_needs_no_pages_or_draft_preview(self):
        self.disable_blog()
        self.post({})
        for drafts in (False, True):
            with self.subTest(drafts=drafts), redirect_stdout(io.StringIO()):
                checker.check_site(self.site, drafts=drafts)

    def test_disabled_blog_rejects_stale_html(self):
        self.disable_blog()
        for relative in ("writing/index.html", "writing/posts/example/custom.html"):
            for drafts in (False, True):
                with self.subTest(relative=relative, drafts=drafts):
                    self.write(f"_site/{relative}", f"<html><body>{escape(self.name)}</body></html>")
                    try:
                        with self.assertRaisesRegex(ValueError, "Blog"):
                            checker.check_site(self.site, drafts=drafts)
                    finally:
                        (self.site / relative).unlink()

    def test_disabled_blog_rejects_links_in_pages_search_and_sitemap(self):
        self.disable_blog()
        for relative, contents in (
            ("index.html", f'<html><body>{escape(self.name)}<a href="/writing/">Blog</a></body></html>'),
            ("about.html", f'<html><body>{escape(self.name)}<a href="writing/posts/example/">Article</a></body></html>'),
            ("search.json", json.dumps([{"href": "writing/posts/example/", "title": "Example article", "text": "Article body."}])),
            ("sitemap.xml", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.org/writing/posts/example/</loc></url></urlset>'),
        ):
            for drafts in (False, True):
                with self.subTest(relative=relative, drafts=drafts):
                    original = (self.site / relative).read_text()
                    self.write(f"_site/{relative}", contents)
                    try:
                        with self.assertRaisesRegex(ValueError, "Blog"):
                            checker.check_site(self.site, drafts=drafts)
                    finally:
                        self.write(f"_site/{relative}", original)

    def test_disabled_blog_rejects_native_and_combined_feed_articles(self):
        self.disable_blog()
        for relative, link in (
            ("writing/index.xml", "https://example.org/writing/posts/example/"),
            ("writing/index.xml", "https://external.example/article"),
            ("index.xml", "https://example.org/writing/posts/example/"),
        ):
            for drafts in (False, True):
                with self.subTest(relative=relative, link=link, drafts=drafts):
                    original = (self.site / relative).read_text()
                    article = f'<item><title>Example article</title><link>{link}</link><guid>{link}</guid></item>'
                    self.write(f"_site/{relative}", f'<rss version="2.0"><channel>{article}</channel></rss>')
                    try:
                        with self.assertRaisesRegex(ValueError, "Blog"):
                            checker.check_site(self.site, drafts=drafts)
                    finally:
                        self.write(f"_site/{relative}", original)

    def test_disabled_blog_still_requires_a_valid_empty_feed(self):
        self.disable_blog()
        for source in (None, '<rss version="2.0"/>', '<feed><channel/></feed>', '<rss>'):
            with self.subTest(source=source):
                if source is None:
                    (self.site / "writing/index.xml").unlink()
                else:
                    self.write("_site/writing/index.xml", source)
                with self.assertRaisesRegex(ValueError, r"writing/index\.xml"):
                    checker.check_site(self.site)


if __name__ == "__main__":
    unittest.main()
