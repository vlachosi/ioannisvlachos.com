"""Regression checks for profile settings shared by all site pages."""

from copy import deepcopy
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("profile_renderer", REPO / "scripts/profile.py")
PROFILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE)


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


if __name__ == "__main__":
    unittest.main()
