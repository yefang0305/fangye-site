---
title: "AI Skill 深度测评第三期：baoyu-skills，一个人的内容工厂"
description: "Skill 深度测评系列第三期。21 个 skill 组成的内容生产线，从生成图片到信息图、漫画、幻灯片、发公众号，全链路覆盖。"
pubDate: 2026-05-27
tags: ["AI Skill", "测评", "内容创作"]
featured: false
---

![AI skill深度测评第三期：baoyu-skills，一个人的内容工厂](/images/skill-review-03-baoyu-skills/cover-baoyu-skills-morandi-journal.png)

> skill深度测评系列 · 第三期

---

上期结尾我预告了baoyu-image-gen。装上之后我才发现——它不是一个skill，它是一整条生产线。

baoyu-image-gen只是baoyu-skills这个项目里的一个零件。整个项目有21个skill，GitHub上19000多颗星，从生成图片到做信息图、画漫画、排幻灯片、发公众号，全链路都覆盖了。

今天不只是拆一个skill，是拆一座工厂。

![baoyu-skills：一个人的内容工厂](/images/skill-review-03-baoyu-skills/01-infographic-content-factory.png)

---

## 一句话讲清它干嘛

baoyu-skills就是一个人的"内容代工厂"。

打个比方。你是个自媒体博主，日常要写文章、配图、排版、做小红书卡片、发公众号。以前你得自己当设计师（Figma画图）、当编辑（排版工具调格式）、当运营（一个平台一个平台手动发）。三个岗位你一个人干。

baoyu-skills干的事是：给你配了一整支团队。画师（image-gen）、设计师（infographic、cover-image）、漫画家（comic）、排版编辑（slide-deck、xhs-images）、发行员（post-to-wechat、post-to-x）。你只需要说"帮我把这篇文章做成小红书图文"，它自己调度该调度的人。

![一人工作室 vs 一支创作团队——baoyu-skills角色分工图](/images/skill-review-03-baoyu-skills/baoyu-skills-roles.png)

**怎么装：** Claude Code里输入 `npx skills add jimliu/baoyu-skills`，一行命令。注意不用全装——21个skill按需选，全装反而拖慢AI响应。

---

## 先看全家福：21个skill都干嘛

别被数量吓到。21个skill分三类：

![baoyu-skills 21个 Skill 核心功能一览表](/images/skill-review-03-baoyu-skills/baoyu-skills-table.png)

![baoyu-skills 三大类 Skill 分区示意图](/images/skill-review-03-baoyu-skills/baoyu-skills-categories.png)

![21 个 Skill 的三层分工](/images/skill-review-03-baoyu-skills/02-framework-skill-layers.png)

---

## 风格这件事，值得单独说

baoyu-skills最让我意外的不是功能多，是**风格多到离谱**。

就拿信息图举例。17种视觉风格，每种长得完全不一样：

- **craft-handmade**：手绘纸工艺感，像手工贴纸
- **claymation**：3D黏土小人，定格动画风
- **kawaii**：日系萌系，大眼睛粉色调
- **cyberpunk-neon**：赛博朋克霓虹灯，暗底亮字
- **pixel-art**：8bit像素风，复古游戏感
- **ikea-manual**：宜家说明书风格，极简线条图
- **lego-brick**：乐高积木风
- **subway-map**：地铁线路图风格

| ![craft-handmade 手绘纸艺](/images/skill-review-03-baoyu-skills/craft-handmade.webp) | ![claymation 3D黏土](/images/skill-review-03-baoyu-skills/claymation.webp) | ![kawaii 日系可爱](/images/skill-review-03-baoyu-skills/kawaii.webp) | ![cyberpunk-neon 赛博霓虹](/images/skill-review-03-baoyu-skills/cyberpunk-neon.webp) |
|---|---|---|---|
| **craft-handmade** (手绘纸艺) | **claymation** (3D黏土) | **kawaii** (日系可爱) | **cyberpunk-neon** (赛博霓虹) |
| ![pixel-art 像素风](/images/skill-review-03-baoyu-skills/pixel-art.webp) | ![ikea-manual 宜家说明书](/images/skill-review-03-baoyu-skills/ikea-manual.webp) | ![lego-brick 乐高积木](/images/skill-review-03-baoyu-skills/lego-brick.webp) | ![subway-map 地铁线路](/images/skill-review-03-baoyu-skills/subway-map.webp) |
| **pixel-art** (8bit像素) | **ikea-manual** (宜家线条) | **lego-brick** (乐高积木) | **subway-map** (地铁线路) |

布局也有20种——金字塔、鱼骨图、漏斗图、冰山图、韦恩图……不是"给你一个模板自己改"，而是"你选一个，我直接给你生成完成品"。

