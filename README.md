# mtsk-theme-designer

让 AI 帮你设计 mtsk（红笺墨语）的界面主题：说出想要的风格，AI 生成 `theme.json`，自动校验、预览，再打包成 `.mtsktheme`，在 App 里「设置 → 外观 → 管理与导入主题 → 右上角 ＋」导入即可。

## 下载

- [Skill 安装包](https://github.com/cloudmantou/mtsk-theme-designer/raw/refs/heads/main/downloads/mtsk-theme-designer.zip)：给 AI 工具安装，不是 App 主题包。
- 直接导入 App：[樱花](https://github.com/cloudmantou/mtsk-theme-designer/raw/refs/heads/main/downloads/themes/sakura.pink.mtsktheme) · [墨夜](https://github.com/cloudmantou/mtsk-theme-designer/raw/refs/heads/main/downloads/themes/moye.night.mtsktheme) · [竹青](https://github.com/cloudmantou/mtsk-theme-designer/raw/refs/heads/main/downloads/themes/zhuqing.classic.mtsktheme)。
- [中文使用说明](https://github.com/cloudmantou/mtsk-theme-designer/blob/main/downloads/使用说明.md)与 [SHA-256 清单](https://github.com/cloudmantou/mtsk-theme-designer/blob/main/downloads/SHA256SUMS.json)。

想查看深浅色近似效果，可下载 `downloads/previews/` 中的 HTML，用浏览器打开。实际显示以 App 为准。

## 安装

解压 `mtsk-theme-designer.zip`，把整个 `mtsk-theme-designer` 文件夹放到你的 AI 工具的 skills 目录（不要只复制 SKILL.md）：

- Claude Code：`~/.claude/skills/mtsk-theme-designer/`（或项目里的 `.claude/skills/`）
- Codex：`~/.codex/skills/mtsk-theme-designer/`，设置了 `CODEX_HOME` 时使用其下的 `skills/`

也可以直接克隆到 Codex 的 skills 目录（目标目录须尚不存在）：

```bash
git clone https://github.com/cloudmantou/mtsk-theme-designer.git "${CODEX_HOME:-$HOME/.codex}/skills/mtsk-theme-designer"
```

在新对话里对 AI 说：「用 $mtsk-theme-designer 帮我做一个护眼绿界面主题，书架保持经典列表，兼顾深浅色，生成预览并打包」。

只需 Python 3.9+，不用安装第三方 Python 包，不依赖 Xcode、App 仓库或网络。脚本路径相对于 skill 目录；从其他目录调用时传入脚本的绝对路径。

## 导入 App

Skill ZIP 给 AI 使用，`themes/` 下的 `.mtsktheme` 才是给 App 的主题文件。把后者保存到 iPhone「文件」，进入「设置 → 外观 → 管理与导入主题 → 右上角 ＋」，选择它并点「安装并使用」。也可从「文件」分享给红笺墨语。

同 ID 会替换旧主题。每个主题单独导入，不能把多个主题放进一个 ZIP；也不能把 JSON 直接改名为 `.mtsktheme`。主题包只改变界面和阅读器工具栏，正文配色仍由阅读设置控制。schemaVersion 1 不支持图片、字体文件、图标替换或任意布局代码。

只能聊天、不能运行脚本的 AI（网页版对话）：把 `SKILL.md`、`references/theme-schema.md`、`references/design-guide.md` 三个文件发给它，让它直接输出 `theme.json`。把输出存成 `theme.json` 文件后就能导入，App 导入时会再校验一次；有问题时确认页能「复制问题清单」发回给 AI 修改。

## 目录

| 路径 | 内容 |
|---|---|
| `SKILL.md` | 给 AI 的工作流程 |
| `references/theme-schema.md` | 完整规则（与 App 仓库 `docs/THEME_SCHEMA_V1.md` 相同） |
| `references/design-guide.md` | 配色与布局设计指南、常见风格配方 |
| `references/theme-keys.json` | 机器可读键表与默认色，由 App 源码生成 |
| `scripts/theme_tool.py` | `new` / `validate` / `preview` / `pack`，只需 Python 3.9+ |
| `scripts/package_skill.py` | 一键生成 skill ZIP、示例 `.mtsktheme`、HTML 预览、中文导入说明与 SHA-256 清单 |
| `examples/` | 樱花、墨夜、竹青三个示例主题 |
| `tests/` | 工具测试与共享夹具（App 的单元测试也用同一批夹具） |

## 打包分发

在本 skill 目录运行，输出目录必须尚不存在：

```bash
python3 -m unittest discover -s tests
python3 scripts/package_skill.py -o /path/to/mtsk-theme-release
```

交付 `mtsk-theme-designer.zip` 给主题作者，交付 `themes/*.mtsktheme` 给 App 用户。分发目录还包含 `previews/*.html`（深浅色近似预览）、`使用说明.md` 和 `SHA256SUMS.json`。打包前校验示例，打包后回读主题；同一输入可重复生成相同字节，已有输出不会覆盖。

维护 App 兼容性时，在 App 仓库运行 `ThemeSkillSpecTests`、`ThemeManifestTests`、`ThemePackageTests`。独立仓库的 Python 测试会跳过需要 App 文档路径的对照项，其余测试可独立执行。Python 通过或 HTML 好看都不等于真机已经验证，交付时注明实际检查范围。

## 维护

此独立仓库初始版本来自 [mtsk 的主题制作 skill](https://github.com/cloudmantou/mtsk/tree/1f3ad858d73a95701a00697acf8ededbfd886c98/skills/mtsk-theme-designer)，对应 `schemaVersion: 1`。运行工具不需要 App 仓库；维护兼容性时才需要对照 App 源码。

App 的主题代码（颜色角色、组件族、行为开关、token）变更后：

1. 从 App 仓库同步 `docs/THEME_SCHEMA_V1.md` 到本仓库的 `references/theme-schema.md`；
2. 同步 `references/theme-keys.json`、工具和共享测试夹具；
3. 在本仓库运行 `python3 -m unittest discover -s tests`，并在 App 仓库运行上述 Swift 测试；
4. 用新的输出目录运行 `package_skill.py`，核对生成物后更新 `downloads/`。不要只更新源文件而保留旧的安装包。
