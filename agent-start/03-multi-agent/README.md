# Multi-Agent（多智能体/指挥官模式）

## 架构说明

Multi-Agent 架构由一个 **Supervisor（指挥官）** 和多个**专业子 Agent** 组成。Supervisor 负责理解用户意图、路由任务到最合适的专家 Agent，并聚合各 Agent 的输出为最终结果。

```
用户请求 → [Supervisor] 路由决策
                ↓
    ┌──────────┬────────────┬──────────┐
[研究Agent] [分析Agent] [代码Agent] [写作Agent]
    └──────────┴────────────┴──────────┘
                ↓
         [Supervisor] 聚合结果 → 最终响应
```

### 核心组件

```
03-multi-agent/
├── src/
│   ├── index.ts              # 入口
│   ├── supervisor.ts         # 指挥官：路由 + 聚合
│   ├── agents/
│   │   ├── research.ts       # 研究专家 Agent
│   │   ├── analysis.ts       # 分析专家 Agent
│   │   ├── coding.ts         # 代码专家 Agent
│   │   └── writing.ts        # 写作专家 Agent
│   ├── registry.ts           # Agent 注册与管理
│   └── types.ts              # AgentCapability 等类型
├── package.json
├── tsconfig.json
└── .env.example
```

## 工作原理

1. Supervisor 接收用户请求，分析所需专业领域
2. 路由到一个或多个专业 Agent（支持并行调用）
3. 各专业 Agent 在各自领域生成回答
4. Supervisor 聚合所有结果，生成统一最终答案

## 特点

| 项目 | 描述 |
|------|------|
| 专业化程度 | ⭐⭐⭐⭐⭐ 每个 Agent 深耕一个领域 |
| 可扩展性 | ⭐⭐⭐⭐⭐ 随时添加新专家 Agent |
| 协调复杂度 | 高（需要精心设计路由逻辑） |
| 并发能力 | ✅ 多 Agent 并行执行 |

## 适用场景

- **多领域复合问题**（同时需要研究+分析+代码）
- **客服系统**（FAQ Agent + 工单 Agent + 升级 Agent）
- **企业知识管理**平台
- **内容审核**（多维度：合规+质量+安全）

## 快速开始

```bash
npm install
cp .env.example .env
npm run dev
```

## 参考资料

- [Multi-Agent Systems Overview](https://docs.anthropic.com/en/docs/build-with-claude/agents)
- [Supervisor Pattern in LangGraph](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/)
- [Anthropic 多 Agent 最佳实践](https://docs.anthropic.com/en/docs/build-with-claude/agents#multi-agent-considerations)
- [AutoGen Multi-Agent Framework](https://microsoft.github.io/autogen/)
