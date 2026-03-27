# AI Workspace

个人 AI 学习与实验工作空间，包含 Claude Code 使用手册和 8 种 Agent 架构脚手架项目。

---

## 目录索引

- [1. 工程概览](#1-工程概览)
- [2. 文档资料](#2-文档资料)
  - [2.1 Claude Code 使用手册](#21-claude-code-使用手册)
- [3. agent-start — Agent 架构脚手架合集](#3-agent-start--agent-架构脚手架合集)
  - [3.1 合集总览 README](#31-合集总览-readme)
  - [3.2 01-react-agent](#32-01-react-agent)
  - [3.3 02-plan-execute-agent](#33-02-plan-execute-agent)
  - [3.4 03-multi-agent](#34-03-multi-agent)
  - [3.5 04-reflexion-agent](#35-04-reflexion-agent)
  - [3.6 05-rag-agent](#36-05-rag-agent)
  - [3.7 06-tool-use-agent](#37-06-tool-use-agent)
  - [3.8 07-judge-critic-agent](#38-07-judge-critic-agent)
  - [3.9 08-memory-agent](#39-08-memory-agent)
- [4. 快速开始](#4-快速开始)
- [5. 技术栈](#5-技术栈)

---

## 1. 工程概览

```
ai_workspace/
├── ReadMe.md                          # 本文件：工程总览与目录索引
├── claude-code-手册.md                 # Claude Code CLI 完整使用手册
└── agent-start/                       # 8 种 Agent 架构 TypeScript 脚手架
    ├── README.md                      # 合集总览与架构速查表
    ├── 01-react-agent/                # ReAct：推理+行动循环
    ├── 02-plan-execute-agent/         # Plan-and-Execute：计划分解与并行执行
    ├── 03-multi-agent/                # Multi-Agent：多智能体指挥官模式
    ├── 04-reflexion-agent/            # Reflexion：自我反思与迭代改进
    ├── 05-rag-agent/                  # RAG：检索增强生成
    ├── 06-tool-use-agent/             # Tool-Use：工具调用与函数执行
    ├── 07-judge-critic-agent/         # Judge/Critic：LLM 评判者
    └── 08-memory-agent/               # Memory-Augmented：记忆增强
```

---

## 2. 文档资料

### 2.1 Claude Code 使用手册

**路径：** [claude-code-手册.md](claude-code-手册.md)

Claude Code CLI 的完整中文参考手册（2026 年 3 月版），适用于 VSCode 扩展及终端环境。涵盖：

- 斜杠命令（Slash Commands）速查
- 快捷键与交互操作
- MCP（Model Context Protocol）服务器配置
- Hooks 自动化配置
- 权限与安全设置
- Agent 模式使用指南
- 常见问题与调试技巧

---

## 3. agent-start — Agent 架构脚手架合集

**路径：** [agent-start/](agent-start/)

8 种主流 AI Agent 架构的 TypeScript 脚手架，均基于 `@anthropic-ai/sdk`，开箱即用。

每个子项目结构一致：
```
<项目名>/
├── README.md        # 架构说明、工作原理、特点、适用场景、参考资料
├── package.json     # 依赖配置（@anthropic-ai/sdk + tsx + typescript）
├── tsconfig.json    # TypeScript 编译配置
├── .env.example     # 环境变量模板（需填入 ANTHROPIC_API_KEY）
└── src/
    └── index.ts     # 完整可运行的 Agent 实现
```

### 3.1 合集总览 README

**路径：** [agent-start/README.md](agent-start/README.md)

包含 8 种架构的速查对比表（复杂度 / 成本 / 可解释性 / 可扩展性 / 最适合场景）及统一的快速启动说明。

---

### 3.2 01-react-agent

**路径：** [agent-start/01-react-agent/](agent-start/01-react-agent/)

| 文件 | 说明 |
|------|------|
| [README.md](agent-start/01-react-agent/README.md) | 架构图、工作原理、特点对比、适用场景、参考论文链接 |
| [src/index.ts](agent-start/01-react-agent/src/index.ts) | ReAct 循环实现：思考链 → 工具调用（search / calculator）→ 观察 → 最终答案 |

**架构：** `思考 → 行动（工具调用）→ 观察 → 思考 → ... → 最终答案`
**适用：** 复杂多步推理、需审计追踪的场景（金融/法律/合规）

---

### 3.3 02-plan-execute-agent

**路径：** [agent-start/02-plan-execute-agent/](agent-start/02-plan-execute-agent/)

| 文件 | 说明 |
|------|------|
| [README.md](agent-start/02-plan-execute-agent/README.md) | 两阶段架构说明、子任务 DAG 概念、Token 效率分析 |
| [src/index.ts](agent-start/02-plan-execute-agent/src/index.ts) | 规划器（Opus）→ 并发执行器（Haiku）→ 聚合器（Opus）三阶段实现 |

**架构：** `目标 → [规划器] 子任务列表 → [执行器] 并发执行 → [聚合器] 最终结果`
**适用：** 大规模数据处理、研究报告生成、批量内容创作

---

### 3.4 03-multi-agent

**路径：** [agent-start/03-multi-agent/](agent-start/03-multi-agent/)

| 文件 | 说明 |
|------|------|
| [README.md](agent-start/03-multi-agent/README.md) | Supervisor 模式架构图、4 个专家 Agent 职责划分、协调机制说明 |
| [src/index.ts](agent-start/03-multi-agent/src/index.ts) | Supervisor 路由 → 并发调用研究/分析/代码/写作专家 Agent → 聚合最终答案 |

**架构：** `用户请求 → [Supervisor 路由] → [专家 Agent 并发] → [Supervisor 聚合]`
**适用：** 多领域复合问题、企业知识管理、多维度内容审核

---

### 3.5 04-reflexion-agent

**路径：** [agent-start/04-reflexion-agent/](agent-start/04-reflexion-agent/)

| 文件 | 说明 |
|------|------|
| [README.md](agent-start/04-reflexion-agent/README.md) | 自我评估循环机制、最大迭代次数控制、质量门槛配置说明 |
| [src/index.ts](agent-start/04-reflexion-agent/src/index.ts) | 生成 → 评估（打分+问题列表）→ 改进，循环至通过或达最大迭代次数 |

**架构：** `初始生成 → [评估器] 打分 → 未通过 → [改进器] 优化 → 循环`
**适用：** 代码审查、学术写作、翻译润色、营销文案打磨

---

### 3.6 05-rag-agent

**路径：** [agent-start/05-rag-agent/](agent-start/05-rag-agent/)

| 文件 | 说明 |
|------|------|
| [README.md](agent-start/05-rag-agent/README.md) | RAG 两阶段（索引/检索）原理、向量数据库选型建议、幻觉抑制机制 |
| [src/index.ts](agent-start/05-rag-agent/src/index.ts) | 内存知识库 + 关键词检索（可替换为向量搜索）+ 带来源引用的答案生成 |

**架构：** `问题 → [检索器] Top-K 文档 → [LLM] 基于证据生成答案（含来源标注）`
**适用：** 企业知识库问答、法律/医学文献检索、客服机器人

---

### 3.7 06-tool-use-agent

**路径：** [agent-start/06-tool-use-agent/](agent-start/06-tool-use-agent/)

| 文件 | 说明 |
|------|------|
| [README.md](agent-start/06-tool-use-agent/README.md) | 工具定义 Schema 规范、工具调用循环机制、错误处理最佳实践 |
| [src/index.ts](agent-start/06-tool-use-agent/src/index.ts) | 3 个模拟工具（天气/时间/数据库查询）+ 自动工具调度循环 |

**架构：** `LLM 推理 → 识别工具需求 → 调用工具 → 获取结果 → 继续推理`
**适用：** API 集成自动化、数据库自然语言查询、DevOps 自动化、IoT 控制

---

### 3.8 07-judge-critic-agent

**路径：** [agent-start/07-judge-critic-agent/](agent-start/07-judge-critic-agent/)

| 文件 | 说明 |
|------|------|
| [README.md](agent-start/07-judge-critic-agent/README.md) | 评分细则（Rubric）设计、5 维度评分体系、批量并发评估说明 |
| [src/index.ts](agent-start/07-judge-critic-agent/src/index.ts) | 5 维度结构化打分（准确性/完整性/清晰度/相关性/可读性）+ 批量并发评估 + 摘要报告 |

**架构：** `待评估内容 → [Judge LLM] 按 Rubric 评分 → 通过/修改/拒绝决策`
**适用：** 内容发布质量门控、代码自动审查、A/B 测试对比、RAG 答案验证

---

### 3.9 08-memory-agent

**路径：** [agent-start/08-memory-agent/](agent-start/08-memory-agent/)

| 文件 | 说明 |
|------|------|
| [README.md](agent-start/08-memory-agent/README.md) | 三层记忆模型（语义/情节/程序）、记忆衰减机制、隐私安全注意事项 |
| [src/index.ts](agent-start/08-memory-agent/src/index.ts) | MemoryStore 类（检索+存储+衰减）+ 对话中自动提取新记忆 + 多轮对话演示 |

**架构：** `对话 → [记忆检索] 相关历史 → [LLM] 个性化响应 → [记忆提取] 存储新信息`
**适用：** 个人 AI 助手、长期学习辅导、对话式推荐、CRM 智能助手

---

## 4. 快速开始

所有 Agent 脚手架运行方式相同：

```bash
# 1. 进入任意子项目
cd agent-start/01-react-agent

# 2. 安装依赖
npm install

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env，填入：ANTHROPIC_API_KEY=sk-ant-...

# 4. 运行
npm run dev
```

---

## 5. 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| TypeScript | 5.x | 主开发语言 |
| Node.js | 18+ | 运行时 |
| @anthropic-ai/sdk | ^0.39.0 | Claude API 调用 |
| tsx | ^4.19.0 | TypeScript 直接运行（无需编译） |
| dotenv | ^16.4.5 | 环境变量管理 |

**使用模型：**
- `claude-opus-4-6` — 规划、评估、聚合（高推理能力）
- `claude-sonnet-4-6` — 执行、生成（平衡性能与成本）
- `claude-haiku-4-5-20251001` — 轻量任务（记忆提取、子任务执行）
