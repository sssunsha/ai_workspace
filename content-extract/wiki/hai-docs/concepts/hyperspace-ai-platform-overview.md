---
sources: [docs__hyperspace-ai__index.md, docs__index.md, docs__team.md]
related: [[llm-proxy-architecture]], [[mcp-registry-overview]], [[pr-bot-overview]], [[eater-overview]]
last-updated: 2026-06-15
---

## 核心定义

Hyperspace AI 是 SAP 内部的综合性 AI 平台，为软件开发团队提供安全合规的生成式 AI 访问能力。平台由三个核心产品组成：LLM Proxy（统一 LLM 访问网关）、MCP Registry（MCP 服务器合规目录）、Pull Request Bot（AI 驱动的 PR 自动化）。

## 关键细节

**三大核心产品**

| 产品 | 职责 | 状态 |
|------|------|------|
| Hyperspace LLM Proxy | 统一访问 Anthropic/OpenAI/Google 等多家 LLM 提供商 | Early Release，生产可用 |
| MCP Registry | SAP 合规 MCP 服务器的中央目录 | Early Release |
| Pull Request Bot | AI 驱动的 PR 摘要、代码审查、Q&A | 可用 |

**另外还有 EATER 项目**（非平台产品，而是评估流程）：负责对第三方 AI 开发工具进行合规评估和发布管理。

**平台架构逻辑**

```
开发者工具（IDE/CLI/CI）
    ↓
LLM Proxy（安全访问 LLM 提供商）
MCP Registry（发现合规 MCP 服务器）
PR Bot（GitHub PR 自动化）
    ↓
SAP AI Core → LLM 提供商 / MCP 服务器 / GitHub
```

**共享基础设施**

- 统一身份认证与授权（SSO/OIDC）
- 集中式成本追踪与优化
- 统一监控与可观测性
- 一致的安全与合规控制

**团队结构**

- **Hyperspace AI Access 团队**：负责 LLM Proxy 开发（3名 AI Developer）
- **Hyperspace Agent Ecosystem 团队**：负责 MCP Registry & Skill Registry（4名 AI Developer）
- **EATER 团队**：评估工具合规，与 DX Team 协作
- **Code Change Intelligence 团队**：负责 PR Bot（4名 AI Developer + PM + UX Designer）

**使命**

通过提供统一合规的平台，消除技术障碍，加速 SAP 内部 AI 采用，让开发团队专注开发而非基础设施管理。

## 不同文档的补充

- `hyperspace-ai/index.md` 提供了完整的平台架构图（marchitecture.png），描述三大 initiative 如何协作
- `team.md` 显示 SAP IT MCP Gateway 尚未上线，目前 remote MCP server 仍采用直连方式
- 整体定位是"内部开发者使用的 AI 工具平台"，不包含嵌入 SAP 产品的 AI 能力

## 未解答的问题

- SAP IT MCP Gateway 预计上线时间？
- Skill Registry（与 MCP Registry 并列提到）具体功能是什么？
- LLM Proxy 的 General Availability 计划时间线？
