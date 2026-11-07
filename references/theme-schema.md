# 主题清单 theme.json · schemaVersion 1

本文是 App 主题的**唯一规则来源**：App 的校验器（`ThemeManifest.swift`）按这里实现，给 AI 用的主题设计 skill（T5）也按这里写。
`ThemeManifestTests.testSchemaDocumentMentionsEveryKey` 会检查代码里的每个颜色角色、布局族、行为开关和 token 都在本文出现；新增键时必须同步更新本文。

## 1. 文件与导入

一个主题是一个目录，目录名就是主题 `id`：

```
<id>/
└─ theme.json
```

导入方式（设置 → 外观 → 管理与导入主题 → 右上角 ＋，或在文件 App / 隔空投送 / 微信里「用其他应用打开」）：

- **`.mtsktheme` 主题包**：把上面的目录压缩成 zip 后改扩展名为 `.mtsktheme`。`theme.json` 可以放在包的根目录，也可以放在包里唯一的顶层文件夹中（直接压缩整个文件夹就是这种情况）。普通 `.zip` 也能导入。
- **单独的 `theme.json`**：AI 生成的 JSON 存成文件后可以直接导入，不用打包。

限制：包不超过 20 MB、不超过 200 个文件；不能含绝对路径、`..` 或反斜杠；只能有一个 `theme.json`。macOS 压缩时附带的 `__MACOSX/`、`.DS_Store` 会被跳过；schemaVersion 1 只使用 `theme.json`，其余文件会在确认页列为「会忽略的文件」（以后的版本会在目录里加 `images/`、`fonts/`）。

导入前会显示确认页。校验不通过时不会安装，确认页列出全部问题，可以一键复制，发回给 AI 修改。同 `id` 的主题再次导入会替换旧的；替换正在使用的主题会立即生效。

## 2. 顶层结构

```json
{
  "schemaVersion": 1,
  "id": "sakura.pink",
  "name": "樱花",
  "author": "某某",
  "version": "1.0",
  "description": "粉白配色，书架用纸墨卡片",
  "base": "refined",
  "colors":   { "inkCanvas": "#FFF6F8", "inkAccent": "#E0607E" },
  "layout":   { "shelfList": "ink" },
  "behavior": { "staggeredShelfAppear": false },
  "tokens":   { "largeRadius": 24 }
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `schemaVersion` | 是 | 固定写 `1`。比 App 支持的版本大时会提示「需要更新 App」。 |
| `id` | 是 | 3–64 个字符，只能用小写字母、数字和 `. _ -`，以字母或数字开头，不能以 `builtin.` 开头。必须与所在目录名一致。 |
| `name` | 是 | 设置里显示的名字，最多 40 个字符。 |
| `author` / `version` / `description` | 否 | 字符串，分别最多 60 / 20 / 200 个字符。 |
| `base` | 是 | `"classic"`（经典香色）或 `"refined"`（新版纸墨）。没写的项一律取 base 的值。 |
| `colors` | 否 | 颜色角色 → 颜色，见第 3 节。 |
| `layout` | 否 | 组件族 → `"classic"` / `"ink"`，见第 4 节。 |
| `behavior` | 否 | 开关 → `true` / `false`，见第 5 节。 |
| `tokens` | 否 | 圆角、阴影、按压反馈、顶栏字体与几种品牌色，见第 6 节。 |

**校验是严格的**：未知字段、拼错的键、类型不对、超出范围都会报错，不会被静默忽略。报错一次列出全部问题，每条带路径，例如：

```
colors.pageCanvsa：未知颜色角色（是不是 pageCanvas？）
tokens.largeRadius：超出范围 0…40
```

## 3. 颜色 `colors`

### 3.1 写法

- `"#RRGGBB"`、`"#RRGGBBAA"` 或 `"#RGB"`。**透明度在最后**（CSS 顺序）；注意 Legado 主题的 `#AARRGGBB` 是透明度在前，不能直接照抄。
- `{"light": "#RRGGBB", "dark": "#RRGGBB"}`：分别给浅色 / 深色模式。只写一个字符串时，深浅色共用同一个颜色。
- `appTint` 还可以写 `"none"`，表示不覆盖系统强调色。

### 3.2 选哪种 base（重要）

经典样式（`classic` 变体）的大部分界面直接用系统颜色，**能改的只有下面「跨皮肤」和「页面专用」两组角色出现的地方**。想大面积换色、做出完全不同的风格，请用 `"base": "refined"`，并改 `ink*` 开头的纸墨原色：纸墨样式的界面全部从这些角色取色。

