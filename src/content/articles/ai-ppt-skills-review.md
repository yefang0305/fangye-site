---
title: "7 个 AI 做 PPT 的开源 Skill 实测，到底该选哪个？"
description: "完整实测 guizang-ppt-skill、frontend-slides，并梳理 huashu-design 等共 7 个开源 PPT / Design Skill，帮你按真实场景选型。"
pubDate: 2026-05-18
tags: ["AI 工具", "PPT", "Skill", "选型"]
featured: true
---

> 你有一份方案，想让 AI 帮你做成演示文稿。这篇文章帮你搞清楚三件事：选哪个、怎么上手、做出来长什么样。

最近开源社区冒出来一堆 PPT / Design Skill，我挑了 7 个比较热的看了一圈。

先说清楚：不是 7 个都完整端到端跑了一遍。

没必要，也不诚实。

我完整做了两个代表性实测：guizang-ppt-skill 和 frontend-slides。huashu-design 用仓库 showcase、README、references 和导出脚本做了资料验证。剩下 4 个，主要看官方示例、仓库结构和适用场景。

这样反而更接近真实选型：你不是为了折腾每个依赖，而是要判断哪个路线适合你。

先不讲道理，直接上图。

## 01 同一个主题，不同 Skill 做出来的差距有多大

测试主题统一用的是《AI Agent 如何改变个人内容生产》，8 页，面向内容创作者和独立开发者。

这是 guizang-ppt-skill 做出来的，电子杂志 × 电子墨水风格：

![guizang-ppt-skill 电子杂志风封面](/images/ai-ppt-skills-review/guizang-slide-01-cover.png)

这是 frontend-slides 做出来的，Notebook Tabs 风格：

![frontend-slides Notebook Tabs 风格封面](/images/ai-ppt-skills-review/frontend-slide-01-cover.png)

这是 huashu-design 官方 showcase，Takram 设计风格：

![huashu-design Takram 风格 PPT showcase](/images/ai-ppt-skills-review/huashu-showcase-ppt-takram.png)

三个完全不同的方向。你不需要懂设计，看一眼就知道自己更喜欢哪种感觉。

后面还有 4 个，继续往下看。

## 02 Skill 是什么？怎么上手？

很多人可能还没搞清楚：这些项目到底是什么？是软件？是插件？

不完全是。

Skill 通常是一整个文件夹，核心是 `SKILL.md`。旁边可能还有模板、脚本、图片资产、参考文档。

它告诉 AI：你帮我做 PPT 的时候，要遵守哪些规则——用什么字体、什么配色、一页放多少内容、导出什么格式。

你可以把它理解成给 AI 的「设计规范手册」。

更准确一点：

> Skill 不是普通 prompt，而是一套给 Agent 执行的工作说明书。

不同项目的上手方式不一样。

- 有的是 `npx skills add ...`
- 有的是 Claude Code plugin marketplace
- 有的是 clone 到 `~/.claude/skills/`
- 有的根本不是普通 Skill，而是要用 CLI 初始化项目

所以下面我不统一写“安装命令”，而是写每个项目最稳的上手方式。

## 03 三条代表路线

我用同一个主题、同一段 brief 完整测了前两个 Skill，又用仓库 showcase 和工具链验证了 huashu-design。下面一个一个讲，每个都附了 prompt 或可参考的 prompt，你可以直接复制。

统一的 brief 是这样的：

> 主题：《AI Agent 如何改变个人内容生产》
> 受众：内容创作者和独立开发者
> 风格要求：专业、有设计感、适合公众号作者做线下分享
> 页面结构：标题页、问题背景、传统流程、Agent 新流程、案例拆解、工具栈、风险与限制、总结页

三个 Skill 的执行方式不完全一样，下面分别说。

---

### 路线 A：guizang-ppt-skill —— 风格最强，管得最死

**GitHub**：https://github.com/op7418/guizang-ppt-skill

