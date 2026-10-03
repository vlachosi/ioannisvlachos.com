"""Regression checks for profile settings shared by all site pages."""

from copy import deepcopy
from html.parser import HTMLParser
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("profile_renderer", REPO / "scripts/profile.py")
PROFILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE)


class ProfileLinks(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.links = []
        self.placeholders = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.links.append(attrs)
        if attrs.get("aria-disabled") == "true":
            self.placeholders.append(attrs)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="site-profile-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.generated = self.root / "_generated"
        (self.root / "_includes").mkdir()
        for filename in ("head.html", "after-body.html"):
            (self.root / "_includes" / filename).write_text(
                (REPO / "_includes" / filename).read_text(encoding="utf-8"), encoding="utf-8"
            )
        self.profile = yaml.safe_load((REPO / "_data/profile.yml").read_text(encoding="utf-8"))

    def render(self, profile=None):
        return PROFILE.render_profile(profile or self.profile, self.generated, self.root)

    def test_visibility_setting_controls_navigation_and_rendering(self):
        profile = deepcopy(self.profile)
        profile["sections"] = {"talks": False, "teaching": False}
        config = self.render(profile)
        self.assertEqual(config["project"]["render"], ["*.qmd", "!talks/", "!teaching/"])
        self.assertNotIn("Talks", [x["text"] for x in config["website"]["navbar"]["right"]])
        profile["sections"]["talks"] = True
        config = self.render(profile)
        self.assertEqual(config["project"]["render"], ["*.qmd", "!teaching/"])
        self.assertIn("Talks", [x["text"] for x in config["website"]["navbar"]["right"]])

    def test_blog_remains_enabled_when_its_visibility_setting_is_missing(self):
        profile = deepcopy(self.profile)
        for sections in ({"talks": False, "teaching": False}, None):
            with self.subTest(sections=sections):
                if sections is None:
                    profile.pop("sections", None)
                else:
                    profile["sections"] = sections
                config = self.render(profile)
                self.assertIs(config["blog-enabled"], True)
                self.assertNotIn("!writing/", config["project"]["render"])
                self.assertIn({"text": "Blog", "href": "writing/index.qmd"}, config["website"]["navbar"]["right"])
                home = yaml.safe_load((self.generated / "home.yml").read_text())
                blog = next(item for item in home["listing"] if item["id"] == "home-blog")
                self.assertEqual(blog["contents"], "writing/posts")
                self.assertIn('/writing/index.xml', (self.generated / "subscriptions.html").read_text())

    def test_disabled_blog_removes_listing_navigation_and_subscription_discovery(self):
        profile = deepcopy(self.profile)
        profile["sections"] = {"blog": False, "talks": True, "teaching": True}
        config = self.render(profile)
        self.assertIs(config["blog-enabled"], False)
        self.assertEqual(config["project"]["render"], ["*.qmd", "!writing/"])
        self.assertEqual(
            [item["text"] for item in config["website"]["navbar"]["right"]],
            ["About", "Research", "Code", "Teaching", "Talks", "CV"],
        )
        home = yaml.safe_load((self.generated / "home.yml").read_text())
        self.assertEqual([item["id"] for item in home["listing"]], ["home-research", "home-projects"])
        self.assertNotIn("writing", (self.generated / "home.yml").read_text())
        options = (self.generated / "subscriptions.html").read_text()
        self.assertNotIn("subscribe-blog", options)
        self.assertNotIn("/writing/", options)
        self.assertIn("Research announcements and code.", options)
        self.assertNotIn("New blog posts", options)
        self.assertEqual(
            {link["href"] for link in ProfileLinks(options).links},
            {"/index.xml", "/research/index.xml", "/projects/index.xml"},
        )
        discovery = yaml.safe_load((self.generated / "subscribe.yml").read_text())["include-in-header"]["text"]
        self.assertNotIn("/writing/", discovery)
        self.assertEqual(discovery.count('rel="alternate"'), 3)

    def test_reenabling_blog_restores_generated_inputs_without_losing_profile_settings(self):
        profile = deepcopy(self.profile)
        profile.setdefault("sections", {})["blog"] = True
        original_profile = deepcopy(profile)
        enabled_config = self.render(profile)
        enabled_files = {path.name: path.read_bytes() for path in self.generated.iterdir()}
        profile["sections"]["blog"] = False
        self.render(profile)
        profile["sections"]["blog"] = True
        self.assertEqual(self.render(profile), enabled_config)
        self.assertEqual({path.name: path.read_bytes() for path in self.generated.iterdir()}, enabled_files)
        self.assertEqual(profile, original_profile)

    def test_contact_and_identity_are_escaped_in_generated_html(self):
        profile = deepcopy(self.profile)
        profile.update(name='Ada <Example> & Co', email='a</script>@example.com')
        profile["links"] = {"github": "https://example.com/a?x=1&y=2", "x": ""}
        config = self.render(profile)
        self.assertEqual(config["website"]["title"], 'Ada <Example> & Co')
        self.assertIn('Ada &lt;Example&gt; &amp; Co', (self.generated / "home-profile.qmd").read_text())
        self.assertIn('Ada &lt;Example&gt; &amp; Co', (self.generated / "head.html").read_text())
        after = (self.generated / "after-body.html").read_text()
        self.assertNotIn('a</script>@', after)
        self.assertIn('a\\u003c/script\\u003e@example.com', after)
        self.assertIn('href="https://example.com/a?x=1&amp;y=2"', (self.generated / "elsewhere.html").read_text())
        self.assertEqual(config["website"]["twitter-card"]["creator"], "")
        self.assertEqual(len(config["website"]["page-footer"]["center"]), 1)

    def test_repeated_render_preserves_include_timestamps(self):
        self.render()
        before = {path.name: path.stat().st_mtime_ns for path in self.generated.iterdir()}
        self.render()
        after = {path.name: path.stat().st_mtime_ns for path in self.generated.iterdir()}
        self.assertEqual(before, after)

    def test_missing_profiles_are_omitted_on_home_research_and_about(self):
        profile = deepcopy(self.profile)
        profile["links"] = {"orcid": "https://orcid.org/example", "ssrn": "https://papers.ssrn.com/example"}
        self.render(profile)
        research = ProfileLinks((self.generated / "research-profiles.html").read_text())
        self.assertEqual([link["href"] for link in research.links], list(profile["links"].values()))
        self.assertEqual(research.placeholders, [])
        for filename in ("home-profile.qmd", "elsewhere.html"):
            source = (self.generated / filename).read_text()
            parsed = ProfileLinks(source)
            self.assertEqual([link["href"] for link in parsed.links], list(profile["links"].values()))
            self.assertEqual(parsed.placeholders, [])
            self.assertNotIn("data-email-slot", source)
        home = ProfileLinks((self.generated / "home-profile.qmd").read_text())
        self.assertEqual(home.links[0]["aria-label"], "ORCID profile")
        self.assertEqual(home.links[0]["class"], "id-icon-only")

    def test_configured_profiles_activate_on_home_and_research_and_can_be_cleared(self):
        profile = deepcopy(self.profile)
        profile["links"]["google_scholar"] = "https://scholar.google.com/citations?user=Example&hl=en"
        profile["links"]["researchgate"] = "https://www.researchgate.net/profile/Example"
        self.render(profile)
        for filename in ("home-profile.qmd", "research-profiles.html"):
            parsed = ProfileLinks((self.generated / filename).read_text())
            scholar = [link for link in parsed.links if link.get("aria-label") == "Google Scholar profile"]
            self.assertEqual([link["href"] for link in scholar], [profile["links"]["google_scholar"]])
        for filename in ("research-profiles.html", "elsewhere.html"):
            parsed = ProfileLinks((self.generated / filename).read_text())
            self.assertIn(profile["links"]["researchgate"], [link["href"] for link in parsed.links])
        profile["links"] = {key: "" for key in PROFILE.RESEARCH_PROFILES}
        config = self.render(profile)
        parsed = ProfileLinks((self.generated / "research-profiles.html").read_text())
        self.assertEqual(parsed.links, [])
        self.assertEqual(parsed.placeholders, [])
        self.assertEqual((self.generated / "research-profiles.html").read_text(), "")
        self.assertEqual((self.generated / "elsewhere.html").read_text(), "")
        self.assertNotIn('class="hero__profiles"', (self.generated / "home-profile.qmd").read_text())
        self.assertFalse(config["has-contact-links"])

    def test_email_and_social_rows_restore_after_clearing_all_contacts(self):
        profile = deepcopy(self.profile)
        profile["links"] = {"github": "https://github.com/example", "x": "", "researchgate": "  "}
        profile["email"] = "person@example.com"
        config = self.render(profile)
        self.assertTrue(config["has-contact-links"])
        about = (self.generated / "elsewhere.html").read_text()
        self.assertEqual([link["href"] for link in ProfileLinks(about).links], ["mailto:person@example.com", "https://github.com/example"])
        self.assertNotIn("ResearchGate", about)
        self.assertNotIn('academic-links', (self.generated / "home-profile.qmd").read_text())
        profile["email"] = ""
        profile["links"]["github"] = ""
        config = self.render(profile)
        self.assertFalse(config["has-contact-links"])
        self.assertEqual((self.generated / "elsewhere.html").read_text(), "")
        self.assertNotIn("data-email-slot", (self.generated / "home-profile.qmd").read_text())
        profile["email"] = "person@example.com"
        profile["links"]["github"] = "https://github.com/example"
        self.render(profile)
        self.assertEqual((self.generated / "elsewhere.html").read_text(), about)


if __name__ == "__main__":
    unittest.main()
