# LLM-as-Judge / Critic Agent（LLM 评判者）

## 架构说明

Judge/Critic Agent 使用一个独立的 LLM 对其他 Agent 或流程的输出进行**结构化评估**，输出评分、详细反馈和通过/拒绝决策。它是构建**质量门控流水线**的关键组件，可独立运行也可嵌入其他架构（如 Reflexion）。

```
待评估内容（来自其他 Agent 或用户）
               ↓
         [Judge Agent] 按评分细则（Rubric）评估
               ↓
    ┌──────────┴──────────┐
  通过（Pass）          拒绝（Fail）
    ↓                      ↓
  发布/接受          返回反馈 → 触发改进
```

### 核心组件

```
07-judge-critic-agent/
├── src/
│   ├── index.ts           # 入口（批量评估示例）
│   ├── judge.ts           # Judge Agent 核心
│   ├── rubrics/
│   │   ├── codeReview.ts  # 代码审查评分细则
│   │   ├── contentQA.ts   # 内容质量评分细则
│   │   └── accuracy.ts    # 准确性评分细则
│   ├── batchEvaluator.ts  # 批量并发评估
│   ├── reporter.ts        # 评估报告生成
│   └── types.ts           # JudgmentResult 等类型
├── package.json
├── tsconfig.json
└── .env.example
```

## 工作原理

1. 定义**评分细则（Rubric）**：各维度权重、通过阈值
2. 将待评估内容 + Rubric 传入 Judge LLM
3. Judge 输出结构化 JSON：总分、各维度得分、具体问题、通过/拒绝
4. 根据判决结果触发后续流程（发布/重试/人工审核）
5. 支持**批量并发**评估多条内容

## 特点

| 项目 | 描述 |
|------|------|
| 一致性 | ⭐⭐⭐⭐⭐ 相同标准自动化评估 |
| 可解释性 | ⭐⭐⭐⭐ 评分有详细理由 |
| 评估偏差 | 需注意 LLM 可能倾向于高分 |
| 并发能力 | ✅ 支持批量并行评估 |

## 适用场景

- **内容发布流水线**质量门控
- **代码审查**自动化（安全性、可读性、性能）
- **学生作业**或考试自动评分
- **RAG 答案**相关性验证
- **A/B 测试**方案对比评判
- **LLM 输出**安全性与合规审查

## 快速开始

```bash
npm install
cp .env.example .env
npm run dev
```

## 参考资料

- [Judging LLM-as-a-Judge（论文）](https://arxiv.org/abs/2306.05685)
- [G-Eval: NLG Evaluation using GPT-4（论文）](https://arxiv.org/abs/2303.16634)
- [Prometheus: LLM 评估框架](https://arxiv.org/abs/2310.08491)
- [RAGAS: RAG 评估框架](https://github.com/explodinggradients/ragas)
- [Anthropic 安全评估最佳实践](https://www.anthropic.com/research/evaluating-ai-systems)