**一句话**：单文件 HTML，杂志风 / 瑞士风，适合线下分享和个人表达。

**上手方式**：

```
npx skills add https://github.com/op7418/guizang-ppt-skill --skill guizang-ppt-skill
```

如果不用 `skills` 命令，也可以按 README 的手动方式，把仓库 clone 到 `~/.claude/skills/guizang-ppt-skill`。

**实测 prompt**：

```
请帮我用 guizang-ppt-skill 生成一套 8 页中文演示文稿。

主题：《AI Agent 如何改变个人内容生产》
受众：内容创作者和独立开发者
风格：A · 电子杂志 × 电子墨水
主题色：靛蓝瓷
页面结构：标题页、问题背景、传统流程、Agent 新流程、案例拆解、工具栈、风险与限制、总结页
输出：单文件 HTML deck
```

这个 Skill 有自己的风格菜单和主题色预设，不是随便写个 prompt 就行的。它的 SKILL.md、template.html、layouts.md 里定好了规则，Agent 按规则执行。

**做出来长这样**：

![guizang-ppt-skill 电子杂志风封面](/images/ai-ppt-skills-review/guizang-slide-01-cover.png)

![guizang-ppt-skill Pipeline 页面](/images/ai-ppt-skills-review/guizang-slide-04-pipeline.png)

**这个 Skill 最有意思的地方：它敢限制你。**

主题色、布局、页面节奏，全都有预设。它甚至会告诉你：8 页以上的 deck，不能全是亮色页，要有暗色页、hero 页，章节页要有呼吸感，图片比例不能乱来。

这些规则看起来麻烦，但恰恰是 AI 做 PPT 不翻车的关键。AI 一旦太自由，就容易做出我们熟悉的 AI 味：紫色渐变、大圆角卡片、悬浮图标、半透明面板、信息全挤一页。

guizang 就是帮你把 AI 管住。

**适合**：线下分享、私享会、个人方法论演讲，不需要复杂图表但要画面有记忆点的内容。

**不适合**：大量数据表格、团队协作改稿、需要导出 PPTX 在 PowerPoint 里反复编辑的企业汇报。

---

### 路线 B：frontend-slides —— 先让你看三个方向，再选

**GitHub**：https://github.com/zarazhangrui/frontend-slides

**一句话**：先出 3 个视觉预览让你挑风格，再生成完整 deck。

**上手方式**：

```
/plugin marketplace add zarazhangrui/frontend-slides
/plugin install frontend-slides@frontend-slides
```

也可以手动 clone 到 `~/.claude/skills/frontend-slides`。这个项目依赖的文件不只 `SKILL.md`，还包括 `STYLE_PRESETS.md`、`viewport-base.css`、`html-template.md` 等。

**实测 prompt**：

```
请帮我用 frontend-slides 生成一套 8 页中文演示文稿。

主题：《AI Agent 如何改变个人内容生产》
受众：内容创作者和独立开发者
风格要求：专业、有设计感、适合公众号作者做线下分享
页面结构：标题页、问题背景、传统流程、Agent 新流程、案例拆解、工具栈、风险与限制、总结页

请先生成 3 个不同风格的视觉预览，我选好后再生成完整 deck。
```

**工作流和别的 Skill 不一样——它多了一步「选风格」**：

它一上来不会直接出完整 deck，先给你看 3 个方向：

- Bold Signal（硬朗，科技发布会感）
- Electric Studio（炫酷，动感）
- Notebook Tabs（柔和，像创作者笔记）

![frontend-slides 三种视觉方向预览](/images/ai-ppt-skills-review/frontend-style-previews.png)

我选了 Notebook Tabs，因为更适合公众号作者线下分享。最后做出来的感觉是「可翻阅的创作者笔记」，不是传统大屏发布会。

![frontend-slides Notebook Tabs 风格封面](/images/ai-ppt-skills-review/frontend-slide-01-cover.png)

