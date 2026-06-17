---
sources: [docs__llm-proxy__configuration__api-endpoints.md, docs__llm-proxy__configuration__cli-commands.md, docs__llm-proxy__configuration__cli-config-file.md, docs__llm-proxy__guides__connect-your-tools.md]
related: [[llm-proxy-architecture]], [[llm-proxy-production-use]]
last-updated: 2026-06-15
---

## 核心定义

Hyperspace LLM Proxy 提供四种提供商兼容的 API 端点（Anthropic、OpenAI、Gemini、LiteLLM），所有端点均在 `http://localhost:6655` 可用，支持多家提供商的模型统一访问。

## 关键细节

**四大端点快速参考**

| 提供商 | Base URL | 主要接口 |
|--------|----------|---------|
| Anthropic | `http://localhost:6655/anthropic/v1` | `POST /messages` |
| OpenAI | `http://localhost:6655/openai/v1` | `POST /chat/completions` |
| Gemini | `http://localhost:6655/gemini` | `POST /v1beta/models/{model}:generateContent` |
| LiteLLM（统一） | `http://localhost:6655/litellm/v1` | `POST /chat/completions`（支持所有模型） |

**LiteLLM 端点的适用场景**

工具只支持 OpenAI 格式但想用 Claude 或 Gemini → 用 LiteLLM 端点，通过 model 字段指定具体模型。

**可用模型（截至文档提取日期）**

*Anthropic（Claude）*

| 技术名 | 系列 |
|--------|------|
| `anthropic--claude-4.7-opus` | Opus |
| `anthropic--claude-4.6-sonnet` / `anthropic--claude-4.6-opus` | Sonnet/Opus |
| `anthropic--claude-4.5-haiku` / `anthropic--claude-4.5-sonnet` / `anthropic--claude-4.5-opus` | Haiku/Sonnet/Opus |
| `anthropic--claude-4-sonnet` | Sonnet |

*OpenAI（GPT）*：`gpt-5.5`、`gpt-5.4`、`gpt-5`、`gpt-5-mini`、`gpt-4.1`、`gpt-4.1-mini`
*Gemini*：`gemini-2.5-pro`、`gemini-2.5-flash`、`gemini-2.5-flash-lite`、`gemini-3.1-flash-lite`
*Perplexity*（通过 LiteLLM 访问）：`sonar`、`sonar-pro`（返回网页引用）
*嵌入模型*：`text-embedding-3-small`、`text-embedding-3-large`（OpenAI），`gemini-embedding`（Gemini）

**"Latest" 版本别名（自动跟随最新版本）**

| 别名 | 当前指向 |
|------|---------|
| `anthropic--claude-sonnet-latest` | `anthropic--claude-4.6-sonnet` |
| `anthropic--claude-opus-latest` | `anthropic--claude-4.7-opus` |
| `anthropic--claude-haiku-latest` | `anthropic--claude-4.5-haiku` |

**配置工具连接（hai configure 命令）**

```bash
# 自动配置 Claude Code（修改 ~/.claude/settings.json）
hai configure claude-code

# 自动配置 OpenCode（修改 ~/.config/opencode/opencode.jsonc）
hai configure opencode
```

**hai proxy start 命令选项**

| 参数 | 说明 |
|------|------|
| `--port <int>` | 修改默认端口（默认 6655） |
| `--dangerous-api-key <string>` | 固定 API Key（WSL 等场景使用，勿提交版本控制） |
| `--headless` | 无 TUI 模式，适合 CI/CD |
| `--verbose` | 详细日志输出 |

**配置文件（~/.config/hai/config.yaml）**

```yaml
auth:
  use-keyring: true           # 使用系统 keyring 持久化 token
  disable-background-refresh: false  # 后台自动刷新 token

proxy:
  port: 6655
  dangerous-api-key: ""       # WSL 场景下固定 key

logging:
  verbose: false
  file: ""
```

优先级：CLI 参数 > 配置文件 > 默认值

**生产可用工具（官方认证）**

Claude Code CLI、Cline、Roo Code、OpenSpec、Pi、OpenCode、Gemini CLI、SpecKit

**实验性工具**：Open WebUI、n8n、Xcode

**社区贡献 recipes**：Goose、Raycast、iTerm2、Obsidian

## 不同文档的补充

- `cli-commands.md` 是自动生成文件，包含完整 CLI 参考
- `api-endpoints.md` 提供了各端点的 curl 请求示例和完整的模型别名列表（用于工具名称硬编码场景）
- Perplexity Sonar 模型的引用格式：非流式在 `choices[0].message.extensions.citations[]`，流式在 SSE chunks 中

## 未解答的问题

- 各模型的 token 配额限制是多少？（文档只说 20 req/min，未说 token 限制）
- 嵌入模型是否有单独的速率限制？
- LiteLLM 端点和原生端点在功能上有哪些差异（除格式外）？
