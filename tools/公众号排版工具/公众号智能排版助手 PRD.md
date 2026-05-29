公众号智能排版助手 PRD
项目概述
产品名称：公众号智能排版助手
一句话描述：一个纯静态 Web 工具，帮助公众号作者将写好的文章内容，通过 AI 自动分析结构并套用专业排版风格，生成可直接粘贴进微信公众号编辑器的富文本内容。
目标用户：个人公众号作者（单用户自用工具）
核心价值：省去手动排版时间，写完内容 → 一键排版 → 复制粘贴发布

用户使用流程
1. 打开网页工具
2. 在左侧输入框粘贴文章内容（支持纯文本 / Markdown）
3. 填写豆包 API Key（首次填写后自动保存）
4. 选择排版风格（4套主题）
5. 点击「智能排版」按钮
6. 右侧实时显示排版预览
7. 点击「复制富文本」
8. 打开微信公众号编辑器，直接粘贴 ✅

功能需求
F1 - 内容输入

左侧大文本框，支持粘贴纯文本和 Markdown
自动识别输入格式（有 # ** 等符号判断为 Markdown，否则为纯文本）
字数统计显示

F2 - API 配置

豆包 API Key 输入框，首次填写后存入 localStorage，下次自动填充
API Key 默认隐藏显示（password 类型），可点击切换明文
API Base URL 可配置（豆包兼容 OpenAI 格式，Base URL 为 https://ark.cn-beijing.volces.com/api/v3）
模型名称可配置（默认填入占位符提示用户填写自己的模型 ID）

F3 - 风格选择
4套固定排版主题，UI 上用卡片形式展示，点击选中：
主题风格描述适合内容📰 商务简约深色标题、细线分割、留白充足行业资讯、职场干货🌿 温暖生活圆润卡片、暖色调、亲切感生活方式、情感类💡 知识干货高亮重点句、编号结构清晰教程、知识科普🖤 高级杂志大字排版、强对比、设计感强品牌调性、深度内容
F4 - AI 排版处理
调用豆包 API，System Prompt 要求模型返回结构化 JSON：
json{
  "title": "文章主标题",
  "sections": [
    {
      "type": "heading1 | heading2 | paragraph | highlight | quote | summary | tip",
      "content": "段落内容"
    }
  ]
}
各 type 含义：

heading1：一级标题
heading2：二级小标题
paragraph：普通正文段落
highlight：重点金句（需视觉突出）
quote：引用内容
summary：总结段
tip：小贴士/注意事项

前端拿到 JSON 后，按选中主题套用对应内联样式渲染成 HTML
F5 - 排版预览

右侧实时渲染预览区，模拟公众号阅读宽度（最大 677px）
预览区样式与最终复制的 HTML 完全一致
加载中显示 loading 状态

F6 - 复制富文本

「复制富文本」按钮，使用 ClipboardItem API 将 HTML 写入剪贴板
复制的是带完整内联样式的 HTML（所有样式必须内联，不能依赖 class）
复制成功后按钮显示「✅ 已复制」，2秒后恢复
同时提供「复制 HTML 源码」按钮（供调试用）


技术要求
技术栈

纯 HTML + CSS + JavaScript（无需框架，保持简单）
不需要任何构建工具，单 HTML 文件即可运行
部署到 Vercel（静态托管）

API 调用
javascript// 豆包 API 兼容 OpenAI 格式
const response = await fetch(`${baseURL}/chat/completions`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${apiKey}`
  },
  body: JSON.stringify({
    model: modelId,
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: articleContent }
    ],
    response_format: { type: 'json_object' } // 强制 JSON 输出
  })
})
内联样式要求
所有排版样式必须是内联 style，示例：
html<!-- 不可以 -->
<h2 class="heading">标题</h2>

<!-- 必须这样 -->
<h2 style="font-size:20px;color:#1a1a1a;font-weight:bold;...">标题</h2>
布局结构
┌─────────────────────────────────────────┐
│  顶部：Logo + 产品名                      │
├──────────────┬──────────────────────────┤
│  左侧         │  右侧                    │
│  - API 配置   │  - 排版预览区             │
│  - 风格选择   │  （模拟公众号宽度）        │
│  - 文章输入   │                          │
│  - 操作按钮   │  - 复制按钮区             │
└──────────────┴──────────────────────────┘

非功能要求

UI 设计：精致、现代感，不要模板感，体现工具的专业性
错误处理：API 报错需有友好提示（Key 错误、网络错误、解析失败等）
响应速度：API 调用期间有明确的 loading 动画，防止用户误以为卡死
单文件：整个工具就是一个 index.html，方便部署和分享


不在范围内（明确排除）

不需要用户登录/注册
不需要历史记录
不需要后端服务
不需要图片上传/处理
不需要多语言