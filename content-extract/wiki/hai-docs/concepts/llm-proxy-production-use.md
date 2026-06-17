---
sources: [docs__llm-proxy__production-use.md, docs__llm-proxy__faq.md, docs__llm-proxy__installation__github-actions.md]
related: [[llm-proxy-architecture]], [[llm-proxy-api-endpoints]]
last-updated: 2026-06-15
---

## 核心定义

Hyperspace LLM Proxy 在生产使用中有明确的合规要求：所有 LLM 请求必须经由代理路由（GTLC 强制要求），不得直连外部 LLM 提供商，且只能在 SAP 公司受管设备上运行。

## 关键细节

**合规要求（不遵守属违规）**

禁止：
- 直连 OpenAI、Anthropic、Google 等外部 LLM 提供商
- 使用个人或团队 AI Core 实例
- 在非 SAP 或个人设备上运行代理
- 共享团队代理（每位用户必须运行自己的代理实例）

允许：
- 通过 Hyperspace LLM Proxy 路由所有 LLM 请求
- 使用官方认证工具（Cline、Claude Code CLI 等）
- SAP 员工（C/I/D 用户）在公司受管设备上使用

**允许的环境**

| 环境 | 是否允许 | 说明 |
|------|---------|------|
| 本地开发机 | ✅ | 标准安装即可 |
| VS Code dev container / Docker（本机） | ✅ | 通过 `host.docker.internal:6655` 访问 |
| 远程 SAP 服务器（无 GUI） | ✅ | 本机运行代理，SSH 反向隧道转发 |
| GitHub Actions / CI/CD | ✅ | Pilot 阶段（2026年6月开始） |
| 已部署的 agent 或托管服务 | ❌ | 用 SAP AI Core 替代 |
| 客户或非 SAP 环境 | ❌ | 不允许 |
| 个人或非 SAP 项目 | ❌ | 不允许 |

**速率限制**

- 20 请求/分钟（每用户）
- 触发限制时建议使用更快的模型（如 Haiku 替代 Sonnet）或在支持的工具中启用 prompt caching

**安全准则（GTLC 要求）**

- 假设 AI 生成的代码不安全，必须人工审查
- 不得将凭证、密码等敏感数据发送给 AI 工具
- 不得将个人数据输入 AI 工具（开发者姓名/邮箱除外）
- 生成代码须经 SAST 和 OSVM 工具扫描
- 不得将 AI 生成代码用于模型训练或 RAG 数据集（工具未明确允许时）

**隐私说明**

- 代理不记录 prompt 内容，仅记录请求元数据（模型、token 数、时间戳）
- AI Core 合同规定提供商不得用请求数据训练模型
- `X-Correlation-ID` header 用于分布式追踪，不含个人信息

**GitHub Actions OIDC 认证流程**

```yaml
jobs:
  ai-task:
    runs-on: [self-hosted, solinas]
    permissions:
      id-token: write   # 每个 job 必须声明
    steps:
      - name: Get LLM Token
        id: llm-token
        uses: hAIperspace/hai-llm-actions-pilot/.github/actions/get-llm-token@main
      # token 通过 steps.llm-token.outputs.token 获取
```

注意事项：
- token 作用域是 per-job，不能在 job 间共享
- 只支持 self-hosted runner（需要 SAP 网络访问）
- 避免无限循环（如 PR 创建触发 → 创建新 PR）
- 不要创建定时触发（cronjob-like）的 AI 工作流

## 不同文档的补充

- `github-actions.md` 提供了四个可直接使用的工作流示例：PR 多 Agent 审查、PR 摘要、质量门控、文档生成
- `production-use.md` 强调了"第三方代码"限制：不得将客户代码用于 AI 生成
- `faq.md` 解释了为何不能使用其他代理方案：Hyperspace Proxy 提供工具-模型配对强制、许可证过滤等合规特性

## 未解答的问题

- 20 req/min 的速率限制在 GA 后是否会提高？
- Docker 容器内访问的 `host.docker.internal` 是否在 Linux Docker 上也有效？
