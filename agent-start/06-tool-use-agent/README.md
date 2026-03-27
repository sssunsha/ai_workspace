# Tool-Use / Function Calling Agent（工具调用）

## 架构说明

Tool-Use Agent 是最基础也是使用最广泛的 Agent 架构。LLM 通过**结构化工具定义**感知可用能力，在推理中决定何时、以何种参数调用外部工具（API、数据库、系统命令等），并将工具返回结果融入后续推理。

```
用户请求 → LLM 识别所需工具
               ↓
         [工具调度器] 路由到对应工具
               ↓
         [工具执行] API/DB/文件系统/计算
               ↓
         [LLM] 将结果融入推理，继续或结束
               ↓
            最终答案
```

### 核心组件

```
06-tool-use-agent/
├── src/
│   ├── index.ts            # 入口
│   ├── agent.ts            # 工具调用循环控制
│   ├── tools/
│   │   ├── weather.ts      # 天气查询工具
│   │   ├── database.ts     # 数据库查询工具
│   │   ├── filesystem.ts   # 文件读写工具
│   │   ├── httpRequest.ts  # HTTP 请求工具
│   │   └── registry.ts     # 工具注册表
│   ├── executor.ts         # 工具执行器（含错误处理）
│   └── types.ts            # Tool、ToolResult 等类型
├── package.json
├── tsconfig.json
└── .env.example
```

## 工作原理

1. 将工具定义（名称、描述、参数 Schema）传入 LLM
2. LLM 推理后决定是否调用工具及调用参数
3. `stop_reason === "tool_use"` 时，提取工具调用信息
4. 执行对应工具函数，获取结果
5. 将 `tool_result` 追加到消息历史，继续 LLM 推理
6. 重复直到 `stop_reason === "end_turn"`

## 特点

| 项目 | 描述 |
|------|------|
| 可扩展性 | ⭐⭐⭐⭐⭐ 随时添加新工具 |
| 实时数据 | ✅ 每次调用获取最新数据 |
| Token 效率 | 高（工具结果通常简洁） |
| 错误处理 | 关键（工具失败需优雅降级） |

## 适用场景

- **API 集成自动化**（CRM、ERP、第三方服务）
- **数据库智能查询**（自然语言转 SQL）
- **DevOps 自动化**（部署、监控、告警）
- **IoT 设备控制**
- **日历/邮件/任务管理**助手

## 快速开始

```bash
npm install
cp .env.example .env
npm run dev
```

## 参考资料

- [Anthropic Tool Use 完整指南](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [并行工具调用](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#parallel-tool-use)
- [Tool Use Best Practices](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#best-practices-for-tool-definitions)
- [Function Calling vs Tool Use 对比](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
