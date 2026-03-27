# Claude Code 完整使用手册

> 版本：2026 年 3 月 | 适用于 Claude Code CLI（VSCode 扩展 & 终端）

---

## 第一部分：常用命令与功能速查表

### 1.1 斜杠命令（Slash Commands）

| 命令 | 分类 | 功能说明 | 示例 |
|------|------|----------|------|
| `/help` | 帮助 | 显示所有可用命令列表及说明 | `/help` |
| `/clear` | 会话 | 清除当前对话历史，释放上下文窗口 | `/clear` |
| `/compact` | 会话 | 压缩对话历史，保留摘要节省 token | `/compact` |
| `/status` | 会话 | 显示当前会话状态、模型、费用信息 | `/status` |
| `/cost` | 会话 | 查看本次会话消耗的 token 数量和费用 | `/cost` |
| `/fast` | 性能 | 切换快速模式（相同模型，更快输出） | `/fast` |
| `/model` | 配置 | 切换 AI 模型（Haiku / Sonnet / Opus） | `/model claude-opus-4-6` |
| `/config` | 配置 | 查看或修改 Claude Code 全局配置 | `/config` |
| `/login` | 认证 | 登录 Anthropic 账户或设置 API Key | `/login` |
| `/logout` | 认证 | 登出当前账户 | `/logout` |
| `/init` | 项目 | 在当前项目根目录生成 `CLAUDE.md` 文件 | `/init` |
| `/memory` | 内存 | 查看和管理持久化记忆内容 | `/memory` |
| `/permissions` | 权限 | 查看和管理工具调用权限策略 | `/permissions` |
| `/mcp` | MCP | 查看已配置的 MCP 服务器列表 | `/mcp` |
| `/add-dir` | 文件 | 向当前会话添加额外可访问目录 | `/add-dir /path/to/dir` |
| `/vim` | 编辑 | 切换 Vim 键盘模式输入 | `/vim` |
| `/terminal-setup` | 环境 | 配置终端集成（颜色、字体、快捷键） | `/terminal-setup` |
| `/doctor` | 诊断 | 诊断 Claude Code 安装和环境问题 | `/doctor` |
| `/bug` | 反馈 | 向 Anthropic 报告 Bug | `/bug` |
| `/release-notes` | 更新 | 查看最新版本的更新说明 | `/release-notes` |
| `/review` | 代码 | 对当前分支的改动进行 AI 代码审查 | `/review` |
| `/commit` | Git | AI 辅助生成提交信息并创建 commit | `/commit` |
| `/pr` | Git | 创建 Pull Request（含 AI 生成描述） | `/pr` |
| `/review-pr` | Git | 审查指定 GitHub PR | `/review-pr 123` |
| `/update-config` | 高级 | 通过对话配置 settings.json、hooks、权限 | `/update-config` |
| `/simplify` | 高级 | 对已更改代码进行质量审查和简化建议 | `/simplify` |
| `/loop` | 自动化 | 定时循环执行某个命令或提示词 | `/loop 5m /review` |

---

### 1.2 上下文引用符号

| 符号 | 功能说明 | 示例 | 效果 |
|------|----------|------|------|
| `@文件路径` | 引用本地文件内容 | `@src/app.ts 这段代码有什么问题？` | Claude 读取文件内容并分析 |
| `@文件夹路径` | 引用整个文件夹 | `@src/components 帮我做代码审查` | Claude 读取该目录下所有文件 |
| `@URL` | 引用网页内容 | `@https://docs.example.com 总结一下` | Claude 抓取并分析页面内容 |
| `#文件路径` | 将文件内容直接嵌入消息 | `#config.json 解释这个配置` | 文件内容直接内联显示 |
| `!命令` | 执行 Shell 命令 | `!npm test` | 运行命令并把输出传给 Claude |

---

### 1.3 键盘快捷键

| 快捷键（Mac） | 快捷键（Win/Linux） | 功能说明 | 使用场景 |
|--------------|-------------------|----------|----------|
| `Cmd+K` | `Ctrl+K` | 打开命令面板 | 快速查找并执行命令 |
| `Cmd+L` | `Ctrl+L` | 清除对话历史 | 开始新话题前清空上下文 |
| `Ctrl+C` | `Ctrl+C` | 中止当前操作 | 中断正在执行的命令或生成 |
| `Tab` | `Tab` | 自动补全 | 补全路径、命令名称 |
| `↑ / ↓` | `↑ / ↓` | 翻看历史输入 | 重用之前的提示词 |
| `Shift+Enter` | `Shift+Enter` | 换行（不提交） | 编写多行提示词 |
| `Escape` | `Escape` | 取消当前输入 | 放弃正在编写的消息 |

