---
source: hai-docs/llm-proxy
type: local_doc
last-updated: 2026-06-15
---

## 产品一句话描述

Hyperspace LLM Proxy 是 SAP 内部开发者访问多家 LLM 提供商的统一安全网关，通过本地代理进程和 SSO 认证消除 API Key 管理负担，同时满足 GTLC 合规要求。

## 核心功能列表

- **统一多提供商访问**：单一端点覆盖 Anthropic（Claude）、OpenAI（GPT）、Google（Gemini）、Perplexity（Sonar）
- **无 API Key 认证**：通过 SSO/OIDC 自动认证，本地生成临时 API Key
- **多端点兼容**：Anthropic 格式、OpenAI 格式、Gemini 格式、LiteLLM 统一格式
- **GitHub Actions OIDC 集成**：CI/CD 流程中无密钥 AI 访问（Pilot 阶段）
- **模型别名与自动更新**：latest 别名自动跟随最新版本
- **嵌入模型支持**：OpenAI 和 Gemini 的文本嵌入
- **速率限制**：20 请求/分钟/用户

## 文档覆盖范围

| 文档分类 | 文件数 | 主要内容 |
|---------|--------|---------|
| 产品概述/架构 | 3 | index.md、quickstart.md、concepts/architecture.md |
| 安装与配置 | 5 | CLI、Desktop App、GitHub Actions、choose-your-setup、dev-containers |
| API 参考 | 3 | api-endpoints.md、cli-commands.md、cli-config-file.md |
| 使用指南 | 4 | connect-your-tools.md、troubleshooting.md、ssh-tunneling.md、desktop-app-user-guide |
| Recipes（工具集成） | 17 | Claude、Cline、Roo Code、OpenSpec、Pi、OpenCode、Gemini CLI 等 |
| 其他 | 5 | production-use.md、faq.md、support.md、whats-new.md、includes |
| 合计 | 37 | — |

## 关键配置/使用入口

**快速启动**

```bash
# macOS 安装
brew tap hAIperspace/hai https://github.tools.sap/hAIperspace/hai-homebrew
brew install hai
hai proxy start        # 触发 SSO 登录，在 localhost:6655 启动代理
hai configure claude-code  # 自动配置 Claude Code
```

**主要 API 端点**

- Anthropic：`http://localhost:6655/anthropic/v1/messages`
- OpenAI：`http://localhost:6655/openai/v1/chat/completions`
- LiteLLM（统一）：`http://localhost:6655/litellm/v1/chat/completions`
- Gemini：`http://localhost:6655/gemini/v1beta/models/{model}:generateContent`

**生产端点（GitHub Actions 专用）**

`https://api.hyperspace.tools.sap/llm-proxy`

**关键合规要求**

所有 LLM 请求必须路由经代理（GTLC 强制），不得直连外部提供商，只能在 SAP 公司受管设备上运行。

**支持的工具（生产认证）**：Claude Code CLI、Cline、Roo Code、OpenSpec、Pi、OpenCode、Gemini CLI、SpecKit
