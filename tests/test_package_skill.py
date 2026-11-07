"""检查用户拿到的分发包能脱离仓库独立使用。"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import package_skill


class ReleaseTests(unittest.TestCase):
    def test_release_is_self_contained_and_all_deliverables_match_checksums(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = Path(tmp) / "release"
            package_skill.build_release(release)
            checksums = json.loads((release / "SHA256SUMS.json").read_text(encoding="utf-8"))
            for relative, expected in checksums.items():
                self.assertEqual(hashlib.sha256((release / relative).read_bytes()).hexdigest(), expected)
            extracted = Path(tmp) / "extracted"
            with zipfile.ZipFile(release / "mtsk-theme-designer.zip") as archive:
                self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in archive.namelist()))
                archive.extractall(extracted)
            standalone = extracted / "mtsk-theme-designer"
            script = standalone / "scripts" / "theme_tool.py"
            packages = sorted((release / "themes").glob("*.mtsktheme"))
            self.assertEqual(len(packages), 3)
            for package in packages:
                result = subprocess.run([sys.executable, str(script), "validate", str(package)],
                                        cwd=tmp, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("没有设计警告", result.stdout)
                self.assertTrue((release / "previews" / f"{package.stem}.html").is_file())
            output = Path(tmp) / "portable-theme"
            for args in (("new", "portable.theme", "--name", "独立测试", "-o", str(output)),
                         ("pack", str(output), "-o", str(Path(tmp) / "portable.mtsktheme")),
                         ("validate", str(Path(tmp) / "portable.mtsktheme"))):
                result = subprocess.run([sys.executable, str(script), *args], cwd=tmp,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_existing_release_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            original = output / "user-file.txt"
            original.write_text("keep", encoding="utf-8")
            with self.assertRaises(ValueError):
                package_skill.build_release(output)
            self.assertEqual(original.read_text(encoding="utf-8"), "keep")

    def test_repeated_release_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / "a", Path(tmp) / "b"
            package_skill.build_release(first)
            package_skill.build_release(second)
            self.assertEqual((first / "SHA256SUMS.json").read_bytes(), (second / "SHA256SUMS.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
