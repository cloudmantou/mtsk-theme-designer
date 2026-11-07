# 主题设计指南

把「想要的风格」变成一份能导入、深浅色都好看、文字看得清的 `theme.json`。字段规则以 theme-schema.md 为准，本文只讲怎么设计。

## 1. 先定 base

| 想要 | 选 |
|---|---|
| 整体换一套配色和气质（暖、冷、暗、粉、绿……） | `refined`，改 `ink*` 原色 |
| 保留经典香色的样子，只换强调色或少数组件 | `classic`，改 `tokens.accent` / `readerAccent` / `buttonOrange`，再把想要的组件族切到 `ink` 并给出 `ink*` 颜色 |

`classic` 的大部分界面直接用 iOS 系统色，主题改不动。用户想「整个界面都变成某种颜色」时，必须选 `refined`。

## 2. 纸墨配色的 11 个核心颜色

`base: refined` 时，下面这些颜色决定了绝大部分界面，按顺序设计：

| 顺序 | 角色 | 作用 | 浅色建议 | 深色建议 |
|---|---|---|---|---|
| 1 | `inkCanvas` | 页面底、系统栏底 | 带一点风格色倾向的近白（L≈95–97%） | 带同一倾向的近黑（L≈6–10%） |
| 2 | `inkSurface` | 卡片、分段滑块 | 比 canvas 更亮或纯白 | 比 canvas 亮 6–10% |
| 3 | `inkFill` | 搜索框、标签、轨道 | 比 canvas 暗 5–8% | 介于 canvas 与 surface 之间 |
| 4 | `inkText` | 主文字 | 同倾向的深色，对 canvas ≥ 7:1 为佳 | 同倾向的浅色，≥ 7:1 为佳 |
| 5 | `inkTextSecondary` | 次文字 | 对 canvas ≥ 4.5:1 | ≥ 4.5:1 |
| 6 | `inkTextTertiary` | 弱提示 | 对 canvas ≈ 2.5–3:1 | 同左 |
| 7 | `inkHairline` | 分隔线 | inkText 加 7–9% 透明度 | inkText 加 8–10% 透明度 |
| 8 | `inkOutline` | 标签描边 | inkText 加 16–18% 透明度 | 同左 |
| 9 | `inkAccent` | 唯一强调色 | 对 canvas ≥ 3:1；按钮上的文字是白色 | 可稍亮、稍饱和 |
| 10 | `inkAccentSoft` | 强调浅底 | inkAccent 加 11–14% 透明度 | inkAccent 加 20% 透明度 |
| 11 | `inkDanger` | 删除等危险操作 | 和 accent 拉开色相，偏砖红 | 稍亮 |

还有几组可以选择性地改：

- 抽屉 `inkDrawerTop` / `inkDrawerBottom` / `inkDrawerText`：抽屉在深浅两种模式下**都是深色**，写一个值即可，上浅下深。文字对 top 至少 4.5:1。
- 阅读器外框 `inkChromePaperBar`（实色栏底）和 `inkChromeForeground`（图标基色）：通常与 canvas、text 同色系，稍做区分。
- `appTint`：系统弹窗按钮、开关的颜色，通常设成和 `inkAccent` 一样；写 `"none"` 则用系统蓝。

## 3. 深色模式

- 不要直接反相。深色的 canvas 用带风格倾向的近黑（例如藏青 `#0E1220`、暖墨 `#121110`），避免纯黑 `#000000`；OLED 风格的纯黑主题例外。
- 深色下层次靠「越上层越亮」：canvas < fill < surface。
- 强调色在深色下提亮 10–20%，饱和度略降，否则会刺眼。
- 只写一个颜色时，深浅色会共用它。页面底、文字这类颜色必须写 `{"light", "dark"}`，`theme_tool.py validate` 会提示。

## 4. 对比度

工具会检查下面的基础对比度组合；这是设计提示，不代表完整的无障碍合规验证。小字号文字应尽量达到 4.5:1，并在 App 中检查选中态、禁用态和实际字体大小：

| 前景 / 背景 | 最低 |
|---|---|
| `inkText` / `inkCanvas`、`inkSurface` | 4.5:1 |
| `inkTextSecondary` / `inkCanvas`、`inkSurface` | 3:1 |
| `inkAccent` / `inkCanvas` | 3:1 |
| `inkDrawerText` / `inkDrawerTop` | 4.5:1 |
| `inkChromeForeground` / `inkChromePaperBar` | 4.5:1 |

