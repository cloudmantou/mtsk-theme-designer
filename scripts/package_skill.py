#!/usr/bin/env python3
"""分发本 skill：生成独立 ZIP、可导入的示例主题、预览和 SHA-256 清单。"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tempfile
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

import theme_tool as tool

SKILL = Path(__file__).resolve().parents[1]
# 只分发有用途的源文件，避免把缓存、生成物或本机文件一起打包。
PATTERNS = (
    "SKILL.md", "README.md", "agents/*.yaml", "references/*.md", "references/*.json",
    "scripts/*.py", "examples/*/theme.json", "tests/test_*.py", "tests/fixtures/*.json",
)

GUIDE = """# 红笺墨语主题制作包

## 直接使用主题

`themes/` 里的 `.mtsktheme` 才是导入 App 的文件，任选一个保存到 iPhone「文件」。
进入红笺墨语：设置 → 外观 → 管理与导入主题 → 右上角 ＋ → 选择文件 → 安装并使用。
也可以在「文件」里长按主题，选择分享，再用红笺墨语打开。
同 ID 的主题会替换旧版本；想保留两个版本，请使用不同 ID。

- 樱花：粉白配色，纸墨基础，经典书架列表。
- 墨夜：藏青与金色，纸墨布局，衬线顶栏。
- 竹青：经典布局，绿色强调，部分纸墨组件。

`previews/` 的 HTML 可在浏览器查看深浅色近似效果，以 App 实际显示为准。
这些主题调整界面和阅读器工具栏；阅读正文配色仍在阅读设置里调整。

## 让 AI 编写新主题

解压 `mtsk-theme-designer.zip`。将其中整个 `mtsk-theme-designer` 文件夹放入
Codex 的 `~/.codex/skills/`（若设置了 CODEX_HOME，则使用其下的 skills 目录）。
新建对话后输入：

> 用 $mtsk-theme-designer 制作一个海盐蓝界面主题，兼顾深浅色，生成预览并打包为 .mtsktheme。

运行脚本需要 Python 3.9+，不需要第三方 Python 包、Xcode、仓库源码或网络。
仅能聊天的 AI 可读取 SKILL.md 和 references 中的 Markdown 规则，输出完整 theme.json。
把 JSON 保存为文件后也能直接导入 App；不能只把 JSON 改名为 .mtsktheme。

Skill ZIP 是给 AI 工具的，不能导入 App，也不能把多个主题压成一个包交给 App。
schemaVersion 1 不支持背景图片、字体文件、任意布局代码或图标替换。
导入报错时，在 App 点「复制问题清单」，交给 AI 修复后重新校验、打包。

`SHA256SUMS.json` 记录各交付文件的 SHA-256，可用于传输后校验。
"""


def build_release(output: Path) -> None:
    output = output.resolve()
    if output.exists():
        raise ValueError(f"输出目录已存在，没有覆盖：{output}")
    examples = sorted((SKILL / "examples").glob("*/theme.json"))
    if not examples:
        raise ValueError("没有可分发的示例主题")
    for example in examples:
        manifest, issues = tool.validate_manifest(example.read_bytes())
        if issues:
            raise ValueError(f"{example}: " + "; ".join(map(str, issues)))
        if manifest["id"] != example.parent.name:
            raise ValueError(f"示例目录与主题 ID 不一致：{example}")
        warnings = tool.design_warnings(manifest)
        if warnings:
            raise ValueError(f"{example}: " + "; ".join(warnings))

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mtsk-skill-", dir=output.parent) as temporary:
        stage = Path(temporary) / "release"
        stage.mkdir()
        with zipfile.ZipFile(stage / "mtsk-theme-designer.zip", "w") as archive:
            files = sorted({p for pattern in PATTERNS for p in SKILL.glob(pattern)})
            for path in files:
                if path.is_symlink() or not path.is_file():
                    raise ValueError(f"不能分发链接或非文件：{path}")
                archive.writestr(tool.zip_entry(f"{SKILL.name}/{path.relative_to(SKILL).as_posix()}"),
                                 path.read_bytes())

        for directory in ("themes", "previews"):
            (stage / directory).mkdir()
        for example in examples:
            theme_id = example.parent.name
            package = stage / "themes" / f"{theme_id}.mtsktheme"
            preview = stage / "previews" / f"{theme_id}.html"
            with redirect_stdout(io.StringIO()):
                for args in (("pack", str(example.parent), "-o", str(package)),
                             ("validate", str(package)),
                             ("preview", str(package), "-o", str(preview))):
                    if tool.main(args) != 0:
                        raise ValueError(f"示例主题无法打包、回读或预览：{theme_id}")
        (stage / "使用说明.md").write_text(GUIDE, encoding="utf-8")
        checksums = {p.relative_to(stage).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(stage.rglob("*")) if p.is_file()}
        (stage / "SHA256SUMS.json").write_text(
            json.dumps(checksums, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stage.rename(output)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, required=True, help="新的分发目录（不覆盖已有目录）")
    args = parser.parse_args(argv)
    try:
        build_release(args.output)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"✗ {error}")
        return 1
    print(f"✓ 已生成 Skill ZIP、示例主题包、预览和校验清单：{args.output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
