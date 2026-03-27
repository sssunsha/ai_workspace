# Agent Start — 8 种 Agent 架构脚手架

本目录包含 8 种主流 AI Agent 架构的 TypeScript 脚手架项目，基于 [Anthropic SDK](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)。

## 目录结构

```
agent-start/
├── 01-react-agent/          # ReAct：推理+行动循环
├── 02-plan-execute-agent/   # Plan-and-Execute：计划分解与并行执行
├── 03-multi-agent/          # Multi-Agent：多智能体指挥官模式
├── 04-reflexion-agent/      # Reflexion：自我反思与迭代改进
├── 05-rag-agent/            # RAG：检索增强生成
├── 06-tool-use-agent/       # Tool-Use：工具调用与函数执行
├── 07-judge-critic-agent/   # Judge/Critic：LLM 评判者
└── 08-memory-agent/         # Memory-Augmented：记忆增强
```

## 架构速查

| # | 架构 | 核心特点 | 最适合场景 |
|---|------|---------|------------|
| 01 | ReAct | 显式推理链，可解释性极强 | 复杂推理/审计追踪 |
| 02 | Plan-Execute | 计划分解，支持并行 | 大规模数据处理 |
| 03 | Multi-Agent | 专家分工，模块化 | 多领域复合问题 |
| 04 | Reflexion | 自我评估，迭代改进 | 内容质量提升 |
| 05 | RAG | 检索增强，降低幻觉 | 企业知识库问答 |
| 06 | Tool-Use | 外部系统集成 | API 自动化 |
| 07 | Judge/Critic | 结构化质量评估 | 内容审核/评分 |
| 08 | Memory | 跨会话持久记忆 | 个人助手 |

## 快速开始

每个子项目均为独立 Node.js 项目，运行方式相同：

```bash
# 进入任意子项目
cd 01-react-agent

# 安装依赖
npm install

# 配置 API Key
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY=sk-ant-...

# 运行
npm run dev
```

## 技术栈

- **运行时**：Node.js 18+
- **语言**：TypeScript 5
- **AI SDK**：`@anthropic-ai/sdk`
- **模型**：claude-opus-4-6（规划/评估）、claude-sonnet-4-6（执行）、claude-haiku-4-5（轻量任务）
