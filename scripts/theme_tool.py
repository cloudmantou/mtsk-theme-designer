#!/usr/bin/env python3
"""mtsk 界面主题工具：校验、对比度检查、预览、打包。

只依赖 Python 3.9+ 标准库。规则来自同目录上一级的 references/theme-keys.json（由 App 源码生成，
App 的单元测试保证两边一致），所以这里的校验结果与 App 导入时的校验相同。

用法：
  theme_tool.py new <id> --name 名称 [--base refined|classic] [-o 输出目录]
  theme_tool.py validate <theme.json | 主题目录 | .mtsktheme>   # 错误 = App 会拒绝；警告 = 设计建议
  theme_tool.py preview <theme.json | 主题目录> [-o preview.html]
  theme_tool.py pack <主题目录> [-o 输出.mtsktheme]
"""
from __future__ import annotations

import argparse
import html
import io
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE.parent / "references" / "theme-keys.json"
SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))

ROLES = [r["name"] for r in SPEC["colorRoles"]]
ROLE_SET = set(ROLES)
LAYOUT = SPEC["layoutFamilies"]
BEHAVIOR = SPEC["behaviorFlags"]
TOKENS = SPEC["tokens"]
TOP = SPEC["topLevel"]
KNOWN_TOP = set(TOP["required"]) | set(TOP["optional"])


_MISSING = object()


@dataclass
class Issue:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}：{self.message}"


# ---------------------------------------------------------------- 颜色

