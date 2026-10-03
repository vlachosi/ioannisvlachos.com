"""RSS announcements preserve identities, public visibility and authored dates."""
from copy import deepcopy
import datetime as dt
from email.utils import parsedate_to_datetime
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import xml.etree.ElementTree as ET

import yaml


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("site_feeds", REPO / "scripts/build-feeds.py")
FEEDS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FEEDS)
TODAY = dt.date(2026, 10, 3)
SITE = "https://example.com/"


class FeedTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="site-feeds-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.output = self.root / "rendered"
        self.write_yaml("_quarto.yml", {"project": {"output-dir": "rendered"}, "website": {"site-url": SITE}, "lang": "en-AU"})
        self.write_yaml("_data/profile.yml", {"name": 'Ada & Example <Lab>'})
        self.write_yaml("research/papers.yml", [])
        self.write_yaml("projects/projects.yml", [])
        self.write_blog([])

    def write_yaml(self, relative, contents):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(contents, allow_unicode=True), encoding="utf-8")

    def source_post(self, slug, *, date="2026-10-01", draft=False, **options):
        folder = self.root / "writing/posts" / slug
        folder.mkdir(parents=True, exist_ok=True)
        metadata = {"title": slug, "description": "A summary.", "date": date, "draft": draft, **options}
        (folder / "index.qmd").write_text("---\n" + yaml.safe_dump(metadata) + "---\n\nText.\n", encoding="utf-8")
        return f"{SITE}writing/posts/{slug}/"

    def blog_item(self, link, title="A Blog post", date="2026-10-01"):
        item = ET.Element("item")
        for key, value in (("title", title), ("link", link), ("guid", link), ("pubDate", FEEDS.rss_date(dt.date.fromisoformat(date))), ("description", "<p>Full article & examples.</p>")):
            ET.SubElement(item, key).text = value
        ET.SubElement(item, f"{{{FEEDS.DC}}}creator").text = "Ada"
        return item

    def write_blog(self, items):
        document = ET.Element("rss", {"version": "2.0"})
        channel = ET.SubElement(document, "channel")
        ET.SubElement(channel, "title").text = "Blog"
        ET.SubElement(channel, "lastBuildDate").text = "Sat, 03 Oct 2026 12:00:00 GMT"
        for item in items:
            channel.append(deepcopy(item))
        path = self.output / "writing/index.xml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(ET.tostring(document, encoding="utf-8", xml_declaration=True))

    def record(self, identifier="market-paper", date="2026-10-02", **extra):
        return {"title": "Research & risk <β>", "abstract": "A & B < C; café.", "feed": {"id": identifier, "date": date}, **extra}

    def build(self, **kwargs):
        return FEEDS.build_feeds(self.root, self.output, today=TODAY, **kwargs)

    def items(self, relative):
        return ET.parse(self.output / relative).findall("channel/item")

    def test_dates_links_and_xml_text_preserve_authored_values(self):
        self.write_yaml("research/papers.yml", [self.record(authors="Ada & Bob", href="https://external.example/old")])
        self.build()
        item = self.items("research/index.xml")[0]
        self.assertEqual(item.findtext("title"), "Research & risk <β>")
        self.assertEqual(item.findtext("description"), "A & B < C; café.")
        self.assertEqual(item.findtext("link"), SITE + "research/#research-market-paper")
        self.assertEqual(item.findtext("guid"), item.findtext("link"))
        self.assertEqual(item.findtext(f"{{{FEEDS.DC}}}creator"), "Ada & Bob")
        self.assertEqual(parsedate_to_datetime(item.findtext("pubDate")), dt.datetime(2026, 10, 1, 14, tzinfo=dt.timezone.utc))
        channel = ET.parse(self.output / "research/index.xml").find("channel")
        self.assertEqual(channel.findtext("title"), "Ada & Example <Lab> — Research")
        self.assertEqual(channel.find(f"{{{FEEDS.ATOM}}}link").attrib["href"], SITE + "research/index.xml")

    def test_rebuild_is_identical_and_wording_does_not_change_identity(self):
        record = self.record()
        self.write_yaml("research/papers.yml", [record])
        self.build()
        paths = [self.output / name for name in ("index.xml", "research/index.xml", "projects/index.xml")]
        before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]
        self.build()
        self.assertEqual(before, [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths])
        original = self.items("research/index.xml")[0]
        record.update(title="A revised title", href="https://external.example/new", abstract="A corrected summary.")
        self.write_yaml("research/papers.yml", [record])
        self.build()
        revised = self.items("research/index.xml")[0]
        self.assertEqual(revised.findtext("guid"), original.findtext("guid"))
        self.assertEqual(revised.findtext("pubDate"), original.findtext("pubDate"))
        self.assertNotEqual(revised.findtext("title"), original.findtext("title"))

    def test_unannounced_draft_placeholder_and_future_items_stay_out(self):
        self.write_yaml("research/papers.yml", [
            self.record("public"), self.record("draft", draft=True),
            self.record("placeholder", placeholder=True), self.record("future", "2026-10-04"),
            {"title": "Undated"}, {"title": "Empty field", "feed": {}},
            {"title": "Empty CMS fields", "feed": {"id": "", "date": ""}},
        ])
        counts = self.build()
        self.assertEqual(counts["research/index.xml"], 1)
        self.assertEqual(counts["index.xml"], 1)
        self.assertEqual(self.items("research/index.xml")[0].findtext("guid"), SITE + "research/#research-public")

    def test_combined_feed_filters_drafts_deleted_posts_and_preserves_blog_content(self):
        public = self.source_post("public")
        draft = self.source_post("private", draft=True)
        future = self.source_post("already-public-future-date", date="2026-10-04")
        deleted = SITE + "writing/posts/deleted/"
        # Accept Quarto's equivalent index.html addresses without changing GUIDs.
        public_item = self.blog_item(public + "index.html")
        self.write_blog([public_item, self.blog_item(draft), self.blog_item(deleted), self.blog_item(future, date="2026-10-04")])
        self.write_yaml("research/papers.yml", [self.record(date="2026-10-02")])
        self.write_yaml("projects/projects.yml", [self.record("package-v1", "2026-10-03", description="Release notes.")])
        self.build()
        items = self.items("index.xml")
        self.assertEqual([item.findtext("guid") for item in items], [future, SITE + "projects/#code-package-v1", SITE + "research/#research-market-paper", public + "index.html"])
        self.assertEqual(items[-1].findtext("description"), public_item.findtext("description"))
        self.assertEqual(items[-1].findtext("pubDate"), public_item.findtext("pubDate"))
        self.assertEqual(items[-1].findtext(f"{{{FEEDS.DC}}}creator"), "Ada")

    def test_removed_or_newly_private_announcements_do_not_linger(self):
        self.write_yaml("research/papers.yml", [self.record()])
        self.build()
        self.assertEqual(len(self.items("index.xml")), 1)
        self.write_yaml("research/papers.yml", [self.record(draft=True)])
        self.build()
        self.assertEqual(self.items("research/index.xml"), [])
        self.assertEqual(self.items("index.xml"), [])
        self.assertIsNone(ET.parse(self.output / "index.xml").find("channel/lastBuildDate"))

    def test_announcement_becomes_eligible_on_its_authored_date(self):
        self.write_yaml("projects/projects.yml", [self.record("package-v1", "2026-10-04")])
        self.build()
        self.assertEqual(self.items("projects/index.xml"), [])
        FEEDS.build_feeds(self.root, self.output, today=dt.date(2026, 10, 4))
        item = self.items("projects/index.xml")[0]
        self.assertEqual(item.findtext("pubDate"), "Sat, 03 Oct 2026 14:00:00 GMT")

    def test_melbourne_midnight_handles_daylight_saving_change(self):
        self.assertEqual(FEEDS.rss_date(dt.date(2026, 10, 3), FEEDS.ANNOUNCEMENT_TIMEZONE), "Fri, 02 Oct 2026 14:00:00 GMT")
        self.assertEqual(FEEDS.rss_date(dt.date(2026, 10, 5), FEEDS.ANNOUNCEMENT_TIMEZONE), "Sun, 04 Oct 2026 13:00:00 GMT")

    def test_mixed_feeds_sort_by_actual_instant_and_preserve_blog_timestamp(self):
        link = self.source_post("same-day", date="2026-10-03")
        item = self.blog_item(link, date="2026-10-03")
        item.find("pubDate").text = "Sat, 03 Oct 2026 01:30:00 +0000"
        self.write_blog([item])
        self.write_yaml("research/papers.yml", [self.record(date="2026-10-03")])
        self.build()
        channel = ET.parse(self.output / "index.xml").find("channel")
        items = channel.findall("item")
        self.assertEqual(items[0].findtext("guid"), link)
        self.assertEqual(items[0].findtext("pubDate"), "Sat, 03 Oct 2026 01:30:00 +0000")
        self.assertEqual(items[1].findtext("pubDate"), "Fri, 02 Oct 2026 14:00:00 GMT")
        self.assertEqual(channel.findtext("lastBuildDate"), "Sat, 03 Oct 2026 01:30:00 GMT")

    def test_stable_order_and_limit_are_independent_of_source_order(self):
        records = [self.record(f"paper-{number:02}", (dt.date(2026, 1, 1) + dt.timedelta(days=number)).isoformat()) for number in range(55)]
        self.write_yaml("research/papers.yml", records)
        self.build()
        before = (self.output / "research/index.xml").read_bytes()
        items = self.items("research/index.xml")
        self.assertEqual(len(items), 50)
        self.assertTrue(items[0].findtext("guid").endswith("paper-54"))
        self.assertTrue(items[-1].findtext("guid").endswith("paper-05"))
        self.write_yaml("research/papers.yml", list(reversed(records)))
        self.build()
        self.assertEqual((self.output / "research/index.xml").read_bytes(), before)

    def test_missing_blog_is_an_error_for_full_build_but_safe_for_partial_render(self):
        self.build()
        (self.output / "writing/index.xml").unlink()
        with self.assertRaisesRegex(FEEDS.FeedError, "Blog RSS feed is missing"):
            self.build()
        results = self.build(require_blog=False)
        self.assertEqual(set(results), {"research/index.xml", "projects/index.xml"})
        self.assertFalse((self.output / "index.xml").exists())

    def test_invalid_or_duplicate_announcement_cannot_publish_ambiguous_item(self):
        for records in ([self.record(date="not-a-date")], [self.record("Upper Case")], [self.record(), self.record()]):
            with self.subTest(records=records):
                self.write_yaml("research/papers.yml", records)
                with self.assertRaises(FEEDS.FeedError):
                    self.build()

    def test_combined_feed_deduplicates_native_blog_guids(self):
        link = self.source_post("public")
        item = self.blog_item(link)
        self.write_blog([item, item])
        self.build()
        self.assertEqual(len(self.items("index.xml")), 1)

    def test_custom_blog_output_names_remain_in_combined_feed_without_drafts(self):
        self.source_post("top-level", **{"output-file": "article.html"})
        self.source_post("format-level", format={"html": {"output-file": "custom"}})
        self.source_post("override", **{"output-file": "ignored", "format": {"html": {"output-file": "notes.txt"}}})
        self.source_post("private-custom", draft=True, format={"html": {"output-file": "private"}})
        public = [
            SITE + "writing/posts/top-level/article.html",
            SITE + "writing/posts/format-level/custom.html",
            SITE + "writing/posts/override/notes.txt.html",
        ]
        draft = SITE + "writing/posts/private-custom/private.html"
        self.write_blog([self.blog_item(link) for link in public + [draft]])
        self.build()
        self.assertEqual({item.findtext("guid") for item in self.items("index.xml")}, set(public))

    def test_blog_enabled_by_default_or_explicitly_preserves_native_items(self):
        link = self.source_post("public")
        item = self.blog_item(link)
        for sections in ({}, {"blog": True}):
            with self.subTest(sections=sections):
                self.write_yaml("_data/profile.yml", {"name": "Ada", "sections": sections})
                self.write_blog([item])
                native = (self.output / "writing/index.xml").read_bytes()
                self.build()
                self.assertEqual([entry.findtext("guid") for entry in self.items("index.xml")], [link])
                self.assertEqual((self.output / "writing/index.xml").read_bytes(), native)
                (self.output / "writing/index.xml").unlink()
                with self.assertRaisesRegex(FEEDS.FeedError, "Blog RSS feed is missing"):
                    self.build()

    def test_disabled_blog_clears_stale_feeds_and_can_be_enabled_again(self):
        link = self.source_post("public")
        self.source_post("private", draft=True)
        sources = {path: path.read_bytes() for path in (self.root / "writing/posts").rglob("*.qmd")}
        self.write_blog([self.blog_item(link)])
        self.write_yaml("research/papers.yml", [self.record()])
        self.write_yaml("projects/projects.yml", [self.record("package-v1")])
        stale_html = self.output / "writing/index.html"
        stale_html.write_text("<html><body>Existing Blog</body></html>")
        self.build()
        self.write_yaml("_data/profile.yml", {"name": "Ada", "sections": {"blog": False}})
        self.build()
        self.assertEqual(self.items("writing/index.xml"), [])
        channel = ET.parse(self.output / "writing/index.xml").find("channel")
        self.assertEqual(channel.findtext("link"), SITE + "subscribe.html")
        self.assertEqual(channel.find(f"{{{FEEDS.ATOM}}}link").attrib["href"], SITE + "writing/index.xml")
        expected = {SITE + "research/#research-market-paper", SITE + "projects/#code-package-v1"}
        self.assertEqual({item.findtext("guid") for item in self.items("index.xml")}, expected)
        self.assertEqual(len(self.items("research/index.xml")), 1)
        self.assertEqual(len(self.items("projects/index.xml")), 1)
        self.assertEqual({path: path.read_bytes() for path in sources}, sources)
        self.assertEqual(stale_html.read_text(), "<html><body>Existing Blog</body></html>")
        self.write_yaml("_data/profile.yml", {"name": "Ada", "sections": {"blog": True}})
        self.write_blog([self.blog_item(link)])
        self.build()
        self.assertEqual({item.findtext("guid") for item in self.items("index.xml")}, expected | {link})

    def test_disabled_blog_builds_without_a_native_feed(self):
        self.write_yaml("_data/profile.yml", {"name": "Ada", "sections": {"blog": False}})
        self.write_yaml("research/papers.yml", [self.record()])
        for require_blog in (True, False):
            with self.subTest(require_blog=require_blog):
                (self.output / "writing/index.xml").unlink()
                self.build(require_blog=require_blog)
                self.assertEqual(self.items("writing/index.xml"), [])
                self.assertEqual([item.findtext("guid") for item in self.items("index.xml")], [SITE + "research/#research-market-paper"])


if __name__ == "__main__":
    unittest.main()
