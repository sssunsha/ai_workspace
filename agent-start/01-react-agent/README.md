# ReAct Agent（推理+行动）

## 架构说明

ReAct（Reasoning + Acting）是一种将**显式推理**与**工具调用行动**交替进行的 Agent 架构。Agent 在每一步先输出"思考"，再决定调用哪个工具，观察结果后继续推理，直到得出最终答案。

```
思考（Thought）→ 行动（Action/工具调用）→ 观察（Observation）→ 思考 → ... → 最终答案
```

### 核心组件

```
01-react-agent/
├── src/
│   ├── index.ts          # 入口：启动 ReAct 循环
│   ├── agent.ts          # ReAct Agent 核心逻辑
│   ├── tools/
│   │   ├── search.ts     # 搜索工具
│   │   ├── calculator.ts # 计算工具
│   │   └── index.ts      # 工具注册与调度
│   └── types.ts          # 类型定义
├── package.json
├── tsconfig.json
└── .env.example
```

## 工作原理

1. 用户提交查询
2. LLM 生成思考链（Chain-of-Thought）
3. LLM 决定调用某个工具
4. 执行工具，获取观察结果
5. 将观察结果反馈给 LLM，继续下一轮推理
6. 重复直到 LLM 输出最终答案（`end_turn`）

## 特点

| 项目 | 描述 |
|------|------|
| 可解释性 | ⭐⭐⭐⭐⭐ 推理链完全透明 |
| Token 消耗 | 高（每步都有推理文本） |
| 调试难度 | 低（每步可观测） |
| 并发能力 | 弱（串行推理） |

## 适用场景

- 需要**审计追踪**的场景（金融、合规、法律）
- 多步骤**科学推理**与验证
- 复杂**数学/逻辑问题**求解
- 教育类问答（需要展示解题过程）

## 快速开始

```bash
# 安装依赖
npm install

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY

# 运行
npm run dev
```

## 参考资料

- [ReAct: Synergizing Reasoning and Acting in Language Models（论文）](https://arxiv.org/abs/2210.03629)
- [Anthropic Tool Use 文档](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Claude Messages API](https://docs.anthropic.com/en/api/messages)
- [LangChain ReAct Agent](https://python.langchain.com/docs/modules/agents/agent_types/react)
