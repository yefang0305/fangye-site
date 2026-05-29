---
name: publish-site
description: 把 fangye.cc 个人网站的本地改动智能发布上线。当用户说“同步”“发布”“上线”“更新文章发上去”“把改动推上去”“publish”“deploy”，或新增/修改了文章、工具、页面后要同步到线上时使用。负责：整理新文章的 frontmatter 与配图 → 本地 build 验证 → 提交并 push 到 GitHub main → Cloudflare 自动部署 → 验证线上。
---

# 发布 fangye.cc 个人网站

这是一个 Astro 静态站，托管在 Cloudflare Workers，绑定域名 https://fangye.cc 。
**推送到 GitHub `main` 分支后，Cloudflare 会自动构建并部署**——没有单独的部署按钮。

## 关键信息

- 项目根目录：`J:\MagicTool\个人网站`（所有命令都在此目录下执行）
- 远端：`origin` → `github.com/yefang0305/fangye-site`，分支 `main`
- 构建命令：`npm run build`（Node 20），产物在 `dist/`
- push 已配置走本地代理（仓库级 `http.proxy=http://127.0.0.1:7897`）。若 push 报 TLS 握手失败或 408 超时，基本是代理没开或端口变了 —— 提醒用户检查代理。
- 线上验证：`https://fangye.cc` 应返回 200。

## 内容规范（整理文章/工具时遵守）

**文章** 放在 `src/content/articles/<英文slug>.md`，会被自动收录、按 `pubDate` 倒序排列。frontmatter 必须是：

```markdown
---
title: "标题"
description: "一句话简介"
pubDate: 2026-06-10
tags: ["标签1", "标签2"]
featured: false
---
正文……
```

整理一篇新文章/草稿时：
- 生成简短英文 slug 作为文件名。
- 正文**去掉开头重复的 `# 标题`**（文章页布局会用 frontmatter.title 渲染 H1）。
- 若草稿含 `## 备选标题`/`## 推荐结构`/`## 正文` 这类元信息块，正文从 `## 正文` 之后取，去掉这些块。
- 配图拷到 `public/images/<slug>/`，正文里用根路径引用：`![说明](/images/<slug>/图.png)`。引用的图若磁盘上不存在，去掉该图片引用而不是留破链。

**工具** 列表在 `src/data/tools.ts`（`ToolItem` 数组）：
- 仅展示卡片：加一条 `status:'showcase'`、`hasPage:false`。
- 可交互工具：在 `src/pages/tools/<slug>.astro` 建页面，并在 `tools.ts` 加 `status:'usable'`、`hasPage:true`、`href:'/tools/<slug>/'`。

## 发布流程（每次执行这套）

1. **看改了什么**：`git status -s` 和 `git diff --stat`，搞清楚是新增文章、改工具、还是改代码/UI。
2. **整理（如有需要）**：如果用户丢了新文章草稿或裸 md，按上面的“内容规范”整理好 frontmatter、slug、配图路径。改 UI/代码则不需要这步。
3. **本地构建验证**：跑 `npm run build`。
   - **构建失败就停下**，把错误报给用户，**不要 push**。
   - 构建成功再继续。
4. **提交并推送**：
   ```bash
   git add -A
   git commit -m "<根据本次改动写的简洁说明，如：新增文章：xxx / 更新工具卡片 / 首页布局调整>"
   git push origin main
   ```
   push 用增大的缓冲已配置好；若失败看“关键信息”里的代理提示。
5. **告知 + 验证**：告诉用户 Cloudflare 正在自动构建（约 1-2 分钟）。可在等待后用 `https://fangye.cc` 做一次抓取验证返回 200（注意请求要走代理 `http://127.0.0.1:7897`）；刚 push 完线上可能还在构建，没通就让用户稍等再看。

## 注意

- commit message 用中文、简洁、说清楚这次同步了什么。
- 只在用户明确要“同步/发布/上线”时才 push；不要在用户只是讨论或预览时擅自推送。
- 不碰账号登录、密钥、DNS、Cloudflare 控制台设置——这些是用户自己的事。
