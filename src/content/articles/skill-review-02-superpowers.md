---
title: "AI Skill 深度测评第二期：Superpowers，给 AI 发一本工作手册"
description: "Skill 深度测评系列第二期。Superpowers 不是单个 skill，而是一整套从接需求到交付的工作流规范，相当于给 AI 发一本员工手册。"
pubDate: 2026-05-26
tags: ["AI Skill", "测评", "Claude Code", "工作流"]
featured: false
---

> skill深度测评系列 · 第二期

---

上期我拆了brainstorming，有朋友问：这个skill是哪来的？

答案是——它是superpowers的一部分。

Superpowers不是一个skill，而是一整套skill的合集。brainstorming只是其中一个。它还包括写计划、写测试、代码评审、bug排查……十几个skill打包在一起，覆盖了从"接需求"到"交付代码"的完整流程。

今天拆这个。

![Superpowers 技能包：多维协作的工作流工具箱](/images/skill-review-02-superpowers/superpowers-package.png)

---

## 一句话讲清它干嘛

Superpowers就是给AI发了一本《员工工作手册》。

新员工入职，公司会给一本手册：接到需求先做什么、开发流程是什么、代码怎么提交、出了bug怎么排查。没有手册，新人全凭感觉做事，质量靠运气。

Superpowers干的就是这件事——它不是教AI一个技能，而是给AI一整套工作规范。从接到你的需求开始，它自动按流程走：先问清楚你要什么（brainstorming），再出实现计划（writing-plans），然后一步步写代码（TDD），写完自己检查（code-review），最后交付。

![Superpowers 工作流程：基于规范的完整开发管线](/images/skill-review-02-superpowers/superpowers-pipeline.png)

**怎么装：** Claude Code里输入 `/plugin install superpowers@claude-plugins-official`，一行命令装完，所有skill自动生效。

---

## 等一下，那它和brainstorming什么区别？

上期测评的brainstorming就是superpowers里的一个skill。那问题来了——我该装哪个？

简单说：**brainstorming是设计师，superpowers是整个公司。**

装brainstorming，你只请了一个设计师帮你想清楚要做什么。想完之后，写代码、测试、评审，都得你自己搞。

装superpowers，你请了一整支团队——设计师（brainstorming）、项目经理（writing-plans）、程序员（TDD）、质检员（code-review）、bug猎人（systematic-debugging）。从需求到交付，全流程有人管。

**怎么选：**

![Brainstorming vs Superpowers 决策对照](/images/skill-review-02-superpowers/superpowers-vs-brainstorming.png)

注意：装了superpowers就自动包含brainstorming，不用重复装。

---

## 我用它做了一个网页

我用superpowers从零做了一个skill对比卡片页面，以下是过程。

**第一步：它问我要做什么**

![brainstorming逐一提问](/images/skill-review-02-superpowers/01-asking-questions.png)

我说"做一个skill对比卡片网页"，它没有直接写代码。而是一个问题一个问题问我：卡片放什么内容？布局用网格还是列表？配色要深色还是浅色？甚至在浏览器里给我看了三种布局的mockup让我选。

**第二步：它出了实现计划**

![writing-plans生成计划](/images/skill-review-02-superpowers/02-writing-plan.png)

问清楚后，它写了一份实现计划——具体到要创建什么文件、代码长什么样、怎么验证。像一份施工图纸，不是"大概做个网页"，而是精确到每一步。

**第三步：它按计划执行**

![最终卡片页面效果](/images/skill-review-02-superpowers/03-result.png)

计划确认后，它直接生成了完整的HTML文件。打开就是一个干净的卡片页面，三张skill对比卡片，响应式布局，手机上也能看。

从"我有个想法"到"打开能用"，整个过程大概十几分钟。我做的事只有回答问题和选选项。

---

## 什么时候用，什么时候别碰

核心判断：**你要不要让AI做一个完整的项目？**

**这些情况，装上它：**

- 你要从零开始做一个项目（网页、工具、功能模块）
- 你希望AI按流程干活，不要东一榔头西一棒子
- 你团队多人用Claude Code，需要统一工作规范

**这些情况，别碰它：**

- 你只是问AI一个问题、聊聊天
- 你写个临时脚本、跑个一次性任务
- 你不写代码，只用AI做内容工作

弊端也说一句——它流程很重。每次做事都要走brainstorming→计划→执行的完整流程，小活会觉得慢。像你只想炒个蛋，它非要先列菜谱、备好食材、摆好盘才开火。

![“炒个蛋” vs “满汉全席”：选择合适的流程复杂度](/images/skill-review-02-superpowers/egg-vs-gourmet.png)

---

## 这是第二期

Skill深度测评系列，每期拆一个，告诉你值不值得装、什么时候用、什么时候别碰。

下期预告：**baoyu-image-gen**——用AI生成图片的skill。

你有想让我拆的skill吗？评论区告诉我。