**这个 Skill 想明白了一件事**：大多数人说不清自己想要什么风格，但一看就知道喜不喜欢。所以它把「选风格」变成了看图选，比让你在 prompt 里写一堆形容词靠谱得多。

**适合**：快速出分享稿、pitch deck 初版、线上演示，或者你压根不知道自己想要什么风格。

**局限**：如果预设风格和内容不搭，后面会别扭。比如严肃的财务汇报硬套活泼的视觉方向，会显得轻浮。

---

### 路线 C：huashu-design —— 什么格式都能出

**GitHub**：https://github.com/alchaincyf/huashu-design

**一句话**：多格式设计工具箱，HTML / PPTX / PDF / MP4 / 信息图都能出。

**上手方式**：

```
npx skills add alchaincyf/huashu-design
```

**Prompt 参考**：

```
请帮我用 huashu-design 生成一套 8 页中文演示文稿。

主题：《AI Agent 如何改变个人内容生产》
受众：内容创作者和独立开发者
风格：参考 Takram 设计方向
输出格式：HTML + 导出 PPTX
页面结构：标题页、问题背景、传统流程、Agent 新流程、案例拆解、工具栈、风险与限制、总结页
```

**说明**：这次我没有完整端到端跑一遍 huashu-design。它不是一个 one-shot 脚本，而是 agent 对话驱动的设计工作流。仓库里已经有 24 个预制 showcase，覆盖 8 个场景 × 3 种风格。下面用的是官方示例和仓库内置 showcase。

![huashu-design Takram 风格 PPT showcase](/images/ai-ppt-skills-review/huashu-showcase-ppt-takram.png)

![huashu-design Build 风格信息图 showcase](/images/ai-ppt-skills-review/huashu-showcase-infographic-build.png)

**三个值得注意的点**：

第一，它的目标不是只生成 HTML。仓库里有 `html2pptx.js`、`render-video.js`、`export_deck_pdf.mjs` 等脚本，提供 HTML 到 PPTX、PDF、视频和图片的导出链路。这很关键——很多场景下你的 PPT 最终是要在 PowerPoint 里打开的。

第二，它的风格体系比较深。参考了 Pentagram、Build、Takram 这些设计公司的方向，拆成了具体的可执行规则。

第三，它会管你的品牌素材。不只是问你品牌色，还要求你把 logo、产品图、UI 截图、字体、品牌规范都喂进去。很多 AI 做出来的东西之所以看着廉价，问题往往不在配色，而在压根没用上真实的品牌素材。

**适合**：内容团队多格式交付——今天要 PPT，明天要宣传图，后天要产品动效。

**局限**：能力范围大，规则就多，学习成本自然也高。只想快速出一套分享稿的话，它偏重了。

## 04 另外 4 个，快速过一遍

### open-slide —— 把 PPT 当代码改

**GitHub**：https://github.com/1weiho/open-slide

**上手方式**：

```
npx @open-slide/cli init my-slide
cd my-slide
pnpm dev
```

天生给 Agent 用的。每页是 React 组件，画布固定 1920 × 1080，Agent 写 React，open-slide 管画布和导航。

它最有意思的地方不在生成，在修改。你可以在浏览器里点某个元素留评论——「这个标题太大」「这块改成红色」——然后让 Agent 按评论自动改源码。

![open-slide inspector 评论迭代界面](/images/ai-ppt-skills-review/open-slide-inspector.webp)

如果你已经在用 Claude Code / Cursor / Codex，愿意把 PPT 当代码项目维护——这个就是给你做的。只想一句话出一套 PPT 的话，它偏重。

---

### html-ppt-skill —— 模板多，快

**GitHub**：https://github.com/lewislulu/html-ppt-skill

**上手方式**：

```
npx skills add https://github.com/lewislulu/html-ppt-skill
```

36 个主题、31 个布局、15 套完整 deck、47 种动画，还有演讲者模式。官方**全套提供了极大量的现成模板**。

