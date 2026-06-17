# content-extract Skill（知识获取）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个 Claude Code Skill，通过自然语言触发，覆盖 content-extract 工作流的分析整理层（scan / build / query / compare / gap / second-pass），支持「知识获取」别名唤醒。

**Architecture:**
Skill 是纯提示词文件（SKILL.md），安装到 `~/.claude/skills/content-extract/`。内部维护一张意图路由表，将自然语言映射到六个功能模块；每个模块包含内容类型检测逻辑和对应的 wiki 构建/查询策略。Skill 不执行任何提取操作（那是 CLI 的工作），只通过 Claude Code 的 Read/Edit/Bash 工具操作 `raw/` 和 `wiki/`。

**Tech Stack:** Claude Code Skill（Markdown frontmatter + 提示词）；项目路径固定为 `/Users/I340818/Documents/ai_workspace/content-extract/`

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `~/.claude/skills/content-extract/SKILL.md` | 创建 | Skill 主文件：frontmatter + 路由表 + 六策略 + 通用规则 |
| `/Users/I340818/Documents/ai_workspace/content-extract/CLAUDE.md` | 创建 | 极简项目结构声明，Claude Code 启动时自动加载 |

---

## Task 1: 创建 CLAUDE.md（项目结构声明）

**Files:**
- Create: `/Users/I340818/Documents/ai_workspace/content-extract/CLAUDE.md`

这个文件让 Claude Code 在任何目录下启动时都知道这个项目的目录结构，是 Skill 正确工作的前提。

- [ ] **Step 1: 创建 CLAUDE.md**

内容如下：

```markdown
# content-extract 知识库项目

## 固定路径
项目根目录：/Users/I340818/Documents/ai_workspace/content-extract/

## 目录结构
- `raw/`：原始内容（由 content-extract TUI/CLI 生成，人不直接读）
  - `raw/<来源名>/`：每个来源一个子目录
  - `raw/topics/<topic名>/`：Topic 学习模式的主题目录
  - 文件名前缀含义：
    - `bili__`：Bilibili 视频转录
    - `web__`：网页爬取
    - `article__`：单篇文章（微信/头条/知乎等）
    - `epub__` / `pdf__`：电子书
    - `code__`：代码工程提取结果
    - `github__`：GitHub 仓库提取结果
    - `local__`：Topic 模式本地文件引用
- `wiki/`：结构化知识库（由 Claude Code 整理生成）
  - `wiki/concepts/`：核心概念页面
  - `wiki/by-source/`：按来源分类的摘要
  - `wiki/topics/<topic名>/`：Topic 学习模式的 wiki
  - `wiki/INDEX.md`：全局索引
- `wiki/changelog.md`：wiki 变更历史

## frontmatter 字段说明
每个 raw/ 文件包含：source / type / platform / extracted_at / content_hash
Topic 模式额外字段：topic（所属主题）/ topic_role（角色）

## 使用方式
分析和构建 wiki 时，调用 `/content-extract` Skill（别名：知识获取）。
```

- [ ] **Step 2: 验证文件创建成功**

```bash
cat /Users/I340818/Documents/ai_workspace/content-extract/CLAUDE.md
```

Expected: 文件内容正常输出

- [ ] **Step 3: Commit**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add CLAUDE.md
git commit -m "feat: 新增 CLAUDE.md，声明项目结构供 Skill 使用"
```

---

## Task 2: 创建 Skill 目录结构

**Files:**
- Create dir: `~/.claude/skills/content-extract/`
- Create: `~/.claude/skills/content-extract/SKILL.md`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p ~/.claude/skills/content-extract
```

- [ ] **Step 2: 验证目录存在**

```bash
ls ~/.claude/skills/ | grep content-extract
```

Expected: `content-extract`

---

## Task 3: 编写 Skill frontmatter 和触发配置

**Files:**
- Modify: `~/.claude/skills/content-extract/SKILL.md`（从空文件开始写）

- [ ] **Step 1: 写入 frontmatter**

