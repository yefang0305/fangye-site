export interface ConceptItem {
  term: string;
  def: string;
  analogy: string;
}

export interface DefectOption {
  label: string;
  drop: string;
}

export interface QuizItem {
  type: 'tf' | 'choice' | 'match';
  q: string;
  options?: string[];
  answer?: number;
  explain: string;
  defects?: DefectOption[];
  chips?: string[];
  mapping?: Record<number, number>;
}

export interface LevelItem {
  id: string;
  icon: string;
  title: string;
  hook: string;
  fixes: number[];
  defectLabel: string;
  isCapstone?: boolean;
  concepts: ConceptItem[];
  takeaway: string;
  ascii?: string;
  quiz: QuizItem[];
}

export interface DefectItem {
  id: number;
  name: string;
  desc: string;
  fixed: string[];
}

export const FIVE_DEFECTS: DefectItem[] = [
  { id: 1, name: "无状态（健忘）", desc: "调用完就忘", fixed: ["L1", "L4", "L5"] },
  { id: 2, name: "不能行动（只会说）", desc: "输出文字 ≠ 行动", fixed: ["L2"] },
  { id: 3, name: "不能持续（一锤子）", desc: "说完就停", fixed: ["L3"] },
  { id: 4, name: "容量有限（装不下）", desc: "上下文窗口有上限", fixed: ["L4", "L6"] },
  { id: 5, name: "会幻觉 / 不可靠", desc: "会自信地编", fixed: ["L7"] },
];

