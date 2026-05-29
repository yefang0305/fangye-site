export type ToolStatus = 'usable' | 'showcase';

export interface ToolItem {
  name: string;
  slug: string;
  description: string;
  category: string;
  status: ToolStatus;
  href: string;
  featured: boolean;
  hasPage: boolean;
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
    hasPage: true,
  },
  {
    name: '公众号排版助手',
    slug: 'wechat-formatter',
    description: '将文章内容通过 AI 自动分析结构并套用专业排版风格，生成可直接粘贴进微信公众号编辑器的富文本内容。',
    category: '文本处理',
    status: 'usable',
    href: '/tools/wechat-formatter/',
    featured: true,
    hasPage: true,
  },
  {
    name: 'MiniMax TTS 字幕',
    slug: 'minimax-tts',
    description: '使用 MiniMax TTS API 将文本转为语音并生成带时间戳的字幕，支持语速和音调调节。',
    category: '语音工具',
    status: 'usable',
    href: '/tools/minimax-tts/',
    featured: false,
    hasPage: true,
  },
  {
    name: '口播文案后处理',
    slug: 'text-polish',
    description: '清理 ASR 转录文本中的语气词、纠正常见误识、自动添加标点和分段，适合处理视频口播文案。',
    category: '文本处理',
    status: 'usable',
    href: '/tools/text-polish/',
    featured: false,
    hasPage: true,
  },
  {
    name: '提示词卡片库',
    slug: 'prompt-cards',
    description: '把常用提示词整理成可复用的任务卡片。',
    category: '提示词助手',
    status: 'showcase',
    href: '/projects/prompt-cards/',
    featured: true,
    hasPage: true,
  },
  {
    name: '工作流检查表',
    slug: 'workflow-checklist',
    description: '把 AI 工作流拆成输入、步骤、验收和复盘。',
    category: '效率工具',
    status: 'showcase',
    href: '/projects/workflow-checklist/',
    featured: false,
    hasPage: true,
  },
  {
    name: '抖音视频下载工具',
    slug: 'douyin-downloader',
    description: '基于 yt-dlp 和 CR TubeGet 的抖音视频批量下载工具，支持多路线下载和 Cookie 管理。本地 Python Web 工具。',
    category: '视频工具',
    status: 'showcase',
    href: '/projects/douyin-downloader/',
    featured: false,
    hasPage: true,
  },
  {
    name: '抖音主页链接采集',
    slug: 'douyin-profile-linker',
    description: '从抖音个人主页批量提取公开作品链接，导出为 Markdown 文件。本地 Python Web 工具。',
    category: '数据采集',
    status: 'showcase',
    href: '/projects/douyin-profile-linker/',
    featured: false,
    hasPage: true,
  },
  {
    name: '抖音批量视频生成',
    slug: 'douyin-batch-video',
    description: '文案到成片全自动流水线：TTS 合成、智能分段、素材混剪、字幕生成、封面渲染。Python 桌面工作台加 CLI。',
    category: '视频工具',
    status: 'showcase',
    href: '/projects/douyin-batch-video/',
    featured: true,
    hasPage: true,
  },
  {
    name: 'MediaPush 发布工作台',
    slug: 'mediapush',
    description: '多账号视频批量发布桌面工具，支持账号管理、定时发布、作品清理和私信管理。PyQt5 加 Playwright。',
    category: '发布工具',
    status: 'showcase',
    href: '/projects/mediapush/',
    featured: false,
    hasPage: true,
  },
  {
    name: '桌面悬浮笔记',
    slug: 'floating-snippets',
    description: 'Windows 桌面悬浮快捷文本管理工具，像素风图标和毛玻璃面板，支持分组管理和一键复制。',
    category: '效率工具',
    status: 'showcase',
    href: '/projects/floating-snippets/',
    featured: false,
    hasPage: true,
  },
];
