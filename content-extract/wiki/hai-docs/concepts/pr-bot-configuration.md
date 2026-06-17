---
sources: [docs__pull-request-bot__advanced-configuration.md, docs__pull-request-bot__features__review.md, docs__pull-request-bot__features__summarize.md, docs__pull-request-bot__integrations__index.md, docs__pull-request-bot__integrations__jira.md, docs__pull-request-bot__integrations__sonarqube.md]
related: [[pr-bot-overview]]
last-updated: 2026-06-15
---

## 核心定义

PR Bot 通过在仓库中创建 `.hyperspace/pull_request_bot.json` 配置文件来自定义行为，支持仓库级、组织级（`githubOrg>` 协议）和跨组织共享配置（`shared>` 协议），提供自动化触发、文件排除、自定义 prompt/模板等能力。

## 关键细节

**配置文件位置**

`.hyperspace/pull_request_bot.json`（提交到仓库即生效）

**完整配置示例**

```json
{
  "$schema": "https://devops-insights-pr-bot.cfapps.eu10-004.hana.ondemand.com/schema/pull_request_bot.json",
  "extends": ["githubOrg>pr-bot-configs/.hyperspace/pull_request_bot.json"],
  "enabled": true,
  "excluded_paths": ["*.lock", "dist/**", "*.min.js"],
  "features": {
    "control_panel": true,
    "summarize": {
      "auto_generate_summary": true,
      "auto_insert_summary": false,
      "auto_run_on_draft_pr": true,
      "auto_exclude_authors": ["I123456"],
      "use_custom_summarize_prompt": true,
      "use_custom_summarize_output_template": false,
      "excluded_paths": ["test/**"]
    },
    "review": {
      "auto_generate_review": false,
      "auto_run_on_draft_pr": false,
      "auto_exclude_authors": [],
      "use_custom_review_focus": true,
      "excluded_paths": ["docs/**"]
    }
  }
}
```

**关键配置项说明**

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `enabled` | `true` | 全局禁用/启用 bot |
| `summarize.auto_generate_summary` | `false` | PR 创建时自动生成摘要 |
| `summarize.auto_insert_summary` | `false` | 描述为空时自动插入摘要 |
| `summarize.auto_run_on_draft_pr` | `true` | Draft PR 也自动运行 |
| `review.auto_generate_review` | `false` | PR 创建时自动生成审查 |
| `review.auto_run_on_draft_pr` | `false` | Draft PR 不自动审查 |

**文件排除规则**

- 全局排除（`root.excluded_paths`）：对摘要和审查都生效
- 功能级排除（`features.summarize.excluded_paths`）：仅对该功能生效
- 两者叠加计算
- 安全保护：不允许 `*`、`**`、`**/*` 等全排除模式

**Glob 语法**

- `*.ext` — 任意扩展名文件
- `dir/**` — 目录下所有文件（递归）
- `**/*.ext` — 任意嵌套目录下的扩展名文件

**自定义文件**

| 文件 | 用途 | 启用配置项 |
|------|------|-----------|
| `.hyperspace/pull_request_bot_summarize_prompt.md` | 自定义摘要 prompt | `use_custom_summarize_prompt: true` |
| `.hyperspace/pull_request_bot_summarize_output_template.md` | 自定义摘要格式模板 | `use_custom_summarize_output_template: true` |
| `.hyperspace/pull_request_bot_review_focus.md` | 自定义审查关注点 | `use_custom_review_focus: true` |

**组织级配置（githubOrg> 协议）**

```json
{
  "extends": ["githubOrg>central-config-repo/.hyperspace/pull_request_bot.json"]
}
```

注意：`githubOrg>` 是字面量协议名，不要替换为实际组织名。

配置优先级：本地配置 > extends 中后面的配置 > extends 中前面的配置 > 默认值
特殊规则：`auto_exclude_authors` 和自定义 review focus 会追加（appended），不会被覆盖。
最大继承深度：10 层

**跨组织共享配置（shared> 协议）**

要求：托管仓库必须是 public，且配置中设置 `"shared": true`。

```json
{
  "extends": [
    "shared>https://github.tools.sap/example-org/shared-configs/.hyperspace/pull_request_bot.json"
  ]
}
```

**集成支持**

| 集成 | 功能增强 | 限制 |
|------|---------|------|
| Jira（jira.tools.sap） | 摘要/审查引入需求上下文 | 不支持 github.com/github.concur.com |
| GitHub Issues | 摘要/审查引入 issue 上下文 | 无限制 |
| SonarQube | AI 驱动的 sonar 问题修复建议 | Pilot 阶段 |

Jira 集成前提：需将技术用户 `T_DOR_AI` 加入 Jira 项目。

## 不同文档的补充

- `advanced-configuration.md` 包含完整的 mermaid 图，清晰展示组织级配置的 extends 关系
- `features/review.md` 说明：即使从 org 配置继承了 `use_custom_review_focus: true`，本地仓库仍需显式声明该选项

## 未解答的问题

- 自动摘要插入时，"等于 PR 模板"的比较算法是否大小写敏感？
- `shared>` 协议是否支持私有仓库（通过 token 访问）？