export const LEVELS: LevelItem[] = [
  /* ============ L0 ============ */
  {
    id: "L0", icon: "🧠", title: "地基：什么是 Harness",
    hook: "模型是大脑，harness 是身体、记忆和缰绳",
    fixes: [1, 2, 3, 4, 5],
    defectLabel: "全 5 大缺陷总览",
    concepts: [
      { term: "裸模型", def: "只会文字进、文字出的无状态函数", analogy: "白房间里被锁住的天才顾问" },
      { term: "Harness", def: "包裹在模型外的整套脚手架软件", analogy: "白房间的门、电话、纸笔、秘书" },
      { term: "Agent", def: "模型 + Harness 的整体", analogy: "能行动、能记忆、能自主的完整工人" },
      { term: "纯函数", def: "同样输入永远给同样输出、不留痕迹", analogy: "失忆 of 顾问，每轮都是新人" },
      { term: "API 调用", def: "通过网络付费调用别人家模型服务", analogy: "不用自己训练，直接雇大脑" },
    ],
    takeaway: "模型是大脑，harness 是身体、记忆和缰绳。所有'AI 会做事'的魔法都不在模型里，而在你亲手设计的外壳里。",
    quiz: [
      {
        type: "tf",
        q: "你和 ChatGPT 连聊了十轮，说明模型把前九轮的内容'记住'了。",
        options: ["对，是模型自己记的", "错，是外面程序把历史重新打包塞回去的"],
        answer: 1,
        explain: "模型本身无状态。'记住'是 harness 每轮把历史整叠重发制造的假象——记忆在 messages 列表里，不在模型里。",
      },
      {
        type: "choice",
        q: "你让 Claude Code 把文件里的 foo 改成 bar。这一步里，'真的去改文件'是谁干的？",
        options: ["模型自己打开文件改的", "harness 解析了模型的'申请单'，用代码执行的", "操作系统自动完成的"],
        answer: 1,
        explain: "模型只能输出文字（'我要改 foo 为 bar'这张申请单）。真正执行的是 harness——它读懂申请单，调用代码去改文件。",
      },
      {
        type: "match",
        q: "把'裸模型的五大先天缺陷'拖到正确描述上。",
        defects: [
          { label: "① 无状态", drop: "每次调用都是全新的它" },
          { label: "② 不能行动", drop: "只能输出文字，碰不到真实世界" },
          { label: "③ 不能持续", drop: "说完一句就停，不会自己接下一步" },
          { label: "④ 容量有限", drop: "一次能读的字数有上限" },
          { label: "⑤ 会幻觉", drop: "自信地编造听起来对的东西" },
        ],
        chips: ["说完一句就停，不会自己接下一步", "只能输出文字，碰不到真实世界", "一次能读的字数有上限", "每次调用都是全新的它", "自信地编造听起来对的东西"],
        mapping: { 0: 3, 1: 1, 2: 0, 3: 2, 4: 4 },
        explain: "五个缺陷记法：①忘②说③停④小⑤编。后面的 L1-L8 就是逐个修这五个洞。",
      },
    ],
  },

  /* ============ L1 ============ */
  {
    id: "L1", icon: "📜", title: "一次模型调用的解剖",
    hook: "messages 列表、token、上下文窗口——所有 harness 的最底层协议",
    fixes: [1],
    defectLabel: "补 ① 无状态（第一次）",
    concepts: [
      { term: "messages 列表", def: "带角色标签的消息数组", analogy: "塞进门缝的那一整叠纸" },
      { term: "system 消息", def: "整段对话的'宪法'，定人格/规则/边界", analogy: "贴在顾问房间里的规则告示" },
      { term: "user / assistant", def: "用户提问 / 模型上一轮的回答", analogy: "对话历史的两方" },
      { term: "token", def: "模型计费的最小单位", analogy: "约等于 0.75 英文单词或半个汉字" },
      { term: "上下文窗口", def: "一次能塞进去的 token 总上限", analogy: "工作台大小" },
      { term: "temperature", def: "采样旋钮，控制随机/发散", analogy: "0=最确定，1=更敢想" },
    ],
    takeaway: "和模型的每次交互 = 组装带角色标签的 messages 列表、塞进上下文窗口、按旋钮续写。记忆、人格、对话全是 harness 在这一叠纸上做文章。",
    quiz: [
      {
        type: "tf",
        q: "把 temperature 调到 0，模型就不会再说错话/产生幻觉了。",
        options: ["对", "错"],
        answer: 1,
        explain: "temperature 控制的是随机性，不是事实性。调到 0 只是更确定地输出，模型照样可能确定地编。幻觉是模型本质，得靠 L7 验证手段治。",
      },
      {
        type: "choice",
        q: "一次模型调用喂进去的输入结构叫什么？",
        options: [
          "一个长字符串",
          "一个带角色标签的消息列表（messages）",
          "一个 JSON 配置",
        ],
        answer: 1,
        explain: "一次调用的输入是 messages 列表，每条消息带 system/user/assistant 角色标签。这是最底层的协议。",
      },
      {
        type: "choice",
        q: "模型一次能'读进眼里'的 token 总量上限叫什么？",
        options: [
          "上下文窗口（context window）",
          "工作内存（working memory）",
          "缓存池（cache pool）",
        ],
        answer: 0,
        explain: "上下文窗口是 L1 的核心概念：输入 + 输出共用一个 token 预算，超了就报错或被截断。L4 整层都在和它搏斗。",
      },
      {
        type: "choice",
        q: "为什么'开一个新会话'通常比'在超长的老会话里继续问'更快更省钱？",
        options: [
          "新会话用了更聪明的模型",
          "老会话的 messages 列表被清空，从短开始；老会话的列表每轮都整段重发",
          "新会话会让模型认真起来",
        ],
        answer: 1,
        explain: "老会话的 messages 越来越长，每轮都被整段重发——token 堆、变慢、可能逼近窗口上限触发压缩。新会话等于手动清空桌子。",
      },
    ],
  },

  /* ============ L2 ============ */
  {
    id: "L2", icon: "🛠️", title: "让模型能'行动'：工具调用",
    hook: "Agent 的'手'不长在模型上，长在 harness 上",
    fixes: [2],
    defectLabel: "补 ② 不能行动",
    concepts: [
      { term: "工具定义", def: "用 JSON Schema 告诉模型：你有什么工具、参数是什么", analogy: "给顾问一张'可用服务清单'" },
      { term: "申请单", def: "模型要调工具时输出的结构化 JSON", analogy: "顾问在纸条上写'请帮我读报告.txt'" },
      { term: "harness 执行", def: "解析申请单，调用真实代码去跑", analogy: "你（房间外的人）真的去开文件" },
      { term: "结果回填", def: "把执行结果打包成 tool 消息塞回 messages", analogy: "把文件内容写成新纸条塞回去" },
      { term: "权限闸", def: "执行前的批准检查（危险操作问用户）", analogy: "删库申请要先过主管签" },
    ],
    takeaway: "模型永远只输出文字（申请单），真正动手的是 harness——所以安全、能力扩展、确定性全都有抓手了。",
    ascii: `   ① 定义工具         ② 模型"申请"        ③ harness 执行
   告诉模型"你有       模型输出结构化         harness 解析申请单,
   哪些工具,参数      JSON:                 真的去跑
   长什么样"           {tool:"read_file",
                        args:{path:"r.txt"}}
                             ↓
                      ④ 结果回填
               把结果当 tool 消息塞回 messages
               → 模型读到后再决定下一步`,
    quiz: [
      {
        type: "tf",
        q: "模型在回答里写出了 'rm -rf /'，你的电脑通常不会被删，因为……",
        options: [
          "模型从来不输出这种危险命令",
          "模型只是输出了文字（申请单），真正执行由 harness 控制；正经 harness 会在执行前弹窗请用户批准",
          "Linux 系统会自动拦截",
        ],
        answer: 1,
        explain: "模型写出 rm -rf 只是字符。要变成真实动作，必须 harness 在第③步去执行——而这里就是权限闸所在。安全闸在 harness 手里，不在模型那里。",
      },
      {
        type: "match",
        q: "把四步工具调用闭环按正确顺序排好。",
        defects: [
          { label: "第 1 步", drop: "定义工具（写明有哪些工具和参数）" },
          { label: "第 2 步", drop: "模型输出结构化申请单" },
          { label: "第 3 步", drop: "harness 真的去执行（产生真实副作用）" },
          { label: "第 4 步", drop: "结果回填到 messages，再喂回模型" },
        ],
        chips: ["harness 真的去执行（产生真实副作用）", "结果回填到 messages，再喂回模型", "定义工具（写明有哪些工具和参数）", "模型输出结构化申请单"],
        mapping: { 0: 2, 1: 3, 2: 0, 3: 1 },
        explain: "口诀：定义→申请→执行→回填。真实副作用（删文件、花钱）只在第③步发生，由 harness 执行。",
      },
      {
        type: "choice",
        q: "工具执行报错了，最好的做法是？",
        options: [
          "harness 抛异常、终止 agent",
          "把错误信息当 tool 结果回填，让模型有机会自我纠错（换参数重试）",
          "再调一次同样的工具",
        ],
        answer: 1,
        explain: "错误回填是 L2+L3 自我纠错的来源。直接终止会浪费模型的纠错能力，是脆弱设计。",
      },
    ],
  },

  /* ============ L3 ============ */
  {
    id: "L3", icon: "🔄", title: "让模型能'持续做事'：Agent Loop",
    hook: "Agent 不是一个更聪明的模型，而是'工具调用 + 一个 while 循环'",
    fixes: [3],
    defectLabel: "补 ③ 不能持续",
    concepts: [
      { term: "Agent Loop", def: "反复调模型 → 执行工具 → 回填 → 调模型……的 while 循环", analogy: "装修工自己看'这面墙白没白，没白就再刷一道'" },
      { term: "max_steps", def: "循环的最大步数上限", analogy: "硬刹车——再刷就强制停下" },
      { term: "退出条件", def: "模型不再输出工具申请 = 它觉得做完了", analogy: "工人在墙边停下说'刷完了'" },
      { term: "分水岭", def: "循环之前叫聊天机器人，循环之后才叫智能体", analogy: "能'自动做完多步'才是 agent" },
    ],
    takeaway: "Agent 不是某种更聪明的模型，而是'工具调用 + 一个 while 循环'。循环让只会走一步的模型一步步走到底，harness 同时握着缰绳。",
    ascii: `   messages = [system, 用户任务]
   while True:
     回复 = 调用模型(messages)             ← L1 的一次调用
     if 回复含工具申请:
       结果 = 执行工具(回复.申请)           ← L2 第③步
       messages.append(回复)
       messages.append(结果)                ← L2 第④步回填
       continue                            ← 关键:再走一步
     else:
       return 回复                         ← 没申请=做完了`,
    quiz: [
      {
        type: "tf",
        q: "Agent loop 里必须设 max_steps 上限，不设会让 agent 拥有无限循环的能力。",
        options: ["对，这是正确的", "错，不设 max_steps 也能正常工作"],
        answer: 0,
        explain: "永远不要让 agent 拥有无限循环的权力。可能陷入死循环、可能无限烧 token。max_steps 是必备的硬刹车。",
      },
      {
        type: "choice",
        q: "在循环里，模型'觉得任务完成了'，harness 是怎么判断的？",
        options: [
          "harness 自己分析任务清单",
          "模型这一轮不再输出工具申请单，只输出文字回答",
          "用户主动点'完成'按钮",
        ],
        answer: 1,
        explain: "退出条件 = 模型不再开工具申请单。是模型在'判断任务完成'，但 harness 在'执行这个判断'——直接 return，跳出 while。",
      },
      {
        type: "tf",
        q: "Agent 的'自主多步'，实现上只是 L2 的工具调用 + 一个 while 循环。",
        options: ["对", "错"],
        answer: 0,
        explain: "这是整门课最反直觉也最重要的一句话：'agentic'的'自主多步'，实现上只是一个 while 循环，没有别的魔法。",
      },
    ],
  },

  /* ============ L4 ============ */
  {
    id: "L4", icon: "📚", title: "装得下、记得住：上下文工程",
    hook: "上下文窗口是有限的办公桌——不是塞得越多越聪明，是放得越准越清醒",
    fixes: [1, 4],
    defectLabel: "补 ①无状态 + ④容量有限",
    concepts: [
      { term: "中间遗忘", def: "塞得越满，模型对中间信息越'视而不见'", analogy: "满桌资料，关键那张被压在中间" },
      { term: "刀一·裁剪", def: "只放相关的，扔掉无关的", analogy: "500 行日志只挑报错那 3 行" },
      { term: "刀二·压缩", def: "长历史总结成短摘要替换掉", analogy: "40 轮对话压成一段'我们定了 X,还差 Y'" },
      { term: "刀三·检索/RAG", def: "海量知识放窗口外，用到才捞", analogy: "不搬整个图书馆，按需去书架上抽那一页" },
      { term: "刀四·外部记忆", def: "大块资料放文件，留指针按需读", analogy: "桌上贴张便利贴：'方案见 D 盘 plan.md'" },
    ],
    takeaway: "上下文窗口是有限办公桌。靠裁剪/压缩/检索/外部记忆四把刀，每轮精准决定'什么摊上桌、什么收进抽屉'。",
    quiz: [
      {
        type: "tf",
        q: "等上下文窗口大到 1000 万 token，上下文工程就没意义了。",
        options: ["对，窗口够大就完事", "错，中间遗忘不随窗口变大消失，token 也更贵更慢"],
        answer: 1,
        explain: "窗口变大只把'装不下'红线往后挪，但中间遗忘不消失（塞满更糟）、成本随 token 数指数级增长。'该放什么'的手艺永远在。",
      },
      {
        type: "match",
        q: "把上下文工程的四把'刀'和它们的核心动作对上。",
        defects: [
          { label: "刀一·裁剪", drop: "只放相关的，扔掉无关的" },
          { label: "刀二·压缩", drop: "长历史总结成短摘要" },
          { label: "刀三·检索/RAG", drop: "按需从外部知识库捞相关片段" },
          { label: "刀四·外部记忆", drop: "卸载到文件，桌上只留指针" },
        ],
        chips: ["按需从外部知识库捞相关片段", "卸载到文件，桌上只留指针", "长历史总结成短摘要", "只放相关的，扔掉无关的"],
        mapping: { 0: 3, 1: 2, 2: 0, 3: 1 },
        explain: "四把刀：裁剪（筛）、压缩（压）、检索（按需捞）、外部记忆（甩出去）。每轮对每块信息问'该用哪把刀'。",
      },
      {
        type: "choice",
        q: "公司有几千页产品文档要做问答 agent。最不该做的是？",
        options: [
          "把几千页全塞进上下文",
          "把文档存进可检索知识库，每次问题只检索最相关的几段塞进上下文",
          "用 RAG 按需加载",
        ],
        answer: 0,
        explain: "全塞进去会溢出 + 中间遗忘 + 极贵极慢。正确做法是 RAG：把文档当外部档案，桌面上只摊当下相关的那几页。",
      },
    ],
  },

  /* ============ L5 ============ */
  {
    id: "L5", icon: "📓", title: "跨会话记得你：记忆系统",
    hook: "记忆不是模型长了记性，是 harness 配了本笔记本 + 上工先翻笔记",
    fixes: [1],
    defectLabel: "补 ① 无状态（终极版）",
    concepts: [
      { term: "短期记忆", def: "单次会话内的 messages 列表", analogy: "今天的桌面" },
      { term: "长期记忆", def: "存在窗口外的持久档案", analogy: "明天的桌面之外，还有你的笔记本" },
      { term: "事实/语义记忆", def: "稳定的事实：你是产品经理、喜欢简洁", analogy: "通讯录" },
      { term: "情景记忆", def: "发生过的事件：上次选了方案 B", analogy: "日记本" },
      { term: "记忆的四个动作", def: "写 / 读 / 更新 / 忘", analogy: "笔记本要勤记勤翻勤改勤扔" },
    ],
    takeaway: "记忆 = 持久外部档案 + 在对的时刻把对的往事检索回上下文（L4）。模型永远失忆，记性在外壳里。",
    quiz: [
      {
        type: "choice",
        q: "'用户是产品经理'属于哪种记忆？",
        options: ["短期·事实", "长期·事实", "长期·情景", "短期·情景"],
        answer: 1,
        explain: "稳定事实 + 跨会话有用 = 长期·事实。这是 harness 长期记忆文件最常记的类别。",
      },
      {
        type: "tf",
        q: "'错误的长期记忆比没有记忆更危险'——因为模型会自信地采用上下文里的过期信息去误导决策。",
        options: ["对", "错"],
        answer: 0,
        explain: "这就是为什么记忆的'更新(Update)'和'遗忘(Forget)'不是可选项，是必备保养。",
      },
      {
        type: "choice",
        q: "记忆在实现上常常就是对记忆库做哪种技术（手段）的应用？",
        options: [
          "RAG（检索增强生成）",
          "微调（fine-tuning）",
          "强化学习（RL）",
        ],
        answer: 0,
        explain: "RAG 是手段，记忆是这个手段服务的对象之一（另一个是领域知识库）。所以 L4 吃透了，L5 几乎免费——记忆本质就是'对一个记忆库做 RAG'。",
      },
    ],
  },

  /* ============ L6 ============ */
  {
    id: "L6", icon: "👥", title: "一个 agent → 一支团队：子代理与编排",
    hook: "靠的不是'更多算力'，而是'更多张干净的桌子'",
    fixes: [4],
    defectLabel: "绕过 ④ 容量上限 + 放大产能",
    concepts: [
      { term: "子代理", def: "一个独立干净上下文的小 agent", analogy: "派出去的下属，桌上只摆他那份资料" },
      { term: "上下文隔离", def: "子代理之间互不污染，主线只收精炼结论", analogy: "每人一间独立办公室" },
      { term: "并行编排", def: "独立子任务同时派出去", analogy: "三家竞品各派一个调研员同时跑" },
      { term: "串行编排", def: "下一步依赖上一步结果", analogy: "先调研后写方案的接力" },
      { term: "何时该拆", def: "任务能清晰切成相对独立的块", analogy: "大而可分才拆，小而连贯别拆" },
    ],
    takeaway: "把一个 agent 变团队，靠'更多张干净的桌子'。隔离保质量、并行提速度；拆有协调成本，默认单代理，遇到'大而可分'才组队。",
    ascii: `        ┌──── 主代理 / Orchestrator ────┐
        │  桌上只放:总目标 + 精炼结论    │
        └──┬─────────┬─────────┬─────────┘
     派子  │     派子 │     派子│
      ▼   任务A  │   任务B  │   任务C│
    ┌──────┐   ┌──────┐   ┌──────┐
    │子代理A│   │子代理B│   │子代理C│
    │独立桌子│   │独立桌子│   │独立桌子│
    │独立loop│   │独立loop│   │独立loop│
    └──┬───┘   └──┬───┘   └──┬───┘
       └──── 精炼结论 ────────┘
                 ▼
          主代理汇总 → 最终产出`,
    quiz: [
      {
        type: "choice",
        q: "'把这个 2000 字段落改通顺'——该不该拆成多个子代理？",
        options: [
          "该拆，大任务就拆",
          "不该拆，小而连贯，拆了协调开销 > 收益",
          "随便",
        ],
        answer: 1,
        explain: "判据：任务能否清晰切成相对独立块。能拆才拆。小而连贯的任务，拆了反而更慢更贵。",
      },
      {
        type: "tf",
        q: "子代理的'并行提速'比'上下文隔离'更根本。",
        options: ["对", "错，隔离才是更根本的收益"],
        answer: 1,
        explain: "即便串行用子代理，'每张桌子只装一件事、互不污染'本身就能显著提升质量、绕过容量墙。隔离是因，提速是其中一个果。",
      },
      {
        type: "match",
        q: "把任务和合适的编排模式对上。",
        defects: [
          { label: "调研 5 个互不依赖的开源库", drop: "并行" },
          { label: "先调研需求产出规格，再据此写实现", drop: "串行" },
        ],
        chips: ["串行", "并行"],
        mapping: { 0: 1, 1: 0 },
        explain: "独立→并行；有依赖→串行。真实系统常是两者混合：能并行的并行，有依赖的串行。",
      },
    ],
  },

  /* ============ L7 ============ */
  {
    id: "L7", icon: "🛡️", title: "靠谱地自主跑：可靠性、验证",
    hook: "能力越强、越自主，越需要缰绳——证据，而非声称",
    fixes: [5],
    defectLabel: "补 ⑤ 不可靠（缰绳）",
    concepts: [
      { term: "假性完成", def: "模型兴高采烈说'搞定了'，其实没真做完", analogy: "谎报军情——最阴险的翻车" },
      { term: "缰绳一·验证门", def: "完成前强制跑确定性检查", analogy: "宣称修好 bug 前必须看到测试通过" },
      { term: "缰绳二·计划-执行分离", def: "先审计划再动手", analogy: "施工前先看图纸" },
      { term: "缰绳三·交叉复查", def: "独立子代理回头审自己产出", analogy: "code review：别人挑刺比自己准" },
      { term: "缰绳四·人在环路", def: "高风险不可逆动作交还人批", analogy: "删库前先弹窗" },
      { term: "可观测性", def: "记录每步：模型想了啥、调了啥、得到啥", analogy: "行车记录仪" },
      { term: "Eval", def: "用标准考题量化'agent 靠不靠谱'", analogy: "定期给员工打 KPI" },
    ],
    takeaway: "可靠性不能向模型索取，只能由 harness 从外部建立：用验证门/复查/计划/人在环路在运行时拦错，用可观测/Eval 看过程、量化质量。证据，而非声称。",
    quiz: [
      {
        type: "choice",
        q: "三种翻车方式里，'假性完成'为什么最危险？",
        options: [
          "因为它会让模型累",
          "因为它伪装成成功，最容易蒙混过关，把没做完的当完成的交付，破坏信任",
          "因为它会让用户多付钱",
        ],
        answer: 1,
        explain: "专治它的是缰绳一·验证门：完成的判定权交给确定性检查（真跑测试/真读回结果），用客观证据而非模型的话认定。",
      },
      {
        type: "tf",
        q: "用独立的子代理复查 agent 的产出，往往比让 agent 自己复查自己更有效。",
        options: ["对", "错"],
        answer: 0,
        explain: "自己复查带着'我刚写完挺满意'的确认偏差，看不见自己的错。独立子代理是张干净、无包袱的新桌子（L6 隔离），旁观者视角更容易挑刺。",
      },
      {
        type: "match",
        q: "把四道缰绳和它们的核心动作对上。",
        defects: [
          { label: "验证门", drop: "完成前用客观检查判定（真跑测试）" },
          { label: "计划-执行分离", drop: "先审计划，再动手" },
          { label: "交叉复查", drop: "独立子代理回头审产出" },
          { label: "人在环路", drop: "高风险操作请人批准" },
        ],
        chips: ["先审计划，再动手", "完成前用客观检查判定（真跑测试）", "高风险操作请人批准", "独立子代理回头审产出"],
        mapping: { 0: 1, 1: 0, 2: 3, 3: 2 },
        explain: "口诀：想(计划)→ 做(自查+请示)→ 验(验证门)→ 复(独立复查)。自主性没被剥夺，每个高风险环节都有关卡。",
      },
    ],
  },

  /* ============ L8 ============ */
  {
    id: "L8", icon: "💼", title: "做成产品：Harness 的产品化",
    hook: "前七层教你'能做到什么'，这一层教你'该做到什么'",
    fixes: [],
    defectLabel: "三笔账：延迟 · 成本 · 边界",
    concepts: [
      { term: "账一·延迟", def: "用户等多久、几步循环才出结果", analogy: "等 30 秒出字=技术上没错，体验已死" },
      { term: "账二·成本", def: "每步烧的 token × 百万用户", analogy: "demo 跑几次无所谓，量产是天文数字" },
      { term: "账三·边界", def: "能碰什么、不能碰什么、错了谁担", analogy: "实验室随便造，卖给用户要担责" },
      { term: "流式输出", def: "逐字蹦出，体感快", analogy: "打字机效果" },
      { term: "模型路由", def: "简单任务派小模型，难任务派大模型", analogy: "便利店结账找店员不找 CEO" },
      { term: "缓存", def: "重复上下文前缀不重复计费", analogy: "一次备案反复用" },
      { term: "优雅降级", def: "模型挂了能换能重试或体面告知", analogy: "飞机一台引擎坏了还能飞" },
    ],
    takeaway: "产品化是给前七层能力算三笔账：延迟、成本、边界。好的 agent 产品不是能力拉满，而是克制得恰到好处。",
    quiz: [
      {
        type: "choice",
        q: "'模型路由'同时改善了三笔账里的哪几笔？",
        options: ["只改善延迟", "改善延迟 + 成本", "改善成本 + 边界", "改善全部三笔"],
        answer: 1,
        explain: "小模型又快又便宜→延迟↓成本↓。边界不受影响（路由改的是模型选择，不是权限）。",
      },
      {
        type: "tf",
        q: "'上下文工程（L4）本质上就是省钱'——因为进入上下文的每个 token 都要付费且每轮都重发。",
        options: ["对", "错"],
        answer: 0,
        explain: "L4 的裁剪/压缩/按需读 = 每轮少塞无关 token = 每轮少付钱 + 更快 + 更不易溢出。省 token 直接等于省钱。",
      },
      {
        type: "match",
        q: "把产品化决策和它改善的'账'对上。",
        defects: [
          { label: "流式输出", drop: "账一·延迟" },
          { label: "prompt 缓存", drop: "账二·成本" },
          { label: "危险命令弹窗", drop: "账三·边界" },
          { label: "max_steps 上限", drop: "账二/账三（成本闸+可控）" },
        ],
        chips: ["账二·成本", "账一·延迟", "账二/账三（成本闸+可控）", "账三·边界"],
        mapping: { 0: 1, 1: 0, 2: 3, 3: 2 },
        explain: "L1-L7 学的每个技术，到了产品层都有'价签'。把 Claude Code 用到极致 = 用更少 token/步数办成同样的事。",
      },
    ],
  },

  /* ============ L9 ============ */
  {
    id: "L9", icon: "🗺️", title: "总图：能力全景解剖",
    hook: "把 L0–L8 拼成一张能随时调取的全景地图",
    fixes: [1, 2, 3, 4, 5],
    defectLabel: "回收'全面性'",
    isCapstone: true,
    concepts: [
      { term: "进化链", def: "从裸模型到生产级 agent 的纵向叙事", analogy: "一件一件装设备，直到能交付百万人" },
      { term: "全景解剖", def: "成熟 agent 同时运转的所有部件", analogy: "成品 agent 的横切图" },
      { term: "缺陷↔解法对照表", def: "5 大缺陷 vs 修补它的层", analogy: "最该背下来的一张表" },
    ],
    takeaway: "Harness engineering 的全部：让确定性的代码(外壳)补模型(大脑)的每一个先天缺陷，在'判断'和'确定性'的正确边界上把它们拼起来。",
    quiz: [
      {
        type: "match",
        q: "【毕业考】把'五大缺陷'重新拖回对应的'主要修补层'。",
        defects: [
          { label: "① 无状态（健忘）", drop: "L1 + L4 + L5" },
          { label: "② 不能行动", drop: "L2" },
          { label: "③ 不能持续", drop: "L3" },
          { label: "④ 容量有限", drop: "L4（+L6）" },
          { label: "⑤ 会幻觉/不可靠", drop: "L7" },
        ],
        chips: ["L3", "L1 + L4 + L5", "L2", "L7", "L4（+L6）"],
        mapping: { 0: 1, 1: 2, 2: 0, 3: 4, 4: 3 },
        explain: "口诀：①忘(L1+L4+L5) ②说(L2) ③停(L3) ④小(L4+L6) ⑤编(L7)。这就是整门课的题眼。",
      },
      {
        type: "choice",
        q: "看到一个新 agent product，从产品视角能问的'账'主要是？",
        options: [
          "延迟/成本/边界",
          "用户数/日活/留存",
          "Bug 数/P99/可用性",
        ],
        answer: 0,
        explain: "产品化三笔账：延迟、成本、边界。这是 L8 给的解剖刀。",
      },
      {
        type: "tf",
        q: "现在你已经装上'harness 解剖视角'：看到任意 agent 都能逐层盘问它怎么补五大缺陷。",
        options: ["对,我可以开始解剖了", "错,还需要更多学习"],
        answer: 0,
        explain: "恭喜通关！9 层练完，你手里的不是零散知识点，而是一张能解剖任何 agent、也能指导你亲手造一个的全景地图。",
      },
    ],
  },
];
