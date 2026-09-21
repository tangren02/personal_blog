from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from generator import build


class GeneratorTests(unittest.TestCase):
    def test_current_site_generates_clean_routes_and_dynamic_card(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "dist"
            with patch.object(build, "DIST_DIR", output):
                result = build.build_site()
            self.assertEqual(result.entry_count, 1)
            self.assertTrue((output / "index.html").exists())
            self.assertTrue((output / "knowledge/projects/index.html").exists())
            self.assertTrue((output / "projects/hstring/index.html").exists())
            project_index = (output / "knowledge/projects/index.html").read_text(encoding="utf-8")
            self.assertIn("C++ / MEMORY · CLOSED PROJECT", project_index)
            self.assertIn("/projects/hstring/", project_index)

    def test_rejects_duplicate_clean_routes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory) / "content"
            content.mkdir()
            entry = """---\nkind: project\nstatus: active\ntitle: Example\nslug: same\nsummary: Example\nupdated: 2026-09-21\norder: 1\n---\nBody\n"""
            (content / "one.md").write_text(entry, encoding="utf-8")
            (content / "two.md").write_text(entry, encoding="utf-8")
            with patch.object(build, "CONTENT_DIR", content):
                with self.assertRaisesRegex(build.BuildError, "duplicate route"):
                    build._load_entries()

    def test_rejects_external_content_resources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            content = Path(directory) / "content"
            content.mkdir()
            entry = """---\nkind: project\nstatus: active\ntitle: Example\nslug: example\nsummary: Example\nupdated: 2026-09-21\norder: 1\n---\n<img src=\"https://example.com/image.png\">\n"""
            (content / "example.md").write_text(entry, encoding="utf-8")
            with patch.object(build, "CONTENT_DIR", content):
                with self.assertRaisesRegex(build.BuildError, "external resource"):
                    build._load_entries()

    def test_empty_categories_use_shared_empty_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "dist"
            with patch.object(build, "DIST_DIR", output):
                build.build_site()
            html = (output / "knowledge/research/index.html").read_text(encoding="utf-8")
            self.assertIn("empty-section", html)
            self.assertIn("第一个科研条目还在整理中", html)


if __name__ == "__main__":
    unittest.main()
