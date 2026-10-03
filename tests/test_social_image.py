"""Social-image cache and CMS data checks; Chromium is mocked throughout."""

from copy import deepcopy
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest import mock
import zlib

import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("site_social_image", ROOT / "scripts/social_image.py")
SOCIAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOCIAL)


def png_bytes(colour=b"\x23\x45\x67", size=(1200, 630)):
    """A real, small RGB PNG makes dimensions and integrity checks meaningful."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    width, height = size
    rows = (b"\x00" + colour * width) * height
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


class CardMarkup(HTMLParser):
    def __init__(self, document):
        super().__init__()
        self.scripts = []
        self.data = ""
        self.in_data = False
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            attrs = dict(attrs)
            self.scripts.append(attrs)
            self.in_data = attrs.get("id") == "card-data"

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_data = False

    def handle_data(self, value):
        if self.in_data:
            self.data += value


class SocialImageTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="site-social-image-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for relative in ["templates/social-card.html", "styles/light.scss"]:
            self.write(relative, (ROOT / relative).read_bytes())
        for key, filename in SOCIAL.FONTS.items():
            self.write("assets/fonts/" + filename, f"fake {key} font".encode())
        self.config = {"website": {"site-url": "https://example.org/academic/"}}
        self.write_config()
        self.profile = {"name": "Ada Example", "role": "Researcher", "affiliation": "Example University", "bio": "Initial biography."}
        self.output = self.root / "assets/generated/social-preview.png"
        self.legacy = self.root / "assets/og.png"
        self.cache = self.root / "_generated/social-image.json"
        renderer = mock.patch.object(SOCIAL, "_render", side_effect=self.render)
        self.renderer = renderer.start()
        self.addCleanup(renderer.stop)
        package_version = mock.patch.object(SOCIAL, "version", return_value="test-playwright-version")
        self.package_version = package_version.start()
        self.addCleanup(package_version.stop)

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def write_config(self):
        self.write("_quarto.yml", yaml.safe_dump(self.config).encode())

    @staticmethod
    def render(document):
        # Distinct visible inputs produce distinct fixture pixels without a browser.
        return png_bytes(hashlib.sha256(document.encode()).digest()[:3]), {"fixture": True}

    def generate(self, profile=None):
        return SOCIAL.generate_social_image(self.root, self.profile if profile is None else profile)

    def test_metadata_versions_png_bytes_and_keeps_legacy_alias(self):
        metadata = self.generate()
        image = self.output.read_bytes()
        self.assertEqual(SOCIAL._png_size(image), (1200, 630))
        self.assertEqual(metadata["image"], "/assets/generated/social-preview.png?v=" + hashlib.sha256(image).hexdigest()[:16])
        self.assertEqual(metadata["image-alt"], "Ada Example. Researcher at Example University. example.org/academic")
        self.assertEqual(self.legacy.read_bytes(), image)
        self.renderer.assert_called_once()

    def test_unrelated_cms_changes_reuse_image_and_preserve_file_timestamps(self):
        original = self.generate()
        paths = [self.output, self.legacy, self.cache]
        for path in paths:
            os.utime(path, ns=(1_000_000_000, 1_000_000_000))
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}
        changed = deepcopy(self.profile)
        changed.update(bio="A rewritten biography.", about_extra="New interests.", email="ada@example.org", links={"github": "https://example.org/github"}, sections={"blog": False})
        self.assertEqual(self.generate(changed), original)
        self.renderer.assert_called_once()
        self.assertEqual({path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}, before)

    def test_name_role_and_affiliation_changes_invalidate_cache(self):
        previous = self.generate()
        for key, value in [("name", "Grace Example"), ("role", "Lecturer"), ("affiliation", "Another University")]:
            with self.subTest(field=key):
                calls = self.renderer.call_count
                self.profile[key] = value
                current = self.generate()
                self.assertEqual(self.renderer.call_count, calls + 1)
                self.assertNotEqual(current["image"], previous["image"])
                self.assertIn(value, current["image-alt"])
                previous = current

    def test_template_fonts_palette_and_renderer_version_invalidate_cache(self):
        self.generate()
        changes = [
            ("templates/social-card.html", lambda data: data + b"\n<!-- revised design -->\n"),
            ("assets/fonts/" + SOCIAL.FONTS["petrona"], lambda data: data + b" revised font"),
            ("styles/light.scss", lambda data: data.replace(b"$paper:", b"$paper: #ffffff;\n$previous-paper:", 1)),
        ]
        for relative, mutate in changes:
            with self.subTest(input=relative):
                calls = self.renderer.call_count
                path = self.root / relative
                path.write_bytes(mutate(path.read_bytes()))
                self.generate()
                self.assertEqual(self.renderer.call_count, calls + 1)
        calls = self.renderer.call_count
        self.package_version.return_value = "new-test-playwright-version"
        self.generate()
        self.assertEqual(self.renderer.call_count, calls + 1)

    def test_missing_corrupt_or_wrong_size_image_is_regenerated(self):
        expected = self.generate()
        for damage in (None, b"not a PNG", png_bytes(size=(2, 2)), png_bytes(b"\x01\x02\x03")):
            with self.subTest(damage="missing" if damage is None else len(damage)):
                calls = self.renderer.call_count
                if damage is None:
                    self.output.unlink()
                else:
                    self.output.write_bytes(damage)
                self.assertEqual(self.generate(), expected)
                self.assertEqual(self.renderer.call_count, calls + 1)
                self.assertEqual(self.output.read_bytes(), self.legacy.read_bytes())

    def test_missing_or_invalid_cache_metadata_is_rebuilt(self):
        expected = self.generate()
        for invalid in (None, "not JSON", "[]", "{}"):
            with self.subTest(cache=invalid):
                calls = self.renderer.call_count
                if invalid is None:
                    self.cache.unlink()
                else:
                    self.cache.write_text(invalid)
                self.assertEqual(self.generate(), expected)
                self.assertEqual(self.renderer.call_count, calls + 1)

    def test_cached_png_restores_missing_or_changed_legacy_alias_without_rendering(self):
        expected = self.generate()
        for damage in (None, b"outdated legacy image"):
            with self.subTest(legacy=damage):
                if damage is None:
                    self.legacy.unlink()
                else:
                    self.legacy.write_bytes(damage)
                self.assertEqual(self.generate(), expected)
                self.assertEqual(self.legacy.read_bytes(), self.output.read_bytes())
                self.renderer.assert_called_once()

    def test_site_domain_and_path_are_visible_but_scheme_query_and_fragment_are_not(self):
        metadata = self.generate()
        self.config["website"]["site-url"] = "http://example.org/academic/?tracking=1#section"
        self.write_config()
        self.assertEqual(self.generate(), metadata)
        self.renderer.assert_called_once()
        self.config["website"]["site-url"] = "https://research.example.org/new-path/"
        self.write_config()
        changed = self.generate()
        self.assertNotEqual(changed["image"], metadata["image"])
        self.assertTrue(changed["image-alt"].endswith("research.example.org/new-path"))

    def test_invalid_site_url_is_rejected_before_rendering(self):
        for address in ("example.org", "/academic/", "file:///tmp/image", "https:///no-host", "javascript:alert(1)"):
            with self.subTest(address=address):
                self.config["website"]["site-url"] = address
                self.write_config()
                with self.assertRaisesRegex(ValueError, "absolute HTTP"):
                    self.generate()
        self.renderer.assert_not_called()

    def test_cms_text_cannot_close_json_script_and_survives_unchanged(self):
        attack = '</script><script>alert("x")</script><img src=x onerror=alert(1)> & Ω\u2028'
        data = SOCIAL._card_data(self.root, {**self.profile, "name": attack})
        document = SOCIAL._document((self.root / "templates/social-card.html").read_text(), data, {"petrona": b"font", "mono": b"font"})
        parsed = CardMarkup(document)
        self.assertEqual(len(parsed.scripts), 2)
        self.assertEqual(json.loads(parsed.data), data)
        self.assertNotIn(attack, document)

    def test_cms_text_that_matches_template_tokens_is_preserved(self):
        name = "__FONT_PETRONA__ __FONT_MONO__ __CARD_DATA__"
        data = SOCIAL._card_data(self.root, {**self.profile, "name": name})
        document = SOCIAL._document((self.root / "templates/social-card.html").read_text(), data, {"petrona": b"font", "mono": b"font"})
        self.assertEqual(json.loads(CardMarkup(document).data)["name"], name)


if __name__ == "__main__":
    unittest.main()
