import type { LevelItem } from './courseData';

export const LOOP_DEFECTS = [
  { id: 1, name: "自动化心跳", desc: "定时心跳启动与分类分诊", fixed: ["LE2", "LE3", "LE8"] },
  { id: 2, name: "物理隔离器", desc: "git worktree 运行环境隔离", fixed: ["LE2", "LE3", "LE8"] },
  { id: 3, name: "显式技能库", desc: "意图债固化与仓库级指引", fixed: ["LE3", "LE8"] },
  { id: 4, name: "外部连接器", desc: "MCP 协议跨端自由连通 API", fixed: ["LE3", "LE8"] },
  { id: 5, name: "子代理分工", desc: "Maker/Checker 阻断与监督", fixed: ["LE2", "LE3", "LE4", "LE8"] },
  { id: 6, name: "落盘记忆体", desc: "跨轮状态存盘与外部记忆", fixed: ["LE2", "LE3", "LE8"] },
];

export const LEVELS: LevelItem[] = [
  /* ============ LE0 ============ */
  {
    id: "LE0", icon: "⚙️", title: "导论：什么是 Loop Engineering",
    hook: "建立“把人从循环中换掉”的心智模型，理解 Harness 上一层的意义",
    fixes: [1, 2, 3, 4, 5, 6],
    defectLabel: "自跑循环六大零件总览",
    concepts: [
      { term: "自跑循环 (Loop)", def: "坐在 Harness 上一层，无需人肉干预、自动接力运转的系统", analogy: "不再按回车发令，而是自己装了个闹钟、自己分工、自己把上一步输出喂给下一步的自动车间" },
      { term: "Harness 层", def: "武装单个 Agent 的单次运行状态和工具", analogy: "给工人穿戴好安全带、防毒面罩和工具包，但他不会自己重来" },
      { term: "人肉时钟", def: "工程师被困在循环内，一句句发 prompt 并回车驱动 AI 的旧交互模式", analogy: "在磨坊里用鞭子一下下抽驴子，停下就得再抽" },
    ],
    takeaway: "循环工程（Loop Engineering）的核心目标是“替换你自己”，将你从人肉敲回车驱动 Agent 的角色中解放出来，变为设计和把关自跑系统的架构师。",
    quiz: [
      {
        type: "choice",
        q: "在循环工程（Loop Engineering）中，最根本的心智模型转变是什么？",
        options: [
          "学习如何写出字句更完美的 System Prompt",
          "把人从“人肉敲回车发指令给 Agent”的角色换成“设计自跑系统”的架构师",
          "优化大模型的物理硬件以提高处理速度"
        ],
        answer: 1,
        explain: "如 Addy Osmani 所说，循环工程是 replacing yourself as the person who prompts the agent. You design the system that does it instead。",
      },
      {
        type: "tf",
        q: "“Loop engineering sits one floor above the harness.” 这句话意味着 Loop 负责武装 Agent 的单次运行工具和权限，而 Harness 负责调度循环。",
        options: ["对", "错"],
        answer: 1,
        explain: "正好相反！Harness 负责单次运行的武装，而 Loop 坐在 Harness 上一层，负责让它自己醒来并自动接力跑下去。",
      },
    ],
  },

  /* ============ LE1 ============ */
  {
    id: "LE1", icon: "🪜", title: "三级跳与四层技术栈",
    hook: "梳理 Prompt、Context、Harness、Loop 四层关系，找准工程位置",
    fixes: [1, 6],
    defectLabel: "理解四层技术栈与调度零件",
    concepts: [
      { term: "Prompt 层", def: "写好单次请求的提示词内容", analogy: "写在一张便签纸上的单次留言" },
      { term: "Context 层", def: "这一个时刻上下文窗口内放什么", analogy: "工作桌面上此时铺开什么参考书和草稿" },
      { term: "Harness 层", def: "限制并武装单次执行的工具和缰绳", analogy: "工人出门背着的特制战术背包" },
      { term: "Loop 层", def: "在 Harness 之上进行自动调度与记忆传递", analogy: "自动生产线上的传送带和中控系统" },
    ],
    takeaway: "大模型工程的四层栈逐层嵌套。每上一层，关注的问题和风险就大一级。Loop 层解决的是怎么让它自己一圈圈跑下去，并在多轮运行中传递记忆。",
    quiz: [
      {
        type: "choice",
        q: "大模型上下文窗口的“中间遗忘”盲区，在技术栈中应该由哪一层来重点设计防御策略？",
        options: [
          "Prompt 层",
          "Context 层 (如 RAG、摘要压缩、信息清洗)",
          "Harness 层"
        ],
        answer: 1,
        explain: "上下文窗口内放什么、怎么清洗压缩、怎么避免中间遗忘，属于 Context Engineering 的管辖范围。",
      },
      {
        type: "tf",
        q: "即便我们把 Prompt 和 Context 调校得再完美，只要没有设计 Loop 层，Agent 依然无法做到无人值守自动接力运行。",
        options: ["对", "错"],
        answer: 0,
        explain: "对。前三层解决了“让它单次跑得好”的问题，只有第四层 Loop 负责自动接力与调度运行。",
      },
    ],
  },

  /* ============ LE2 ============ */
  {
    id: "LE2", icon: "🔄", title: "一个循环的五个动作",
    hook: "剖析 Discovery, Handoff, Verification, Persistence, Scheduling 五步大跨越",
    fixes: [1, 2, 5, 6],
    defectLabel: "拆解五大动作相关零件",
    concepts: [
      { term: "发现 (Discovery)", def: "定时唤醒去读取环境异动，找出要做什么", analogy: "早会前分诊员去邮箱查收构建失败报错" },
      { term: "交付 (Handoff)", def: "将任务隔离分派给具体的子 Agent 执行", analogy: "包工头给不同的瓦工安排独立的隔离工作间" },
      { term: "验证 (Verification)", def: "对产出的代码进行独立的挑刺和测试，判断能否合入", analogy: "质检员单独拿出一张卷子考核厨师，无情打分说不" },
      { term: "持久化 (Persistence)", def: "把当前的进度和结果落盘记在磁盘上，实现跨轮记忆", analogy: "工地大门口贴着的当日工程进度表" },
    ],
    takeaway: "五动作是 Discovery、Handoff、Verification、Persistence、Scheduling。其中 Verification（验证）是唯一敢放手让人走开的硬刹车。",
    quiz: [
      {
        type: "match",
        q: "将五大动作与它们在循环中对应的典型工程实现形式配对。",
        defects: [
          { label: "发现 (Discovery)", drop: "读取昨天 CI 测试失败记录或 Issue 列表" },
          { label: "交付 (Handoff)", drop: "拉取干净的 Git Worktree 并分发任务" },
          { label: "验证 (Verification)", drop: "由独立的 Checker 模型来判断 lint 与测试是否通过" },
          { label: "持久化 (Persistence)", drop: "将当前状态写入 loop_status.md 或 Linear 状态板" },
          { label: "调度 (Scheduling)", drop: "在系统级使用 cron 周期性唤醒进程" }
        ],
        chips: [
          "读取昨天 CI 测试失败记录或 Issue 列表",
          "拉取干净 of Git Worktree 并分发任务",
          "由独立的 Checker 模型来判断 lint 与测试是否通过",
          "将当前状态写入 loop_status.md 或 Linear 状态板",
          "在系统级使用 cron 周期性唤醒进程"
        ],
        mapping: { 0: 0, 1: 1, 2: 2, 3: 3, 4: 4 },
        explain: "这五大动作构成了循环每旋转一圈的完整生命周期。",
      },
      {
        type: "tf",
        q: "为了防止代码合并冲突，在‘交付（Handoff）’动作中，最合理的做法是让多个 Agent 在不同的物理 Git Worktree 下各自独立工作，而不是共用一个工作目录。",
        options: ["对", "错"],
        answer: 0,
        explain: "对。多个 Agent 共用同一个目录就像多个程序员同时在一行代码上提交合并，必然会引发混乱的物理文件冲突。",
      },
    ],
  },

  /* ============ LE3 ============ */
  {
    id: "LE3", icon: "📦", title: "自跑循环的六个零件",
    hook: "拼装 Automation, Worktrees, Skills, MCP, Sub-agents, Memory 六大硬装",
    fixes: [1, 2, 3, 4, 5, 6],
    defectLabel: "点亮六大自跑零件",
    concepts: [
      { term: "Skills 技能", def: "固化在仓库里的明确指令或执行包，无需每轮重写", analogy: "工具书和随身手册，要用时直接调取命令" },
      { term: "MCP 连接器", def: "标准化的外部协议接口，负责跟 Slack / Linear 交互", analogy: "万能插座，插上就能跟真实世界各种系统对话" },
      { term: "Memory 跨轮记忆", def: "状态必须落盘在 Git/文件上，防止会话结束丢失", analogy: "工地门口每天更新的白板字" },
    ],
    takeaway: "六大零件为自动化心跳、物理隔离、Skills 技能包、MCP 连接器、子代理分工与落盘记忆。前两者保运转，中两者连生态，后两者做阻断和状态续航。",
    quiz: [
      {
        type: "choice",
        q: "如果想让你的 Agent 在执行中自动到 Linear 看板领取缺陷，修复后给 Slack 发一条通知，我们应该优先使用什么技术来实现这些外部连接？",
        options: [
          "微调（Fine-tune）一个大模型",
          "编写极其复杂的 Prompt 告诉模型 Slack 网址",
          "引入 MCP (Model Context Protocol) 外部连接器"
        ],
        answer: 2,
        explain: "MCP 旨在连通 AI 与各种外部 API（Slack、Linear、数据库等），是循环工程里经典的外部连接器。",
      },
      {
        type: "tf",
        q: "因为大模型的 messages 上下文会随着交互越积越多，所以我们应该把跨轮的“待办清单”和“已试失败路径”直接写进 Git 仓库中的状态文件，而不是只留在对话里。",
        options: ["对", "错"],
        answer: 0,
        explain: "对。仓库是不可被擦除的磁盘记忆，利用状态文件存储跨轮数据，第二天醒来还能接力跑。",
      },
    ],
  },

  /* ============ LE4 ============ */
  {
    id: "LE4", icon: "🛡️", title: "生成器与评判器 Maker/Checker",
    hook: "探讨为什么 AI 绝对不能给自己写的代码打分",
    fixes: [5],
    defectLabel: "拧紧 ⑤ 子代理 零件",
    concepts: [
      { term: "Maker 生成器", def: "负责根据报错，疯狂尝试编写和修改代码的 Agent 角色", analogy: "满头大汗不停炒菜的厨师" },
      { term: "Checker 评判器", def: "带着独立指令、负责测试和无情挑刺的独立模型实例", analogy: "专门品尝打分、绝对不包庇厨师的无情美食家" },
      { term: "Checker 物理阻断", def: "用全新、无污染（Fresh）的模型上下文来进行评估判分", analogy: "拉开隔离窗，蒙眼盲测" },
    ],
    takeaway: "干活的 Agent（Maker）太容易盲目自信和妥协。必须在物理上隔绝上下文，派一个独立模型的 Checker 专门挑刺，这是无人值守系统不失控的前提。",
    quiz: [
      {
        type: "choice",
        q: "为什么在设计自跑循环的 Checker（评判器）时，强调要使用一个“全新且干净（Fresh）”的模型实例，而不是在 Maker 的对话历史里直接问它？",
        options: [
          "为了省 token",
          "因为 Maker 在自己的对话历史里极其容易说服自己，产生主观偏差和妥协情绪；而干净的模型没有 Maker 的思维惯性",
          "因为 Fresh 模型运行速度快"
        ],
        answer: 1,
        explain: "Maker 很容易盲目点头。换一个带着无情挑刺指令的 Checker 盲测，才能发现逻辑漏洞。",
      },
      {
        type: "tf",
        q: "Maker/Checker 阻断机制意味着大模型不能在一次运行里既当选手又当裁判，应该分成两个子 Agent 团队协作运转。",
        options: ["对", "错"],
        answer: 0,
        explain: "对。子代理团队协作和物理隔离，能有效阻断“自我赞美”的恶性循环。",
      },
    ],
  },

  /* ============ LE5 ============ */
  {
    id: "LE5", icon: "🎪", title: "三个真实的自跑 Loop 案例",
    hook: "拆解 Addy Osmani 的 triage 循环和 Stripe 等经典工业范式",
    fixes: [1, 2, 3, 4, 5, 6],
    defectLabel: "检验六大零件协同",
    concepts: [
      { term: "Triage Loop", def: "Chrome 团队 Addy 实现的早晨分诊循环", analogy: "自动分诊台：过滤错误、提取 issue，给人类列出待办" },
      { term: "Stripe PR 滚轴", def: "大规模流水线，自动开分支修改、跑测试、合 PR", analogy: "流水线装配车间：只要绿灯亮起，车辆自行开出" },
    ],
    takeaway: "真实的 Loop 范式都遵循了“小规模起步、高强度验证、人肉留卡点”的逻辑。自动化是手段，人工复核是缰绳。",
    quiz: [
      {
        type: "tf",
        q: "在 Chrome 团队的 Triage 循环中，Addy 强调他并不手动去 Prompt 那个分诊 Agent，而是设置了定时任务（Automation）触发 Skill，并由另一个 Agent 验证结果。",
        options: ["对", "错"],
        answer: 0,
        explain: "对。这印证了循环的核心——定时心跳 + 自动发现 + 监督验证。",
      },
    ],
  },

  /* ============ LE6 ============ */
  {
    id: "LE6", icon: "💸", title: "代价：验证债与 Token 失控",
    hook: "剖析自跑循环潜藏的四大隐性债务，钉死上限防线",
    fixes: [5, 6],
    defectLabel: "抵御验证债与 Token 失控",
    concepts: [
      { term: "验证债 (Verification Debt)", def: "自动生成的代码没有被严密测试，错误悄悄累积", analogy: "把错题胡乱堆在抽屉里，假装自己全学会了" },
      { term: "理解腐烂 (Comprehension Debt)", def: "代码在疯长，但由于是 AI 写的，人脑中的项目地图早已过期", analogy: "路越铺越长，你却只拿着十年前的指南针" },
      { term: "Token 失控", def: "死循环导致在一夜之间烧干一整月的 API 额度", analogy: "水龙头没关，漏了一整晚把地板泡烂" },
    ],
    takeaway: "必须用预算天花板（Token/重试上限）和独立 Checker 来抵御隐性债。执行可以外包，但理解力和判断力绝不可外包。",
    quiz: [
      {
        type: "choice",
        q: "为了防止你的 Agent 在你睡觉时因为一个死循环 Bug 烧光你整月的 API 账单，以下哪项措施是最根本的防线？",
        options: [
          "改用更贵但更聪明的模型",
          "给循环强制设置单次运行的 max_steps、每秒/每日 token 上限和最大重试限制，超限即熔断",
          "期盼代码自然不出 bug"
        ],
        answer: 1,
        explain: "多重硬预算并联（Token限额、重试次数、时间熔断）是防止爆账单唯一的硬防线。",
      },
      {
        type: "tf",
        q: "Comprehension Debt（理解债）是指因为 AI 自动写代码太快，人类工程师不需要再阅读和理解任何代码，从而彻底实现了心智的解放。",
        options: ["对", "错"],
        answer: 1,
        explain: "错！这是认知投降。代码写得越快，人脑的理解缺口越大，最终你会彻底丧失对项目的把控力。必须定期人肉阅读 PR 摘要并抽查核心逻辑。",
      },
    ],
  },

  /* ============ LE7 ============ */
  {
    id: "LE7", icon: "👮", title: "当工程师，不只是按下启动键",
    hook: "警惕认知投降与架空，确定人在环路的判断力价值",
    fixes: [5],
    defectLabel: "拧紧 ⑤ 判断力 哨卡",
    concepts: [
      { term: "认知投降", def: "对 Agent 的决定和代码产生盲信，闭眼合并 PR", analogy: "当甩手掌柜，连账单都懒得对，最终被管家架空" },
      { term: "判断力", def: "辨别方案是否真的正确、代码根基是否合理的稀缺资产", analogy: "决定马车朝哪走，而不是去当拉车的马" },
    ],
    takeaway: "循环是个忠实的乘号，它会放大你本身的特质。如果你带入的是理解，它放大理解；如果你带入的是偷懒，它放大偷懒。保持对系统的掌控权。",
    quiz: [
      {
        type: "choice",
        q: "Addy Osmani 说的“Two people can build the same loop and get opposite outcomes.” 核心表达了什么？",
        options: [
          "同样的循环在不同操作系统上运行速度不同",
          "同样的工具，有人用来放大专业判断，有人用来逃避理解决策，半年后两人的工程能力和项目结局会截然相反",
          "大模型的返回完全随机，无法预测"
        ],
        answer: 1,
        explain: "循环是个乘号，乘的是你本身的输入。保持判断力，stay the engineer！",
      },
      {
        type: "tf",
        q: "在自跑循环中，我们不应该去焊死大门以图再也不进车间，而应该主动留几道人工复核（Escalation）哨口，保留自己说“不”的权力。",
        options: ["对", "错"],
        answer: 0,
        explain: "对。留出人肉卡点，让我们始终有钥匙可以走进车间看清发生了什么。",
      },
    ],
  },

  /* ============ LE8 ============ */
  {
    id: "LE8", icon: "🚀", title: "今天就动手：搭建第一个 Loop",
    hook: "在 Claude Code 中实践 /loop 和 /goal 关卡，体验自调度",
    fixes: [1, 2, 3, 4, 5, 6],
    defectLabel: "在终端跑起第一个自跑循环",
    concepts: [
      { term: "/loop", def: "Claude Code 中原生内置的定时后台循环指令", analogy: "给你本机的 Agent 装一个定时闹钟" },
      { term: "/goal", def: "直到条件达成（通过 Checker 盲测）才停下的自动化硬指令", analogy: "不见兔子不撒鹰" },
      { term: "--worktree", def: "克隆出临时物理工作区防止并行 Agent 打架冲突", analogy: "给后台作业的 Agent 批一间单独的隔音工作室" },
    ],
    takeaway: "用本地 /loop 和 /goal 练习起步，钉死预算防线、配置 Checker 盲测、拉起 worktree 隔离，你就掌握了拼装自跑循环的全套手艺。",
    quiz: [
      {
        type: "choice",
        q: "在 Claude Code 中，当你想让它持续修改代码、运行测试，直到 test/auth.test.ts 里的测试全部通过才停下，最应该跑哪条命令？",
        options: [
          "/loop 5m run auth test",
          "/goal all tests in test/auth.test.ts pass",
          "/help"
        ],
        answer: 1,
        explain: "`/goal` 用于跑到指定条件满足为止。而 `/loop` 只是定时周期执行任务。",
      },
      {
        type: "tf",
        q: "在 Claude Code 本地终端跑的 `/loop` 任务是 session-scoped（会话级）的，一般在 7 天后会自动过期，且当电脑关机或合盖时会暂停。",
        options: ["对", "错"],
        answer: 0,
        explain: "对。这是本地 Loop 的运行边界，如果想要通宵或云端挂载，需要使用 actions 或 Cloud Routines。",
      },
    ],
  },

  /* ============ LE ============ */
  {
    id: "LE", icon: "🗺️", title: "总图：五动作与六零件全景解剖图",
    hook: "温习四层栈、五大动作、六大零件与四大防御手段，拿到毕业寄语",
    fixes: [1, 2, 3, 4, 5, 6],
    defectLabel: "全面回收系统掌控力",
    isCapstone: true,
    concepts: [
      { term: "四层技术栈", def: "Prompt -> Context -> Harness -> Loop 的分层工程", analogy: "一幢大楼的四层楼板" },
      { term: "验证债防御", def: "依靠独立 Checker 对生成代码说“不”，拦截低质 PR", analogy: "质量关防洪堤" },
    ],
    takeaway: "恭喜通关！自跑循环的秘密尽在：五大动作保障流程运转、六个零件支撑机器装配、四大代价警醒底线红线。智能不在模型，在循环中运转。Stay the Engineer！",
    quiz: [
      {
        type: "match",
        q: "【毕业考】将自跑循环的六大核心零件与对应的典型作用拖动配对。",
        defects: [
          { label: "自动化心跳", drop: "定时启动并触发分诊与 Triage" },
          { label: "物理隔离器", drop: "git worktree 保证并行开发不踩脚" },
          { label: "显式技能库", drop: "SKILL.md 固化仓库级指令与规范" },
          { label: "外部连接器", drop: "MCP 协议连通 Slack、Linear 等外部 API" },
          { label: "子代理分工", drop: "Maker/Checker 分离，无情 Checker 盲评" },
          { label: "落盘记忆体", drop: "loop_status.md 状态文件让 Agent 续接记忆" }
        ],
        chips: [
          "定时启动并触发分诊与 Triage",
          "git worktree 保证并行开发不踩脚",
          "SKILL.md 固化仓库级指令与规范",
          "MCP 协议连通 Slack、Linear 等外部 API",
          "Maker/Checker 分离，无情 Checker 盲评",
          "loop_status.md 状态文件让 Agent 续接记忆"
        ],
        mapping: { 0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5 },
        explain: "这六大零件是自跑循环组装的终极基石。盖住答案能默写出来，说明你已经完全吃透了本课程！",
      },
      {
        type: "tf",
        q: "恭喜通关 Loop Engineering 课程！你已经掌握了如何将自己从循环中剥离，设计出具有自启动、自隔离、强 Checker 验证和落盘状态延续的自跑循环系统！",
        options: ["我已做好准备，当一名掌控循环的工程师！", "还需要继续修炼"],
        answer: 0,
        explain: "向你致敬，掌控循环的工程师！Build the loop, but stay the engineer！",
      },
    ],
  },
];
