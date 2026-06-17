---
source: hai-docs/pull-request-bot
type: local_doc
last-updated: 2026-06-15
---

## 产品一句话描述

Hyperspace Pull Request Bot 是通过 slash 命令（`/summarize`、`/review`、`/ask`）在 GitHub PR 中提供 AI 驱动摘要、代码审查和问答服务的 GitHub App，由 Code Change Intelligence 团队开发。

## 核心功能列表

- **`/summarize`**：生成 PR 结构化摘要，含变更概述、影响分析、测试建议
- **`/review`**：AI 代码审查，覆盖安全、性能、最佳实践，含内联注释和 suggestion 块
- **`/ask <问题>`**：关于 PR 代码变更的交互式问答（支持整个 PR 或特定代码行）
- **Control Panel**：PR 中的快捷操作面板（需配置启用）
- **Sonar Fix**（Pilot）：SonarQube 发现问题的 AI 修复建议
- **Pipeline Fix**（Pilot）：CI/CD 流水线失败的 AI 诊断和修复建议
- **自动化触发**：PR 创建时自动生成摘要/审查（需配置）
- **组织级配置继承**：通过 `githubOrg>` 协议共享配置

## 文档覆盖范围

| 文档分类 | 文件数 | 主要内容 |
|---------|--------|---------|
| 产品概述/快速开始 | 2 | index.md、getting-started.md |
| 前置条件 | 4 | access-permissions、feature-availability、limitations、prerequisites |
| 功能详情 | 6 | ask、control-panel、delete-comments、pipeline-fix、review、sonar-fix、summarize |
| 高级配置 | 1 | advanced-configuration.md（含组织配置、文件排除、自定义 prompt） |
| 集成 | 4 | jira、github-issues、sonarqube、integrations/index |
| 帮助支持 | 4 | faq、troubleshooting、contact、includes（两个） |
| 架构/更新 | 2 | architecture、whats-new |
| 合计 | 25 | — |

## 关键配置/使用入口

**前提**：安装 Hyperspace Insights GitHub App 到组织或仓库

**基础命令**

```
/summarize                                          # 生成摘要
/summarize https://jira.tools.sap/browse/PROJ-123  # 附 Jira 上下文
/review                                             # 代码审查
/review Focus on security implications              # 指定审查重点
/ask What does this function do?                   # 问答
```

**配置文件**：`.hyperspace/pull_request_bot.json`

```json
{
  "$schema": "https://devops-insights-pr-bot.cfapps.eu10-004.hana.ondemand.com/schema/pull_request_bot.json",
  "features": {
    "summarize": { "auto_generate_summary": true },
    "review": { "auto_generate_review": false }
  }
}
```

**支持的 GitHub 实例**：github.tools.sap、github.wdf.sap.corp、github.concur.com、github.com

**PR 大小限制**：超过 300 个文件或 50,000 行变更时 bot 自动跳过
