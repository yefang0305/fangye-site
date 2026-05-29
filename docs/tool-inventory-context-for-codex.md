# fangye.cc 工具整理上下文

这份文档给后续新开的 Codex 对话使用。目标是让它在整理本地小工具时，理解当前个人网站的技术架构、内容模型和接入方式，避免把本地工具源码和网站代码混在一起。

## 项目定位

`fangye.cc` 是一个 Astro 静态个人网站，定位是：

- AI 工具实验室
- 个人文章库
- 小工具展示和站内可用工具入口

网站第一版已经搭好，核心页面包括：

- 首页：`src/pages/index.astro`
- 文章列表：`src/pages/articles/index.astro`
- 文章详情：`src/pages/articles/[slug].astro`
- 工具列表：`src/pages/tools/index.astro`
- 站内文本清理器：`src/pages/tools/text-cleaner.astro`
- 关于页：`src/pages/about.astro`
- RSS：`src/pages/rss.xml.js`

## 技术栈

- Astro 5
- TypeScript
- Markdown 内容集合
- 纯 CSS
- 少量原生浏览器 JavaScript，用于站内小工具

关键配置：

- `package.json`
- `astro.config.mjs`
- `tsconfig.json`
- `src/content/config.ts`
- `src/styles/global.css`

常用命令：

```powershell
npm install
$env:ASTRO_TELEMETRY_DISABLED='1'; npm run dev
$env:ASTRO_TELEMETRY_DISABLED='1'; npm run build
```

构建产物在 `dist/`，不要手动编辑 `dist/`。

## 目录边界

### 网站源码

这些目录属于网站本身：

- `src/`
- `public/`
- `docs/`
- `package.json`
- `astro.config.mjs`
- `tsconfig.json`
- `DEPLOYMENT.md`

### 待整理的小工具

本地工具主要放在：

- `tools/`

这里可能包含：

- 纯前端 HTML 工具
- Python Flask/FastAPI/脚本工具
- 依赖本地运行时、DLL、FFmpeg、浏览器、Cookie、API Key 的工具
- README、测试、打包运行时、旧项目文件

整理工具时，优先只读分析 `tools/`，不要删除、移动、重命名原始工具目录，除非用户明确要求。

### 临时或生成目录

这些通常不应纳入整理结论或提交：

- `node_modules/`
- `dist/`
- `.astro/`
- `.superpowers/`
- `*.log`

## 当前工具数据模型

工具列表由 `src/data/tools.ts` 驱动。

