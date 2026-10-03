"""Rendered-site checker regressions, using a minimal temporary website."""
from contextlib import redirect_stdout
from html import escape
import importlib.util
import io
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
            "writing/index.html", "cv/index.html", "404.html",
        ):
            self.write(f"_site/{page}", f"<!doctype html><html><body>{escape(self.name)}</body></html>")
        self.write("_site/search.json", "[]")
        self.write("_site/sitemap.xml", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>')
        self.write("_site/writing/index.xml", '<rss version="2.0"><channel/></rss>')
        patch = mock.patch.object(checker, "ROOT", self.root)
        patch.start()
        self.addCleanup(patch.stop)

    def write(self, relative, source):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")

    def test_escaped_profile_name_is_recognized_in_rendered_pages(self):
        with redirect_stdout(io.StringIO()):
            checker.check_site(self.site)

    def test_missing_profile_identity_still_fails(self):
        self.write("_site/about.html", "<!doctype html><html><body>Different identity</body></html>")
        with self.assertRaisesRegex(ValueError, "Missing profile identity: about.html"):
            checker.check_site(self.site)


if __name__ == "__main__":
    unittest.main()
