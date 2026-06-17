# Hyperspace AI 产品文档索引

> 来源：hai-docs（89个文档文件）
> 产品：LLM Proxy / PR Bot / MCP Registry / EATER
> 更新：2026-06-15

---

## 平台概览

[[hyperspace-ai-platform-overview]] — Hyperspace AI 三大产品架构 + 团队结构

---

## 概念页面（concepts/）

### LLM Proxy

| 概念 | 内容 |
|------|------|
| [[llm-proxy-architecture]] | hai CLI 安装，SSO/OIDC 认证，GitHub Actions 集成 |
| [[llm-proxy-api-endpoints]] | 四大端点（Anthropic/OpenAI/Gemini/LiteLLM），模型列表，CLI 命令 |
| [[llm-proxy-production-use]] | GTLC 合规要求，20 req/min 限制，数据隐私规则 |

### PR Bot

| 概念 | 内容 |
|------|------|
| [[pr-bot-overview]] | /summarize /review /ask 命令，PR 大小限制，路线图 |
| [[pr-bot-configuration]] | JSON 配置格式，组织级 githubOrg> 继承，文件排除，Jira 集成 |

### MCP Registry

| 概念 | 内容 |
|------|------|
| [[mcp-registry-overview]] | 合规目录，本地/远程服务器类型，6步提交流程，安全准则 |

### EATER 评估项目

| 概念 | 内容 |
|------|------|
| [[eater-overview]] | 4阶段105天评估流程，工具状态清单，已通过工具 |

---

## 来源摘要（by-source/）

- [[by-source/hai-docs-llm-proxy]] — LLM Proxy 产品摘要（37个文档）
- [[by-source/hai-docs-pull-request-bot]] — PR Bot 产品摘要（25个文档）
- [[by-source/hai-docs-mcp-registry]] — MCP Registry 摘要（10个文档）
- [[by-source/hai-docs-eater]] — EATER 评估项目摘要（10个文档）
- [[by-source/hai-docs-tools-report]] | **⭐ 工具选型报告** — 所有 EATER 工具按类别/状态整理，含快速选型指南

---

## 关键注意事项

- **所有开源 AI 编程工具必须通过 LLM Proxy** — 这是 GTLC 强制要求
- **Roo Code 已于 2026-05-15 停止维护** — 迁移到 Cline 或 Claude Code
- **MCP Gateway 尚未上线** — remote MCP server 目前仍直连