```markdown
---
name: content-extract
description: |
  知识获取与整理助手。管理 raw/ 原始内容和 wiki/ 知识库的全套分析工作流。

  触发词（以下任意一种均可激活）：
  - 直接调用：「知识获取」「/content-extract」
  - 扫描状态：「有什么内容」「看看 raw 里有什么」「现在状态怎么样」
  - 构建 wiki：「帮我整理」「构建知识库」「更新 wiki」「建 wiki」
  - 查询内容：「帮我查」「问一下」「什么是」「wiki 里有没有」
  - 对比分析：「对比」「比较」「有什么不同」「两个来源」
  - 发现盲区：「盲区」「缺什么」「还差什么」「知识 gap」
  - 第二轮挖掘：「还不清楚」「第二轮」「再挖深一点」「second pass」
  - 学习路径：「学习路径」「从哪里开始」「我想学 XX」「怎么学」
---
```

- [ ] **Step 2: 验证 frontmatter 写入**

```bash
head -25 ~/.claude/skills/content-extract/SKILL.md
```

Expected: frontmatter 内容正常显示

---

## Task 4: 编写项目路径声明和意图路由表

**Files:**
- Modify: `~/.claude/skills/content-extract/SKILL.md`（追加内容）

- [ ] **Step 1: 追加项目路径和路由表**

在 frontmatter 之后追加：

```markdown
# 知识获取（content-extract Skill）

## 项目固定路径

所有操作基于：`/Users/I340818/Documents/ai_workspace/content-extract/`
- `raw/`：原始内容输入层
- `wiki/`：结构化知识输出层
- `CLAUDE.md`：项目结构声明

---

## 意图路由

收到用户请求后，先判断意图，再执行对应模块：

| 用户说了什么 | 识别意图 | 执行模块 |
|------------|---------|---------|
| 「有什么」「看看」「现在状态」「raw 里有什么」 | 扫描 | → [SCAN] |
| 「整理」「建 wiki」「构建」「更新 wiki」 | 构建 | → [BUILD] |
| 「查」「问」「什么是」「怎么」「wiki 里有没有」 | 查询 | → [QUERY] |
| 「对比」「比较」「有什么不同」「两个来源」 | 对比 | → [COMPARE] |
| 「盲区」「缺什么」「还差什么」「知识 gap」 | 盲区 | → [GAP] |
| 「还不清楚」「第二轮」「再挖深一点」 | 二轮 | → [SECOND-PASS] |
| 「学习路径」「我想学」「从哪开始」 | 学习 | → [TOPIC-QUERY] |

**内容类型自动检测**（在 BUILD / QUERY 模块执行前运行）：

扫描 `raw/` 子目录文件名前缀，识别内容类型：
- `bili__` / `dy__` → 视频转录 → 策略A
- `web__` / `article__` → 网页文章 → 策略B
- `epub__` / `pdf__` → 电子书 → 策略C
- `code__` → 代码工程 → 策略D（含 SECOND-PASS）
- `github__` → GitHub 仓库 → 策略E
- `raw/topics/<name>/` → Topic 学习模式 → 策略F

混合多种类型时：同类型先整合 → 再做跨类型关联。

---
```

---

## Task 5: 编写 SCAN 和 BUILD 模块

**Files:**
- Modify: `~/.claude/skills/content-extract/SKILL.md`（追加）

- [ ] **Step 1: 追加 SCAN 模块**

```markdown
## [SCAN] 扫描当前状态

**执行步骤：**
1. 列出 `raw/` 所有子目录，统计每个目录的 .md 文件数量
2. 识别各子目录的内容类型（按文件名前缀）
3. 检查 `wiki/` 是否存在，有多少 concepts/ 页面
4. 检查各子目录的 `.processed.json`，有无 needs_transcription / failed 状态
5. 输出状态报告，格式如下：

```
📦 raw/ 内容概览
├── 刘伯涛财富圈-B站/     56 个文件 [视频转录] ✓ wiki 已构建
├── 无忌心法学-B站/        96 个文件 [视频转录] ✗ wiki 未构建
├── feelgoodpal-com__zh__blog/ 1633 个文件 [网页文章] ✗ wiki 未构建
├── spartacus/             92 个文件 [代码工程] ✗ wiki 未构建
└── topics/
    └── （无主题目录）

📚 wiki/ 状态
└── （wiki 尚未构建）

