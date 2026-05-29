# 抖音主页链接采集

从抖音个人主页链接批量提取所有公开作品的视频链接，导出为 Markdown 文件。

## 功能

- 输入抖音个人主页 URL（如 `https://www.douyin.com/user/MS4wLjABxxxx`）
- 自动解析 `sec_uid`，分页获取所有公开作品
- 去重后导出为 Markdown 文件（含编号列表和时间戳）
- 支持可选 Cookie 配置（文本粘贴或 Netscape 格式文件）

## 环境要求

- Python 3.9+
- 网络可访问 `www.douyin.com`

## 安装

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt
```

## 运行

```bash
python app.py
```

浏览器打开 `http://127.0.0.1:5999`，在页面中输入抖音主页链接后点击「开始提取」。

## Cookie 配置（可选）

抖音部分账号或大量提取可能需要登录态 Cookie。两种方式：

1. **Cookie 文本**：在页面文本框中粘贴 Netscape 格式的 Cookie 文本
2. **Cookie 文件**：填写 Netscape 格式 Cookie 文件的路径

Cookie 文件可通过浏览器扩展（如 EditThisCookie）导出为 Netscape 格式获取。

不填 Cookie 时，工具以无登录状态提取，部分受限账号可能获取不到作品。

## 输出

提取结果保存在 `output/` 目录下，文件名格式：

```
douyin_links_{sec_uid}_{时间戳}.md
```

## 限制

- 仅提取抖音公开作品，无法获取私密/删除作品
- 接口限制：单次提取页数上限 500 页，每页最多 50 条
- 频繁请求可能触发风控，建议使用 Cookie 并控制提取频率
- 本工具仅提取链接，不包含视频下载、ASR 等功能
- 抖音 API 可能变更，如遇失效请检查接口参数

## 运行测试

```bash
# 使用 pytest
python -m pytest tests/ -v

# 或无 pytest 时使用内置脚本
python tests/__init__.py
```

## 项目结构

```
抖音主页链接采集/
├── app.py                  # Flask Web 入口
├── requirements.txt        # Python 依赖
├── README.md               # 本文件
├── core/
│   ├── __init__.py          # URL 解析、API 响应解析
│   ├── profile_extractor.py # 主页链接提取核心
│   └── markdown_exporter.py # Markdown 导出
├── templates/
│   └── index.html           # 浏览器 UI
├── tests/
│   ├── __init__.py           # 内置测试脚本
│   └── test_core.py          # pytest 测试
└── output/                  # 导出文件目录
```
