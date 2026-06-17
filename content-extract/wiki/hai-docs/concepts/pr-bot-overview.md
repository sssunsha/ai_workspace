---
sources: [docs__pull-request-bot__index.md, docs__pull-request-bot__getting-started.md, docs__pull-request-bot__features__review.md, docs__pull-request-bot__features__summarize.md, docs__pull-request-bot__features__ask.md, docs__pull-request-bot__additional-info__architecture.md, docs__pull-request-bot__before-you-begin__limitations.md]
related: [[hyperspace-ai-platform-overview]], [[pr-bot-configuration]]
last-updated: 2026-06-15
---

## 核心定义

Hyperspace Pull Request Bot 是通过 AI 增强 GitHub PR 工作流的自动化工具，以 slash 命令方式提供 PR 摘要、代码审查和交互式问答功能，由 Code Change Intelligence 团队开发，通过安装 Hyperspace Insights GitHub App 启用。

## 关键细节

**核心功能与命令**

| 命令 | 功能 | 典型响应时间 |
|------|------|------------|
| `/summarize` | 生成 PR 变更结构化摘要（含影响分析、测试建议） | 10–30 秒 |
| `/review` | AI 代码审查（安全、性能、最佳实践 + 内联注释） | 30–60 秒 |
| `/ask <问题>` | 关于代码变更的 Q&A | 取决于问题复杂度 |

**支持的 GitHub 实例**

所有功能均支持：github.tools.sap、github.wdf.sap.corp、github.concur.com、github.com
Jira 集成仅支持 github.tools.sap（不支持 github.com 和 github.concur.com）

**前提条件**

只需安装 **Hyperspace Insights GitHub App** 到组织或仓库，无需其他配置即可使用基础功能。

**/summarize 使用变体**

```
/summarize                                              # 基础摘要
/summarize Focus on API changes                        # 自定义方向
/summarize https://jira.tools.sap/browse/PROJ-123     # 引入 Jira 上下文
/summarize #456                                        # 引入 GitHub Issue 上下文
/summarize Focus on API changes https://jira...        # 组合用法
```

摘要操作后可：
- 插入为 PR 描述（自动删除评论）
- 生成新摘要
- 删除评论

**/review 扩展能力**

- 可通过 `/review Focus on security` 指定审查重点
- 支持 GitHub suggestion 块（一键应用代码建议）
- 支持用户反馈评级（Awesome/Helpful/Neutral/Not helpful）

**/ask 使用场景**

- PR 时间线评论：询问整个 PR
- 内联评论：点击行号询问特定代码行/块/文件

**限制（严格）**

| 限制类型 | 阈值 | 说明 |
|---------|------|------|
| 变更文件数 | > 300 | 超过则跳过分析 |
| 变更行数 | > 50,000 | 超过则跳过分析 |

**自动排除的文件类型**：二进制文件、图片、字体、PDF、压缩包、checksum 文件

**自动化功能（需配置）**

- 自动生成摘要（PR 创建时触发）
- 自动插入 PR description（为空或等于模板时）
- 自动生成代码审查（PR 创建时触发）

**代理检测 AGENTS.md 等文件**

Bot 自动检测并使用仓库中的 `AGENTS.md`、`CLAUDE.md`、`.github/copilot-instructions.md`、`.instructions/**/*.md` 作为额外上下文。

**路线图（已知规划）**

| 功能 | 状态 |
|------|------|
| SonarQube Integration（Sonar Fix） | 开发中 |
| Pipeline Fix | Pilot 阶段 |
| Flow Metrics Integration | Ideation |
| ChangeLog Generation | Ideation |
| Upgrade Assistance（CAP/Fiori） | Ideation |

## 不同文档的补充

- `limitations.md` 明确 Bot 不替代人工审查，强调 AI 辅助而非取代
- `architecture.md` 提供了功能演进时间线，说明 Jira 集成和 GitHub Issue 链接已实现
- `features/review.md` 说明自动审查会跳过 username 以 `serviceuser` 结尾的 PR

## 未解答的问题

- Bot 使用哪个 LLM 模型进行分析？是否可配置？
- 每个仓库的月调用量限制是多少？
- SonarFix Pilot 的申请方式？