💡 建议：说「帮我整理刘伯涛的内容」开始构建 wiki
```

---

## [BUILD] 构建或增量更新 wiki

**执行步骤：**

1. **确定目标来源**：用户是否指定了特定来源？未指定则处理所有未构建的来源。
2. **检测内容类型**：按文件名前缀路由到对应策略（A-F）
3. **上下文大小检查**：目标目录文件总大小 > 500KB → 自动分批（每批 20-30 个文件）
4. **执行策略**：按策略A-F的规则构建 wiki
5. **增量模式**：若 wiki/concepts/ 已存在 → 只更新受影响页面，不重建

**分批构建指令模板：**
```
读取 raw/<来源>/ 下第 1-20 个文件，
按照以下规则建立 wiki/concepts/ 初始骨架：[对应策略规则]
```
```
继续读取第 21-40 个文件，补充和更新 wiki/concepts/。
已有的页面直接修改，不重建。
```

**wiki 基础目录结构：**
```
wiki/
├── INDEX.md          （概念索引 + 来源分布）
├── concepts/         （核心概念页面）
├── by-source/        （按来源分类摘要）
└── changelog.md      （变更记录）
```

**每个概念页面格式（wiki/concepts/CONCEPT.md）：**
```yaml
---
sources: [文件名列表]
related: [[concept-a]], [[concept-b]]
last-updated: YYYY-MM-DD
---
```
```markdown
## 核心定义
（1-3 句话）

## 关键细节
（具体数据、案例、代码片段）

## 不同来源的视角
（同一概念在不同来源的表述差异）

## 未解答的问题
（整理时仍不清楚的地方）
```

---
```

---

## Task 6: 编写六条内容策略（策略A-F）

**Files:**
- Modify: `~/.claude/skills/content-extract/SKILL.md`（追加）

- [ ] **Step 1: 追加策略A-D**

```markdown
## 内容策略

### 策略A：视频转录（bili__ / dy__）

**核心原则：** 重复出现 3 次以上的观点才建独立 concepts/ 页面。

**构建规则：**
- 概念按三类组织子目录：理念类（无时效）/ 方法论类（注明适用条件）/ 案例类（标注日期）
- 口语谐音词统一处理：「谷票/谷市」→「股票/股市」
- 相互矛盾的观点记录在 INDEX.md 底部「冲突记录」区
- sources 字段区分不同 UP 主：`bili__刘伯涛__xxx.md`

**第一步推荐查询：**
```
读取所有 bili__*.md 的标题和 frontmatter，
统计每个核心概念出现在多少个视频中，按频次排序列出 Top 15。
这些是最值得建 wiki 页面的概念。
```

---

### 策略B：网页文章（web__ / article__）

**核心原则：** 按核心观点组织，不按文章组织。

**构建规则：**
- 同一观点在多篇文章出现 → 合并为一个 concepts/ 页面，注明来源数量
- 整站爬取（多页）→ 先建 by-source/ 导图，再提取跨文章概念
- 单篇文章 → 直接归入相关 concepts/ 页面，不单独建文件
- platform 字段区分来源：wechat / toutiao / generic

**第一步推荐查询：**
```
读取所有 article__*.md 和 web__*.md 的 frontmatter，
按 platform 分类统计数量，列出 Top 10 高频主题关键词。
```

---

### 策略C：电子书（epub__ / pdf__）

**核心原则：** 按核心论点组织，不按章节组织。

**两阶段读取策略（节省上下文）：**
- 第一阶段：只读 `__toc.md` + 第一章（前言）+ 最后 1-2 章（结语）
  → 建立全书论点框架
- 第二阶段：按用户具体问题，定向读对应章节（通过 chapter_title frontmatter 定位）

**四种书型对应规则：**
- 技术手册：按功能/概念分类，不按章节
- 商业/投资书：区分「原则（无步骤）」和「操作（有具体步骤）」，标注 `is_actionable`
- 学术著作：保留「局限性」字段，记录结论的适用边界
- 叙事/案例集：按规律/模式提炼，不按故事顺序

**第一步推荐查询：**
```
读取 epub__*__toc.md（目录结构文件），
用一句话说明这本书的核心主张，
列出全书 5-8 个核心论点。
```

---

### 策略D：代码工程（code__）

**核心原则：** 理解架构和设计意图，不记录代码行。

**构建层次（按优先级）：**
1. 读 `code__*__overview.md` → 建整体架构框架
2. 读测试文件提取结果 → 建「系统契约」页面（系统对外承诺的行为）
3. 读接口/类型定义 → 补充「公开 API」页面
4. 读 `code__*__git_history.md`（如存在）→ 标注高频变更的复杂区域
5. 执行 SECOND-PASS → 暴露盲区

**wiki 组织（4个核心页面）：**
- `架构总览.md`：模块划分、数据流向、关键依赖
- `系统契约.md`：测试文件揭示的行为承诺
- `公开API.md`：对外暴露的接口和类型
- `复杂区域.md`：git 热力图标出的高频变更文件

**第一步推荐查询：**
```
读取 raw/<工程名>/code__*__overview.md，
用三个层次回答：
1. 一句话：这个工程是什么
2. 五分钟：主要模块、数据流向、核心文件
3. 深度：各模块职责、模块间关系
只陈述文件中有的事实，不推断。
```

---
```