HEX_RE = re.compile(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")


def parse_hex(value: str):
    """返回 (r, g, b, a)，0–1；CSS 顺序，alpha 在最后。"""
    if not isinstance(value, str) or not HEX_RE.fullmatch(value):
        return None
    h = value[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def suggestion(key: str, candidates) -> str:
    def distance(a: str, b: str) -> int:
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
            prev = cur
        return prev[-1]

    limit = max(2, len(key) // 3)
    best = None
    for c in sorted(candidates):
        d = distance(key.lower(), c.lower())
        if d <= limit and (best is None or d < best[1]):
            best = (c, d)
    return f"（是不是 {best[0]}？）" if best else ""


# ---------------------------------------------------------------- 校验（与 App 的 ThemeManifest 一致）

def is_bool(v) -> bool:
    return isinstance(v, bool)


def is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def valid_id(value: str) -> bool:
    return (isinstance(value, str) and re.fullmatch(TOP["idPattern"], value) is not None
            and not value.startswith(TOP["idForbiddenPrefix"]))


def validate_manifest(data: bytes) -> tuple[dict | None, list[Issue]]:
    """返回 (解析后的对象, 错误列表)。错误为空才可导入。"""
    if len(data) > TOP["maxManifestBytes"]:
        return None, [Issue("$", f"文件超过 {TOP['maxManifestBytes'] // 1024} KB")]
    def reject_constant(value):
        raise ValueError(f"JSON 不支持 {value}")

    try:
        root = json.loads(data.decode("utf-8-sig"), parse_constant=reject_constant)
    except Exception as exc:  # noqa: BLE001
        return None, [Issue("$", f"不是合法的 JSON（{exc}）")]
    if not isinstance(root, dict):
        return None, [Issue("$", "顶层必须是对象 {…}")]

    issues: list[Issue] = []
    for key in sorted(root):
        if key not in KNOWN_TOP:
            issues.append(Issue(key, f"未知字段（允许的字段：{', '.join(sorted(KNOWN_TOP))}）"))

    sv = root.get("schemaVersion")
    if is_number(sv) and sv == SPEC["schemaVersion"]:
        pass
    elif is_number(sv) and sv > SPEC["schemaVersion"]:
        return None, [Issue("schemaVersion", f"主题需要更新版本的 App（本机支持到 {SPEC['schemaVersion']}）")]
    elif sv is None:
        issues.append(Issue("schemaVersion", f"缺少，必须写 {SPEC['schemaVersion']}"))
    else:
        issues.append(Issue("schemaVersion", f"必须是数字 {SPEC['schemaVersion']}"))

    def required_string(key):
        if key not in root:
            issues.append(Issue(key, "缺少"))
            return None
        if not isinstance(root[key], str):
            issues.append(Issue(key, "必须是字符串"))
            return None
        return root[key]

    theme_id = required_string("id")
    if theme_id is not None and not valid_id(theme_id):
        issues.append(Issue("id", "只能用小写字母、数字和 . _ -，3–64 个字符，以字母或数字开头，且不能以 builtin. 开头"))
    name = required_string("name")
    if name is not None and (not name.strip() or len(name) > TOP["maxLength"]["name"]):
        issues.append(Issue("name", f"不能为空，最多 {TOP['maxLength']['name']} 个字符"))
    for key in ("author", "version", "description"):
        if key in root:
            if not isinstance(root[key], str):
                issues.append(Issue(key, "必须是字符串"))
            elif len(root[key]) > TOP["maxLength"][key]:
                issues.append(Issue(key, f"最多 {TOP['maxLength'][key]} 个字符"))
    base = required_string("base")
    if base is not None and base not in SPEC["bases"]:
        issues.append(Issue("base", "必须是 \"classic\"（经典香色）或 \"refined\"（新版纸墨）"))

    # colors
    colors = root.get("colors", _MISSING)
    if colors is not _MISSING:  # 显式写 null 也要报错，与 App 一致
        if not isinstance(colors, dict):
            issues.append(Issue("colors", "必须是对象 {\"角色名\": 颜色}"))
        else:
            for key in sorted(colors):
                path = f"colors.{key}"
                if key not in ROLE_SET:
                    issues.append(Issue(path, "未知颜色角色" + suggestion(key, ROLES)))
                    continue
                value = colors[key]
                if isinstance(value, str):
                    if value == "none" and key in SPEC["colorRolesAllowingNone"]:
                        continue
                    if parse_hex(value) is None:
                        issues.append(Issue(path, f"颜色格式错误：\"{value}\"，应写 #RRGGBB 或 #RRGGBBAA"))
                elif isinstance(value, dict):
                    for sub in sorted(value):
                        if sub not in ("light", "dark"):
                            issues.append(Issue(f"{path}.{sub}", "未知字段（只允许 light、dark）"))
                    light, dark = value.get("light"), value.get("dark")
                    if not isinstance(light, str) or not isinstance(dark, str):
                        issues.append(Issue(path, "深浅色写法必须同时给出 light 和 dark 两个十六进制颜色"))
                    else:
                        if parse_hex(light) is None:
                            issues.append(Issue(f"{path}.light", f"颜色格式错误：\"{light}\""))
                        if parse_hex(dark) is None:
                            issues.append(Issue(f"{path}.dark", f"颜色格式错误：\"{dark}\""))
                else:
                    issues.append(Issue(path, "颜色必须是 \"#RRGGBB\" 字符串或 {\"light\", \"dark\"} 对象"))

    # layout
    layout = root.get("layout", _MISSING)
    if layout is not _MISSING:  # 显式写 null 也要报错，与 App 一致
        if not isinstance(layout, dict):
            issues.append(Issue("layout", "必须是对象 {\"组件族\": \"classic\" | \"ink\"}"))
        else:
            for key in sorted(layout):
                path = f"layout.{key}"
                if key not in LAYOUT:
                    issues.append(Issue(path, "未知组件族" + suggestion(key, LAYOUT)))
                elif layout[key] not in SPEC["layoutVariants"]:
                    issues.append(Issue(path, "必须是 \"classic\"（经典香色样式）或 \"ink\"（纸墨样式）"))

    # behavior
    behavior = root.get("behavior", _MISSING)
    if behavior is not _MISSING:  # 显式写 null 也要报错，与 App 一致
        if not isinstance(behavior, dict):
            issues.append(Issue("behavior", "必须是对象 {\"开关名\": true | false}"))
        else:
            for key in sorted(behavior):
                path = f"behavior.{key}"
                if key not in BEHAVIOR:
                    issues.append(Issue(path, "未知行为开关" + suggestion(key, BEHAVIOR)))
                elif not is_bool(behavior[key]):
                    issues.append(Issue(path, "必须是 true 或 false"))

    # tokens
    tokens = root.get("tokens", _MISSING)
    if tokens is not _MISSING:  # 显式写 null 也要报错，与 App 一致
        if not isinstance(tokens, dict):
            issues.append(Issue("tokens", "必须是对象"))
        else:
            for key in sorted(tokens):
                path = f"tokens.{key}"
                spec = TOKENS.get(key)
                value = tokens[key]
                if spec is None:
                    issues.append(Issue(path, "未知 token" + suggestion(key, TOKENS)))
                elif spec["kind"] == "number":
                    if not is_number(value):
                        issues.append(Issue(path, "必须是数字"))
                    elif not spec["minimum"] <= value <= spec["maximum"]:
                        issues.append(Issue(path, f"超出范围 {fmt(spec['minimum'])}…{fmt(spec['maximum'])}"))
                elif spec["kind"] == "color":
                    if not isinstance(value, str) or parse_hex(value) is None:
                        issues.append(Issue(path, "必须是 \"#RRGGBB\" 或 \"#RRGGBBAA\"（token 颜色不分深浅色）"))
                elif spec["kind"] == "fontWeight":
                    if value not in SPEC["fontWeights"]:
                        issues.append(Issue(path, "必须是 " + " / ".join(SPEC["fontWeights"])))
                elif spec["kind"] == "fontDesign":
                    if value not in SPEC["fontDesigns"]:
                        issues.append(Issue(path, "必须是 " + " / ".join(SPEC["fontDesigns"])))
    return root, issues


def fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


# ---------------------------------------------------------------- 解析出实际颜色（用于对比度和预览）

def resolved_colors(manifest: dict) -> dict[str, dict[str, tuple]]:
    """role -> {"light": rgba, "dark": rgba}。只覆盖有默认值的角色（refined 的 ink* 与常用跨皮肤角色）。"""
    base = manifest.get("base", "refined")
    colors = manifest.get("colors") or {}
    # App 里两张基础色板的 ink* 原色相同；经典的跨皮肤角色是 iOS 系统色（这里用近似值）。
    defaults = dict(SPEC["defaultColors"]["refined"])
    if base == "classic":
        defaults.update(SPEC["defaultColors"]["classicApproximate"])
    out: dict[str, dict[str, tuple]] = {}

    def from_value(value):
        if isinstance(value, str) and parse_hex(value):
            c = parse_hex(value)
            return {"light": c, "dark": c}
        if isinstance(value, dict) and parse_hex(value.get("light", "")) and parse_hex(value.get("dark", "")):
            return {"light": parse_hex(value["light"]), "dark": parse_hex(value["dark"])}
        return None

    for role, value in defaults.items():
        out[role] = from_value(value)
    for role, value in colors.items():
        parsed = from_value(value)
        if parsed:
            out[role] = parsed
    if base == "refined":
        for role, link in SPEC["refinedLinks"].items():
            if role in colors or link["source"] not in out:
                continue
            src = out[link["source"]]
            out[role] = {m: (*src[m][:3], src[m][3] * link["opacity"]) for m in ("light", "dark")}
    return out


def over(fg, bg):
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3)) + (1.0,)


def luminance(c) -> float:
    def ch(x):
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def contrast(fg, bg) -> float:
    fg = over(fg, bg)
    l1, l2 = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


CONTRAST_PAIRS = [
    # (前景, 背景, 最低对比度, 说明)
    ("inkText", "inkCanvas", 4.5, "正文文字 / 页面底"),
    ("inkText", "inkSurface", 4.5, "正文文字 / 卡片"),
    ("inkTextSecondary", "inkCanvas", 3.0, "次要文字 / 页面底"),
    ("inkTextSecondary", "inkSurface", 3.0, "次要文字 / 卡片"),
    ("inkAccent", "inkCanvas", 3.0, "强调色 / 页面底"),
    ("inkDrawerText", "inkDrawerTop", 4.5, "抽屉文字 / 抽屉底"),
    ("inkChromeForeground", "inkChromePaperBar", 4.5, "阅读器外框图标 / 栏底"),
    ("primaryText", "pageCanvas", 4.5, "文字 / 页面底"),
]


def design_warnings(manifest: dict) -> list[str]:
    warnings: list[str] = []
    colors = manifest.get("colors") or {}
    resolved = resolved_colors(manifest)
    base = manifest.get("base")
    layout_values = dict(SPEC["builtinLayout"].get(base, {}), **(manifest.get("layout") or {})).values()
    shows_ink = any(v == "ink" for v in layout_values)
    for fg, bg, minimum, label in CONTRAST_PAIRS:
        if fg.startswith("ink") and not shows_ink:
            continue
        if fg not in resolved or bg not in resolved or not resolved[fg] or not resolved[bg]:
            continue
        if fg not in colors and bg not in colors:
            continue  # 两边都是内置值，不用提醒
        for mode in ("light", "dark"):
            ratio = contrast(resolved[fg][mode], over(resolved[bg][mode], (1, 1, 1, 1) if mode == "light" else (0, 0, 0, 1)))
            if ratio < minimum:
                warnings.append(f"对比度不足：{label}（{fg} 在 {bg} 上，{'浅色' if mode == 'light' else '深色'}）"
                                f" {ratio:.2f}:1，建议至少 {minimum}:1")
    for role in ("inkCanvas", "inkSurface", "inkFill", "inkText", "inkTextSecondary", "inkTextTertiary",
                 "pageCanvas", "groupedCanvas", "cardSurface", "primaryText"):
        if isinstance(colors.get(role), str):
            warnings.append(f"colors.{role} 只给了一个颜色，深色模式会沿用浅色值；建议写成 {{\"light\", \"dark\"}}")
    layout = dict(SPEC["builtinLayout"].get(base, {}), **(manifest.get("layout") or {}))
    uses_classic = any(v == "classic" for v in layout.values())
    tokens = manifest.get("tokens") or {}
    if uses_classic and ("inkAccent" in colors or "appTint" in colors):
        missing = [t for t in ("accent", "readerAccent", "buttonOrange") if t not in tokens]
        if missing:
            warnings.append("有组件族用 classic 样式，它们的强调色来自 tokens；没设置 "
                            + "、".join(missing) + "，书架更新圆点、按钮等会保持原来的红橙色")
    if base == "classic" and any(r.startswith("ink") for r in colors):
        if not any(v == "ink" for v in (manifest.get("layout") or {}).values()):
            warnings.append("base 是 classic 且没有组件族用 ink 样式，ink* 颜色不会显示出来")
    return warnings


# ---------------------------------------------------------------- 读入

def safe_archive_path(path: str) -> bool:
    return (bool(path) and not path.startswith("/") and "\\" not in path
            and not any(ord(c) < 0x20 for c in path) and ".." not in path.split("/"))


def read_manifest_file(path: Path) -> bytes:
    with path.open("rb") as source:
        return source.read(TOP["maxManifestBytes"] + 1)


def load_target(target: Path) -> tuple[bytes, list[str]]:
    """返回 (theme.json 字节, 包内其余文件)。"""
    if target.is_dir():
        manifest = target / "theme.json"
        if not manifest.is_file():
            raise ValueError(f"{target} 里没有 theme.json")
        others = sorted(str(p.relative_to(target)) for p in target.rglob("*")
                        if p.is_file() and p.name not in ("theme.json", ".DS_Store"))
        return read_manifest_file(manifest), others
    if target.stat().st_size > SPEC["package"]["maxBytes"]:
        raise ValueError("主题包超过 20 MB")
    if target.suffix.lower() == ".json":
        return read_manifest_file(target), []
    if zipfile.is_zipfile(target):
        with zipfile.ZipFile(target) as z:
            entries = z.infolist()
            if len(entries) > SPEC["package"]["maxEntries"]:
                raise ValueError("主题包里的文件超过 200 个")
            for entry in entries:
                # orig_filename 保留 NUL；ZipInfo.filename 会在 NUL 处截断。
                if not safe_archive_path(entry.orig_filename):
                    raise ValueError(f"主题包里有不安全的路径：{entry.orig_filename!r}")
            files = [e for e in entries if not e.filename.endswith("/")
                     and not e.filename.startswith("__MACOSX/") and e.filename.split("/")[-1] != ".DS_Store"]
            manifests = [e for e in files if e.filename.split("/")[-1] == "theme.json"
                         and len([p for p in e.filename.split("/") if p]) <= 2]
            if len(manifests) != 1:
                raise ValueError("包里应当正好有一个 theme.json（根目录或唯一顶层文件夹）")
            manifest = manifests[0]
            if manifest.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise ValueError("theme.json 必须使用 ZIP 的 Store 或 Deflate 压缩方式")
            prefix = manifest.filename.rpartition("/")[0]
            if prefix and any(not e.filename.startswith(prefix + "/") for e in files):
                raise ValueError("theme.json 必须放在包的根目录，或唯一的顶层文件夹里")
            # 有界解压，不因一个很小的 zip 而把巨大 JSON 读入内存。
            with z.open(manifest) as source:
                data = source.read(TOP["maxManifestBytes"] + 1)
            others = sorted(e.filename[len(prefix) + 1:] if prefix else e.filename
                            for e in files if e is not manifest)
            return data, others
    if target.suffix.lower() in (".mtsktheme", ".zip"):
        raise ValueError("不是可读取的 ZIP 主题包；不能只把 JSON 文件改扩展名")
    return read_manifest_file(target), []


def zip_entry(path: str) -> zipfile.ZipInfo:
    """固定时间与权限，使同一输入的分发包可以重复生成。"""
    entry = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    entry.create_system = 3
    entry.external_attr = 0o100644 << 16
    entry.compress_type = zipfile.ZIP_DEFLATED
    return entry


# ---------------------------------------------------------------- 命令

def cmd_validate(args) -> int:
    data, others = load_target(Path(args.target))
    manifest, issues = validate_manifest(data)
    if issues:
        print(f"✗ 有 {len(issues)} 处错误，App 会拒绝导入：")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print(f"✓ 校验通过：{manifest['name']}（{manifest['id']}，基于 {manifest['base']}）")
    for name in others:
        print(f"  · 会被忽略的文件：{name}")
    warnings = design_warnings(manifest)
    for w in warnings:
        print(f"  ! {w}")
    if not warnings:
        print("  没有设计警告。")
    return 0


def cmd_pack(args) -> int:
    folder = Path(args.folder)
    data, _ = load_target(folder)
    manifest, issues = validate_manifest(data)
    if issues:
        for issue in issues:
            print(f"  - {issue}")
        print("✗ 校验未通过，未打包。")
        return 1
    if folder.name != manifest["id"]:
        print(f"! 目录名 {folder.name} 与 id {manifest['id']} 不同；包里会使用 id 作为目录名。")
    out = Path(args.output or f"{manifest['id']}.mtsktheme")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zip_entry(f"{manifest['id']}/theme.json"), data)
    out.write_bytes(buffer.getvalue())
    print(f"✓ 已打包：{out}（{out.stat().st_size} 字节）")
    return 0