![html-ppt-skill 模板预览](/images/ai-ppt-skills-review/html-ppt-skill-templates.png)

价值很直接：快。技术分享、内部汇报、小型路演，很多时候不需要从零设计，模板够多本身就是生产力。适合先套模板再人工改。

---

### beautiful-html-templates —— 给 Agent 用的素材库

**GitHub**：https://github.com/zarazhangrui/beautiful-html-templates

**上手方式**：

它更像模板库，不是传统“安装后直接调用”的 PPT Skill。Agent 主要读取 `AGENTS.md` 和 `index.json`，根据 brief 选择模板再改内容。

不是完整的 PPT 工作流，更像一批给 Agent 用的设计素材。**它包含了 34 套风格迥异的现成模板**，覆盖非常广：

![beautiful-html-templates 风格图库](/images/ai-ppt-skills-review/beautiful-html-gallery-grid.png)

想批量出多套风格统一的内容，或者给团队攒一套视觉规范，它很实用。

---

### open-design —— 不只是 PPT

**GitHub**：https://github.com/nexu-io/open-design

**上手方式**：

它更像应用 / 本地工作台。最快是用官方预构建桌面 app；源码方式则需要 clone 仓库并安装 Node / pnpm 环境。

已经不算 PPT Skill 了，更像一个跑在本地的开源版 Claude Design。支持多种 coding-agent CLI，内置了 design systems、skills、deck mode、prototype mode，还把 guizang-ppt-skill 也集成进去了。

![open-design 设计方向选择器](/images/ai-ppt-skills-review/open-design-direction-picker.png)

![open-design magazine deck 示例](/images/ai-ppt-skills-review/open-design-magazine-deck.png)

只做一份 PPT 的话它太重。但如果你想搭一整套本地设计工作流，值得看。

## 05 到底选哪个？

| 你的场景 | 推荐 Skill | 理由 |
|---|---|---|
| 给客户做方案汇报，要交付 PPTX / PDF | huashu-design | 仓库提供 HTML → PPTX / PDF 等导出链路，品牌素材管理完整 |
| 线下分享、私享会、个人演讲 | guizang-ppt-skill | 风格强烈，审美约束严格，不容易翻车 |
| 不知道要什么风格，先看看再说 | frontend-slides | 先给你 3 个视觉预览让你挑 |
| 公司内部周报、技术分享 | html-ppt-skill | 模板多，快，够用就行 |
| 团队要统一视觉风格 | beautiful-html-templates | 风格库丰富，适合沉淀规范 |
| 想跟 AI 反复改到满意 | open-slide | 支持逐元素评论修改 |
| 想搭一整套设计工作流 | open-design | 生态最全，不只是 PPT |

再具体一点：

**你是创业者，要做 pitch deck？**
先用 frontend-slides 探索风格，确定方向后再看 huashu-design 这类多格式链路，方便后续交付 PPTX / PDF。

**你是自媒体，要做线下分享稿？**
直接用 guizang-ppt-skill。杂志风很适合个人表达，做出来有记忆点，适合拍照发朋友圈。

**你是自媒体，要做小红书图文？**
看 beautiful-html-templates 或者 huashu-design 的信息图模式。

**你只是想快速出一版内部用的？**
html-ppt-skill，套模板，改文字，五分钟搞定。

## 最后

以前做 PPT 你得自己拖版式、调颜色、对齐元素。现在你只需要选对 Skill，把方案丢给 Agent 就行了。

7 个 Skill 都是开源的，链接都在上面。挑一个，试试。

---

**Sources**

- https://github.com/op7418/guizang-ppt-skill
- https://github.com/zarazhangrui/frontend-slides
- https://github.com/alchaincyf/huashu-design
- https://github.com/1weiho/open-slide
- https://github.com/lewislulu/html-ppt-skill
- https://github.com/zarazhangrui/beautiful-html-templates
- https://github.com/nexu-io/open-design