`base` 为 `refined` 时，跨皮肤、页面专用和阅读器外框角色**默认跟随对应的 `ink*` 角色**（例如改了 `inkCanvas`，`pageCanvas`、`groupedCanvas` 也会变；`filterText` 是 `inkText` 的 78% 透明度）。只有想让某处和纸墨原色不同时，才需要单独写这些角色；单独写的值优先。`base` 为 `classic` 时没有这种联动。

### 3.3 纸墨原色（只在 `ink` 变体里生效）

| 角色 | 用途 |
|---|---|
| `inkCanvas` | 页面画布（纸色），也是系统导航栏 / tab bar 底色 |
| `inkSurface` | 浮起表面：卡片、分段控件滑块 |
| `inkFill` | 填充：搜索框、筛选标签、分段控件轨道 |
| `inkText` / `inkTextSecondary` / `inkTextTertiary` | 主 / 次 / 三级文字 |
| `inkHairline` | 极淡的分隔线 |
| `inkOutline` | 标签外框等看得见的细线 |
| `inkAccent` | 唯一强调色（按钮、选中、进度） |
| `inkAccentSoft` | 强调色浅底（强调标签、次按钮底） |
| `inkDanger` | 删除等破坏性操作 |
| `inkDrawerTop` / `inkDrawerBottom` | 抽屉背景渐变（上 / 下） |
| `inkDrawerCard` / `inkDrawerHairline` / `inkDrawerText` | 抽屉里的分组卡片、分隔线、文字 |
| `inkChromeForeground` | 阅读器外框前景基色（按透明度派生图标、文字） |
| `inkChromePaperBar` | 阅读器实色栏底（漫画、本地书） |
| `inkChromeGlassTint` | 阅读器毛玻璃上叠的底色 |
| `inkChromeWell` | 阅读器凹槽（滑块轨道） |
| `inkChromeRim` | 阅读器玻璃描边高光 |

### 3.4 跨皮肤角色（经典和纸墨都会读）

| 角色 | 用途 |
|---|---|
| `groupedCanvas` | 分组列表页底色 |
| `pageCanvas` | 普通页面底色（书架、发现、搜索、详情、目录） |
| `cardSurface` | 卡片 / 行底色 |
| `fieldFill` | 输入框、简介卡等填充 |
| `primaryText` / `secondaryText` / `tertiaryText` | 文字颜色 |
| `primaryStyle` / `secondaryStyle` / `tertiaryStyle` | 同上，用在前景样式处（经典是系统层级样式） |
| `labelText` / `secondaryLabelText` | 目录页文字 |
| `separator` | 卡片描边 / 分隔线 |
| `tertiaryFill` | 加载占位块、禁用按钮底 |
| `placeholderShimmer` | 加载占位的扫光高光 |
| `appTint` | 系统控件强调色（弹窗按钮、开关、选择器），可写 `"none"` |

### 3.5 页面专用角色

| 角色 | 用途 |
|---|---|
| `filterText` / `filterDot` | 发现页分类文字 / 分隔点 |
| `sourcePickerCurrentFill` | 发现页书源选择器「当前书源」卡片底 |
| `siteChipOutline` | 站点管理标签描边 |
| `siteBatchNeutral` / `siteBatchDestructive` | 站点管理批量条：中性按钮底 / 删除按钮底 |
| `siteCheckActive` | 站点检测通过色 |
| `siteFloatingOutline` | 站点管理浮动条描边 |

### 3.6 阅读器外框（文字 / 漫画 / 本地书共用）

| 角色 | 用途 |
|---|---|
| `chromeBackground` | 顶栏 / 底栏 / 深色浮层底 |
| `chromeControl` | 栏内控件底（胶囊、按钮） |
| `chromeInactive` | 非选中文字 / 图标 |
| `chromeIcon` | 栏上图标与文字 |
| `chromeSecondaryText` | 面板分组标题等次级文字 |
| `chromeAccent` | 进度条、选中项 |
| `chromeHairline` | 外框分隔线 |
| `chromeSubtleFill` | 按下、圆钮底 |
| `chromeWell` | 凹槽底 |
| `chromeFloatingButton` | 正文右侧悬浮圆钮底 |
| `chromeForeground` | 「前景色 × 透明度」的基色 |
| `readerPanelBackground` / `readerPanelControl` | 阅读设置面板底 / 面板内控件底 |

**阅读正文的背景与文字颜色不属于 App 主题**，由阅读器自己的阅读主题决定。

## 4. 布局 `layout`

每个组件族二选一：`"classic"`（经典香色样式）或 `"ink"`（纸墨样式）。可以混搭，例如经典的书架配纸墨的阅读器。

