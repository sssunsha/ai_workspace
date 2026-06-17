---
source: hai-docs/eater/tools
type: local_doc
last-updated: 2026-06-15
---

# AI 工具评估报告（EATER）

> 来源：Hyperspace AI 内部文档 `eater/tools/`
> 更新日期：2026-06-15
> 说明：本报告涵盖 EATER（Enterprise AI Tool Evaluation & Release）流程评估过的所有工具，按类别和状态整理，方便选型参考。

---

## 快速选型指南

**我是开发者，想用 AI 写代码** → 优先看 [Code Generation ✅ GA](#code-generation--代码生成)：Claude Code、GitHub Copilot、Cline、OpenCode

**我是 PM 或 UX 设计师** → 看 [UX & PM ✅ GA](#ux--pm-工具)：Aha!、Dovetail、Microsoft Copilot Chat

**我需要自动化测试** → 看 [QA ✅ GA](#quality-assurance--质量保证)：DiffBlue Cover、Tricentis

**我需要监控/可观测性** → 看 [AIOps ✅ GA](#aiops--finops)：Dynatrace Davis AI、Langfuse、CrewAI

**我想了解哪些工具被拒绝了及原因** → 看各分类的 [❌ Rejected 区](#rejected-工具汇总)

---

## 状态说明

| 图标 | 状态 | 含义 |
|------|------|------|
| ✅ | Generally Available | 可直接使用，通过全部评审 |
| 🔄 | Productive Pilot / Limited Rollout | 试点中，名额有限，可申请候补 |
| 🧪 | Non-Productive Trial | 仅供非生产环境试用，尚在评估 |
| 🚀 | Planned | 计划中，尚未开始试点 |
| ❌ | Rejected | 已拒绝，附拒绝原因 |

---

## Code Generation — 代码生成

### ✅ Generally Available（可直接使用）

| 工具 | 简介 | 使用要求 |
|------|------|---------|
| **Claude Code** | Anthropic 的 AI 编程助手，高级推理能力 | **必须**通过 Hyperspace LLM Proxy |
| **Cline** | 可编辑文件、运行命令、使用浏览器工具的 AI 助手 | **必须**通过 Hyperspace LLM Proxy |
| **GitHub Copilot** | AI 结对编程，写代码更快 | 通过 Software Hub 申请 |
| **OpenCode** | 终端 AI 编程助手（开源） | **必须**通过 Hyperspace LLM Proxy |
| **OpenSpec** | Spec-Driven Development 插件，让 AI 编程更可预测 | **必须**通过 Hyperspace LLM Proxy |
| **Pi** | 极简开源终端 AI 编程 Agent | **必须**通过 Hyperspace LLM Proxy |
| **Gemini CLI** | Google 开源 AI Agent，终端内使用 Gemini 能力 | **必须**通过 Hyperspace LLM Proxy |
| **SpecKit** | Spec-Driven Development 工具集（开源） | **必须**通过 Hyperspace LLM Proxy |
| **Warp Terminal** | AI 增强终端，内置命令建议和解释 | 直接使用 |
| ~~**Roo Code**~~ | ⚠️ **已于 2026-05-15 停止维护**，正评估 ZooCode 替代 | — |

### 🔄 Productive Pilot（试点进行中）

| 工具 | 试点信息 | 参与方式 |
|------|---------|---------|
| **Cursor** | 2026-03-12 至 06-12，约 1000 人参与（Business AI、CPIT、CS&D、oCTO、P&E） | 名额已满，联系 LoB SPOC 加候补名单 |

### 🧪 Non-Productive Trial（非生产试用）

| 工具 | 简介 | 状态备注 |
|------|------|---------|
| **Codex CLI** | OpenAI 开源终端 AI 编程 Agent | 正在评审生产使用资质 |
| **Goose** | 开源 on-machine AI Agent，可从头构建项目 | 需通过 LLM Proxy |
| **Vibe Kanban** | AI 看板工具（开源） | 试用中 |

### 🧪 Non-Productive Trial — Commercial（商业产品试用）

| 工具 | 试点信息 | 参与方式 |
|------|---------|---------|
| **Amazon Q Developer** | 至 2026-05 中，限 ABAP 开发者（Eclipse IDE） | 联系 LoB SPOC |
| **AWS Kiro** | 至 2026-05 中，~50 人参与（P&E + Business AI） | 联系 LoB SPOC |
| **Google Antigravity** | 至 2026-05-26，~100 人参与 | 联系 LoB SPOC |
| **IBM Bob** | 计划 2026-06 中旬 至 07 中旬 | 联系 LoB SPOC |

---

## UX & PM 工具

### ✅ Generally Available

| 工具 | 简介 | 使用要求 / 备注 |
|------|------|--------------|
| **Aha!** | Jira 工作流的 AI 知识发现和自动化平台 | Software Hub 申请；⚠️ 目前仅限项目成员使用 |
| **Dovetail** | AI 客户反馈洞察平台（整合通话、工单、调研） | Software Hub 申请；⚠️ 仅限 UX Insights Hub |
| **FigmaMake / Code** | Figma AI 代码生成（设计转代码） | Software Hub 申请；⚠️ 生成代码不可直接用于生产系统，不能输入 SAP 数据 |
| **Microsoft Copilot Chat** | M365 对话式 AI，通用生产力和信息检索 | 使用 SAP 凭据登录 m365copilot.com；完整 M365 Copilot 仍在候补名单 |

### 🔄 Limited Rollout

| 工具 | 简介 | 参与方式 |
|------|------|---------|
| **Perplexity** | AI 研究和答案引擎 | 仅限提名用户，由 CPIT AI CoE 管理（非 EATER） |

### 🔄 Productive Pilot

| 工具 | 试点信息 | 参与方式 |
|------|---------|---------|
| **Lovable** | AI 用户体验优化平台 | 2026-03-26 至 07-16，600 名 PM & UX 设计师参与；联系 LoB SPOC 候补 |
| **Vercel V0** | AI UI 生成工具（React 组件从文本描述生成） | 2026-06-01 至 09-01，~500 人参与（BTP、CX、HCM 等多团队）；联系 LoB SPOC 候补 |

---

## Quality Assurance — 质量保证

### ✅ Generally Available

| 工具 | 简介 | 使用要求 |
|------|------|---------|
| **DiffBlue Cover** | AI 自动生成单元测试套件 | Software Hub 申请 |
| **Tricentis** | 企业级持续测试平台（功能、性能、端到端自动化） | Software Hub 申请 |

### 🧪 Non-Productive Trial

| 工具 | 试点信息 | 参与方式 |
|------|---------|---------|
| **SauceLabs AI** | 云端测试平台，AI 增强测试自动化和分析 | ~50 人，至 2026-06-13；Software Hub 申请，加入 PoC 团队 |

---

## AIOps & FinOps

### ✅ Generally Available

| 工具 | 简介 | 使用要求 |
|------|------|---------|
| **Dynatrace Davis AI** | AI APM，智能根因分析 | Software Hub 申请 |
| **CrewAI** | 开源多 Agent 编排框架 | Software Hub 申请 |
| **Langfuse** | 开源 LLM 可观测性和分析平台 | Software Hub 申请 |

### 🧪 Non-Productive Trial（开源）

| 工具 | 简介 |
|------|------|
| **LlamaIndex** | 开源 LLM 数据框架，支持自定义数据源的索引和检索 |
| **N8N** | 可视化工作流自动化平台（需通过 LLM Proxy） |
| **OpenLLMetry** | OpenTelemetry 扩展，为 LLM 应用提供 tracing 和 metrics |

### 🚀 Planned

| 工具 | 简介 |
|------|------|
| **AWS DevOps Agent** | Amazon AI DevOps 自动化 Agent（构建、测试、部署） |
| **Azure SRE Agent** | Microsoft AI SRE Agent（自动故障检测和修复） |
| **Weights & Biases** | ML 实验追踪和模型管理平台 |

---

## Other Tools — 其他

### ✅ Generally Available

| 工具 | 简介 | 使用要求 |
|------|------|---------|
| **OpenWebUI** | 开源 LLM 本地 Web 界面 | 需通过 LLM Proxy；Software Hub 申请 |

### 🚀 Planned

| 工具 | 简介 | 详情 |
|------|------|------|
| **DX Developer Intelligence Platform** | 开发者生产力度量平台（整合 GitHub、Jira + 问卷数据） | 45天，计划 Q2 2026，Business Network + HCM 部分团队 |

---

## ❌ Rejected 工具汇总

### Code Generation 拒绝工具

| 工具 | 拒绝原因 |
|------|---------|
| AgentGateway | 不在 EATER 范围（属于 Agent/MCP 治理，归 CPA workstream） |
| Bmad Method | 不在 EATER 范围 |
| Claude Code JetBrains Plugin | 不在 EATER 范围（IDE 插件归 CPA workstream） |
| Claude Code Security | 仍处于 preview 模式，等企业版发布后重新评估 |
| claude-devtools | 不具备企业就绪度（社区支持不足） |
| Claude Managed Agents | Beta 阶段，正式 GA 后重新评估 |
| Claw Code | 不具备企业就绪度 |
| Cmux | 无企业版 |
| CocoIndex | 不具备企业就绪度 |
| Code Assistant | SAP 内部开源项目，不在 EATER 范围 |
| cx | 不具备企业就绪度 |
| Entire | 尚不具备企业就绪度 |
| Gemini Code Assist Enterprise | 基于用户试用反馈拒绝 |
| GSD / GSD 2 | OpenSpec 和 SpecKit 已是批准的 SDD 框架替代品 |
| JetBrains AI | LoB 不再推进测试 |
| Kilo Code | GTLC 未批准（安全问题），建议使用 OpenCode |
| MemPalace | 不在 EATER 范围（MCP 服务器归 CPA workstream） |
| on.auto | 不具备企业就绪度 |
| OpenChamber | 不在 EATER 范围（AI Agent 编排平台） |
| OpenClaw | 存在高危安全漏洞，建议使用 Claude Code 或 Cline |
| Pixel-Agents | 无有效业务案例 |
| Ruflo (Claude-Flow) | LoB 不再推进；MCP 服务器存在安全隐患（未使用 Hyperspace MCP Registry） |
| SuperClaude | 不在 EATER 范围 |
| Theia IDE | 已有多个 IDE-first AI 助手获批 |
| Windsurf | 基于用户试用反馈拒绝 |

### UX & PM 拒绝工具

| 工具 | 拒绝原因 |
|------|---------|
| Base44 | 基于用户试用反馈拒绝 |
| Bolt.new | 基于用户试用反馈拒绝 |
| ChatPRD | 基于用户试用反馈拒绝 |
| Claude Code PowerPoint & Excel Plugin | 不在 EATER 范围（归 CPA workstream） |
| Figma Console MCP | MCP 服务器不在 EATER 范围，需走 MCP Registry 流程 |
| Frontitude | 高风险安全问题（用户和访问管理） |
| Google Stitch | 仍在 beta，需企业版才能开展试点 |
| kapa.ai | 不在 EATER 范围（inbound 场景） |
| Listen Labs | Dovetail 是已批准的替代工具 |
| Replit | 基于用户试用反馈拒绝 |
| SubFrame | 基于用户试用反馈拒绝 |
| Supernova | 基于用户试用反馈拒绝 |
| wonder.design | 无企业版 |

### QA 拒绝工具

| 工具 | 拒绝原因 |
|------|---------|
| Evinced（chatbot/debugger/unit tester） | 基于用户试用反馈拒绝 |
| Evinced（mobile/accessibility） | 基于用户试用反馈拒绝 |
| Qodo | Hyperspace PR Bot 是替代工具；LoB 不再推进 |
| TestMu AI (LambdaTest) | 成本高、迁移成本高；SauceLabs AI 是替代评估方向 |

### AIOps 拒绝工具

| 工具 | 拒绝原因 |
|------|---------|
| Arize | 基于用户试用反馈拒绝 |
| Helicone | 基于用户试用反馈拒绝 |
| Freeplay | 基于用户试用反馈拒绝 |
| LlamaParse | 与 LlamaIndex 开源版重复 |
| LLaMA-Factory | 最多只能批准用于中国，其他场景需直接对齐 GTLC |
| TruEra | 被 SAP 竞争对手 Snowflake 收购 |

---

## 关键洞察

1. **所有 AI 编程工具（开源类）必须通过 Hyperspace LLM Proxy** — Claude Code、Cline、OpenCode、Pi、Gemini CLI 等均有此要求，这是 GTLC 合规的强制要求。

2. **Roo Code 已停止维护**（2026-05-15），ZooCode 正在评估中，尚不可用。现有 Roo Code 用户建议迁移到 Cline 或 Claude Code。

3. **被拒绝工具的两大主因**：
   - **不在 EATER 范围**（Agent/MCP/Plugin 治理归 CPA workstream）
   - **基于用户试用反馈**（Windsurf、Base44、Bolt.new 等均如此，说明实际体验不符合预期）

4. **商业 AI IDE 竞争格局**：Cursor 在 Pilot 中（1000人），Gemini Code Assist Enterprise 已被拒绝（用户反馈差），JetBrains AI 被拒（LoB 不再推进）。GitHub Copilot 是唯一商业 IDE 助手目前 GA。

5. **Spec-Driven Development 赛道**：OpenSpec 和 SpecKit 均已 GA，GSD/GSD2 因此被拒绝，赛道收敛明显。
