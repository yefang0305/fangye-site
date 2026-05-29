# 抖音视频批量下载工具

从抖音作品链接批量下载视频的本地 Web 工具。默认支持 yt-dlp，也补回了原工作台里的 CR TubeGet 路线：填写 CR TubeGet 目录后，可优先用 `qjs.exe` 生成 `a_bogus` 并通过抖音详情接口拿视频直链；目录里有 `crck.exe` 时会自动导出登录 Cookie。

## 环境准备

```bash
pip install -r requirements.txt
```

## 启动

```bash
python app.py
```

浏览器打开 `http://127.0.0.1:5080`。

## URL 输入格式

支持以下抖音链接类型（每行一个）：

- 作品链接: `https://www.douyin.com/video/1234567890123456789`
- 图文链接: `https://www.douyin.com/note/9876543210987654321`
- 短链接: `https://v.douyin.com/AbCdEfG/`

以 `#` 开头的行为注释，会被忽略。重复链接自动去重。

## Cookie 选项

抖音部分视频需要登录才能下载。提供两种方式传入 Cookie：

1. **Cookie 文件**: 用浏览器扩展（如 Get cookies.txt LOCALLY）导出 `douyin.com` 的 Netscape 格式 cookies.txt，然后在页面中填写文件路径。
2. **从浏览器读取**: 选择 Chrome / Edge / Firefox 直接从浏览器 Cookie 数据库读取（使用前需关闭对应浏览器）。

> Windows 下从浏览器读取 Cookie 可能遇到 DPAPI 解密失败，此时建议改用 cookies.txt 文件。

## CR TubeGet 选项

本工具已从原工作台默认目录复制了一份最小 CR TubeGet 运行时到 `crtubeget_runtime/`，页面会默认使用这个目录。你也可以改填自己本机其他 CR TubeGet 目录路径。

运行时目录要求：

- 必须包含 `qjs.exe`，用于执行 `ab.js` 并生成抖音接口需要的 `a_bogus` 参数。
- 可选包含 `crck.exe`，工具会调用它导出 Netscape 格式 Cookie。
- 可选包含 `ab.js` 缓存；远程 `http://www.cr-soft.top/js/ab.js` 不可用时会回退到本地缓存。

当前内置目录包含：

- `qjs.exe`
- `crck.exe`
- `crck.exe.config`
- `ab.js`
- `BouncyCastle.Crypto.dll`
- `Newtonsoft.Json.dll`
- `System.Data.SQLite.dll`
- `vcruntime140.dll`
- `libwinpthread-1.dll`
- `Interop.IWshRuntimeLibrary.dll`
- `Interop.SHDocVw.dll`

下载策略：

- **优先使用 CR TubeGet**：填写目录后直接走 CR TubeGet 路线。
- **优先使用 yt-dlp，失败再尝试 CR TubeGet**：适合你想保留 yt-dlp 通用能力，同时把 CR TubeGet 当兜底。

不填写 CR TubeGet 目录时，工具只使用 yt-dlp。

## 输出

- **视频**: 默认保存在 `downloads/` 目录，文件名格式为 `{标题}-{视频ID}.mp4`。
- **报告**: 每次下载运行后在 `reports/` 目录生成 `download_report_YYYYMMDD_HHMMSS.md` 和 `.json` 两份报告，记录每个链接的下载状态。

## 常见失败原因

| 错误信息 | 原因 | 解决方法 |
|---------|------|---------|
| 未找到 CR TubeGet qjs.exe | CR TubeGet 目录填错或文件缺失 | 选择包含 qjs.exe 的目录 |
| 获取抖音 a_bogus 脚本失败 | 远程 ab.js 不可用且本地无缓存 | 确认网络可访问或放入可用 ab.js |
| 抖音要求新鲜 Cookie | Cookie 过期或无效 | 重新导出 cookies.txt，或使用 crck.exe |
| 无法解密浏览器 Cookie | Windows DPAPI 权限限制 | 改用 cookies.txt 文件 |
| 无法复制浏览器 Cookie 数据库 | 浏览器进程未关闭 | 完全关闭浏览器后重试 |
| HTTP 403 / 404 | 视频已删除或私密 | 检查链接是否仍然有效 |
| 下载完成后未找到输出文件 | yt-dlp 输出文件名匹配失败 | 检查 downloads 目录 |

## 运行测试

```bash
python test_douyin.py
```

测试仅验证 URL 解析、去重、报告生成和下载器选项构造，不进行实际网络下载。
