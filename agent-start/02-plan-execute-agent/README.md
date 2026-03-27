# Plan-and-Execute Agent（计划与执行）

## 架构说明

Plan-and-Execute 将复杂任务分为两个独立阶段：**规划阶段**由一个高能力模型分解子任务，**执行阶段**由轻量模型逐步（或并行）完成各子任务。规划与执行解耦，大幅提升效率与可扩展性。

```
复杂目标 → [规划器] 分解为子任务列表 → [执行器] 并行/串行执行 → 聚合结果
```

### 核心组件

```
02-plan-execute-agent/
├── src/
│   ├── index.ts          # 入口
│   ├── planner.ts        # 规划器：调用强模型分解任务
│   ├── executor.ts       # 执行器：并发执行子任务
│   ├── aggregator.ts     # 聚合器：合并所有子任务结果
│   └── types.ts          # Task、Plan 等类型定义
├── package.json
├── tsconfig.json
└── .env.example
```

## 工作原理

1. **规划阶段**：用 `claude-opus-4-6` 将用户目标拆解为带依赖关系的子任务 DAG
2. **执行阶段**：用 `claude-haiku-4-5` 按拓扑顺序执行，无依赖的任务并行处理
3. **聚合阶段**：将所有子任务结果聚合成最终输出
4. **重规划**（可选）：若某子任务失败，触发局部重规划

## 特点

| 项目 | 描述 |
|------|------|
| 可扩展性 | ⭐⭐⭐⭐⭐ 支持数十个子任务并行 |
| Token 效率 | 高（执行器用轻量模型） |
| 灵活性 | 中（计划一旦确定较难动态调整） |
| 适合长任务 | ✅ |

## 适用场景

- **大规模数据处理**与 ETL 管道
- **研究报告**自动生成（多维度并行调研）
- **代码库**批量重构或分析
- 复杂**项目管理**自动化工作流

## 快速开始

```bash
npm install
cp .env.example .env
npm run dev
```

## 参考资料

- [Plan-and-Solve Prompting（论文）](https://arxiv.org/abs/2305.04091)
- [LangGraph Plan-and-Execute](https://langchain-ai.github.io/langgraph/tutorials/plan-and-execute/plan-and-execute/)
- [Anthropic Model Comparison](https://docs.anthropic.com/en/docs/about-claude/models)
- [并发任务调度模式](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#parallel-tool-use)
