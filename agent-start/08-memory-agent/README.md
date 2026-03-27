# Memory-Augmented Agent（记忆增强）

## 架构说明

Memory-Augmented Agent 为 LLM 添加**持久化记忆层**，使 Agent 能跨会话记住用户偏好、历史决策、关键事实等信息，提供个性化、连贯的长期交互体验。记忆分为多个层次：短期（上下文窗口）、长期（向量存储）、情节（交互历史）。

```
新对话轮 → [记忆检索] 相关历史记忆
               ↓
         [LLM + 记忆上下文] 生成响应
               ↓
         [记忆提取器] 从对话中提取新事实
               ↓
         [记忆存储] 持久化到记忆库
               ↓（下次对话循环复用）
```

### 核心组件

```
08-memory-agent/
├── src/
│   ├── index.ts              # 入口（多轮对话示例）
│   ├── agent.ts              # Memory Agent 主控制器
│   ├── memory/
│   │   ├── shortTerm.ts      # 短期记忆（当前会话窗口）
│   │   ├── longTerm.ts       # 长期记忆（向量存储）
│   │   ├── episodic.ts       # 情节记忆（交互历史摘要）
│   │   └── manager.ts        # 记忆管理器（读/写/遗忘）
│   ├── extractor.ts          # 记忆提取：从对话提取关键信息
│   ├── retriever.ts          # 记忆检索：相关记忆搜索
│   └── types.ts              # MemoryEntry、UserProfile 等类型
├── data/
│   └── memory-store.json     # 本地记忆持久化（示例）
├── package.json
├── tsconfig.json
└── .env.example
```

## 工作原理

1. **记忆检索**：新对话开始时，检索与当前话题相关的历史记忆
2. **上下文构建**：将相关记忆注入系统提示，增强 LLM 的背景认知
3. **响应生成**：LLM 结合记忆上下文生成个性化响应
4. **记忆提取**：对话结束后，用轻量模型提取新事实/偏好/决策
5. **记忆写入**：新记忆存入长期存储，旧记忆按时间衰减
6. **记忆整合**（可选）：定期压缩/合并冗余记忆

## 记忆类型

| 类型 | 存储内容 | 示例 |
|------|---------|------|
| 语义记忆 | 用户偏好、事实 | "用户偏好 TypeScript" |
| 情节记忆 | 历史交互摘要 | "上周帮用户调试了 React 项目" |
| 程序记忆 | 工作流偏好 | "用户喜欢先看代码再看解释" |

## 特点

| 项目 | 描述 |
|------|------|
| 个性化 | ⭐⭐⭐⭐⭐ 随使用时间持续提升 |
| 上下文连贯性 | ✅ 跨会话保持一致 |
| 隐私风险 | 需考虑数据安全与用户授权 |
| 存储成本 | 低（文本数据量小） |

## 适用场景

- **个人 AI 助手**（记住工作习惯、技术栈偏好）
- **长期学习辅导**（记录知识掌握程度）
- **对话式推荐系统**（积累用户兴趣图谱）
- **CRM 智能助手**（客户历史与偏好）
- **团队知识管理**（记住项目决策历史）

## 快速开始

```bash
npm install
cp .env.example .env
npm run dev
```

## 参考资料

- [MemGPT: LLMs as Operating Systems（论文）](https://arxiv.org/abs/2310.08560)
- [A Survey on Memory for LLM-based Agents（论文）](https://arxiv.org/abs/2404.01907)
- [Zep: 开源 Agent 记忆框架](https://github.com/getzep/zep)
- [Mem0: 个人 AI 记忆层](https://github.com/mem0ai/mem0)
- [Anthropic Long Context Best Practices](https://docs.anthropic.com/en/docs/build-with-claude/context-windows)
