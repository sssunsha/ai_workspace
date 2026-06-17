---
sources: [docs__mcp-registry__index.md, docs__mcp-registry__prerequisites.md, docs__mcp-registry__how-tos__discover-servers.md, docs__mcp-registry__how-tos__submit-server.md, docs__mcp-registry__dos-and-donts.md, docs__mcp-registry__pilot-program.md]
related: [[hyperspace-ai-platform-overview]]
last-updated: 2026-06-15
---

## 核心定义

Hyperspace MCP Registry 是 SAP 内部的 MCP 服务器合规目录，提供经过安全审查的 MCP 服务器集中发现和管理能力，让 SAP 开发者无需自行评估合规性即可直接使用。

## 关键细节

**核心价值**

| 问题 | 解决方案 |
|------|---------|
| 不知道哪些 MCP 服务器合规可用 | 集中目录，所有 server 已通过合规审查 |
| 各工具配置方式不同 | Portal UI 提供 "Set Up" 按钮，生成工具特定配置 |
| GitHub Copilot 企业策略限制 | Registry API 作为 Copilot 的 allowlist |

**三种组件的区别**

| 组件 | 作用 | 使用时机 |
|------|------|---------|
| MCP Registry | 服务器目录/发现 | 浏览和发现合规 MCP 服务器 |
| MCP Servers | 实际提供数据/工具的服务 | 配置到 IDE 中使用 |
| SAP IT MCP Gateway | 远程服务器的中央访问点 | 尚未上线，未来自动处理 |

**服务器类型**

| 类型 | 运行位置 | 认证方式 | 示例 |
|------|---------|---------|------|
| Local | 用户机器 | 通常无需认证 | CAP MCP、UI5 MCP、Fiori MCP |
| Remote | 托管服务器 | OAuth（通过 SAP IT MCP Gateway） | Context7、Jira MCP、Portal MCP |

**入门前提**

- 非 GitHub Copilot 用户：无额外前提，直接访问 Portal 即可
- GitHub Copilot 用户：需注册 GitHub Copilot MCP Pilot（当前已满员）

**Portal 访问地址**：`https://portal.hyperspace.tools.sap/hyperspace-ai/mcp-registry`

**本地服务器配置示例**

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

**远程服务器配置示例**

```json
{
  "mcpServers": {
    "io.github.upstash/context7": {
      "type": "streamableHttp",
      "url": "https://mcp.context7.com/mcp"
    }
  }
}
```

**提交新 MCP 服务器的流程（6步）**

1. 确认服务器功能完整、已测试、有文档
2. 完成 SAP 合规要求（SADD、LeanIX、PET、GTLC 审批）
3. 通过 `hai-requests` 提交注册请求（需包含 `server.json`）
4. 与 Hyperspace 团队对齐注册内容
5. GTLC 合规评估（通过 MCPLIST Jira board 跟踪）
6. 合规通过后，server 出现在 Portal 目录，加入 Copilot allowlist

**注意**：`server.json` 不是 `mcp.json`（使用配置）也不是 `package.json`，需按 MCP Specification 格式填写。

**使用 MCP 服务器的安全准则**

- 只使用 Hyperspace MCP Registry 中的服务器，禁止使用未经批准的服务器
- 不向外部 MCP 服务器发送敏感/保密数据
- 所有 MCP 服务器输出必须经过验证（包括用作另一组件输入时）
- 仅启用当前任务所需的 MCP 服务器（减少 LLM 上下文）
- 定期审查 allowlist，不要永久批准危险操作
- MCP 服务器输出可能成为 prompt injection 攻击向量

**不会被接受的服务器类型**

- 未经授权访问 SAP 内部服务的服务器
- 仅供单个团队/项目使用的服务器
- 个人开发无团队支持的服务器
- 实验性/开发中的非生产就绪服务器

## 不同文档的补充

- `dos-and-donts.md` 同时包含消费者和开发者的安全准则
- `submit-server.md` 说明本地服务器（npm 发布）支持通过 renovate 自动更新版本
- `prerequisites.md` 说明 GitHub Copilot MCP Pilot 当前已满，需等待下次开放

## 未解答的问题

- SAP IT MCP Gateway 上线后，remote 服务器的 URL 会如何变化？
- Registry 中目前有哪些已收录的服务器（具体数量和名称）？
- 提交请求后的 SLA 是多少天？