def cmd_new(args) -> int:
    if not valid_id(args.id):
        print("✗ id 只能用小写字母、数字和 . _ -，3–64 个字符，以字母或数字开头")
        return 1
    folder = Path(args.output or args.id)
    if (folder / "theme.json").exists() and not args.force:
        print(f"✗ {folder / 'theme.json'} 已存在，没有覆盖。要重新开始请加 --force，或换一个目录。")
        return 1
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {"schemaVersion": SPEC["schemaVersion"], "id": args.id, "name": args.name, "author": "",
                "version": "1.0", "description": "", "base": args.base, "colors": {}, "layout": {},
                "behavior": {}, "tokens": {}}
    (folder / "theme.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ 已创建 {folder / 'theme.json'}")
    return 0


def css(c) -> str:
    return f"rgba({round(c[0]*255)},{round(c[1]*255)},{round(c[2]*255)},{c[3]:.3f})"


def cmd_preview(args) -> int:
    data, _ = load_target(Path(args.target))
    manifest, issues = validate_manifest(data)
    if issues:
        for issue in issues:
            print(f"  - {issue}")
        print("✗ 校验未通过，先修正再预览。")
        return 1
    colors = resolved_colors(manifest)
    tokens = manifest.get("tokens") or {}
    base = manifest["base"]
    radius = tokens.get("largeRadius", 20 if base == "refined" else 16)
    layout = dict(SPEC["builtinLayout"][base], **(manifest.get("layout") or {}))
    # 经典样式组件的强调色来自 token；默认值与 App 的经典 token 表相同。
    classic_accent = tokens.get("readerAccent", "#C82515")
    classic_drawer = tokens.get("drawerBackground", "#1A1C1F")

    def pane(mode: str) -> str:
        c = {k: css(v[mode]) for k, v in colors.items() if v}
        get = lambda k, fallback: c.get(k, fallback)  # noqa: E731
        ink = lambda family: layout.get(family) == "ink"  # noqa: E731
        dark = mode == "dark"
        shelf_card = ink("shelfList")
        rows = "".join(
            f"<div class='row{' card' if shelf_card else ''}'><div class='cover' style='background:linear-gradient(#7a5c6a,#4b3440)'>{t[0]}</div>"
            f"<div><div class='t'>{t}</div><div class='s'>阅读到 第一章 · 2 章未读</div></div></div>"
            for t in ("红笺阅读示例", "山海札记", "夜航船"))
        # 页面级颜色用跨皮肤角色：纸墨时它们跟随 ink*，经典时是系统色（近似）。
        accent = get("inkAccent", "#DB593C") if ink("button") else classic_accent
        accent_soft = get("inkAccentSoft", "#DB593C1C") if ink("button") else get("fieldFill", "#F2F2F7")
        drawer_top = get("inkDrawerTop", "#262320") if ink("drawerSidebar") else classic_drawer
        drawer_bottom = get("inkDrawerBottom", "#14120F") if ink("drawerSidebar") else classic_drawer
        drawer_text = get("inkDrawerText", "#F2EDE6") if ink("drawerSidebar") else "#FFFFFF"
        bar = get("inkChromePaperBar", "#F6F3ED") if ink("readerBars") else "#292929"
        chrome = get("inkChromeForeground", "#1D1B18") if ink("readerBars") else "#FFFFFF"
        return f"""
<section class='phone' style='--canvas:{get("pageCanvas", "#000" if dark else "#fff")};--surface:{get("cardSurface", "#fff")};
  --fill:{get("fieldFill", "#eee")};--text:{get("primaryText", "#fff" if dark else "#000")};--text2:{get("secondaryText", "#666")};
  --text3:{get("tertiaryText", "#999")};--accent:{accent};
  --accentSoft:{accent_soft};--hair:{get("separator", "rgba(128,128,128,.3)")};
  --drawerTop:{drawer_top};--drawerBottom:{drawer_bottom};
  --drawerText:{drawer_text};--bar:{bar};
  --chrome:{chrome};--r:{radius}px'>
  <div class='mode'>{'浅色' if mode == 'light' else '深色'}</div>
  <div class='top'><span>☰</span><div class='seg'><b>书架</b><i>发现</i></div><span>⌕ ＋</span></div>
  <div class='search'>⌕ 搜索书名或作者</div>
  {rows}
  <div class='btns'><span class='primary'>开始阅读</span><span class='secondary'>加入书架</span></div>
  <div class='drawer'><div>我的书源</div><div>阅读记录</div><div>设置</div></div>
  <div class='reader'><span>‹</span><span>第一章 清晨的书桌</span><span>⋯</span></div>
  <div class='progress'><i></i></div>
</section>"""

    page = f"""<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{html.escape(manifest['name'])} · 主题预览</title>
<style>
body{{margin:0;padding:16px;font-family:-apple-system,"PingFang SC",sans-serif;background:#888;display:flex;gap:16px;flex-wrap:wrap}}
h1{{width:100%;margin:0;color:#fff;font-size:18px}}
.phone{{width:360px;background:var(--canvas);color:var(--text);border-radius:28px;padding:14px;box-sizing:border-box}}
.mode{{font-size:12px;color:var(--text3)}}
.top{{display:flex;justify-content:space-between;align-items:center;padding:8px 2px}}
.seg{{background:var(--fill);border-radius:999px;padding:3px;display:flex;gap:4px}}
.seg b{{background:var(--surface);border-radius:999px;padding:4px 14px}} .seg i{{font-style:normal;color:var(--text2);padding:4px 14px}}
.search{{background:var(--fill);color:var(--text2);border-radius:999px;padding:9px 14px;margin:6px 0 10px}}
.row{{display:flex;gap:12px;padding:10px 4px;border-bottom:0.5px solid var(--hair)}}
.row.card{{background:var(--surface);border-radius:var(--r);border:none;margin-bottom:8px;padding:10px}}
.cover{{width:44px;height:62px;border-radius:5px;color:#fff;display:flex;align-items:center;justify-content:center;font-size:20px}}
.t{{font-weight:600}} .s{{color:var(--text2);font-size:13px;margin-top:6px}}
.btns{{display:flex;gap:10px;margin:14px 0}}
.primary{{background:var(--accent);color:#fff;border-radius:999px;padding:9px 18px}}
.secondary{{background:var(--accentSoft);color:var(--accent);border-radius:999px;padding:9px 18px}}
.drawer{{background:linear-gradient(var(--drawerTop),var(--drawerBottom));color:var(--drawerText);border-radius:var(--r);padding:12px}}
.drawer div{{padding:6px 0}}
.reader{{margin-top:12px;background:var(--bar);color:var(--chrome);border-radius:14px;padding:12px;display:flex;justify-content:space-between}}
.progress{{height:4px;background:var(--fill);border-radius:2px;margin-top:8px}} .progress i{{display:block;width:40%;height:100%;background:var(--accent);border-radius:2px}}
</style>
<h1>{html.escape(manifest['name'])}（{html.escape(manifest['id'])}）· 近似预览，以 App 实际效果为准</h1>
{pane('light')}{pane('dark')}"""
    out = Path(args.output or "preview.html")
    out.write_text(page, encoding="utf-8")
    print(f"✓ 已生成预览：{out}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="mtsk 界面主题工具")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("new", help="新建主题目录")
    p.add_argument("id")
    p.add_argument("--name", required=True)
    p.add_argument("--base", choices=SPEC["bases"], default="refined")
    p.add_argument("-o", "--output")
    p.add_argument("--force", action="store_true", help="覆盖已存在的 theme.json")
    p.set_defaults(func=cmd_new)
    p = sub.add_parser("validate", help="校验 theme.json / 主题目录 / .mtsktheme")
    p.add_argument("target")
    p.set_defaults(func=cmd_validate)
    p = sub.add_parser("preview", help="生成浅色 / 深色近似预览 HTML")
    p.add_argument("target")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_preview)
    p = sub.add_parser("pack", help="打包成 .mtsktheme")
    p.add_argument("folder")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_pack)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, NotImplementedError) as error:
        print(f"✗ {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