- [ ] **Step 2: 追加策略E-F**

```markdown
### 策略E：GitHub 仓库（github__）

**核心原则：** Issues 的设计讨论信息密度 > README。

**文件类型与用途：**
- `__overview.md`：先读，建整体认知框架
- `__releases.md`：演进时间线，单独建一个「演进历史」页面
- `__issues__*.md`：设计决策和已知问题，信息密度最高
- `__discussions.md`：社区最佳实践
- `__wiki__*.md`：深度文档（如存在）

**四种使用场景对应查询：**
- 快速了解工具：只读 overview + releases
  ```
  这个工具的核心能力、典型使用场景和主要限制是什么？
  ```
- 评估是否引入：读 releases + issues（关注 breaking changes 和 bug 模式）
  ```
  这个库的维护活跃度、breaking change 频率、主要 bug 类型如何？
  ```
- 学习最佳实践：读 issues + discussions
  ```
  社区最常见的 3 类使用问题是什么？给出的最佳实践有哪些？
  ```
- 深度研究实现：全量 + 代码结构
  ```
  代码架构怎么组织？核心模块职责是什么？如何扩展？
  ```

---

### 策略F：Topic 学习模式（raw/topics/<name>/）

**核心原则：** 目标是「我怎么学会这个主题」，不是「这些资料说了什么」。

**wiki 固定结构（4个文件）：**
```
wiki/topics/<topic名>/
├── roadmap.md      推荐学习路径（按 topic_role 排序）
├── concepts/       核心概念（跨来源整合）
├── sources.md      各来源的定位说明
└── gaps.md         当前资料的知识盲区
```

**构建步骤：**
1. 读所有文件的 frontmatter，统计 topic_role 分布
2. 先建 roadmap.md（推荐学习顺序：入门概述→核心方法论→深度参考→代码实例）
3. 跨来源提取核心概念，建 concepts/
4. 建 sources.md（每个资料的定位说明）
5. 建 gaps.md（当前资料缺少哪些 topic_role 类型）

**topic_role 置信度权重（高→低）：**
代码实例 > 核心方法论 > 深度参考 > 案例研究 > 入门概述 > 工具介绍 > 个人笔记

**第一步推荐查询：**
```
读取 raw/topics/<topic>/ 下所有文件的 frontmatter（不读正文），
统计各 topic_role 数量，
告诉我这个学习集合的覆盖情况和明显缺口。
```

---
```

---

## Task 7: 编写 QUERY、COMPARE、GAP、SECOND-PASS 模块

**Files:**
- Modify: `~/.claude/skills/content-extract/SKILL.md`（追加）

- [ ] **Step 1: 追加查询和分析模块**