---

### 1.4 内存与持久化文件

| 文件 | 位置 | 作用 | 生命周期 |
|------|------|------|----------|
| `CLAUDE.md` | 项目根目录 | 项目级规则、编码规范、架构说明 | 长期（随项目） |
| `CLAUDE.md` | `~/.claude/CLAUDE.md` | 全局规则，跨所有项目生效 | 长期（全局） |
| `CLAUDE.local.md` | 项目根目录 | 个人临时覆盖规则，不提交 Git | 按需删除 |
| `MEMORY.md` | `~/.claude/projects/xxx/memory/` | Claude 自动写入的跨会话记忆 | 手动清理 |
| `settings.json` | 项目根 / `~/.claude/` | 模型、权限、MCP、Hook 等配置 | 长期 |
| `settings.local.json` | 项目根目录 | 个人本地配置覆盖，不提交 Git | 长期（本地） |

---

### 1.5 权限配置速查

| 权限类型 | 语法格式 | 示例 | 说明 |
|----------|----------|------|------|
| 允许执行 | `"Bash(命令:*)"` | `"Bash(npm:*)"` | 允许所有 npm 命令 |
| 允许读文件 | `"Read(路径)"` | `"Read(//workspace/**)"` | 允许读取 workspace 下所有文件 |
| 允许网络 | `"WebFetch(domain:域名)"` | `"WebFetch(domain:github.com)"` | 允许访问指定域名 |
| 需要确认 | 在 `ask` 数组中 | `"Bash(rm:*)"` | 删除命令需要用户确认 |
| 禁止操作 | 在 `deny` 数组中 | `"Bash(git push --force:*)"` | 禁止强制推送 |

---

### 1.6 MCP 服务器常用类型

| 类型 | 功能 | npm 包示例 |
|------|------|-----------|
| `filesystem` | 访问本地文件系统 | `@modelcontextprotocol/server-filesystem` |
| `github` | GitHub API 操作 | `@modelcontextprotocol/server-github` |
| `postgres` | PostgreSQL 数据库 | `@modelcontextprotocol/server-postgres` |
| `brave-search` | 网络搜索 | `@modelcontextprotocol/server-brave-search` |
| `puppeteer` | 浏览器自动化 | `@modelcontextprotocol/server-puppeteer` |
| `slack` | Slack 消息集成 | `@modelcontextprotocol/server-slack` |
| `memory` | 知识图谱记忆 | `@modelcontextprotocol/server-memory` |

---

---

## 第二部分：核心功能与技巧详解

### 目录

