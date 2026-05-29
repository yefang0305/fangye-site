# fangye.cc Personal Site Design

## Goal

Build `fangye.cc` as a personal technical creator site focused on AI tools, automation workflows, efficiency experiments, personal articles, and small tools built by the owner.

The first version should feel like a dark technical lab: content-led, useful, and experimental, without looking like a marketing landing page.

## Audience

The site is for visitors who want to read practical AI tool notes, learn reusable workflows, discover small utilities, or understand what the owner is building.

## Positioning

Primary positioning: AI tools lab and personal article library.

The site should communicate:

- The owner writes about AI tools, prompts, automation, and efficiency.
- The owner builds small tools and experiments.
- Articles are the main entry point.
- Tools are visible and easy to find.

## Information Architecture

The first version includes:

- Home page
- Articles index
- Article detail pages
- Tools index
- Tool detail pages
- About page

## Home Page

The home page uses a content-first layout.

Top navigation:

- `fangye.cc`
- Articles
- Tools
- About

Hero direction:

- Title: `AI 工具实验室`
- Supporting copy: `记录 AI 工具、自动化工作流和效率实验，也发布一些自己做的小工具。`

Main content:

- Featured or latest articles are the primary visual focus.
- Featured tools appear alongside the article area.
- Category links below the first screen help visitors browse by topic.

Article categories:

- AI tools
- Prompts
- Automation
- Efficiency

Tool categories:

- Text processing
- Image processing
- Prompt helpers
- Efficiency tools

## Visual Direction

The selected visual direction is dark lab.

The style should use:

- A dark blue-green or near-black base background
- Soft high-contrast text
- One or two restrained accent colors, such as cyan green, cool white, or a small amount of amber
- Clean spacing and readable typography
- Minimal decorative effects

The site should not feel like a generic SaaS landing page. It should feel like a personal workspace where useful notes and tools are collected.

## Content Model

Articles should be authored in Markdown or MDX.

Each article should support:

- Title
- Description
- Publish date
- Tags
- Optional featured flag
- Body content with headings, links, code blocks, quotes, and images

Tools should support:

- Name
- Description
- Category
- Status: usable on site or external/project showcase
- Optional URL
- Optional detail page
- Optional featured flag

## Tool Strategy

The tools section supports both:

- Simple tools that can run directly inside the website
- Larger projects that are shown as project cards or detail pages with links

The first version should include one real on-site tool. Recommended starter tool: a text cleaning or formatting utility.

## Technical Approach

Use Astro for the first version.

Reasons:

- Strong fit for Markdown/MDX articles
- Fast static output
- Easy deployment to Cloudflare Pages, Vercel, or Netlify
- Simple path for adding small interactive front-end tools
- Low maintenance for a personal site

## First Version Scope

Included:

- Astro project setup
- Dark lab visual system
- Home page
- Articles index
- Article detail template
- Two or three sample articles
- Tools index
- Two or three sample tool cards
- One usable on-site text utility
- About page
- Basic SEO metadata
- Sitemap and RSS if supported cleanly by the project setup
- Deployment notes for binding `fangye.cc`

Not included:

- Login
- Comments
- Database-backed CMS
- Admin dashboard
- Payments or memberships
- Server-side AI API tools

## UX Requirements

- The first screen should immediately show that the site is about AI tools, workflows, and small experiments.
- Articles must be easy to scan by title, description, date, and tags.
- Tools must clearly distinguish between usable on-site tools and external/project showcases.
- Long-form article reading should be comfortable on desktop and mobile.
- Mobile navigation and layouts must not overlap or require horizontal scrolling.

## Verification

The implementation should be considered acceptable when:

- The local dev server starts successfully.
- Home, articles, tools, about, and sample detail pages load.
- Markdown or MDX articles render correctly.
- The first on-site text tool works in the browser.
- Desktop and mobile layouts are usable.
- A production build completes successfully.
- The deployment notes explain how to connect `fangye.cc`.

## Open Decisions

No blocking decisions remain for the first implementation plan.

Future decisions can be made after the first version exists:

- Exact article categories
- Real bio and contact links
- Final tool list
- Deployment provider
- Whether to add server-side AI features