| 组件族 | 范围 |
|---|---|
| `button` | 主 / 次按钮 |
| `rowHighlight` | 整行按下高亮 |
| `topBarDivider` | 顶栏底部分隔线 |
| `searchBar` | 搜索框 |
| `pageState` | 空态 / 错误态 |
| `bookCover` | 书封（占位封面、真封面的书脊） |
| `bookFeedRow` | 搜索 / 发现结果行 |
| `listSurface` | 设置等列表页的底色与行底 |
| `hairlineSeparator` | 分隔视图画成淡发丝线 |
| `drawerPush` | 抽屉拉出时书架页后退缩小 |
| `rootDrawer` | 首页抽屉容器 |
| `homeHeader` | 首页顶部「书架 / 发现」切换 |
| `drawerSidebar` | 左侧抽屉 |
| `shelfList` | 书架列表模式 |
| `shelfCover` | 书架封面模式 |
| `shelfPlaceholder` | 书架加载占位 |
| `localShelf` | 本地书籍分区 |
| `discoverTabs` | 发现页顶部分类标签 |
| `discoverCategory` | 发现页分类流 |
| `searchScope` | 搜索范围 / 结果筛选芯片 |
| `searchFooter` | 搜索分页页脚 |
| `bookDetail` | 书籍详情页 |
| `catalog` | 目录页 |
| `sourceSwitchPage` | 换源页 |
| `siteManager` | 站点管理 |
| `readerBars` | 阅读器顶栏 / 底栏 |
| `readerTutorial` | 阅读器操作教程 |
| `readerFontDrawer` | 阅读器字体抽屉 |
| `readerSettings` | 阅读设置面板 |
| `readerChrome` | 阅读器外框小部件（面板标题、进度条、圆钮） |

## 5. 行为 `behavior`

| 开关 | 说明 |
|---|---|
| `pageStateRiseIn` | 空态 / 错误态出现时轻微上浮淡入 |
| `coverFadeIn` | 网络取回的封面从占位淡入 |
| `staggeredShelfAppear` | 书架首次出现时逐行浮入 |
| `readerStabilizesSafeArea` | 阅读器对安全区变化做防抖（纸墨浮动外框需要） |
| `readerCatalogSlidesUp` | 阅读器目录从底部升起（否则从左侧滑入） |
| `readerStatusBarFollowsBars` | 状态栏只在外框收起时隐藏 |
| `readerFollowsThemeColorScheme` | 本地书阅读器跟随阅读主题的日夜 |
| `comicForcesDarkScheme` | 漫画阅读器强制深色 |
| `overridesSystemBars` | 用 `inkCanvas` / `inkText` 覆盖系统导航栏和 tab bar |

## 6. Token `tokens`

| 键 | 类型 / 范围 | 说明 |
|---|---|---|
| `accent` | 颜色 | 品牌强调色（经典样式的次按钮文字、选中态） |
| `readerAccent` | 颜色 | 经典阅读器强调色，也是经典书架「有更新」小圆点的颜色 |
| `buttonOrange` | 颜色 | 经典橙色操作按钮 |
| `drawerBackground` / `drawerRow` | 颜色 | 经典抽屉底 / 行底 |
| `hudBackground` | 颜色 | 提示浮层底 |
| `scrim` | 颜色 | 弹层遮罩 |
| `buttonRadius` / `hudRadius` | 0…40 | 按钮 / 提示浮层圆角 |
| `smallRadius` / `mediumRadius` / `largeRadius` | 0…40 | 通用小 / 中 / 大圆角 |
| `floatingShadowOpacity` | 0…1 | 浮起元素阴影不透明度 |
| `floatingShadowRadius` | 0…40 | 阴影模糊半径 |
| `floatingShadowX` / `floatingShadowY` | -40…40 | 阴影偏移 |
| `pressedOpacity` | 0.2…1 | 按下时的不透明度 |
| `pressedScale` | 0.85…1 | 按下时的缩放 |
| `topBarTitleSize` | 14…26 | 顶栏标题字号 |
| `topBarTitleWeight` | `regular` / `medium` / `semibold` / `bold` / `heavy` | 顶栏标题字重 |
| `topBarTitleDesign` | `default` / `rounded` / `serif` / `monospaced` | 顶栏标题字体风格 |

token 颜色只接受单个十六进制，不分深浅色。动画曲线不开放。

## 7. 设计建议（给 AI 和作者）

- 深浅色都要给：所有 `ink*` 文字与底色角色建议写 `{"light", "dark"}`，深色模式下不要直接沿用浅色值。
- 正文文字与底色的对比度至少 4.5:1，次级文字至少 3:1。
- 强调色只用一个（`inkAccent`），`inkAccentSoft` 用它的 10%–20% 透明度。
- 抽屉（`inkDrawer*`）在两种模式下都是深色。