1. [会话管理与上下文控制](#1-会话管理与上下文控制)
2. [文件引用与代码上下文](#2-文件引用与代码上下文)
3. [CLAUDE.md 项目规则系统](#3-claudemd-项目规则系统)
4. [内存与跨会话记忆](#4-内存与跨会话记忆)
5. [Git 工作流集成](#5-git-工作流集成)
6. [权限系统详解](#6-权限系统详解)
7. [MCP 服务器配置](#7-mcp-服务器配置)
8. [Hooks 自动化配置](#8-hooks-自动化配置)
9. [settings.json 配置全解](#9-settingsjson-配置全解)
10. [多目录与多项目管理](#10-多目录与多项目管理)
11. [IDE 集成技巧](#11-ide-集成技巧)
12. [高级技巧与最佳实践](#12-高级技巧与最佳实践)

---

### 1. 会话管理与上下文控制

Claude Code 的每次对话都在一个"会话"中进行，理解上下文管理是高效使用的关键。

#### 1.1 上下文窗口管理

Claude 有上下文窗口（token）限制。当对话很长时，可以：

```
# 压缩历史，节省 token（推荐长对话时使用）
/compact

# 完全清空，重新开始
/clear

# 查看当前消耗
/cost
```

**技巧：** 在切换到新任务前使用 `/compact`，Claude 会自动总结之前的对话摘要，保留关键信息同时释放空间。

#### 1.2 快速模式

```
# 切换快速模式（同模型更快响应，适合简单任务）
/fast
```

快速模式使用相同的模型，但优化了输出速度，适合不需要深度思考的简单问答。

#### 1.3 查看会话状态

```
/status
```

显示：当前模型名称、已使用 token 数、会话时长、工作目录等信息。

---

### 2. 文件引用与代码上下文

向 Claude 提供准确的代码上下文是获得高质量回答的核心。

#### 2.1 引用单个文件

```
@src/app.ts 这个文件有内存泄漏吗？

@package.json 依赖版本是否有冲突？
```

Claude 会读取文件完整内容进行分析。

#### 2.2 引用整个目录

```
@src/components 帮我审查这些组件是否符合 React 最佳实践

@tests/ 这些测试覆盖率是否足够？
```

**注意：** 引用大型目录可能消耗大量 token，建议精准引用。

#### 2.3 嵌入文件内容（#）

```
#config.json 根据这个配置，帮我生成对应的 TypeScript 类型定义
```

`#` 与 `@` 的区别：`#` 会将文件内容直接内联展示在对话中，`@` 则由 Claude 在后台读取。

#### 2.4 引用网页内容

```
@https://api.example.com/docs 根据这个文档帮我实现一个 API 调用函数
```

Claude 会抓取页面内容并结合你的需求进行处理。

#### 2.5 执行命令并分析结果

```
!npm test 分析测试失败的原因

!git log --oneline -20 根据这些提交记录生成更新日志
```

`!` 符号会实际执行命令，并把输出传给 Claude 分析。

#### 2.6 组合使用（最佳实践）

```
@src/service/user.service.ts !npm test -- user.spec.ts
根据文件内容和测试输出，帮我修复失败的测试
```

---

### 3. CLAUDE.md 项目规则系统

`CLAUDE.md` 是 Claude Code 最重要的功能之一，它让 Claude 在每次会话开始时自动加载你预设的规则。

#### 3.1 文件层级

```
优先级（从高到低）：
1. 当前项目 CLAUDE.local.md    （个人覆盖，不提交 Git）
2. 当前项目 CLAUDE.md          （团队共享规则）
3. 父目录 CLAUDE.md            （可继承上层目录规则）
4. ~/.claude/CLAUDE.md         （全局规则，所有项目生效）
```

#### 3.2 初始化项目规则

```
/init
```

Claude 会分析你的项目结构，自动生成合适的 `CLAUDE.md` 初稿，包括：
- 项目技术栈描述
- 常用命令（build、test、lint）
- 代码规范建议

#### 3.3 CLAUDE.md 推荐内容结构

```markdown
# 项目规则

## 项目概述
这是一个基于 Angular + TypeScript 的前端项目。

## 常用命令
- 构建：`npm run build`
- 测试：`npm test`
- 代码检查：`npm run lint`
- 启动开发服务器：`npm start`

## 编码规范
- 所有注释和文档必须用英文
- 使用 async/await，不使用 .then()/.catch()
- 组件文件名使用 kebab-case
- 私有方法以 _ 开头

## 架构说明
- 服务层位于 src/lib/services/
- 组件位于 src/lib/components/
- 类型定义位于 src/lib/types/

## 注意事项
- 不要修改 dist/ 目录
- API Key 不能提交到代码库
- 提交前必须通过 lint 检查
```

#### 3.4 CLAUDE.local.md 个人规则

适合存放不想共享给团队的个人偏好：

```markdown
# 个人开发规则（不提交 Git）

## 调试偏好
- 遇到问题先查看 src/debug/ 目录下的日志工具

## 本地环境
- 本地后端 API 地址：http://localhost:3000
- 测试账号：test@example.com / password123
```

---

### 4. 内存与跨会话记忆

Claude Code 支持在多次会话间保持记忆，无需每次重复说明背景。

#### 4.1 自动记忆系统

Claude 会自动将重要信息写入：
```
~/.claude/projects/<项目路径>/memory/MEMORY.md
```

#### 4.2 手动保存记忆

在对话中直接告诉 Claude：

```
请记住：我们团队使用 Conventional Commits 规范，提交信息格式为 "feat(scope): description"

请记住：这个项目使用自定义的 HTTP 拦截器，不要直接使用 fetch

请记住：用户更喜欢简洁的代码回复，不需要详细解释
```

#### 4.3 查看和管理记忆

```
/memory
```

显示当前已保存的所有记忆条目，支持查看、编辑、删除。

#### 4.4 忘记特定记忆

```
请忘记之前关于使用 Redux 的记忆，我们现在改用 Zustand 了
```

#### 4.5 跨项目全局记忆

在 `~/.claude/CLAUDE.md` 中写入全局规则，对所有项目生效：

```markdown
# 全局个人规则

## 沟通偏好
- 所有回复必须中英双语
- 代码注释和文档用英文
- 回复要简洁，不要重复我说的内容

## 技术偏好
- TypeScript 优先于 JavaScript
- 函数式编程优先于 OOP
- 单元测试覆盖率要求 80% 以上
```

---

### 5. Git 工作流集成

Claude Code 深度集成 Git，大幅提升代码提交和审查效率。

#### 5.1 AI 辅助提交

```
/commit
```

Claude 会：
1. 执行 `git diff --staged` 分析变更
2. 生成符合 Conventional Commits 规范的提交信息
3. 展示给你确认
4. 执行 `git commit`

**技巧：** 在 `CLAUDE.md` 中注明提交规范，Claude 会自动遵守：
```markdown
## Git 提交规范
格式：`type(scope): description`
类型：feat, fix, docs, refactor, test, chore
```

#### 5.2 创建 Pull Request

```
/pr
```

Claude 会：
1. 分析当前分支与主分支的差异
2. 生成 PR 标题和描述（含 Summary 和 Test plan）
3. 调用 `gh pr create` 创建 PR

#### 5.3 代码审查

```
# 审查当前分支改动
/review

# 审查指定 PR（需要 gh CLI 和 GitHub 权限）
/review-pr 123
/review-pr https://github.com/org/repo/pull/123
```

#### 5.4 使用 Git Worktree 隔离开发

Claude Code 支持在隔离的 worktree 中进行实验性开发：

```
# 让 Claude 在 worktree 中工作（不影响主工作区）
请在 worktree 中实现这个功能
```

Agent 会在 `.claude/worktrees/` 下创建隔离副本，完成后可选择保留或删除。

---

### 6. 权限系统详解

权限系统控制 Claude 可以执行哪些操作，是安全使用 Claude Code 的核心机制。

#### 6.1 权限配置文件位置

```
优先级（从高到低）：
1. 项目 settings.local.json    （个人本地，不提交）
2. 项目 settings.json          （团队共享）
3. ~/.claude/settings.json     （全局默认）
```

#### 6.2 完整权限配置示例

```json
{
  "permissions": {
    "allow": [
      "Bash(npm:*)",
      "Bash(npx:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Read(**)",
      "Write(**)",
      "Edit(**)",
      "WebFetch(domain:github.com)",
      "WebFetch(domain:npmjs.com)"
    ],
    "ask": [
      "Bash(git push:*)",
      "Bash(git reset:*)",
      "Bash(rm:*)"
    ],
    "deny": [
      "Bash(git push --force:*)",
      "Bash(git reset --hard:*)",
      "Bash(sudo:*)"
    ]
  }
}
```

#### 6.3 默认权限模式

```json
{
  "defaultMode": "bypassPermissions"    // 允许一切（开发时方便）
  "defaultMode": "confirmAllPermissions" // 所有操作都需确认（最安全）
  "defaultMode": "usePolicy"            // 按 allow/ask/deny 规则执行
}
```

#### 6.4 通过命令行临时修改

```bash
# 以允许一切的模式启动（仅当前会话）
claude --dangerously-skip-permissions

# 指定权限模式
claude --permission-mode bypassPermissions
```

---

### 7. MCP 服务器配置

MCP（Model Context Protocol）让 Claude 能访问外部工具和服务，极大扩展了能力边界。

#### 7.1 配置结构

在 `~/.claude/settings.json` 或项目 `settings.json` 中：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/username/workspace"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxx"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "your_api_key"
      }
    }
  }
}
```

#### 7.2 查看 MCP 状态

```
/mcp
```

显示所有已配置的 MCP 服务器及其连接状态。

#### 7.3 使用 MCP 功能示例

配置了 GitHub MCP 后：
```
帮我查看 organization/repo 最近 10 个未解决的 issue

帮我给 PR #456 添加审查评论
```

配置了数据库 MCP 后：
```
查询 users 表中最近注册的 10 个用户

帮我优化这条 SQL 查询的性能
```

---

### 8. Hooks 自动化配置

Hooks 让你可以在特定事件发生时自动执行命令，实现工作流自动化。

#### 8.1 Hook 类型与触发时机

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "echo '即将执行 Bash 命令'"
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "npm run lint --fix"
        }]
      }
    ],
    "Stop": [
      {
        "hooks": [{
          "type": "command",
          "command": "say 'Claude 已完成任务'"
        }]
      }
    ],
    "Notification": [
      {
        "hooks": [{
          "type": "command",
          "command": "osascript -e 'display notification \"Claude 需要你的确认\" with title \"Claude Code\"'"
        }]
      }
    ]
  }
}
```

#### 8.2 常用 Hook 场景

**代码写入后自动格式化：**
```json
{
  "PostToolUse": [{
    "matcher": "Write|Edit",
    "hooks": [{"type": "command", "command": "prettier --write ."}]
  }]
}
```

**Claude 停止时发送系统通知（macOS）：**
```json
{
  "Stop": [{
    "hooks": [{"type": "command", "command": "osascript -e 'display notification \"任务完成\" with title \"Claude Code\"'"}]
  }]
}
```

**提交前自动运行测试：**
```json
{
  "PreToolUse": [{
    "matcher": "Bash(git commit:*)",
    "hooks": [{"type": "command", "command": "npm test"}]
  }]
}
```

#### 8.3 通过命令配置 Hooks

```
/update-config
```

然后用自然语言描述：
```
每次 Claude 写入文件后，自动运行 eslint --fix
当 Claude 停止时，在终端显示完成提示音
```

---

### 9. settings.json 配置全解

#### 9.1 完整配置示例

```json
{
  // 默认使用的模型
  "model": "claude-sonnet-latest",

  // 权限配置
  "permissions": {
    "allow": ["Bash(npm:*)", "Bash(git:*)", "Read(**)", "Write(**)"],
    "ask": ["Bash(rm:*)", "Bash(git push:*)"],
    "deny": ["Bash(sudo:*)"],
    "defaultMode": "usePolicy",
    "additionalDirectories": ["/Users/username/.claude"]
  },

  // MCP 服务器
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
    }
  },

  // 环境变量
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
    "NODE_ENV": "development"
  },

  // Hooks
  "hooks": {
    "Stop": [{
      "hooks": [{"type": "command", "command": "echo '✅ Claude 完成'"}]
    }]
  }
}
```

#### 9.2 配置文件优先级

```
settings.local.json（项目本地，最高）
    ↓ 覆盖
settings.json（项目共享）
    ↓ 覆盖
~/.claude/settings.json（全局默认，最低）
```

#### 9.3 模型配置

```json
{
  "model": "claude-opus-4-6",
  "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-4-5-20251001",
  "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-4-6",
  "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-4-6"
}
```

#### 9.4 快速修改配置

```bash
# 命令行修改模型
claude --model claude-opus-4-6

# 通过自然语言配置（推荐）
/update-config
> 请将默认模型改为 claude-opus-4-6，并允许所有 npm 命令
```

---

### 10. 多目录与多项目管理

#### 10.1 添加额外目录

```
/add-dir /path/to/another/project
```

或在 settings.json 中永久配置：

```json
{
  "permissions": {
    "additionalDirectories": [
      "/Users/username/.claude",
      "/Users/username/workspace/shared-libs",
      "/Users/username/Documents/reference"
    ]
  }
}
```

#### 10.2 跨项目引用文件

配置额外目录后，可以直接引用：

```
@/Users/username/workspace/shared-libs/utils.ts
这里有共享工具函数，请帮我在当前项目中正确使用它
```

#### 10.3 多项目全局规则

在 `~/.claude/CLAUDE.md` 中设置跨项目统一规则：

```markdown
# 全局开发规则

## 通用规范
- 所有代码注释和文档用英文
- 提交信息遵循 Conventional Commits
- 安全敏感信息不得硬编码

## 技术偏好
- TypeScript 优先
- 函数组件优先于类组件（React）
- 异步操作使用 async/await
```

---

### 11. IDE 集成技巧

#### 11.1 VSCode 集成

Claude Code 作为 VSCode 扩展运行时，提供以下功能：

**侧边栏使用：**
- 点击左侧 Claude 图标打开面板
- 支持与当前编辑器文件直接交互
- 代码建议可一键应用

**右键菜单：**
- 选中代码 → 右键 → "Ask Claude" 快速提问
- "Explain this code" / "Fix this code" 快捷操作

**内联建议：**
- Claude 修改建议会以 diff 形式显示
- 支持部分接受（accept line / accept word）

#### 11.2 利用 IDE 选中内容

在 VSCode 中选中一段代码后，Claude 会自动感知到选中内容（IDE selection），无需手动引用文件：

```
（选中代码后直接问）
这段代码的时间复杂度是多少？有没有更好的实现方式？
```

#### 11.3 终端集成

```
/terminal-setup
```

配置终端主题和快捷键，让 Claude Code 在终端中有更好的显示效果。

---

### 12. 高级技巧与最佳实践

#### 12.1 高效提问技巧

**提供完整上下文：**
```
// ✅ 好的方式
@src/auth/token.service.ts @src/auth/auth.guard.ts
当 token 过期时，守卫没有正确触发刷新逻辑，请修复

// ❌ 不好的方式
token 刷新有问题，帮我修复
```

**指定期望的输出格式：**
```
请分析这段代码的问题，以以下格式回答：
1. 问题描述（一句话）
2. 根本原因
3. 修复方案（提供代码）
4. 预防措施
```

**利用链式思考：**
```
在回答前，先列出你的分析思路，然后再给出方案
```

#### 12.2 代码审查最佳实践

```
# 全面代码审查
/review

# 专注安全性审查
@src/auth/ 请对这个认证模块做安全审查，重点关注 OWASP Top 10 漏洞

# 性能审查
@src/components/DataTable.tsx 这个组件在大数据量时性能很差，帮我分析并优化
```

#### 12.3 调试技巧

```
# 结合错误日志调试
!npm test 2>&1 | tail -50
根据这个错误输出，帮我定位问题

# 结合文件内容调试
@src/api/user.api.ts !curl -X POST http://localhost:3000/api/users -d '{"name":"test"}'
根据代码实现和 API 响应，分析为什么返回 400 错误
```

#### 12.4 自动化工作流

利用 `/loop` 命令创建定时任务：

```
# 每 5 分钟运行一次代码审查
/loop 5m /review

# 每小时检查测试状态
/loop 1h !npm test
```

#### 12.5 token 节省技巧

```
1. 使用 /compact 定期压缩对话
2. 精准引用文件而不是整个目录
3. 简单任务使用 /fast 模式或 Haiku 模型
4. 在 CLAUDE.md 中写入规则，减少重复说明
5. 使用 /clear 在切换任务时清空上下文
```

#### 12.6 安全使用建议

```
1. 生产环境不要使用 bypassPermissions 模式
2. 在 settings.local.json 中存放敏感配置（不提交 Git）
3. 为破坏性操作（rm、force push）设置 ask 权限
4. 定期检查 /permissions 查看当前权限状态
5. MCP 服务器的 API Key 存放在环境变量中，不要硬编码
```

#### 12.7 团队协作建议

```
1. CLAUDE.md 提交到 Git，让团队共享规则
2. CLAUDE.local.md 加入 .gitignore，存放个人偏好
3. settings.json 提交基础配置（不含敏感信息）
4. settings.local.json 加入 .gitignore，存放个人密钥
5. 在 CLAUDE.md 中记录项目架构，帮助 Claude 更准确理解代码
```

---

## 附录：常见问题

### Q: Claude 忘记了之前的对话内容怎么办？
**A:** 使用 `/memory` 查看记忆系统，或在 `CLAUDE.md` 中写入持久化规则。重要的上下文信息应该写入 `CLAUDE.md` 而不是依赖对话记忆。

### Q: 如何让 Claude 遵守特定的编码规范？
**A:** 在 `CLAUDE.md` 中详细描述编码规范，包括命名约定、文件结构、注释规范等。Claude 每次会话都会自动加载。

### Q: Claude 执行了危险操作怎么办？
**A:** 立即按 `Ctrl+C` 中止。之后在 `settings.json` 的 `deny` 列表中添加该命令，防止再次发生。

### Q: 如何提高 Claude 回答的准确性？
**A:** 提供更多上下文（文件引用、错误信息、期望结果），并在 `CLAUDE.md` 中描述项目架构和技术栈。

### Q: MCP 服务器连接失败怎么办？
**A:** 运行 `/mcp` 查看服务器状态，运行 `/doctor` 诊断问题，检查 API Key 是否正确配置在环境变量中。

---

*本手册最后更新：2026 年 3 月*
*官方文档：https://docs.anthropic.com/claude-code*
