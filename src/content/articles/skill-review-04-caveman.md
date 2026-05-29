---
title: "AI Skill 深度测评第四期：Caveman，一个让 AI 闭嘴省钱的 skill"
description: "Skill 深度测评系列第四期。一整套 token 压缩方案，核心思路朴素到不行：废话少说，直接给答案，号称省 65% token。"
pubDate: 2026-05-28
tags: ["AI Skill", "测评", "省钱"]
featured: false
---



> skill深度测评系列 · 第四期

---

上期结尾我预告了Caveman。当时写的是"一个让Claude像原始人一样说话的skill，号称能省65%的token"。

装上之后我发现——它不只是"说话像原始人"这么简单。它是一整套token压缩方案，从AI回复到commit message到CLAUDE.md记忆文件，能压的全给你压了。

但核心思路确实朴素到不行：**废话少说，直接给答案。**

---

## 一句话讲清它干嘛

Caveman就是给AI装了一个"废话过滤器"。

打个比方。你去修电脑，遇到两种师傅。A师傅说："嗯，我看了一下，您这个问题呢，可能是因为系统在启动过程中加载了过多的后台服务，导致内存占用过高，所以呢我建议您可以考虑一下关闭一些不必要的启动项，这样的话应该能有效改善开机速度。"B师傅说："启动项太多。关掉这三个。好了。"

技术水平一样，但B师傅说了不到A师傅四分之一的字。你的时间也省了。

Caveman就是把AI从A师傅变成B师傅。



**怎么装：** Claude Code里输入 `/install JuliusBrussee/caveman`，一行命令。装完之后每次新对话自动生效，不用手动开。想关掉说一句"normal mode"就行。

---

## 我现场试了一下

为了写这篇测评，我专门做了一组对比实验：同一个编程问题，先用正常模式问一遍，再开Caveman问一遍。

### 场景一：问一个React re-render的bug

**正常模式下Claude的回复：**



> 正常Claude花了69个token，先是"The reason your React component..."开场，铺垫了一整段因果关系，最后才说出"用useMemo"这个答案。

**开了Caveman之后：**



> Caveman Claude用了19个token，三句话："New object ref each render. Inline object prop = new ref = re-render. Wrap in `useMemo`."

同一个答案，同一个解决方案。token用量砍掉了72%。

### 场景二：问auth middleware的token过期bug

正常模式："Sure! I'd be happy to help you with that. The issue you're experiencing is most likely caused by your authentication middleware not properly validating the token expiry..."——还没说到重点呢，客气话先来一通。

Caveman模式："Bug in auth middleware. Token expiry check use `<` not `<=`. Fix:"——直接定位问题、给出原因、上代码。

### 场景三：六档"话少"程度可选

这是Caveman最有趣的设计。不是只有"废话"和"不废话"两档，而是六个等级：

| 等级 | 风格 | 同一个问题的回答 |
|------|------|-----------------|
| **lite** | 去掉废话，保留完整句子 | "Your component re-renders because you create a new object reference each render." |
| **full** | 经典原始人，省冠词、用短句 | "New object ref each render. Wrap in `useMemo`." |
| **ultra** | 电报体，缩写一切能缩的 | "Inline obj prop → new ref → re-render. `useMemo`." |
| **wenyan-lite** | 半文言 | "組件頻重繪，以每繪新生對象參照故。" |
| **wenyan-full** | 全文言 | "物出新參照，致重繪。useMemo之。" |
| **wenyan-ultra** | 极限文言 | "新參照→重繪。useMemo。" |

对，你没看错——它甚至有**文言文模式**。用中文写代码注释的朋友可以感受一下，"此函数乃处理用户认证之用"这种感觉。

切换方式就是 `/caveman lite`、`/caveman ultra`、`/caveman wenyan` 这样一个指令。



### 不只是回复省token——它还能压缩你的记忆文件

Caveman有个我觉得更实用的子功能：`/caveman-compress`。

你知道CLAUDE.md吗？就是那个每次对话Claude都会读取的项目指令文件。这个文件写得越长，每次对话的input token就越多。而大部分CLAUDE.md都是自然语言写的——"You should always make sure to run the test suite before pushing..."这种。

`/caveman-compress CLAUDE.md` 会把这个文件自动压缩成原始人风格。比如上面那句话变成："Run tests before push to main."——意思完全一样，token少了一半。

官方测试数据：五个真实记忆文件，平均压缩率46%。也就是说，**你每次对话的起步input token能直接砍掉近一半。**



它很贴心地会保存一份 `.original.md` 备份。压缩出问题了随时恢复。

### 还有两个小工具值得一提

**`/caveman-commit`**——生成精简的commit message。严格Conventional Commits格式，主题行50字以内，只写"为什么"不写"做了什么"（因为diff已经说了）。

**`/caveman-stats`**——看你这次对话省了多少token。直接读Claude Code的session log算出来的，不是AI估算。状态栏还会显示一个 `[CAVEMAN] ⛏ 12.4k` 的徽章，告诉你累计省了多少。



---

## 什么时候用，什么时候别碰

核心判断：**你在不在意token消耗？**

**这些情况，装上它：**

- 你用API按量付费，每个token都是真金白银——Caveman能帮你省65%的输出token
- 你的CLAUDE.md或项目记忆文件很长，每次对话起步就吃掉大量context——用compress压一遍，长期受益
- 你觉得AI回复太啰嗦，经常要跳过前面三行寒暄找答案——Caveman直接砍掉那些"Sure! I'd be happy to help"

**这些情况，别碰它：**

- 你在学习阶段，需要AI给你解释清楚来龙去脉——原始人省掉的可能恰好是你需要的解释
- 你在写文档或给非技术人员做交付，需要完整、友好的措辞——caveman的碎片化句式不适合直接交付
- 你团队协作，别人也要看AI的输出——不是每个人都能习惯"Pool reuse DB conn. Skip handshake → fast"这种电报体

弊端说实话——

第一，可读性是个取舍。省token的代价是阅读门槛上升，特别是ultra和wenyan模式，不熟悉的人看着像乱码。第二，它有"自动清晰度"机制——遇到安全警告、不可逆操作、用户困惑时会自动切回正常语言——但这个判断不是100%准确。第三，和其他skill偶尔会冲突。比如你同时装了brainstorming和caveman，brainstorming想让AI多问你几轮需求，caveman想让AI少说话，两个skill的"人格"可能打架。

---

## 这是第四期

Skill深度测评系列，每期拆一个，告诉你值不值得装、什么时候用、什么时候别碰。

前三期：[brainstorming](链接) → [superpowers](链接) → [baoyu-skills](链接)

下期继续拆。你有想让我拆的skill吗？评论区告诉我。
