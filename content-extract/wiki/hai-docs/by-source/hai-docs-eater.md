---
source: hai-docs/eater
type: local_doc
last-updated: 2026-06-15
---

## 产品一句话描述

EATER（Expedited AI Tools Evaluation & Rollout）是 SAP Developer Experience 计划中的 AI 开发工具评估和发布项目，通过 4 阶段约 105 天的系统化流程，将第三方 AI 工具从初始请求评估到全面上线，确保每个工具满足企业安全合规和质量标准。

## 核心功能列表

- **4阶段评估流程**：准入评估（2-4周）→ 非生产试用（15-30天）→ 生产试验（60-90天）→ 全面上线
- **Tech Radar 可视化**：展示 80+ 工具在各评估阶段的分布状态
- **工具目录**：按能力领域（Code Gen、QA、PM/UX、AIOps/FinOps）分类的工具状态清单
- **LoB SPOC 网络**：各业务部门有指定联络人（SPOC）负责协调评估参与
- **工具请求流程**：通过 TPAITR Jira 提交评估请求

## 文档覆盖范围

| 文档分类 | 文件数 | 主要内容 |
|---------|--------|---------|
| 产品概述 | 1 | index.md |
| 评估流程 | 1 | evaluation/process.md |
| 工具目录 | 4 | code-generation、quality-assurance、pm-ux、aiops-finops |
| Tech Radar | 1 | radar/index.md |
| 帮助支持 | 2 | faq、support |
| 合计 | 10 | — |

## 关键配置/使用入口

**提交工具评估请求**

TPAITR Jira：`https://jira.tools.sap/secure/RapidBoard.jspa?projectKey=TPAITR&rapidView=58751`

提交前必须检查：
1. Software Hub 是否已有该工具
2. TPAITR Jira 是否已有请求
3. Tech Radar 是否已评估
4. 工具是否在 EATER 范围内（Code Gen/QA/PM/UX/AIOps/FinOps，非 Agent/Skill/MCP）

**参与试用/Pilot**：联系对应 LoB SPOC，表达参与意向

**信息获取渠道**：每两周周五 15:00 CET 公开论坛

**当前生产可用工具**（通过 LLM Proxy 使用）：Claude Code、Cline、OpenCode、OpenSpec、Pi、Gemini CLI、SpecKit、Roo Code（已停止维护）

**当前 Pilot 工具**（2026年中）：Cursor（1000名参与者，名额已满）
