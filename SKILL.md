---
name: mtsk-theme-designer
description: 为 mtsk / 红笺墨语编写、校验、预览和打包可导入的界面主题（theme.json / .mtsktheme）。用于设计配色、皮肤、组件风格，或根据 App 的导入错误修复主题。正文阅读主题、背景图片和字体文件不属于此格式。
---

# mtsk 界面主题设计

为 mtsk（红笺墨语）iOS 阅读 App 设计**界面主题**：一个 `theme.json`，或打包好的 `.mtsktheme`。用户在 App「设置 → 外观 → 管理与导入主题 → 右上角 ＋」里导入，或在文件 App 里用本 App 打开。

主题**只能是数据**：颜色、圆角、阴影、按压反馈、顶栏字体，以及每个组件族选「经典」还是「纸墨」样式。不能写代码，不能自定义任意布局，不能换阅读正文的颜色，schemaVersion 1 也不能带图片和字体。用户要求做不到的事时，直接说明，并给出最接近的可行方案。

本 skill 自带字段表、示例和 Python 工具，不依赖 App 仓库或 Xcode。需要 Python 3.9+，无第三方 Python 依赖。下方 `scripts/`、`references/` 和 `examples/` 都相对于本 `SKILL.md` 所在目录；执行脚本时使用该目录下脚本的绝对路径，生成文件写入用户的输出目录。

## 先读这些

- [references/theme-schema.md](references/theme-schema.md)：完整规则，每个字段、角色、组件族、token 的含义和取值范围。**写 JSON 前必读**。
- [references/design-guide.md](references/design-guide.md)：怎样把「想要的风格」变成配色，深色模式怎么做，常见风格的配方。
- [references/theme-keys.json](references/theme-keys.json)：机器可读的键表与纸墨默认色（由 App 源码生成）。查默认值、核对拼写用。
- `examples/`：三个能直接导入的示例。樱花基于纸墨；墨夜基于纸墨，深色为主；竹青基于经典，混用了几个纸墨组件。

## 工作流程

### 1. 弄清需求

问清楚，或从用户描述里推断，下面四件事。最多问一轮，其余用合理默认值并告诉用户：

1. **风格关键词**：例如「护眼绿」「暗夜金」「少女粉」「极简黑白」「旧书纸」。
2. **基础 `base`**：想大面积换色、整体换风格，选 `refined`（纸墨，默认推荐）；只想在经典香色界面上换强调色和少数组件，选 `classic`。原因见 theme-schema.md 第 3.2 节：经典样式的大部分界面直接用系统色，改不了。
3. **布局**：哪些组件族用 `ink`（纸墨卡片风），哪些用 `classic`（香色列表风）。没提就沿用 base 的默认值。
4. **名称与 id**：`id` 只能用小写字母、数字和 `. _ -`，例如 `jade.green`。

### 2. 建目录

```bash
python3 scripts/theme_tool.py new <id> --name "<名称>" --base refined -o <id>
```

或者照着 `examples/` 里最接近的一个改。

### 3. 设计配色并写 `theme.json`

按 design-guide.md 的步骤来：

- `base: refined` 时只改 `ink*` 原色就够了；页面底色、文字、阅读器外框等 35 个角色会自动跟随（theme-schema.md 第 3.2 节）。只有想让某处与纸墨原色不同时，才单独写那个角色。
- 页面底色、卡片、填充和三档文字都写 `{"light": …, "dark": …}`，深色模式要单独设计，不要把浅色值反相。
- 颜色写 `#RRGGBB` 或 `#RRGGBBAA`，**透明度在最后**。
- 只写需要改的项，其余继承 base。

### 4. 校验，直到零错误

```bash
python3 scripts/theme_tool.py validate <id>
```

- **错误（✗）**：必须全部修掉。字段表与 App 对照测试，错误夹具由 Python 和 Swift 共同验证；压缩包另检查路径、目录结构、20 MB 包大小、200 个条目和 256 KB 清单限制。最终以 App 导入确认页为准。
- **警告（!）**：对比度不足、深色模式没单独给值等设计问题。默认要修；用户明确要求保留时，交付时说明原因。

不能运行脚本时（例如在纯聊天环境里），逐条对照 theme-schema.md 自查，并告诉用户导入时 App 会再校验一次。

### 5. 预览

```bash
python3 scripts/theme_tool.py preview <id> -o <id>-preview.html
```

生成浅色、深色两屏的近似效果，包含书架、搜索框、按钮、抽屉和阅读器外框。能打开浏览器就看一眼再交付；预览只是近似效果，以 App 实际显示为准。

### 6. 打包与交付

```bash
python3 scripts/theme_tool.py pack <id> -o <名称>.mtsktheme
python3 scripts/theme_tool.py validate <名称>.mtsktheme
```

回读最终打包文件后再交付。`.mtsktheme` 必须是真正的 ZIP，里面只有一个 `<id>/theme.json`；不能只把 JSON 文件改扩展名。每个主题单独打包，预览 HTML 放在包外。skill 自身的 ZIP 含多个示例，不能作为 App 主题导入。

交付时给用户：

1. `.mtsktheme` 文件；不能打包时直接给 `theme.json` 的完整内容，App 也能导入单独的 `theme.json`。
2. 一句话说明风格和基于哪套皮肤，以及改了哪些组件的布局。
3. 导入方法：把文件存到「文件」App，在 mtsk 里打开「设置 → 外观 → 管理与导入主题 → 右上角 ＋」选择它，或者在文件 App 里点它，用 mtsk 打开。确认页点「安装并使用」。
4. 校验结果。有警告时列出来。

同 `id` 再次导入会替换旧主题；更新原主题保留 `id` 并调整 `version`，新增独立主题则换一个 `id`。不要把工具检查、HTML 预览或模拟器验证称为真机验证。

需要把本 skill 分发给其他作者时，按 [README.md](README.md) 的「打包分发」操作；普通主题制作不需要重打 skill 包。

## 用户贴回 App 的报错时

App 导入失败时，确认页有「复制问题清单」，格式是每行 `路径：说明`，例如：

```
colors.pageCanvsa：未知颜色角色（是不是 pageCanvas？）
tokens.largeRadius：超出范围 0…40
```

逐条按路径修改：路径就是 JSON 里的键，提示的候选名就是正确拼写。改完重新跑第 4 步，再按第 6 步交付整份文件，不要只给片段。

## 不能做的事（直接告诉用户）

- 任意布局、移动或隐藏按钮、新增页面：只能在每个组件族的 `classic` 和 `ink` 两种样式之间选。
- 阅读正文的背景色和文字色：由阅读器自己的「阅读主题」决定，在阅读界面设置里改。
- 背景图片、自定义字体文件、图标替换：schemaVersion 1 不支持，包里的其他文件会被忽略。顶栏标题只能在 `default`、`rounded`、`serif`、`monospaced` 四种系统字体风格里选。
- 动画曲线和时长：不开放。只能用 `behavior` 开关关掉几种入场动画。
