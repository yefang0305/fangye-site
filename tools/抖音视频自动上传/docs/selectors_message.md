# 抖音创作者后台 — 陌生人私信 DOM 选择器

> 本文档记录通过 `tmp/probe_douyin_message.py` 探测得到的所有选择器。
> **抖音改版时，第一处要改的就是本文档对应的常量（在 `publisher/douyin_message.py` 顶部）。**

**侦察日期**：2026-04-28
**页面 URL**：https://creator.douyin.com/creator-micro/data/following/chat
**二次侦察日期**：2026-04-29
**侦察时浏览器版本**：Playwright bundled Chromium（未单独记录版本）
**侦察时使用的账号**：profiles/14

---

## 1. 切到消息 Tab

```
selector: .semi-tabs-tab[role="tab"]
点击方式:
  page.get_by_role("tab", name="全部").click()
  page.get_by_role("tab", name="陌生人私信").click()
切换后等待时间: 1500ms（凭 hand-feel）
```

**备注**：默认进入通常是"全部"Tab。当前实现会依次扫描"全部"和"陌生人私信"，只取带 `.semi-badge-primary` 的会话，并用 conversation_id 合并同一人的消息。激活项带 `.semi-tabs-tab-active`，`aria-selected="true"`。

---

## 2. 会话列表

```
container selector: .semi-list-items
items selector:     li.semi-list-item
```

**备注**：列表使用 ReactVirtualized 虚拟滚动；空列表或列表末尾会显示 `没有更多了~`。

---

## 3. 单个会话项内字段（相对 selector）

| 字段 | Selector | 取值方式 |
|------|---------|---------|
| 用户名 | `[class^="item-header-name-"]` | `.inner_text()` |
| 头像 URL | `img` | `.get_attribute("src")` |
| 预览文字 | `[class^="item-content-"] [class^="text-"]` | `.inner_text()` |
| 时间字符串 | `[class^="item-header-time-"]` | `.inner_text()` |
| 未读标记 | `.semi-badge-primary` | `.count() > 0` 判定是否未读 |
| "粉丝"标签 | `.semi-tag-content` | 可选，文本为 `粉丝` 时显示粉丝标签 |

---

## 4. 稳定 ID 来源

```
来源: 用户名 + 头像 URL 文件名 hash
读取方式:
  1. user_name = item.locator('[class^="item-header-name-"]').inner_text().strip()
  2. avatar = item.locator("img").get_attribute("src") or ""
  3. avatar_id = avatar.split("?")[0].rstrip("/").split("/")[-1]
  4. conversation_id = f"{user_name}_{avatar_id}"
示例值: 高栋栋จุ๊บ_thirdwx.qlogo.cn_mmopen_vi_32_Q0j4TwGTfTIUN1KEQg0ibkQH5IcJljicSVfs5GsY2LGdUhneG48qJp03uuHicHibicJx7IHwibuib5hdEP0BQCa0MvAsQ_132.jpeg
```

**关键**：`li.semi-list-item` 没有 `data-*` 属性，点击会话后 URL 也不变化。第一版用用户名 + 头像文件名作为稳定 ID；回复时重新遍历"全部"和"陌生人私信"列表，按相同规则匹配目标会话。

---

## 5. 回复流程

### 5.1 打开会话详情
```
点击会话项的什么元素（整个 item？某个内部按钮？）: 整个 li.semi-list-item
等待详情加载的标志: [class^="box-header-name-"] 或 .chat-input-nSWBco[contenteditable="true"]，超时 15000ms
```

### 5.2 输入并发送
```
输入框 selector: .chat-input-nSWBco[contenteditable="true"]
输入方式: click 后 page.keyboard.type(text)，或 locator.evaluate 设置 innerText 并触发 input 事件
发送按钮 selector: button.chat-btn:has-text("发送")
```

### 5.3 成功判定
```
首选标志: 输入文字后发送按钮从 disabled 变为可用；发送后输入框清空，且历史消息区新增一条同文本消息
selector: .chat-input-nSWBco[contenteditable="true"] / [class^="box-item-message-"] pre
等待超时: 15000ms
```

