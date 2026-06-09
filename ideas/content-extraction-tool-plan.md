# Content Extraction Tool — 自动化工具设计计划书

> 创建日期：2026-06-01
> 状态：设计完成，待实现
>
> **关联文档**：[content-extraction.md](./content-extraction.md) — 本工具的操作手册，记录了所有来源的提取细节、异常处理方案和工具选型依据。本计划书是对该手册的工程化落地设计。

---

## 一、背景与目标

### 问题

[content-extraction.md](./content-extraction.md) 已经把工作流梳理清楚了，但每次使用仍需要：
- 手动选择和运行不同来源的提取脚本
- 记忆各平台的参数差异（Cookie 路径、字幕语言、反爬延迟）
- 手动触发 Wiki 构建
- 没有统一的状态追踪（哪些已处理、哪些失败、哪些待转录）

### 目标

把「给我一个 URL 或路径，给你一个可查询的 Wiki」这件事自动化，减少人工干预到接近零。

---

## 二、架构决策

### 三层分离

工作流分为三层，每层职责严格独立：

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: 提取层（content-extract CLI）               │
│  ─ 纯机械操作：调 shell 命令、下文件、转格式            │
│  ─ 不需要 LLM，不消耗 token                           │
│  ─ 可独立运行、可测试、可 cron 调度                    │
└──────────────────────────┬──────────────────────────┘
                           ↓ ./raw/*.md
┌──────────────────────────┴──────────────────────────┐
│  Layer 2: 编排层（Claude Code Skill）                 │
│  ─ 需要理解内容、做判断、跨文件整合                    │
│  ─ 调用 Layer 1 的 CLI，决定何时构建/更新 Wiki         │
│  ─ 处理异常（转录失败、内容过大、质量差）               │
└──────────────────────────┬──────────────────────────┘
                           ↓ ./wiki/*.md
┌──────────────────────────┴──────────────────────────┐
│  Layer 3: 消费层（Obsidian）                          │
│  ─ 人类阅读层：Graph view · Dataview · 移动端          │
│  ─ 不参与生产，只消费 wiki/ 内容                       │
│  ─ 负责可视化关联、发现知识 gap、日常浏览               │
└─────────────────────────────────────────────────────┘
```

**核心原则**：`raw/` 是 LLM 的原料，人不读。人只通过 Obsidian 读 `wiki/`。

### 为什么不是其他方案

| 方案 | 排除原因 |
|------|---------|
| 纯 Skill | Skill 只是提示词，无法执行 yt-dlp/Whisper 等外部进程 |
| MCP Server | 比 CLI 重——需要维护 server 进程、注册工具 schema。提取是批处理，不需要实时调用 |
| 纯 Workflow Agent | 提取层仍要跑外部进程，音频转录时间不确定，放在 agent 内等待不合适 |
| 单一 Python 脚本 | 无法被 Claude Code Skill 统一调度，缺乏状态管理 |

**最终方案：Python CLI（提取） + Claude Code Skill（编排） + Textual TUI（默认 UI） + Streamlit（可选 Web UI）**

### UI 选型决策：为什么是 Textual 而非 Streamlit 作为默认

| 维度 | Textual TUI | Streamlit Web UI |
|------|-------------|-----------------|
| 启动速度 | 即时（< 100ms） | 需要启动浏览器 + 服务进程（2-5s） |
| 进程管理 | 无（随终端关闭） | 需要管理后台服务 |
| 实时日志 | 原生支持（RichLog 组件） | 需要 polling 或 WebSocket |
| 键盘操作 | 完整支持 | 依赖浏览器 |
| 离线可用 | 是 | 需要本地服务 |
| 视觉体验 | 终端内全屏 | 浏览器页面，更现代 |
| 适合场景 | 日常主力使用 | 分享给他人、非终端用户 |

**决策**：`content-extract`（无参数）默认启动 Textual TUI；`content-extract --web` 启动 Streamlit。两者共用同一套 `extractors/` 代码，UI 只是调用层。

---

## 三、目录结构

```
content-extract/                     ← 独立 Python 项目（可 pip install -e . 安装）
│
├── pyproject.toml                   ← 项目配置，定义 content-extract 命令入口
├── .gitignore                       ← 排除 cookies、raw/、audio/、chroma-db/ 等
├── requirements.txt                 ← 分组依赖（core / video / ebook / rag / ui）
│
├── content_extract/                 ← 主包
│   ├── __init__.py
│   ├── cli.py                       ← Click CLI 入口：无参数 → 启动 TUI；有参数 → 直接执行
│   ├── registry.py                  ← 已处理 URL/路径的增量登记（.processed.json）
│   ├── config.py                    ← 读取 ~/.content-extract/config.toml（Cookie 路径等）
│   │
│   ├── extractors/                  ← 各来源提取器（CLI 和 UI 共用）
│   │   ├── base.py                  ← 基类：定义 extract(source) → Path 接口
│   │   ├── web.py                   ← crawl4ai / Jina Reader
│   │   ├── bilibili.py              ← yt-dlp + Cookie + SRT 清洗
│   │   ├── douyin.py                ← yt-dlp + Whisper（带限速）
│   │   ├── ebook.py                 ← EPUB（ebooklib）+ PDF（pymupdf4llm）
│   │   ├── code.py                  ← 三档模式（overview/priority/full）；overview 输出架构层识别+推荐阅读路径+git热力图；priority/full 额外输出 __imports.json（模块依赖关系图）
│   │   ├── local_docs.py            ← Markdown wikilink 解析 + Office 转换
│   │   ├── github.py                ← gh CLI：overview/issues/releases/discussions/wiki
│   │   └── article.py               ← 单篇文章：Jina Reader + Playwright 降级 + 平台专项
│   │
│   ├── transcribe/
│   │   ├── whisper_local.py         ← faster-whisper 封装
│   │   ├── whisper_api.py           ← OpenAI Whisper API 封装
│   │   └── queue.py                 ← 处理 needs_transcription.txt 队列
│   │
│   ├── utils/
│   │   ├── frontmatter.py           ← 写入统一 frontmatter（source/type/platform）
│   │   ├── clean.py                 ← 转录质量清洗（Claude Haiku）
│   │   └── pdf_detect.py            ← 判断扫描版 vs 文字型 PDF
│   │
│   └── ui/                          ← UI 层（调用 extractors/，不含业务逻辑）
│       ├── tui.py                   ← Textual TUI：无参数启动时的默认界面
│       └── web.py                   ← Streamlit Web UI：content-extract --web 启动
│
└── skill/
    └── SKILL.md                     ← Claude Code Skill 文件（编排层）
```

---

## 四、CLI / UI 接口设计

### 启动行为：无参数 vs 有参数

```bash
content-extract              # 无参数 → 启动 Textual TUI（全屏终端 UI）
content-extract --web        # 可选 → 启动 Streamlit 浏览器 UI
content-extract web <url>    # 有参数 → 直接执行，不启动 UI（与现有 CLI 完全一致）
```

**设计原则**：UI 只是调用层，所有业务逻辑在 `extractors/` 里，CLI 和 UI 共用同一套代码。

---

### TUI 界面设计（Textual）

```
┌─ Content Extract ─────────────────────────────────────────────────┐
│  [1] 添加来源   [2] 队列状态   [3] Wiki 管理   [4] 配置   [Q] 退出 │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌── 添加来源 ──────────────────────┐  ┌── 处理队列 ───────────┐  │
│  │  URL / 路径:                     │  │ ✓ bili__BVxxx.md      │  │
│  │  > _                             │  │ ✓ bili__BVyyy.md      │  │
│  │                                  │  │ ⟳ web__example.md     │  │
│  │  类型: [自动识别 ▾]              │  │ ✗ dy__yyy (失败)      │  │
│  │                                  │  │ ⏳ needs_transcript   │  │
│  │  [提取]  [提取并更新 Wiki]        │  └──────────────────────┘  │
│  └──────────────────────────────────┘                             │
│                                                                   │
│  ┌── 实时日志 ─────────────────────────────────────────────────┐  │
│  │  [10:32:01] 正在提取: https://zhuanlan.zhihu.com/p/xxx       │  │
│  │  [10:32:04] ✓ 完成 → raw/article__zhihu-com__xxx.md         │  │
│  │  [10:32:04] 是否立即更新 Wiki? [Y/n]                         │  │
│  └─────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

**TUI 四个面板**：

| 面板 | 功能 |
|------|------|
| 添加来源 | 粘贴 URL 或路径，选择来源类型（可自动识别），一键提取 |
| 处理队列 | 实时展示已处理/进行中/失败/待转录的条目，支持重试失败项 |
| Wiki 管理 | 触发 Wiki 构建/更新，查看 `wiki/INDEX.md` 摘要，打开 Obsidian |
| 配置 | 查看和修改 `config.toml`（Cookie 路径、Whisper 模型等） |

---

### Web UI 界面设计（Streamlit，可选）

`content-extract --web` 启动，在 `http://localhost:8501` 打开：

```
侧边栏（导航）          主区域
─────────────────       ─────────────────────────────────────
📥 添加内容       →     URL/路径输入框
                        来源类型下拉（自动识别）
📋 队列状态       →     带进度条的任务列表，状态实时刷新
                        失败项展示错误原因 + 重试按钮

📚 Wiki 浏览      →     wiki/INDEX.md 内容展示
                        概念搜索框
                        「更新 Wiki」按钮

⚙️  配置          →     表单编辑 config.toml 各项
                        Cookie 文件状态检测（有效/失效提示）

📊 统计           →     内容源分布饼图（raw/ 前缀统计）
                        近 7 天提取量折线图
                        转录队列积压数
```

Web UI 适合：不习惯终端操作、需要在浏览器中操作、与他人分享工作状态时。

---

### 命令结构（有参数时，行为与纯 CLI 完全相同）

```bash
content-extract                          # 无参数 → 启动 Textual TUI
content-extract --web                    # 可选 → 启动 Streamlit Web UI
content-extract init                     # 初始化项目：生成 wiki/DASHBOARD.md、CLAUDE.md、.gitignore
content-extract <来源类型> <输入> [选项]
content-extract status                   # 查看处理队列状态
content-extract transcribe               # 处理 needs_transcription.txt 队列
content-extract clean                    # 批量清洗低质量转录文字
content-extract config                   # 查看/编辑配置
```

### 各来源类型命令

```bash
# 网页
content-extract web https://example.com/article
content-extract web https://example.com --crawl          # 整站爬取
content-extract web https://example.com --crawl --limit 100

# 视频（平台自动识别）
content-extract video https://www.bilibili.com/video/BVxxx
content-extract video https://space.bilibili.com/UID/video --limit 50
content-extract video https://www.douyin.com/user/xxx --limit 30 --min-duration 60

# 电子书
content-extract ebook ./books/                            # 整目录批量
content-extract ebook ./book.epub
content-extract ebook ./paper.pdf

# 本地代码
content-extract code ./my-project
content-extract code ./my-project --lang typescript       # 仅 TS 专项提取

# 本地文档
content-extract docs ./my-vault                           # Obsidian vault
content-extract docs ./documents                          # 含 .docx/.pptx

# GitHub 仓库
content-extract github OWNER/REPO                          # 全量（overview+issues+releases+discussions+wiki）
content-extract github OWNER/REPO --skip issues,wiki       # 跳过指定层（布尔排除，对应 extractor 参数）
content-extract github OWNER/REPO --code                   # 同时提取代码结构（较慢）
content-extract github OWNER/REPO --issue-limit 200        # 加大 Issues 拉取量
# 注：--skip 语法对应 extract_github_repo(issues=False, wiki=False) 参数，见操作手册 1.6 节

# 单篇网络文章（平台自动识别）
content-extract article https://zhuanlan.zhihu.com/p/xxxxxxxx
content-extract article https://mp.weixin.qq.com/s/xxxxxxxx  # 触发微信手动指引
content-extract article https://medium.com/@author/title
content-extract article --batch article_urls.txt              # 批量收藏

# 状态管理
content-extract status                                    # 显示队列状态
content-extract status --failed                           # 只看失败项
content-extract transcribe                                # 消费转录队列
content-extract transcribe --model large-v3 --device mps
```

### 全局选项

```bash
--output ./raw          # 输出目录（默认 ./raw）
--force                 # 忽略增量登记，强制重新处理
--dry-run               # 只打印将要执行的操作，不实际运行
--config ~/.content-extract/config.toml
```

### 统一输出格式

所有提取器输出到 `./raw/`，文件名格式：`{prefix}__{id}__{slug}.md`

frontmatter 格式统一（由 `utils/frontmatter.py` 写入）：

```yaml
---
source: https://original-url-or-path
type: web | video | ebook | code | local_doc | github | article
platform: bilibili | douyin | epub | pdf | wechat | toutiao | generic  # article/video/ebook 有
subtype: overview | issues | releases | discussions | wiki | code_structure  # 仅 github 有
extracted_at: 2026-06-01T10:30:00
content_hash: sha256前8位                                 # 用于增量去重
---
```

---

## 五、状态管理设计

### `.processed.json`（增量登记）

存放在输出目录下，记录每个已处理来源的状态：

```json
{
  "https://example.com/article": {
    "status": "done",
    "output_file": "web__example-com__article.md",
    "extracted_at": "2026-06-01T10:30:00",
    "content_hash": "a1b2c3d4"
  },
  "https://www.bilibili.com/video/BVxxx": {
    "status": "needs_transcription",
    "output_file": "bili__BVxxx__title.md",
    "extracted_at": "2026-06-01T10:31:00"
  },
  "https://www.douyin.com/video/yyy": {
    "status": "failed",
    "error": "音频下载失败：403",
    "extracted_at": "2026-06-01T10:32:00",
    "retry_count": 2
  }
}
```

### 状态流转

```
pending → extracting → done
                     → needs_transcription → transcribing → done
                     → failed (retry_count < 3) → pending
                     → failed (retry_count >= 3) → skipped（需人工处理）
```

---

## 六、配置文件设计

`~/.content-extract/config.toml`（全局）或 `./content-extract.toml`（项目级，优先）：

```toml
[cookies]
bilibili = "~/.content-extract/bilibili_cookies.txt"
douyin   = "~/.content-extract/douyin_cookies.txt"

[whisper]
# 默认值，可在运行时通过 --model / --device 覆盖
# 抖音建议 large-v3；M 系 Mac 建议 device=mps, compute_type=float16
model        = "medium"          # tiny / base / small / medium / large-v3
device       = "cpu"             # cpu / mps / cuda
compute_type = "int8"            # int8 / float16（mps/cuda 用 float16）

[douyin]
min_duration = 60          # 跳过短于此时长（秒）的视频
sleep_min    = 5           # 请求间隔最小秒数
sleep_max    = 12

[output]
dir = "./raw"

[clean]
enabled = true             # 是否自动触发转录质量清洗
model   = "claude-haiku-4-5-20251001"

[rag]
embedding_model = "BAAI/bge-small-zh-v1.5"   # 中文内容
chroma_dir      = "./chroma-db"
```

---

## 七、Skill 设计（编排层）

`skill/SKILL.md` 是 Claude Code Skill 文件，安装后通过 `/content-extract` 调用。

### Skill 的职责

Skill **不负责**提取（那是 CLI 的事），Skill 负责：

1. **识别用户意图** — 从用户输入判断来源类型
2. **调用 CLI** — 用 Bash 工具执行 `content-extract <type> <source>`
3. **等待 + 监控** — 检查输出文件是否出现，查看 status
4. **触发 Wiki 构建** — raw/ 有新文件后，按 CLAUDE.md 规则更新 wiki/
5. **异常处理** — 遇到 needs_transcription / failed 时，决策下一步

### Skill 核心逻辑（伪代码）

```
用户说：「帮我提取 https://... 的内容」

1. 判断类型（URL 特征识别）
   Bilibili → video bilibili
   douyin.com / 抖音 → video douyin
   github.com/OWNER/REPO → github（overview+issues+releases+discussions+wiki）
   mp.weixin.qq.com / weixin.qq.com → article (platform=wechat)
   toutiao.com / ixigua.com → article (platform=toutiao)
   其他单篇 URL → article (platform=generic)
   .epub/.pdf → ebook
   本地路径 → code 或 docs（看是否有 package.json / .md 文件）
   其他 URL → web

2. 执行：content-extract <type> <source> [--output ./raw]

3. 检查结果：content-extract status
   - done → 继续步骤 4
   - needs_transcription → 提示用户「有 N 个视频需要转录，运行 content-extract transcribe 处理，或现在执行？」
   - failed → 展示错误，建议解决方案（Cookie 失效？网络问题？）

4. 询问用户：「提取完成，是否现在更新 Wiki？」
   - 是 → 读取 ./raw/ 新增文件，按 CLAUDE.md 规则更新 ./wiki/
   - 否 → 结束，告知可以之后手动触发

5. Wiki 更新完成 → 展示更新了哪些概念页面

6. [仅代码工程触发] 困惑驱动第二轮（见 content-extraction.md 2.1B 节）
   询问用户：「是否要进行第二轮定向提取？我可以先列出我还不清楚的关键问题。」
   - 是 → 执行：列出 10 个「改代码必须知道但现在不知道」的问题
           → 用问题驱动定向 grep/glob
           → 将新文件加入 raw/，更新 Wiki
           → 重复直到 Claude 不再产生新问题
   - 否 → 结束
```

### Skill 文件结构（SKILL.md）

```markdown
---
name: content-extract
description: |
  内容提取与知识库构建。给定 URL 或本地路径，自动识别来源类型，
  调用 content-extract CLI 提取内容到 ./raw/，再更新 ./wiki/。
  触发词：「提取」「抓取」「帮我了解」「加入知识库」「content-extract」
---

# 使用说明
...（详细的 Skill 内容，参见第七节设计）
```

---

## 八、实现路线图

### Phase 0：脚手架（约 1 天）

目标：能跑起来，骨架完整，即使功能空着。

- [ ] 初始化 Python 项目（`pyproject.toml`、`click` CLI 框架）
- [ ] 实现 `registry.py`（`.processed.json` 读写）
- [ ] 实现 `config.py`（配置文件加载，支持全局 + 项目级）
- [ ] 实现 `utils/frontmatter.py`（统一 frontmatter 写入）
- [ ] `content-extract status` 命令可以运行
- [ ] `content-extract init` 命令：在当前目录初始化项目结构，生成 `wiki/DASHBOARD.md` 模板、`CLAUDE.md`、`.gitignore`
- [ ] `content-extract`（无参数）打印"TUI 即将上线"占位提示
- [ ] 创建 `skill/SKILL.md` 骨架
- [ ] 创建 `.gitignore`（cookies、raw/、audio/、chroma-db/）
- [ ] 在 `wiki/` 目录创建 `DASHBOARD.md` 模板（Dataview 查询：最近更新、孤立节点、未解答问题）

**验收标准**：`pip install -e .` 后 `content-extract --help` 正常显示所有命令；无参数运行不报错

---

### Phase 1：核心提取器（约 3 天）

目标：覆盖最高频场景（网页 + Bilibili），把 content-extraction.md 里的脚本迁移进来。

- [ ] `extractors/base.py` 基类接口
- [ ] `extractors/web.py`（crawl4ai，含增量去重）
- [ ] `extractors/bilibili.py`（yt-dlp + Cookie + SRT 去重行清洗）
- [ ] `transcribe/whisper_local.py`（faster-whisper 封装）
- [ ] `transcribe/queue.py`（消费 needs_transcription 队列）
- [ ] `content-extract web <url>` 端到端可用
- [ ] `content-extract video <bilibili url>` 端到端可用
- [ ] `content-extract transcribe` 可用

**验收标准**：给一个 Bilibili UP 主 URL，5 分钟内 `./raw/` 出现对应 `.md` 文件，frontmatter 格式正确

---

### Phase 2：补全提取器 + TUI（约 5 天）

目标：覆盖所有来源，同时上线 Textual TUI。

**Phase 2A：高复杂度提取器（约 2 天）**
- [ ] `extractors/douyin.py`（限速、Whisper 转录、质量过滤）
- [ ] `extractors/ebook.py`（EPUB + PDF，按页切分）
- [x] `extractors/code.py`（三档模式已实现：overview/priority/full；overview 含架构层识别、推荐阅读路径、git 信息；priority/full 含测试文件 > 类型定义 > 入口文件分层提取 + __imports.json 依赖图；见操作手册 3.3/3.7 节）

**Phase 2B：中等复杂度提取器（约 1.5 天）**
- [ ] `extractors/local_docs.py`（wikilink 解析 + Office 转换；注意 `office__` 前缀）
- [ ] `extractors/github.py`（gh CLI：overview/issues/releases/discussions/wiki/代码结构；`--skip` 参数对应 `issues=False` 等布尔参数，见 1.6 节）
- [ ] `extractors/article.py`（Jina Reader 通用 + Playwright 降级 + 微信/头条专项，见 1.7 节）
- [ ] `utils/clean.py`（Claude Haiku 转录质量清洗，含低质量过滤）
- [ ] `utils/pdf_detect.py`（扫描版 vs 文字型识别）

**Phase 2C：Textual TUI（约 1.5 天）**
- [ ] 安装 Textual（`pip install textual`）
- [ ] `ui/tui.py`：实现四面板布局（添加来源 / 处理队列 / Wiki 管理 / 配置）
- [ ] `cli.py` 无参数入口：检测是否有子命令参数，无则调用 `tui.launch()`
- [ ] TUI 内可显示实时日志（`textual` 的 `RichLog` 组件）
- [ ] TUI 内触发提取后更新队列面板状态
- [ ] TUI 的「打开 Obsidian」按钮：`open obsidian://open?vault=wiki` (macOS)

**验收标准**：
- `content-extract`（无参数）打开全屏 TUI
- `content-extract video <url>` 仍然直接在终端执行，不启动 TUI
- 所有来源类型在 TUI 里均可触发提取

---

### Phase 3：Skill 完整实现（约 1 天）

目标：Claude Code 中 `/content-extract` 可以端到端完成「提取 → 查询 Wiki」全流程。

- [ ] Skill 的来源类型自动识别逻辑
- [ ] Skill 调用 CLI 并解读 status 输出
- [ ] Skill 触发 Wiki 构建（调用 CLAUDE.md 规则）
- [ ] Skill 的异常处理对话分支（转录队列、失败项、内容过大）
- [ ] 安装说明（将 skill/ 目录链接到 `~/.claude/skills/`）

**验收标准**：
- 输入「帮我提取 https://space.bilibili.com/UID/video」
- Skill 自动识别为 Bilibili，调用 CLI，展示进度，完成后询问是否更新 Wiki
- 整个过程不需要手动输入任何命令参数

---

### Phase 4：可选增强（按需实现）

优先级从高到低，按实际使用需求决定是否做：

| 功能 | 描述 | 依赖 |
|------|------|------|
| RAG 集成 | `content-extract index` 命令，将 wiki/ 向量化到 ChromaDB | chromadb + sentence-transformers |
| Web UI（Streamlit） | `content-extract --web` 启动浏览器 UI，适合非终端用户 | streamlit |
| 说话人分离 | `--diarize` 选项，访谈/对话视频专用 | pyannote.audio + HuggingFace token |
| 定时调度 | `content-extract watch <url> --interval 1d` 定期重新提取 | cron / APScheduler |
| Plugin 打包 | 将 CLI + Skill 打包成 Claude Code Plugin 发布 | 待 Plugin 格式稳定后 |

---

## 九、关键设计决策记录

### 为什么不做成 MCP Server

MCP Server 的优势是 Claude 可以实时调用工具（类似 function calling）。但提取工作是**批处理**——抓一个 Bilibili UP 主的 50 个视频可能需要 30 分钟，期间不需要 Claude 做任何决策。MCP 适合「短操作 + 实时返回」，不适合这个场景。

CLI 的额外好处：可以直接在终端运行（不需要 Claude Code），可以加入 cron，可以被其他工具调用。

### 为什么 Skill 不直接内嵌提取逻辑

Skill 里可以写 Bash 工具调用，理论上能直接 `subprocess` 调 yt-dlp。但这样做：
- Skill 变成几百行，难以维护
- 没有状态管理（重试、队列、增量去重）
- 无法在 Claude Code 之外单独使用

Skill 的职责应该只是**编排**，不是执行。执行是 CLI 的事。

### 关于 frontmatter 的 content_hash

每个输出文件写入源内容的 SHA256 前 8 位。增量运行时：
- URL 已在 `.processed.json` 中 → 跳过
- URL 在登记中但 hash 变了 → 重新提取（内容更新）
- `--force` → 无视登记，强制重新提取

### 关于 Cookie 存储位置

Cookie 文件存在 `~/.content-extract/` 而不是项目目录，原因：
1. 不会被 .gitignore 遗漏（经常出现 .gitignore 配好但 Cookie 已经被提交的情况）
2. 多个项目共享同一份 Cookie，不需要每个项目单独导出
3. 路径在 config.toml 中显式配置，意图明确

### TUI 与 CLI 的无缝切换实现

`cli.py` 的入口逻辑：

```python
import click

@click.group(invoke_without_command=True)
@click.option("--web", is_flag=True, help="启动 Streamlit Web UI")
@click.pass_context
def main(ctx, web):
    if web:
        import subprocess
        from content_extract.ui.web import APP_PATH
        subprocess.run(["streamlit", "run", APP_PATH])
    elif ctx.invoked_subcommand is None:
        # 无子命令：启动 Textual TUI
        from content_extract.ui.tui import TUIApp
        TUIApp().run()
    # 有子命令时 Click 自动分发，不走上面两个分支

# 各子命令用 @main.command() 装饰器注册（不用 add_command）
@main.command("web")
@click.argument("url")
@click.option("--crawl", is_flag=True, help="整站爬取")
@click.option("--limit", default=200)
def web_cmd(url, crawl, limit):
    from content_extract.extractors.web import WebExtractor
    WebExtractor().extract(url, crawl=crawl, limit=limit)

@main.command("video")
@click.argument("url")
@click.option("--limit", default=50)
def video_cmd(url, limit):
    from content_extract.extractors import auto_detect_video
    auto_detect_video(url, limit=limit)

# github / article / ebook / code / docs 同理...
```

关键点：`invoke_without_command=True` 让 `@click.group` 在没有子命令时也执行 `main()`；子命令用 `@main.command()` 装饰器注册，不用 `add_command()`（两种方式等价，但装饰器方式更清晰）。注意 `web` 子命令名称和 `--web` 全局选项名称相同但不冲突——Click 先解析全局选项，再按位置参数匹配子命令名。

### UI 与 extractors 的解耦原则

TUI/Web UI 只做：
1. 收集用户输入（URL、路径、选项）
2. 调用 `extractors/<type>.extract(source, config)` 
3. 展示返回的 `Path` 和进度回调

UI 不包含任何提取逻辑。所有平台细节（Cookie 路径、SRT 清洗、Whisper 参数）都在 `extractors/` 里，CLI 和 UI 行为完全一致。

---

## 十、与 content-extraction.md 的关系

本计划书是 [content-extraction.md](./content-extraction.md) 的**工程化落地**。

- [content-extraction.md](./content-extraction.md) 是**操作手册**：记录了每种来源的提取细节、脚本逻辑、异常处理方案。实现时直接参考对应章节。
- 本文件是**设计文档**：记录架构决策、接口设计、实现路线图。

**对应关系**：

| 本计划书章节 | content-extraction.md 对应章节 |
|------------|-------------------------------|
| `extractors/web.py` | 1.1 技术博客 / 文档网站 |
| `extractors/bilibili.py` | 1.2 视频网站 → Bilibili |
| `extractors/douyin.py` | 1.2 视频网站 → 抖音 |
| `transcribe/whisper_local.py` | 1.2 视频网站 → Whisper 转录（通用兜底）|
| `extractors/ebook.py` | 1.3 电子书 |
| `extractors/code.py` | 1.4 本地代码工程 |
| `extractors/local_docs.py` | 1.5 本地文档工程 |
| `extractors/github.py` | 1.6 GitHub 仓库 |
| `extractors/article.py` | 1.7 单篇网络文章 |
| `utils/clean.py` | 3.2 字幕/转录质量差 |
| `utils/pdf_detect.py` | 3.4 PDF 扫描版 / 复杂排版 |
| `registry.py` | 爬取脚本的增量去重机制 |
| Skill 编排层 | Part 2 通用分析整理与检索 |
| Obsidian 消费层 | 2.5 Obsidian 集成 |
| `ui/tui.py` | 四、CLI/UI 接口设计 → TUI 界面设计 |
| `ui/web.py` | 四、CLI/UI 接口设计 → Web UI 界面设计 |

---

## 十一、Obsidian 集成层设计

### 定位

Obsidian 是 Layer 3（消费层），**不需要代码实现**，只需要：

1. 把 `./wiki/` 作为 vault 打开（一次性操作）
2. 在 `wiki/` 里放 `DASHBOARD.md`（Phase 0 任务，随项目脚手架一起生成）

### DASHBOARD.md 模板（Phase 0 随脚手架生成）

````markdown
# 知识库 Dashboard

## 最近更新的概念（过去 7 天）
```dataview
TABLE file.mtime AS "更新时间", sources AS "来源", related AS "关联"
FROM "concepts"
SORT file.mtime DESC
LIMIT 20
```

## 各来源内容量
```dataview
TABLE length(rows) AS "文件数"
FROM "by-source"
GROUP BY file.folder
```

## 待追问的问题（gap 清单）
```dataview
LIST
FROM "concepts"
WHERE contains(file.content, "未解答的问题")
SORT file.mtime DESC
LIMIT 30
```

## 孤立概念（无 related 连线）
```dataview
LIST
FROM "concepts"
WHERE !related
SORT file.name ASC
```
````

### 与 CLAUDE.md Schema 的对接点

`wiki/concepts/` 里的 frontmatter 字段直接被 Dataview 消费：

| frontmatter 字段 | Obsidian 中的作用 |
|-----------------|-----------------|
| `related: [[xxx]]` | Graph view 连线 + Dataview 过滤孤立节点 |
| `sources: [...]` | Dataview 展示来源溯源 |
| `last-updated:` | Dataview 排序最近更新 |

这些字段由 LLM 在 Wiki 构建时写入（见 CLAUDE.md 规则），人不需要手动维护。

### Gap 发现 → 修复 工作流

```
Obsidian Graph view 发现孤立节点
      ↓
DASHBOARD 「孤立概念」列表定位到具体文件
      ↓
Claude Code 指令：
"wiki/concepts/xxx.md 目前没有 related 关联，
 请阅读其内容，在现有 wiki/concepts/ 中找出相关概念，
 更新双方的 related 字段"
      ↓
Obsidian 自动刷新，节点出现连线
```

### 为什么不需要更多插件

Obsidian 有几百个插件，但这个工作流只需要 Dataview：

- **Wiki 组织**：LLM 负责，不需要 Obsidian 插件
- **标签管理**：frontmatter 里的 `type/platform` 字段已经是 Dataview 可查的 metadata
- **模板**：DASHBOARD.md 是静态文件，不需要模板插件
- **同步**：iCloud 或 Obsidian Sync 任选，不依赖第三方插件

唯一必装：**Dataview**。其余按需，但默认不装。

---

## 更新记录

| 日期 | 内容 |
|------|------|
| 2026-06-01 | 初始版本，基于 content-extraction.md 的工程化落地设计 |
| 2026-06-01 | GitHub 仓库升级为正式来源（1.6 节），更新 CLI 命令、frontmatter subtype 字段、Phase 2、Skill 识别逻辑、对应关系表 |
| 2026-06-01 | 新增单篇网络文章来源（1.7 节）：article.py 提取器、CLI 命令 content-extract article、Skill 识别逻辑（微信/头条/通用）、frontmatter platform 枚举、对应关系表 |
| 2026-06-01 | 架构从两层改为三层（加入 Layer 3 Obsidian 消费层），新增第十一章节（Obsidian 集成层设计：DASHBOARD.md 模板、frontmatter 对接点、gap 发现工作流、极简插件原则），Phase 0 补充 DASHBOARD.md 生成任务 |
| 2026-06-01 | 全文二次审查修订：GitHub `--only` 语法改为 `--skip`（与 extractor 布尔参数对齐）；Click 代码片段改为 `@main.command()` 装饰器方式，增加完整示例；Phase 2 拆分为 2A/2B/2C，时间估计调整为约 5 天；新增 `content-extract init` 命令（CLI 结构 + Phase 0）；对应关系表加 ui/tui.py、ui/web.py 条目 |
| 2026-06-06 | 更新 code.py 描述为测试优先分层（测试>接口>文档>入口>Git热力图）；Phase 2A code.py 任务描述同步；Skill 核心逻辑新增步骤6（代码工程触发困惑驱动第二轮，与操作手册 2.1B 节对齐）；目录结构 code.py 注释更新 |
| 2026-06-01 | 新增 UI 支持：架构升级（CLI+TUI+Web UI 三种入口），无参数启动 Textual TUI，--web 启动 Streamlit；目录结构新增 ui/ 模块；Phase 2 合并提取器补全+TUI；Phase 4 补 Web UI；九、新增 UI-CLI 无缝切换实现和解耦原则；对应关系表补 ui/tui.py、ui/web.py |
| 2026-06-07 | code.py 升级三档模式（overview/priority/full）：overview 新增架构层识别（_ARCH_LAYERS 目录名映射）、推荐阅读路径（5步，基于配置+入口+热力图）；priority/full 新增 __imports.json 生成（TS/JS/Python import 依赖图）；目录结构注释和 Phase 2A 任务条目同步更新；参考 Understand-Anything 和 agency-agents 思路 |

---

*下一步：确认实现路线图的优先级，从 Phase 0 开始。*