```markdown
## [QUERY] 查询 wiki

**执行步骤：**
1. 读取 `wiki/INDEX.md`（如存在）了解概念分布
2. 在 `wiki/concepts/` 中找到相关页面
3. 基于页面内容回答用户问题
4. 如 wiki 尚未构建，提示用户先执行 BUILD

**常用查询模板：**

概念查询：
```
根据 wiki/INDEX.md，找出和「[主题]」相关的所有概念，
按相关度排序，并从对应的 concepts/ 页面提炼要点。
```

学习路径：
```
我想了解「[概念X]」，从 wiki 里找出所有相关内容，
给我一个从基础到深入的阅读路径（附对应来源文件）。
```

操作性建议提取：
```
从 wiki 里找出所有「is_actionable: true」的概念，
只给我有具体操作步骤的建议，原则性说法排除。
```

观点一致性检查：
```
从 wiki 里找出 sources 包含多个来源的概念，
哪些概念的不同来源表述有明显差异？
```

---

## [COMPARE] 跨来源对比分析

**执行步骤：**
1. 识别用户想对比的来源（两个 UP 主 / 书 vs 视频 / 多本书）
2. 读取相关 wiki/concepts/ 页面的「不同来源的视角」字段
3. 生成对比报告

**对比报告结构：**
```markdown
## 一致的核心观点（置信度最高）
- [观点]（来源：A + B）

## 互补的观点（各有侧重）
- A 的视角：[...]
- B 的视角：[...]

## 明显矛盾（需要你自己判断）
- A 说：[...]（来源：文件名）
- B 说：[...]（来源：文件名）
```

**可信度权重参考（从高到低）：**
代码/测试 > 官方文档/技术规范 > 技术博客 > 视频/音频转录

---

## [GAP] 发现知识盲区

**执行步骤：**
1. 读取 `wiki/INDEX.md` 和所有 `wiki/concepts/` 文件
2. 检测三类盲区：

**盲区类型A：未解答的问题**
```
找出所有 concepts/ 页面中「未解答的问题」字段不为空的概念，
按重要性排序，列出 Top 5。
```

**盲区类型B：孤立概念（无 related 连线）**
```
找出没有 related 字段或 related 为空的概念页面，
这些是知识图谱中的孤立节点，
建议：找到它们与已有概念的关联并补充。
```

**盲区类型C：低置信度概念**
```
找出 sources 字段只有 1 个来源的概念，
标记为「低置信度」，这些需要更多来源验证。
```

**Topic 模式专属盲区检测：**
```
读取 raw/topics/<topic>/ 下所有文件的 topic_role 分布，
当前缺少哪些角色类型（入门概述/核心方法论/代码实例等）？
建议接下来收集哪类资料？
```

---

## [SECOND-PASS] 困惑驱动第二轮（代码工程专用）

**适用场景：** 代码工程 wiki 初步构建后，暴露剩余盲区。

**执行步骤：**
1. 读取当前 `wiki/concepts/` 所有文件
2. 输出「改代码必须知道但现在仍不清楚」的问题清单

**输出格式：**
```
以下是我还不清楚的关键问题（请根据这些问题补充 raw/ 里的对应文件）：

1. [问题] → 可能在哪里找到答案：[目录/文件类型/关键词]
2. [问题] → 可能在哪里找到答案：[目录/文件类型/关键词]
...（最多 10 条）
```

**用户收到清单后的操作：**
1. 在项目目录里用 grep/glob 找到对应文件
2. 用 `content-extract code ./my-project --mode priority` 补充提取
3. 说「继续整理」→ Skill 执行 BUILD --incremental 更新 wiki
4. 重复直到问题不再产生新问题（或所有问题都是「需要运行才能知道」）

**停止条件：**
- 新生成的问题开始重复之前的 → 信息足够
- 剩余问题都是 runtime 才能回答的（日志、性能、实际行为）→ 进入运行时阶段

---

## [TOPIC-QUERY] 学习路径生成（Topic 模式）

**执行步骤：**
1. 确认用户指定的 topic 名称（或询问）
2. 读取 `wiki/topics/<topic>/roadmap.md`（如存在）
3. 读取 `raw/topics/<topic>/` 下所有文件的 frontmatter

**学习路径查询模板：**
```
读取 raw/topics/<topic>/ 下所有文件的 topic_role 字段，
按以下顺序生成推荐学习路径：
入门概述 → 核心方法论 → 深度参考 → 代码实例 → 案例研究

每个阶段列出：资料名称（文件名）、预计时间、完成后能理解什么。
```

**进度导航：**
```
用户说「我已经看完了 [资料A]」后：
找出下一个推荐资料，说明选择理由（它覆盖了什么当前知识的空白）。
```

---
```

---

## Task 8: 编写通用规则和范例参考

**Files:**
- Modify: `~/.claude/skills/content-extract/SKILL.md`（追加）