小红书卡片也一样，9种风格搭6种布局，排列组合下来有54种出图方案。你想要notion风的知识卡片？一句话。想要复古风的对比图？一句话。想要黑板风的优缺点对比？也是一句话。

| ![cute 可爱萌系](/images/skill-review-03-baoyu-skills/cute.webp) | ![notion Notion风](/images/skill-review-03-baoyu-skills/notion.webp) |
|---|---|
| **cute** (可爱萌系) | **notion** (Notion风) |
| ![retro 复古风](/images/skill-review-03-baoyu-skills/retro.webp) | ![chalkboard 黑板风](/images/skill-review-03-baoyu-skills/chalkboard.webp) |
| **retro** (复古风) | **chalkboard** (黑板风) |

这才是baoyu-skills真正的壁垒：不是"能出图"，而是**出图有审美**。

---

## 我用它批量生产了一个月的小红书内容

说个真实的事。我有个小红书账号做命理知识科普，从今年三月底开始用baoyu-xhs-images做图。一个月做了9套卡片，几乎每天一套，每套8-13张图。

以前做一套卡片的流程是：写好内容→打开设计工具→手动排版→调字号配色→逐张导出→检查对齐。一套10张的卡片，排版就要一两个小时。

现在的流程是：写好内容→告诉baoyu-xhs-images用chalkboard风格→它自动拆解内容、分配到每张卡片→一次性全部出完。十来分钟搞定。

**先看效果——这些全是它生成的：**

![甲木日主性格卡片](/images/skill-review-03-baoyu-skills/jiamu-card.png)

"十天干性格"那套，每张一个天干，配了手绘插图——甲木画了一棵大树，主题是"仁慈大方、宽厚温和"。黑板风格、粉笔字、手绘图标，看起来像老师在黑板上画的板书。

![十二长生“长生”阶段卡片](/images/skill-review-03-baoyu-skills/changsheng-card.png)

"十二长生"那套更复杂，13张图讲一个事物从诞生到消亡的12个阶段。每张都有对应的手绘插图——"长生"阶段画了发芽的小苗，"帝旺"画了巨大的树冠。

![十二地支关系封面卡片](/images/skill-review-03-baoyu-skills/dizhi-relations-cover.png)

最让我意外的是"十二地支关系"那套。封面是一张完整的圆形关系图，十二地支围成一圈，中间用不同颜色标注了合、冲、刑、破、害、会六种关系。这种复杂的关系图，如果手画至少要半小时，它直接生成了。

![日支十神看内心世界封面卡片](/images/skill-review-03-baoyu-skills/rizhi-inner-world-cover.png)

"日支十神看内心世界"那套，封面画了一个人的侧脸剖面图，左脑标注"夫妻宫"，右脑标注"潜意识"和"内心世界"。后面每张卡片用"优点/缺点"的对比布局，把十个日支神煞的性格特征讲清楚。

**数据表现：**

这9套卡片发出去之后，数据超出我预期。"八字自测孩子有没有读书命"那条7万多阅读、近3000赞。"夫妻宫看配偶信息"系列单条最高1.7万阅读。对一个垂直领域的账号来说，这个数据相当不错。

![小红书后台数据表现](/images/skill-review-03-baoyu-skills/xhs-backend-stats.png)

重点不是说AI做的图就一定好——而是它解决了一个实际问题：**让我从"两小时排版一套图"变成"十分钟出一套图"，省下来的时间用来打磨内容本身。**

---

### 进阶玩法：如何用 baoyu-infographic 做一张商业/技术信息图？

如果说做小红书卡片是自媒体博主的提效神器，那么做**结构化信息图（Infographic）**就是职场人、技术博主和运营的刚需。

以前我们要做一张对比图、金字塔图或韦恩图，得先去百度搜模板，或者自己用 PPT 抠色块，调对齐。而在 `baoyu-skills` 里，生成一张专业信息图非常简单。

比如你想把一个复杂的“柜子组装流程”做成可视化说明书，你只需要给它提供一个简单的 Markdown 文本：
```markdown
# 简易木柜组装步骤
1. 整理工具与设计方案
2. 拆箱分类所有板材与配件
3. 拼装主柜体底座与侧板
4. 安装柜子背板与固定螺丝
5. 使用锤子加固背板边缘
6. 调整柜门铰链并进行挂装
7. 推进抽屉并检查滑动顺畅度
8. 将柜体固定在墙面上防倾倒
```
然后对 AI 说：
> “使用 baoyu-infographic 的 **ikea-manual（宜家说明书）** 风格，画一张 **8步流程图**。”

它出来的效果是这样的：

![宜家说明书风格对比图](/images/skill-review-03-baoyu-skills/ikea-manual.webp)

极简的黑白线条、标志性的宜家组装小人、规整的布局，看起来根本不像 AI 随手画的，反而像是一份精致的产品说明书。

