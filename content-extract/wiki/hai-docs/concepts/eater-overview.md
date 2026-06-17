---
sources: [docs__eater__index.md, docs__eater__evaluation__process.md, docs__eater__tools__code-generation.md, docs__eater__tools__quality-assurance.md, docs__eater__tools__pm-ux.md, docs__eater__tools__aiops-finops.md, docs__eater__radar__index.md]
related: [[hyperspace-ai-platform-overview]]
last-updated: 2026-06-15
---

## 核心定义

EATER（Expedited AI Tools Evaluation & Rollout）是 SAP Developer Experience 项目下的 AI 工具评估和发布流程，负责将第三方商业和开源开发 AI 工具系统化地从初始请求评估到全面上线，整个流程约 105 天。

## 关键细节

**EATER 的范围（4个能力领域）**

| 领域 | 说明 |
|------|------|
| Code Generation | AI 代码补全、生成、重构工具 |
| Quality Assurance | 自动化测试、bug 检测、质量验证工具 |
| PM & UX | 设计、原型、团队协作工具 |
| AIOps & FinOps | 系统监控、成本优化、AI 使用追踪 |

**超出 EATER 范围的内容**（会被拒绝）：
- AI Agents、Skills、Plugins、MCP Servers（归 SAP Central Agent & Skill Marketplace 管理）
- 嵌入 SAP 产品面向客户销售的 AI 能力
- 内部自研工具（非第三方商业/开源工具）

**4阶段评估流程**

```
提交请求 → 准入评估（2-4周）→ 非生产试用（15-30天）→ 生产试验（60-90天）→ 全面上线
```

| 阶段 | 时长 | 关键问题 | 通过标准 |
|------|------|---------|---------|
| Intake（准入） | 2-4周 | 这个工具值得评估吗？ | Go/No-Go 决策 |
| Non-Productive Trial | 15-30天 | 工具是否满足需求？ | 满意度 ≥ 3.5/5 |
| Productive Pilot | 60-90天 | 与现有工具相比如何？ | 综合评分 ≥ 4.0/5 + 全部审批 |
| Generally Available | 持续 | 如何规模化？ | — |

**Productive Pilot 阶段特点**

- 500–1000 名用户参与，使用付费企业许可证在真实开发工作上测试
- 需通过完整合规审查：Security Engineering、SADD、TPRM、Enterprise Architecture

**三维评估框架**

- **Desirability（可取性）**：用户需求、与现有工具的差异化、业务对齐
- **Feasibility（可行性）**：企业架构合规、GTLC 法律合规、供应商合规、安全要求
- **Viability（可行商业性）**：许可成本、ROI、开源工具的成本优势

**已通过，生产可用（Code Generation 领域）**

| 工具 | 说明 |
|------|------|
| Claude Code | 通过 Hyperspace LLM Proxy 使用 |
| Cline | VS Code 扩展，通过 Proxy 使用 |
| GitHub Copilot | 通过 Software Hub 申请 |
| OpenCode | 开源，通过 Proxy 使用 |
| OpenSpec | SDD 框架，通过 Proxy 使用 |
| Pi | 轻量终端 AI Agent，通过 Proxy 使用 |
| Gemini CLI | Google 开源，通过 Proxy 使用 |
| SpecKit | SDD 工具集，通过 Proxy 使用 |
| Warp Terminal | AI 增强终端 |

**特别提醒**：Roo Code 已于 2026年5月15日停止维护（原团队转向 Roomote），正在评估 ZooCode 作为替代。

**当前进行中的 Pilot**

- **Cursor**：2026年3月-6月，约1000名参与者，许可证已分配完毕
- **Amazon Q Developer**：针对 ABAP 开发者（Eclipse IDE 支持）
- **AWS Kiro**：约50名用户，spec-driven 开发
- **Google Antigravity**：约100名用户，agent-first IDE

**代表性被拒绝案例（Code Generation 领域）**

| 工具 | 拒绝原因 |
|------|---------|
| Kilo Code | GTLC 因安全问题未批准（建议用 OpenCode 替代） |
| Windsurf | 用户反馈评分不佳 |
| Gemini Code Assist Enterprise | 用户反馈评分不佳 |
| Claude Code JetBrains Plugin | 超出 EATER 范围（属于 Agent/Skill/Plugin 类别） |
| MemPalace | 超出 EATER 范围（MCP 服务器类别） |

**参与方式**

- 提交评估请求：TPAITR Jira（需先检查 Software Hub 和 Tech Radar 避免重复）
- 参与试用/Pilot：联系对应 LoB SPOC
- 了解进展：每两周周五下午3点（CET）公开论坛 + CPA EATER Workstream

## 不同文档的补充

- `evaluation/process.md` 包含 mermaid 流程图和涉及方（SGSC、GTLC、GPO、SAM、TPRM、EA 等）的职责时间表
- `tools/code-generation.md` 是最完整的工具状态清单，含详细的拒绝原因
- EATER 技术雷达可视化展示所有评估工具（80+ 工具）

## 未解答的问题

- 2026年下半年预计有哪些新工具进入评估？
- Cursor 的 Pilot 结果和 GA 计划是什么？
- ZooCode 是否会正式进入 EATER 评估？
