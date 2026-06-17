---
sources: [docs__llm-proxy__index.md, docs__llm-proxy__concepts__architecture.md, docs__llm-proxy__quickstart.md, docs__llm-proxy__installation__cli.md, docs__llm-proxy__installation__choose-your-setup.md, docs__llm-proxy__faq.md]
related: [[hyperspace-ai-platform-overview]], [[llm-proxy-api-endpoints]], [[llm-proxy-cli-configuration]], [[llm-proxy-production-use]]
last-updated: 2026-06-15
---

## 核心定义

Hyperspace LLM Proxy 是 SAP 内部开发团队访问多家 LLM 提供商（Anthropic、OpenAI、Google Gemini）的统一安全网关，通过本地代理进程实现无需管理 API Key 的合规访问。所有请求路由经 SAP AI Core 完成，内置认证、限流和成本追踪。

## 关键细节

**安装方式**

| 方式 | 平台 | 特点 |
|------|------|------|
| hai CLI（命令行） | macOS/Linux/Windows/WSL | 主流方式，Homebrew 安装 |
| Desktop App（图形界面） | macOS/Windows | Beta 版，菜单栏/系统托盘驻留 |
| GitHub Actions（CI/CD） | github.tools.sap | Pilot 阶段，基于 OIDC 无密钥认证 |

**macOS 安装（推荐方式）**

```bash
brew install gh
gh auth login --hostname github.tools.sap
brew tap hAIperspace/hai https://github.tools.sap/hAIperspace/hai-homebrew
brew install hai
hai proxy start     # 启动代理，触发 SSO 登录
```

**代理运行后的关键信息**

- 本地地址：`http://localhost:6655`（默认端口，可通过 `--port` 修改）
- API Key：本地 session key，仅在 localhost 有效，无泄漏风险
- Token 缓存：认证 token 缓存约 12 小时，重启代理无需重新打开浏览器
- WSL 限制：keyring 不支持，API key 每次重启会刷新，可通过 `proxy.dangerous-api-key` 固定

**认证流程**

1. 用户运行 `hai proxy start`
2. 浏览器打开，SSO（OIDC）登录
3. 本地代理启动，监听 6655 端口
4. AI 工具通过本地代理发请求 → Hyperspace 后端 → SAP AI Core → LLM 提供商

**架构组件**

- **Hyperspace Portal**：工作区管理界面，管理 extensions 和访问控制
- **hai CLI / Desktop App**：本地代理应用，负责认证和请求转发
- **Hyperspace LLM Proxy 后端**：核心服务，负责路由、授权和 AI Core 集成
- **SAP AI Core**：企业级 AI 平台，实际连接 LLM 提供商

**GitHub Actions 集成（Pilot）**

- 使用 OIDC token 实现无密钥认证
- 需要仓库注册为 Hyperspace portal 组件
- 生产端点：`https://api.hyperspace.tools.sap/llm-proxy`
- 提供 composite actions：`get-llm-token`、`setup-claude`、`setup-copilot`
- 注意：`id-token: write` 权限必须在每个 job 中声明

**解决的核心问题**

- 各团队无需自行配置 AI Core 实例和管理 API Key
- 消除 shadow IT 和不合规的个人 API Key 使用
- 提供集中的 AI 费用监控（未来）
- 统一开发者体验

## 不同文档的补充

- `faq.md` 明确：代理不记录 prompt 内容，仅记录请求元数据（模型、token 数、时间戳）
- `faq.md` 明确：模型提供商依合同不得使用请求数据进行训练
- `architecture.md` 提供了详细的请求流向图（本地开发和 CI/CD 两条路径）
- `installation/cli.md` 说明 WSL 环境下 keyring 不支持，需用 `dangerous-api-key` 固定 key

## 未解答的问题

- Desktop App 的自动更新机制和当前版本稳定性如何？
- 当代理处于离线状态时，AI 工具的降级行为是什么？
- hai CLI 和 Desktop App 能否同时运行？（文档明确说不行，但原因未深入解释）