除了宜家风，你还可以选择 **claymation（3D黏土）**、**cyberpunk-neon（赛博霓虹）** 或 **pixel-art（像素风）**，并配上**漏斗图（funnel）**、**韦恩图（venn）**或**鱼骨图（fishbone）**等 20 种布局。任何复杂的逻辑关系，一句话就能变成可视化的结构图。

---

### 终极奥义：多 Skill 协同的“全链路自动生产线”

看到这里，你可能会想：这不就是一堆“做图工具”吗？

还记得我们开头的分工图吗？`baoyu-skills` 真正的威力，在于它的 **Multi-Agent 协同机制**。你不需要单独去调每一个工具，当你把一整篇 Markdown 文章交出来时，AI 会在后台开启一条流水线：

1. **画师分析与插画生成**：
   调用 `baoyu-article-illustrator` 读取整篇文章，AI 会自动寻找最适合插入图片的位置，并拟定 prompt。紧接着，`baoyu-image-gen` 在后台并发启动，一口气画出 3-5 张风格完全统一的插图。
2. **封面图自动设计**：
   调用 `baoyu-cover-image` 提取文章标题，选用 **morandi-journal（莫兰迪手账风）** 风格自动排版，并压上标题字样，做出文章的头图封面。
3. **微信排版与发布**：
   调用 `baoyu-markdown-to-html` 将文章和刚才生成的所有插图自动打包，转换为完美排版的微信 HTML 格式；最后调用 `baoyu-post-to-wechat` 直接一键推送到公众号草稿箱。

在整个过程中，你的命令只有一句话：
> “帮我把这篇文章配上插图，并同步到公众号草稿箱。”

剩下的工作，全部由这支 AI 代理团队以**并发、异步**的方式在几分钟内干完。这也就是我们上面画的“三大类 Skill 分区” and “一人工作室 vs AI 内容代工厂”的真正实现。

![多 Skill 协同：从文章到公众号草稿](/images/skill-review-03-baoyu-skills/03-flowchart-multi-skill-pipeline.png)

---

## 核心引擎：baoyu-image-gen

上面这些做信息图、漫画、封面、小红书卡片的skill，底层都要调一个东西——baoyu-image-gen。它是整个工厂的"发电机"。

这个发电机有意思的地方是：它不绑定任何一家供应商。支持的AI绘图服务包括：

- OpenAI GPT Image 2
- Google Gemini
- 阿里通义万象（DashScope）
- 火山引擎即梦（Jimeng）
- 火山引擎豆包（Seedream）
- 智谱GLM-Image
- MiniMax
- OpenRouter
- Replicate
- Azure OpenAI
- Codex CLI（用Codex订阅的额度，不需要额外API Key）

你有哪家的API Key，它就用哪家。有多家的话还有自动优先级：Google→OpenAI→Azure→OpenRouter→DashScope→其他。

还支持参考图（给一张图让AI保持同一个人物/物体的身份不变）、批量生成（一次出几十张，自动并发控制）、多种尺寸比例（16:9、1:1、9:16等）、质量档位（普通预览/2K高清）。

![baoyu-image-gen：不绑定供应商的绘图引擎](/images/skill-review-03-baoyu-skills/04-infographic-image-engine.png)

一句话概括：**你不用管图是谁画的，只管说你要什么图。**

---

## 什么时候用，什么时候别碰

核心判断：**你有没有"内容→发布"的批量需求？**

**这些情况，装上它：**

- 你做自媒体，经常要把文章变成图文、卡片、封面——我亲测一个月9套图，效率提升五六倍
- 你写技术文档，需要配信息图、流程图、架构图
- 你要同时发多个平台（公众号+小红书+推特），需要统一的内容生产流程

**这些情况，别碰它：**

- 你只是偶尔需要一张图——直接用在线工具更快
- 你对设计有很高的定制要求——预设风格再多也不如自己在Figma里画
- 你不做内容，只写代码——21个skill里大多数跟你没关系

弊端也说实话——

第一，上手成本不低。21个skill各有各的参数和用法，搞清楚哪个skill该在什么场景用，需要花时间。第二，依赖API Key。image-gen要跑起来得先配好至少一个AI绘图服务的密钥，不是装完就能用。第三，风格虽多但不能自定义。17种信息图风格里没有你想要的？目前没有"自己加一种风格"的机制。第四，生成质量不稳定。同样的prompt跑两次，出来的图可能差别很大，有时候需要多试几次才能得到满意的结果。

---

## 这是第三期

Skill深度测评系列，每期拆一个，告诉你值不值得装、什么时候用、什么时候别碰。

下期预告：**Caveman**——一个让Claude像原始人一样说话的skill，号称能省65%的token。"why use many token when few token do trick"。听起来像个梗，但背后的省钱思路很认真。

你有想让我拆的skill吗？评论区告诉我。