### 5.4 历史消息读取
```
消息文本 selector: [class^="box-item-message-"] pre
我方消息判定: 向上找真正的 [class^="box-item-"] 容器，class 中包含 is-me- 即我方消息
对方消息判定: 同上，不包含 is-me- 即对方消息
聊天窗口刷新: 打开回复窗口期间，每 20 秒只刷新当前会话历史
```

---

## 6. 已知问题 / 注意事项

- 抖音私信页基于 Semi Design，`.semi-*` 类相对稳定。
- `item-header-name-*`、`item-header-time-*`、`item-content-*`、`text-*`、`box-header-name-*` 是 CSS Modules 编译产物，要用 `[class^="..."]` 前缀 selector。
- 回复输入框是 `div[contenteditable="true"]`，不是 `textarea`；`.fill()` 未必可靠，优先用点击后键盘输入。
- 发送按钮初始为 `button.semi-button.semi-button-disabled.chat-btn`，输入内容后应移除 disabled 状态。
- 陌生人 Tab 可能为空；测试账号 profiles/14 在 2026-04-29 有 1 条陌生人私信（高栋栋จุ๊บ）。
- 头像 URL 的域名可能在 `p3/p11` 之间变化，conversation_id 只取 URL 路径最后的文件名，去掉 `?from=...` 查询参数。
- 2026-04-29 回复实测：发送后页面会先出现本地消息气泡，如果立刻关闭浏览器，可能尚未真正提交完成。脚本发送成功后需要额外等待数秒再关闭浏览器。
- 用户手动确认：回复真正发出后，陌生人私信里的会话会转移到全部私信列表。因此回复成功后的理想验证是重新刷新陌生人 Tab，该会话不再出现在陌生人未读列表；UI 仍应同步写入本地 `seen` 状态作为保险。
- 2026-04-29 需求调整：集成页不再是"未读后处理即移除"模型，而是消息处理台。回复/标记后消息仍保留在当前列表；后续刷新如果同一 conversation_id 有新内容，则更新同一行并顶到上方。
- 2026-04-29 需求调整：抓取范围从"仅陌生人私信"扩展为"全部 + 陌生人私信"两个 Tab 中的未读红点会话；回复流程使用无头 Chromium。
- 2026-04-29 需求调整：全局后台巡检改为每 1 小时一轮；打开单个回复/聊天窗口时，该账号标记 busy，全局巡检跳过该账号，聊天窗口自己每 20 秒刷新当前会话。
- 2026-04-29 需求调整：消息列表持久化到 `data/message_cache.json`，启动时先恢复历史列表，然后私信页打开后自动后台刷新一次。

---

## 7. 验证脚本输出

T1 Step 5 跑通后，把验证输出贴到这里：

```
默认 Tab 找到 4 个会话
[0] 用户名: 水球泡 | unread=True | 时间: 09:26 | 预览: 这么棒，太谢谢了
[1] 用户名: 天乙先生 | unread=True | 时间: 03-12 | 预览: 你收到一条新类型消息，请打开抖音app查看
[2] 用户名: 鱼鱼大王 | unread=True | 时间: 03-06 | 预览: AI啊
[3] 用户名: dyebjl1yf5fp | unread=True | 时间: 01-07 | 预览: https://ohhgurku63.feishu.cn/file/JB7Ub741GoFSN3xBb6pciSlgnyb

陌生人 Tab 找到 1 个会话
[0] 用户名: 高栋栋จุ๊บ | unread=True | 时间: 星期日 | 预览: 师傅，您在还哪的，我要有机会想来听您讲讲道

打开会话后找到 1 个输入框，1 个发送按钮
输入框: .chat-input-nSWBco[contenteditable="true"]
发送按钮: button.chat-btn:has-text("发送")

扩展抓取验证（全部 + 陌生人私信）：
profiles/14 抓到 6 个带红点会话，包含高栋栋จุ๊บ / 天乙先生 / 水球泡 / 鱼鱼大王 / dyebjl1yf5fp / 天乙师兄。
```