- [ ] **Step 1: 追加通用规则**

```markdown
## 通用规则

### 上下文大小管理

raw/ 文件总大小估算：
- < 200KB → 一次性处理
- 200KB ~ 600KB → 分批（每批 20-30 个文件）
- > 600KB → 强制分批 + 建议先用 scan 了解结构

分批时：后续批次直接修改已有 concepts/ 页面，不重建。

### wiki 更新规则

新增 raw/ 文件后（增量更新）：
```
只读新增文件，找出受影响的 wiki/concepts/ 页面，
只更新这些页面，在 changelog.md 记录，
如有新概念添加到 INDEX.md。
不重建整个 wiki。
```

### 不知道 wiki 里有什么时

```
读取 wiki/INDEX.md，
按出现频次和关联数排序所有概念，
标出孤立节点（无 related 连线）。
```

### 概念质量清理

```
读取所有 wiki/concepts/ 文件，
找出哪些概念实际上是同一个东西的不同表述，
建议合并列表（不自动合并，等用户确认）。
```

---

## 使用范例速查

| 用户说的话 | 走的模块 | 简要说明 |
|-----------|---------|---------|
| `知识获取，现在有什么` | SCAN | 扫描 raw/ 状态报告 |
| `帮我整理刘伯涛的内容` | BUILD + 策略A | 构建视频 wiki |
| `散户最常犯什么错误` | QUERY | 查 wiki 回答 |
| `刘伯涛和无忌对比一下` | COMPARE | 跨来源对比报告 |
| `wiki 里还有什么盲区` | GAP | 三类盲区检测 |
| `代码还有什么不清楚的` | SECOND-PASS | 输出疑问清单 |
| `我想学量化投资，从哪开始` | TOPIC-QUERY | 生成学习路径 |
| `帮我看看这本书讲什么` | BUILD + 策略C | 两阶段电子书分析 |
| `这个 GitHub 库值得用吗` | BUILD + 策略E | 评估报告 |
| `继续整理` / `更新 wiki` | BUILD --incremental | 增量更新 |
```

- [ ] **Step 2: 验证完整 Skill 文件**

```bash
wc -l ~/.claude/skills/content-extract/SKILL.md
```

Expected: 300行以上

```bash
head -5 ~/.claude/skills/content-extract/SKILL.md
tail -5 ~/.claude/skills/content-extract/SKILL.md
```

Expected: frontmatter 开头，结尾是速查表

---

## Task 9: 验证 Skill 可被识别

- [ ] **Step 1: 检查 Skill 目录结构**

```bash
ls -la ~/.claude/skills/content-extract/
```

Expected:
```
SKILL.md
```

- [ ] **Step 2: 验证 frontmatter 格式正确**

```bash
python3 -c "
import re
content = open('/Users/I340818/.claude/skills/content-extract/SKILL.md').read()
fm = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
if fm:
    print('✓ frontmatter 格式正确')
    print(fm.group(1)[:200])
else:
    print('✗ frontmatter 格式错误')
"
```

Expected: `✓ frontmatter 格式正确` + 内容预览

- [ ] **Step 3: 测试 Skill 激活**

在 Claude Code 里输入：
```
知识获取，扫描一下现在有什么内容
```

Expected: Skill 激活，输出 raw/ 状态报告

- [ ] **Step 4: 最终 Commit**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add CLAUDE.md
git commit -m "docs: CLAUDE.md 声明项目结构（供 content-extract Skill 使用）"
```

---

## 自检清单

- [x] **Spec 覆盖**：6个功能模块全部有对应 Task（SCAN/BUILD/QUERY/COMPARE/GAP/SECOND-PASS）
- [x] **6条策略**：策略A-F 全部覆盖（视频/文章/电子书/代码/GitHub/Topic）
- [x] **自然语言触发**：frontmatter description 包含所有触发词和别名「知识获取」
- [x] **无占位符**：所有查询模板都有完整提示词文本
- [x] **固定路径**：项目路径在 CLAUDE.md 和 SKILL.md 中均明确声明
- [x] **增量更新**：BUILD 模块有明确的增量规则
- [x] **上下文管理**：有分批处理规则（200KB 阈值）
- [x] **SECOND-PASS**：有完整的停止条件和用户操作流程
