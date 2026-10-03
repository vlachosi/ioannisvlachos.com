"""Check preparation wiring without launching the social-image browser."""

import builtins
import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType
import unittest
from unittest import mock

import yaml


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare-site.py"
SPEC = importlib.util.spec_from_file_location("prepare_integration", SCRIPT)
PREPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARE)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="site-prepare-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.profile = {"name": "Ada Example", "bio": "First paragraph.\n\nSecond paragraph.", "links": {}}
        for relative, data in {
            "_data/profile.yml": self.profile,
            "_data/cv.yml": {},
            **{path: [] for path in PREPARE.COLLECTIONS.values()},
        }.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml.safe_dump(data), encoding="utf-8")
        (self.root / "cv").mkdir()

    def test_check_only_does_not_import_renderers_or_write_generated_files(self):
        original_import = builtins.__import__

        def without_renderers(name, *args, **kwargs):
            if name in {"profile", "social_image"} or name.startswith("playwright"):
                self.fail(f"Validation-only mode imported renderer dependency: {name}")
            return original_import(name, *args, **kwargs)

        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        with mock.patch("builtins.__import__", side_effect=without_renderers):
            PREPARE.prepare(self.root, check_only=True)
        self.assertEqual(sorted(path.relative_to(self.root) for path in self.root.rglob("*")), before)

    def test_preparation_merges_generated_image_metadata_with_profile_configuration(self):
        renderer = ModuleType("profile")
        image_renderer = ModuleType("social_image")
        calls = []

        def render_profile(profile, generated, *, repo_root):
            calls.append("profile")
            self.assertEqual(profile, self.profile)
            self.assertEqual(repo_root, self.root)
            self.assertTrue(generated.is_dir())
            return {"website": {"title": profile["name"], "navbar": {"right": []}}, "blog-enabled": True}

        def generate_social_image(root, profile):
            calls.append("image")
            self.assertEqual(root, self.root)
            self.assertEqual(profile, self.profile)
            return {"image": "/assets/generated/social-preview.png?v=example-digest", "image-alt": "Ada Example — research & code"}

        renderer.render_profile = render_profile
        image_renderer.generate_social_image = generate_social_image
        with mock.patch.dict(sys.modules, {"profile": renderer, "social_image": image_renderer}):
            PREPARE.prepare(self.root, drafts=False)
        self.assertEqual(calls, ["profile", "image"])
        metadata = yaml.safe_load((self.root / "_generated/site.yml").read_text())
        self.assertEqual(metadata["website"], {
            "title": "Ada Example", "navbar": {"right": []},
            "image": "/assets/generated/social-preview.png?v=example-digest",
            "image-alt": "Ada Example — research & code",
        })
        self.assertIs(metadata["blog-enabled"], True)


if __name__ == "__main__":
    unittest.main()