主按钮是白字配 `inkAccent` 底，过浅的强调色（例如浅粉 `#F7B7C8`）放在按钮上看不清，要加深。

## 5. 布局混搭

- 每个组件族独立选择。常见组合：
  - 「经典书架 + 纸墨阅读器」：`shelfList`、`shelfCover` 用 `classic`，`readerBars`、`readerSettings`、`readerChrome` 用 `ink`。
  - 「纸墨整体 + 经典列表」：base 用 `refined`，只把 `shelfList` 改成 `classic`（樱花示例）。
- 同一区域的几个组件族尽量保持一致，否则会显得拼凑：
  - 书架区：`shelfList`、`shelfCover`、`shelfPlaceholder`、`localShelf`
  - 阅读器区：`readerBars`、`readerSettings`、`readerChrome`、`readerFontDrawer`、`readerTutorial`
  - 首页区：`rootDrawer`、`homeHeader`、`drawerSidebar`、`drawerPush`
- 组件族选 `classic` 时，它的强调色来自 token，不来自 `ink*`：`accent`（次按钮文字、选中态）、`readerAccent`（经典阅读器、书架「有更新」小圆点）、`buttonOrange`（橙色操作按钮）。只要有组件族用 `classic`（包括 base 是 `classic`），就把这三个 token 也设成主题的强调色，否则会混进原来的红橙色。
- 组件族选 `ink` 时，它的颜色来自 `ink*` 角色。base 是 `classic` 时，切到 `ink` 的组件族要给出对应的 `ink*` 颜色（竹青示例），否则会显示纸墨的默认暖白配色。

## 6. Token

- 圆角保持 `smallRadius ≤ mediumRadius ≤ largeRadius`。气质偏锐利，整体收小（例如 6 / 10 / 14）；偏柔和，整体放大（例如 12 / 16 / 24）。
- `buttonRadius` 只影响经典样式的按钮；纸墨样式的按钮固定是胶囊形。
- 阴影：`floatingShadowOpacity` 0.06–0.14 之间比较自然，`floatingShadowY` 取半径的一半左右。
- 顶栏标题：`topBarTitleDesign` 用 `serif` 有书卷气，`rounded` 显得亲和，`monospaced` 适合极客风；`topBarTitleWeight` 一般选 `semibold`。

## 7. 常见风格配方（起点，按需微调）

| 风格 | canvas（浅 / 深） | text（浅 / 深） | accent | 备注 |
|---|---|---|---|---|
| 旧书纸（默认纸墨） | `#F7F5F1` / `#121110` | `#1D1B18` / `#F2EFEA` | `#DB593C` | 不写 colors 就是它 |
| 护眼绿 | `#EEF4EC` / `#0F1612` | `#1A261E` / `#E3ECE5` | `#3C8A5E` | fill 用 `#E1EBDF` / `#18221C` |
| 樱花粉 | `#FFF6F8` / `#1C1416` | `#2B1B20` / `#F6E9EC` | `#E0607E` | 见 `examples/sakura.pink` |
| 暗夜金 | `#F4F1EA` / `#0E1220` | `#1B1F2A` / `#E9E4D8` | `#9A6B12` / `#D9A441` | 见 `examples/moye.night`，标题用 serif |
| 极简黑白 | `#FFFFFF` / `#000000` | `#111111` / `#F5F5F5` | `#111111` / `#9A9A9A` | 深色下强调色不能接近白色，否则主按钮的白字看不清；`inkAccentSoft` 用 8–12% 透明度 |
| 海盐蓝 | `#F2F6F9` / `#0D141B` | `#16212B` / `#E4ECF2` | `#2F6F9F` / `#5DA0D0` | |

## 8. 交付前自查

- [ ] `validate` 零错误
- [ ] 警告都已处理，或已向用户说明保留的原因
- [ ] 页面底、卡片、填充和三档文字都有深浅两套颜色
- [ ] 抽屉文字在深色抽屉底上看得清
- [ ] `id` 唯一且有意义；同 `id` 再次导入会替换旧主题，改版时保持 `id` 不变并调整 `version`