当前类型：

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
```

含义：

- `usable`：可以直接在网站里使用的工具。
- `showcase`：只能展示说明、截图、链接或使用方法，不能直接在静态网页里完整运行。

如果后续整理发现需要更细的分类，可以建议扩展为：

```ts
export type ToolStatus = 'usable' | 'showcase' | 'local-only' | 'external';
```

但不要直接改模型，除非用户同意。

## 工具接入策略

整理每个工具时，先判断它属于哪一类。

### A. 可站内运行

适合直接做成 Astro 页面，例如：

- 纯文本处理
- JSON/Markdown/CSV 格式化
- 简单图片参数计算
- 提示词模板生成
- 不需要后端、不需要密钥、不访问本地文件系统的纯浏览器工具

接入方式：

- 新建页面：`src/pages/tools/<slug>.astro`
- 在 `src/data/tools.ts` 新增一条记录
- `status` 设为 `usable`
- `href` 指向 `/tools/<slug>/`

实现原则：

- 优先使用原生 HTML、CSS、JavaScript。
- 小工具脚本可以直接写在对应 `.astro` 页面内。
- 不要引入 React/Vue/Svelte，除非工具复杂到纯 JS 明显难维护。
- 所有处理尽量在浏览器本地完成。

### B. 可展示但不适合站内运行

适合做成项目展示卡片或详情页，例如：

- 依赖 Python
- 依赖 FFmpeg
- 依赖 PyQt/PySide 桌面 GUI
- 依赖本地 DLL/EXE
- 依赖 Cookie、登录态或浏览器自动化
- 依赖用户本地文件路径
- 依赖私密 API Key
- 涉及批量下载、采集、发布、平台风控或账号风险

接入方式：

- 在 `src/data/tools.ts` 新增一条记录
- `status` 设为 `showcase`
- `href` 可以先指向 `/tools/`
- 如果要做详情页，可新建 `src/pages/tools/<slug>.astro`

详情页建议包含：

- 工具用途
- 运行环境
- 关键依赖
- 输入输出
- 使用步骤
- 风险提示
- 本地路径或仓库路径
- 是否未来可 Web 化

### C. 不建议放到网站

以下内容通常不应直接放上公开网站：

- 含账号 Cookie、Token、API Key 的脚本或配置
- 含平台绕过、批量采集、自动发布等高风险自动化逻辑
- 大体积运行时、DLL、EXE、视频、缓存、日志
- 用户隐私数据或历史输出

这类工具可以只做内部记录，不做公开展示，或者展示为“本地工具，不开放在线使用”。

## 当前已有工具线索

`tools/` 目录中目前能看到这些候选：

- `tools/抖音主页链接采集`
- `tools/抖音视频下载`
- `tools/公众号排版工具`
- `tools/MINIMAX语音生成`
- `tools/_拆分盘点/工具拆分盘点报告.md`

其中 `tools/_拆分盘点/工具拆分盘点报告.md` 已经对一个更大的视频工具做过只读盘点，可作为整理方法参考。

注意：这些工具里有些可能涉及平台采集、下载、本地运行时或 API 依赖。整理时要先识别风险和依赖，不要默认它们适合公开站内使用。

## 推荐整理输出格式

后续 Codex 整理工具时，建议产出一份 Markdown 报告，例如：

`docs/tools-inventory-YYYY-MM-DD.md`

每个工具按这个结构记录：

```markdown
## 工具名称

- 本地路径：
- 当前入口：
- 工具类型：
- 主要功能：
- 关键依赖：
- 输入：
- 输出：
- 是否可站内运行：
- 推荐接入方式：
- 风险或注意事项：
- 需要补充的信息：
```

`是否可站内运行` 建议使用：

- `yes`：可直接做成 Astro 站内工具
- `partial`：可抽出部分纯前端能力
- `no-showcase`：只适合展示
- `no-private`：不适合公开展示

## 推荐整理流程

1. 只读扫描 `tools/` 的一级目录。
2. 对每个工具读取 README、入口文件、requirements/package 配置。
3. 判断工具依赖和运行边界。
4. 分类为站内工具、展示工具、本地私有工具。
5. 写工具盘点报告。
6. 给出 `src/data/tools.ts` 的建议新增条目。
7. 如用户确认，再修改网站代码。

不要在第一轮盘点时：

- 删除原工具文件
- 移动原工具目录
- 批量重命名
- 把本地依赖复杂的工具强行改成 Web 工具
- 把敏感配置写入网站源码

## 网站风格要求

现有网站是深色实验室风格，设计上要保持：

- 深色背景
- 青绿色强调色
- 内容优先
- 卡片边框克制
- 页面适配手机和桌面
- 不做营销式大段落
- 不使用花哨装饰

新增工具页应复用：

- `BaseLayout`
- `SectionHeader`
- `ToolCard`
- `global.css` 中已有的卡片、按钮、表单、网格样式

## 验证要求

每次修改网站代码后至少运行：

```powershell
$env:ASTRO_TELEMETRY_DISABLED='1'; npm run build
```

如果新增了站内工具，还要手动验证：

- 页面能打开
- 输入输出逻辑正确
- 移动端不横向溢出
- 不需要后端即可运行

如果只是做工具盘点报告，不需要构建。

## 给后续 Codex 的一句话任务说明

你正在整理 `J:\MagicTool\个人网站\tools` 下的本地小工具。请先只读盘点每个工具的用途、入口、依赖、风险和是否适合接入 `fangye.cc` Astro 静态网站。不要移动或删除原工具文件。整理完成后，把结论写到 `docs/tools-inventory-YYYY-MM-DD.md`，并给出可以新增到 `src/data/tools.ts` 的建议条目。
