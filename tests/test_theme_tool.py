"""theme_tool.py 的测试。运行：python3 -m unittest discover -s skills/mtsk-theme-designer/tests"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import zipfile
import warnings
from contextlib import redirect_stdout
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import theme_tool as tool  # noqa: E402

FIXTURES = SKILL / "tests" / "fixtures"
EXPECTED = json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))


def run(*argv) -> tuple[int, str]:
    out = io.StringIO()
    with redirect_stdout(out):
        code = tool.main(list(argv))
    return code, out.getvalue()


class ValidationMatchesAppTests(unittest.TestCase):
    def test_fixtures_produce_the_same_issue_paths_as_the_app(self):
        for name, expected in EXPECTED.items():
            if name.startswith("_"):
                continue
            with self.subTest(fixture=name):
                _, issues = tool.validate_manifest((FIXTURES / name).read_bytes())
                self.assertEqual(sorted(i.path for i in issues), sorted(expected))

    def test_every_fixture_is_listed(self):
        files = {p.name for p in FIXTURES.glob("*.json")} - {"expected.json"}
        self.assertEqual(files, {k for k in EXPECTED if not k.startswith("_")})

    def test_examples_are_valid_and_warning_free(self):
        for folder in sorted((SKILL / "examples").iterdir()):
            with self.subTest(example=folder.name):
                manifest, issues = tool.validate_manifest((folder / "theme.json").read_bytes())
                self.assertEqual(issues, [])
                self.assertEqual(manifest["id"], folder.name)
                self.assertEqual(tool.design_warnings(manifest), [])

    def test_suggestions_and_hex(self):
        self.assertEqual(tool.suggestion("pageCanvsa", tool.ROLES), "（是不是 pageCanvas？）")
        self.assertEqual(tool.parse_hex("#fff"), (1.0, 1.0, 1.0, 1.0))
        self.assertAlmostEqual(tool.parse_hex("#00000080")[3], 128 / 255)
        self.assertIsNone(tool.parse_hex("ffffff"))


class DesignWarningTests(unittest.TestCase):
    def manifest(self, **colors):
        return {"schemaVersion": 1, "id": "w.test", "name": "w", "base": "refined", "colors": colors}

    def test_low_contrast_text_is_flagged(self):
        warnings = tool.design_warnings(self.manifest(inkText={"light": "#DDDDDD", "dark": "#F2EFEA"}))
        self.assertTrue(any("inkText 在 inkCanvas" in w and "浅色" in w for w in warnings), warnings)

    def test_single_value_canvas_is_flagged(self):
        warnings = tool.design_warnings(self.manifest(inkCanvas="#FFFFFF"))
        self.assertTrue(any("colors.inkCanvas 只给了一个颜色" in w for w in warnings), warnings)

    def test_linked_roles_follow_ink_overrides(self):
        resolved = tool.resolved_colors(self.manifest(inkCanvas={"light": "#FF0000", "dark": "#00FF00"}))
        self.assertEqual(resolved["pageCanvas"]["light"][:3], (1.0, 0.0, 0.0))
        self.assertEqual(resolved["groupedCanvas"]["dark"][:3], (0.0, 1.0, 0.0))

    def test_classic_components_without_accent_tokens_are_flagged(self):
        m = self.manifest(inkAccent="#2F6F9F")
        m["layout"] = {"shelfList": "classic"}
        warnings = tool.design_warnings(m)
        self.assertTrue(any("readerAccent" in w for w in warnings), warnings)
        m["tokens"] = {"accent": "#2F6F9F", "readerAccent": "#2F6F9F", "buttonOrange": "#2F6F9F"}
        self.assertFalse(any("readerAccent" in w for w in tool.design_warnings(m)))

    def test_classic_ink_colors_without_ink_layout_are_flagged(self):
        m = {"schemaVersion": 1, "id": "c.test", "name": "c", "base": "classic", "colors": {"inkAccent": "#00AA00"}}
        self.assertTrue(any("不会显示出来" in w for w in tool.design_warnings(m)))


class CommandTests(unittest.TestCase):
    def test_new_validate_preview_pack_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "jade.green"
            self.assertEqual(run("new", "jade.green", "--name", "翡翠", "-o", str(folder))[0], 0)
            code, out = run("validate", str(folder))
            self.assertEqual(code, 0, out)
            preview = Path(tmp) / "p.html"
            self.assertEqual(run("preview", str(folder), "-o", str(preview))[0], 0)
            self.assertIn("翡翠", preview.read_text(encoding="utf-8"))
            package = Path(tmp) / "翡翠.mtsktheme"
            self.assertEqual(run("pack", str(folder), "-o", str(package))[0], 0)
            with zipfile.ZipFile(package) as z:
                self.assertEqual(z.namelist(), ["jade.green/theme.json"])
            code, out = run("validate", str(package))
            self.assertEqual(code, 0, out)

    def test_invalid_theme_is_not_packed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "bad"
            folder.mkdir()
            (folder / "theme.json").write_bytes((FIXTURES / "invalid-many.json").read_bytes())
            code, out = run("pack", str(folder), "-o", str(Path(tmp) / "x.mtsktheme"))
            self.assertEqual(code, 1)
            self.assertIn("colors.pageCanvsa", out)
            self.assertFalse((Path(tmp) / "x.mtsktheme").exists())

    def test_new_refuses_to_overwrite_an_existing_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "keep.me"
            self.assertEqual(run("new", "keep.me", "--name", "原稿", "-o", str(folder))[0], 0)
            manifest = folder / "theme.json"
            manifest.write_text(manifest.read_text(encoding="utf-8").replace('"colors": {}', '"colors": {"inkAccent": "#123456"}'), encoding="utf-8")
            code, out = run("new", "keep.me", "--name", "重来", "-o", str(folder))
            self.assertEqual(code, 1)
            self.assertIn("#123456", manifest.read_text(encoding="utf-8"), "原有设计不能被清空")
            self.assertEqual(run("new", "keep.me", "--name", "重来", "-o", str(folder), "--force")[0], 0)
            self.assertNotIn("#123456", manifest.read_text(encoding="utf-8"))

    def test_classic_preview_uses_the_classic_dark_palette(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "plain.classic"
            folder.mkdir()
            (folder / "theme.json").write_text(json.dumps(
                {"schemaVersion": 1, "id": "plain.classic", "name": "经典", "base": "classic",
                 "colors": {"pageCanvas": {"light": "#FAFAFA", "dark": "#101010"}}}), encoding="utf-8")
            out = Path(tmp) / "p.html"
            self.assertEqual(run("preview", str(folder), "-o", str(out))[0], 0)
            panes = out.read_text(encoding="utf-8").split("<section")[1:]
            self.assertIn("--canvas:rgba(250,250,250", panes[0])
            self.assertIn("--canvas:rgba(16,16,16", panes[1])
            self.assertIn("--text:rgba(255,255,255", panes[1], "经典深色文字是白色")

    def test_new_rejects_bad_id(self):
        self.assertEqual(run("new", "Bad ID", "--name", "x")[0], 1)


class PackageCompatibilityTests(unittest.TestCase):
    def validate_zip(self, entries):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.mtsktheme"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)  # 重复路径夹具是有意构造的。
                with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                    for name, data in entries:
                        archive.writestr(name, data)
            return run("validate", str(path))

    def setUp(self):
        self.manifest = (FIXTURES / "valid-minimal.json").read_bytes()

    def test_rejects_unsafe_paths_even_in_ignored_files(self):
        for path in ("../x", "/x", "a/../x", "a\\x", "__MACOSX/../x", "x\ny"):
            with self.subTest(path=path):
                code, out = self.validate_zip([("theme.json", self.manifest), (path, b"x")])
                self.assertEqual(code, 1, out)
                self.assertIn("不安全", out)

    def test_rejects_more_than_200_entries_including_junk(self):
        code, out = self.validate_zip([("theme.json", self.manifest)]
                                      + [(f"__MACOSX/{i}", b"") for i in range(200)])
        self.assertEqual(code, 1, out)
        self.assertIn("200", out)

    def test_rejects_stray_siblings_of_manifest_folder(self):
        code, out = self.validate_zip([("test/theme.json", self.manifest), ("other.txt", b"x")])
        self.assertEqual(code, 1, out)
        self.assertIn("唯一", out)

    def test_rejects_duplicate_or_deep_manifests(self):
        for paths in (("theme.json", "theme.json"), ("a/theme.json", "b/theme.json"), ("a/b/theme.json",)):
            with self.subTest(paths=paths):
                self.assertEqual(self.validate_zip([(p, self.manifest) for p in paths])[0], 1)

    def test_accepts_root_and_single_folder_with_macos_junk(self):
        for prefix in ("", "test/"):
            with self.subTest(prefix=prefix):
                code, out = self.validate_zip([(prefix + "theme.json", self.manifest),
                                              ("__MACOSX/._theme.json", b"x"), (".DS_Store", b"x")])
                self.assertEqual(code, 0, out)

    def test_rejects_compressed_oversized_manifest(self):
        code, out = self.validate_zip([("theme.json", b" " * (tool.TOP["maxManifestBytes"] + 1))])
        self.assertEqual(code, 1, out)
        self.assertIn("256 KB", out)

    def test_rejects_oversized_package_before_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "large.mtsktheme"
            with path.open("wb") as file:
                file.truncate(tool.SPEC["package"]["maxBytes"] + 1)
            code, out = run("validate", str(path))
            self.assertEqual(code, 1, out)
            self.assertIn("20 MB", out)

    def test_renaming_json_to_mtsktheme_does_not_make_a_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fake.mtsktheme"
            path.write_bytes(self.manifest)
            self.assertEqual(run("validate", str(path))[0], 1)

    def test_json_extension_is_parsed_as_json_like_the_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "theme.json"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("theme.json", self.manifest)
            self.assertEqual(run("validate", str(path))[0], 1)

    def test_rejects_compression_not_supported_by_the_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lzma.mtsktheme"
            with zipfile.ZipFile(path, "w", zipfile.ZIP_LZMA) as archive:
                archive.writestr("theme.json", self.manifest)
            code, out = run("validate", str(path))
            self.assertEqual(code, 1, out)
            self.assertIn("Deflate", out)

    def test_missing_file_reports_failure_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run("validate", str(Path(tmp) / "missing.json"))[0], 1)

    def test_same_input_produces_identical_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs = [Path(tmp) / f"{i}.mtsktheme" for i in range(2)]
            for output in outputs:
                self.assertEqual(run("pack", str(SKILL / "examples" / "moye.night"), "-o", str(output))[0], 0)
            self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())


class SkillStructureTests(unittest.TestCase):
    def test_frontmatter_and_files(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: mtsk-theme-designer\ndescription: "))
        self.assertLessEqual(len(text.splitlines()), 500)
        for rel in ["agents/openai.yaml", "references/theme-schema.md", "references/design-guide.md",
                    "references/theme-keys.json", "scripts/theme_tool.py"]:
            self.assertTrue((SKILL / rel).is_file(), rel)

    def test_reference_schema_is_the_app_doc(self):
        repo_doc = SKILL.parents[1] / "docs" / "THEME_SCHEMA_V1.md"
        if not repo_doc.exists():
            self.skipTest("skill copied outside the app repo")
        self.assertEqual((SKILL / "references" / "theme-schema.md").read_text(encoding="utf-8"),
                         repo_doc.read_text(encoding="utf-8"),
                         "改了 docs/THEME_SCHEMA_V1.md 后要复制到 references/theme-schema.md")


if __name__ == "__main__":
    unittest.main()
