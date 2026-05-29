# fangye.cc Personal Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first Astro version of `fangye.cc`, a dark-lab personal site for AI tool articles and small utilities.

**Architecture:** Use Astro content collections for articles, static data for tools, reusable layouts/components for the dark visual system, and a client-side text utility for the first on-site tool. The site builds to static output suitable for Cloudflare Pages, Vercel, Netlify, or similar hosting.

**Tech Stack:** Astro, TypeScript, Markdown content collections, plain CSS, vanilla browser JavaScript for the text tool.

---

## File Structure

- Create `package.json`: project scripts and dependencies.
- Create `astro.config.mjs`: Astro site configuration, sitemap integration, RSS-ready site URL.
- Create `tsconfig.json`: strict Astro TypeScript defaults.
- Create `src/content/config.ts`: article collection schema.
- Create `src/content/articles/*.md`: sample article content.
- Create `src/data/tools.ts`: typed tool metadata.
- Create `src/layouts/BaseLayout.astro`: HTML shell, metadata, nav, footer.
- Create `src/layouts/ArticleLayout.astro`: article detail page layout.
- Create `src/components/*.astro`: focused UI blocks for articles, tools, tags, and sections.
- Create `src/pages/index.astro`: content-first home page.
- Create `src/pages/articles/index.astro`: articles index.
- Create `src/pages/articles/[slug].astro`: article detail route.
- Create `src/pages/tools/index.astro`: tools index.
- Create `src/pages/tools/text-cleaner.astro`: usable on-site text cleaner.
- Create `src/pages/about.astro`: about page.
- Create `src/pages/rss.xml.js`: RSS feed endpoint.
- Create `src/styles/global.css`: dark-lab visual system and responsive layout.
- Create `public/favicon.svg`: simple site favicon.
- Create `DEPLOYMENT.md`: deployment and `fangye.cc` DNS notes.
- Create `.gitignore`: ignore dependencies, builds, local temp, and brainstorm files.

## Task 1: Project Scaffold

**Files:**
- Create: `package.json`
- Create: `astro.config.mjs`
- Create: `tsconfig.json`
- Create: `.gitignore`
- Create: `public/favicon.svg`

- [ ] **Step 1: Create package and config files**

Create `package.json`:

```json
{
  "name": "fangye-personal-site",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "astro dev",
    "build": "astro build",
    "preview": "astro preview",
    "astro": "astro"
  },
  "dependencies": {
    "@astrojs/rss": "^4.0.11",
    "@astrojs/sitemap": "^3.2.1",
    "astro": "^5.0.0"
  },
  "devDependencies": {
    "typescript": "^5.8.0"
  }
}
```

Create `astro.config.mjs`:

```js
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://fangye.cc',
  integrations: [sitemap()],
});
```

Create `tsconfig.json`:

```json
{
  "extends": "astro/tsconfigs/strict"
}
```

Create `.gitignore`:

```gitignore
node_modules/
dist/
.astro/
.vercel/
.netlify/
.superpowers/
*.log
```

Create `public/favicon.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#0b1116"/>
  <path d="M17 17h30v8H27v9h17v8H27v15H17V17z" fill="#9ff5d7"/>
</svg>
```

- [ ] **Step 2: Install dependencies**

Run:

```powershell
npm install
```

Expected: `node_modules` and `package-lock.json` are created, and npm exits successfully.

- [ ] **Step 3: Verify Astro command**

Run:

```powershell
npm run astro -- --version
```

Expected: Astro prints a version number and exits successfully.

## Task 2: Content Model And Sample Content

**Files:**
- Create: `src/content/config.ts`
- Create: `src/content/articles/ai-tool-workflow.md`
- Create: `src/content/articles/prompt-library.md`
- Create: `src/content/articles/automation-notes.md`
- Create: `src/data/tools.ts`

- [ ] **Step 1: Create article schema**

Create `src/content/config.ts`:

```ts
import { defineCollection, z } from 'astro:content';

const articles = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    tags: z.array(z.string()),
    featured: z.boolean().default(false),
  }),
});

export const collections = { articles };
```

- [ ] **Step 2: Create sample articles**

Create `src/content/articles/ai-tool-workflow.md`:

```markdown
---
title: "把 AI 工具变成日常工作流"
description: "记录一个从临时提问到稳定流程的 AI 工具使用方法。"
pubDate: 2026-05-28
tags: ["AI 工具", "工作流", "效率"]
featured: true
---

AI 工具最有价值的地方，不是偶尔回答一个问题，而是进入每天都会重复发生的工作环节。

## 从问题开始

先找一个重复出现、边界清晰、结果容易检查的任务，例如整理资料、改写文案、生成提纲或检查清单。

## 固定输入和输出

把输入格式、输出格式和验收标准写下来。这样 AI 不只是聊天对象，而是一个可复用的步骤。

## 保留人工判断

工作流不应该让人失去判断力。好的 AI 流程会把注意力留给更重要的选择。
```

Create `src/content/articles/prompt-library.md`:

```markdown
---
title: "提示词库应该解决什么问题"
description: "提示词不是咒语，而是可以复用的任务说明。"
pubDate: 2026-05-27
tags: ["提示词", "AI 工具"]
featured: true
---

提示词库的目标不是收集花哨句子，而是沉淀稳定的任务上下文。

## 一个好提示词的组成

它应该包含角色、目标、输入材料、输出格式和检查标准。

## 什么时候值得保存

当一个提示词被你重复使用三次以上，或者能显著减少沟通成本，就值得沉淀下来。
```

Create `src/content/articles/automation-notes.md`:

```markdown
---
title: "自动化笔记：先减少切换，再追求复杂"
description: "个人自动化实践里，最先值得处理的是高频切换。"
pubDate: 2026-05-26
tags: ["自动化", "效率"]
featured: false
---

自动化不一定从复杂系统开始。很多时候，减少复制、粘贴、切换窗口，就是第一步。

## 先找摩擦

如果一个动作每天重复很多次，而且每次都需要你重新组织上下文，它就是自动化候选。

## 小工具优先

一个十分钟能写好的小工具，可能比一个庞大的系统更快改变日常体验。
```

- [ ] **Step 3: Create tool data**

Create `src/data/tools.ts`:

```ts
export type ToolStatus = 'usable' | 'showcase';

export interface ToolItem {
  name: string;
  slug: string;
  description: string;
  category: string;
  status: ToolStatus;
  href: string;
  featured: boolean;
}

export const tools: ToolItem[] = [
  {
    name: '文本清理器',
    slug: 'text-cleaner',
    description: '清理多余空行、首尾空格和重复空白，适合处理复制来的文本。',
    category: '文本处理',
    status: 'usable',
    href: '/tools/text-cleaner/',
    featured: true,
  },
  {
    name: '提示词卡片库',
    slug: 'prompt-cards',
    description: '把常用提示词整理成可复用的任务卡片。',
    category: '提示词助手',
    status: 'showcase',
    href: '/tools/',
    featured: true,
  },
  {
    name: '工作流检查表',
    slug: 'workflow-checklist',
    description: '把 AI 工作流拆成输入、步骤、验收和复盘。',
    category: '效率工具',
    status: 'showcase',
    href: '/tools/',
    featured: false,
  },
];
```

## Task 3: Layouts, Components, And Global Style

**Files:**
- Create: `src/layouts/BaseLayout.astro`
- Create: `src/layouts/ArticleLayout.astro`
- Create: `src/components/ArticleCard.astro`
- Create: `src/components/ToolCard.astro`
- Create: `src/components/SectionHeader.astro`
- Create: `src/styles/global.css`

- [ ] **Step 1: Create base layout**

Create `src/layouts/BaseLayout.astro`:

```astro
---
import '../styles/global.css';

interface Props {
  title?: string;
  description?: string;
}

const {
  title = 'fangye.cc - AI 工具实验室',
  description = '记录 AI 工具、自动化工作流和效率实验，也发布一些自己做的小工具。',
} = Astro.props;

const pageTitle = title.includes('fangye.cc') ? title : `${title} | fangye.cc`;
---

<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content={description} />
    <meta name="theme-color" content="#0b1116" />
    <link rel="icon" href="/favicon.svg" />
    <title>{pageTitle}</title>
  </head>
  <body>
    <header class="site-header">
      <a class="brand" href="/">fangye.cc</a>
      <nav class="site-nav" aria-label="主导航">
        <a href="/articles/">文章</a>
        <a href="/tools/">工具</a>
        <a href="/about/">关于</a>
      </nav>
    </header>
    <main>
      <slot />
    </main>
    <footer class="site-footer">
      <span>fangye.cc</span>
      <span>AI tools, workflows, and small experiments.</span>
    </footer>
  </body>
</html>
```

- [ ] **Step 2: Create article layout**

Create `src/layouts/ArticleLayout.astro`:

```astro
---
import BaseLayout from './BaseLayout.astro';

const { frontmatter } = Astro.props;
const date = new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(frontmatter.pubDate);
---

<BaseLayout title={frontmatter.title} description={frontmatter.description}>
  <article class="article-shell">
    <a class="back-link" href="/articles/">返回文章</a>
    <header class="article-header">
      <p class="eyebrow">{date}</p>
      <h1>{frontmatter.title}</h1>
      <p class="lead">{frontmatter.description}</p>
      <div class="tag-row">
        {frontmatter.tags.map((tag: string) => <span class="tag">{tag}</span>)}
      </div>
    </header>
    <div class="prose">
      <slot />
    </div>
  </article>
</BaseLayout>
```

- [ ] **Step 3: Create reusable cards**

Create `src/components/ArticleCard.astro`:

```astro
---
interface Props {
  title: string;
  description: string;
  pubDate: Date;
  tags: string[];
  href: string;
}

const { title, description, pubDate, tags, href } = Astro.props;
const date = new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(pubDate);
---

<article class="article-card">
  <a href={href}>
    <p class="eyebrow">{date}</p>
    <h3>{title}</h3>
    <p>{description}</p>
    <div class="tag-row">
      {tags.map((tag) => <span class="tag">{tag}</span>)}
    </div>
  </a>
</article>
```

Create `src/components/ToolCard.astro`:

```astro
---
interface Props {
  name: string;
  description: string;
  category: string;
  status: 'usable' | 'showcase';
  href: string;
}

const { name, description, category, status, href } = Astro.props;
---

<article class="tool-card">
  <a href={href}>
    <div class="tool-meta">
      <span class="tag">{category}</span>
      <span class={`status status-${status}`}>{status === 'usable' ? '站内可用' : '项目展示'}</span>
    </div>
    <h3>{name}</h3>
    <p>{description}</p>
  </a>
</article>
```

Create `src/components/SectionHeader.astro`:

```astro
---
interface Props {
  eyebrow: string;
  title: string;
  description?: string;
}

const { eyebrow, title, description } = Astro.props;
---

<header class="section-header">
  <p class="eyebrow">{eyebrow}</p>
  <h2>{title}</h2>
  {description && <p>{description}</p>}
</header>
```

- [ ] **Step 4: Create global CSS**

Create `src/styles/global.css` with the dark lab visual system, responsive grids, article prose, cards, forms, and buttons.

## Task 4: Pages And Routing

**Files:**
- Create: `src/pages/index.astro`
- Create: `src/pages/articles/index.astro`
- Create: `src/pages/articles/[slug].astro`
- Create: `src/pages/tools/index.astro`
- Create: `src/pages/about.astro`

- [ ] **Step 1: Create home page**

Create `src/pages/index.astro` using `BaseLayout`, `ArticleCard`, `ToolCard`, `SectionHeader`, `getCollection('articles')`, and `tools`. Show the hero, featured/latest articles, featured tools, article categories, and tool categories.

- [ ] **Step 2: Create articles index**

Create `src/pages/articles/index.astro` with a sorted list of all articles.

- [ ] **Step 3: Create article detail route**

Create `src/pages/articles/[slug].astro` with `getStaticPaths()`, `entry.render()`, and `ArticleLayout`.

- [ ] **Step 4: Create tools index**

Create `src/pages/tools/index.astro` listing all tools and making status clear.

- [ ] **Step 5: Create about page**

Create `src/pages/about.astro` with a concise personal introduction placeholder, site focus, and contact placeholders that are clearly editable text.

## Task 5: On-Site Text Cleaner Tool

**Files:**
- Create: `src/pages/tools/text-cleaner.astro`

- [ ] **Step 1: Create text cleaner page**

Create `src/pages/tools/text-cleaner.astro` with:

- A textarea for input
- A readonly textarea for output
- Buttons for `清理文本`, `复制结果`, and `清空`
- Checkboxes for removing extra blank lines, trimming each line, and collapsing repeated spaces
- Client-side script that performs the transformations in the browser

- [ ] **Step 2: Manual verification**

Run the dev server, open `/tools/text-cleaner/`, paste:

```text
  第一行   


第二     行
```

Expected output with all options enabled:

```text
第一行
第二 行
```

## Task 6: RSS, SEO, And Deployment Notes

**Files:**
- Create: `src/pages/rss.xml.js`
- Create: `DEPLOYMENT.md`

- [ ] **Step 1: Create RSS endpoint**

Create `src/pages/rss.xml.js` with `@astrojs/rss` and all articles sorted by publish date.

- [ ] **Step 2: Create deployment notes**

Create `DEPLOYMENT.md` explaining:

- `npm install`
- `npm run dev`
- `npm run build`
- Cloudflare Pages build command: `npm run build`
- Cloudflare Pages output directory: `dist`
- DNS binding idea for `fangye.cc`: point the domain to the selected hosting provider using that provider's instructions, then enable HTTPS.

## Task 7: Verification

**Files:**
- Verify all created files.

- [ ] **Step 1: Build**

Run:

```powershell
npm run build
```

Expected: Astro builds successfully and generates `dist`.

- [ ] **Step 2: Preview**

Run:

```powershell
npm run dev
```

Expected: Local site starts and prints a localhost URL.

- [ ] **Step 3: Browser check**

Open the local URL and verify:

- `/`
- `/articles/`
- At least one article detail page
- `/tools/`
- `/tools/text-cleaner/`
- `/about/`

Expected: All pages render, mobile width is usable, and the text cleaner works.

## Self-Review

- Spec coverage: The plan covers the Astro setup, dark lab visual system, home page, article index/detail pages, tools index, one usable text utility, about page, SEO sitemap/RSS, deployment notes, and build/browser verification.
- Placeholder scan: The only editable content placeholders are intentional user-facing bio/contact text on the about page. No implementation task is blocked by an unspecified decision.
- Type consistency: Article frontmatter fields match `src/content/config.ts`; tool statuses match `ToolStatus`; component props match the planned page usage.
