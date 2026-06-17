---
source: hai-docs/mcp-registry
type: local_doc
last-updated: 2026-06-15
---

## 产品一句话描述

Hyperspace MCP Registry 是 SAP 内部开发者的 MCP 服务器合规目录，提供经过 GTLC 安全审查的服务器集中发现和配置指引，解决 MCP 服务器的合规不确定性问题。

## 核心功能列表

- **合规服务器目录**：所有收录服务器已完成 SADD、安全扫描等合规评估
- **Portal UI 发现**：通过 Hyperspace Portal 浏览、搜索、查看服务器详情
- **配置生成**：每个服务器提供 "Set Up" 按钮，生成工具特定配置代码
- **GitHub Copilot Allowlist**：Registry API 作为 GitHub Copilot 企业策略中的 MCP allowlist
- **联合目录**：包含 SAP 内部自研服务器和经审批的开源服务器
- **服务器提交流程**：SAP 团队可通过 `hai-requests` 提交新服务器注册

## 文档覆盖范围

| 文档分类 | 文件数 | 主要内容 |
|---------|--------|---------|
| 产品概述 | 1 | index.md |
| 前置条件/快速开始 | 1 | prerequisites.md |
| 使用指南 | 4 | discover-servers、github-copilot、request-server、submit-server |
| 安全规范 | 1 | dos-and-donts.md |
| 帮助支持 | 2 | faq、support |
| 特殊页面 | 1 | pilot-program.md |
| 合计 | 10 | — |

## 关键配置/使用入口

**访问 Registry**

`https://portal.hyperspace.tools.sap/hyperspace-ai/mcp-registry`

**本地服务器配置示例**（以 Claude Code 为例）

```json
{
  "mcpServers": {
    "com.github/cap-js.mcp-server": {
      "command": "npx",
      "args": ["-y", "@cap-js/mcp-server"]
    }
  }
}
```

**GitHub Copilot 用户**：需额外注册 GitHub Copilot MCP Pilot（当前已满员）

**提交新服务器**：在 `hai-requests` 创建 issue，选择 "MCP Server Submission" 模板，附上符合 MCP Specification 格式的 `server.json`

**最重要的安全规则**：只使用 Hyperspace MCP Registry 收录的服务器，禁止使用其他来源的未审批服务器
