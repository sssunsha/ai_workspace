# Reflexion Agent（自我反思）

## 架构说明

Reflexion 让 Agent 具备**自我批评与迭代改进**的能力。Agent 生成初始响应后，由一个评估器（可以是同一个 LLM）对输出打分、指出问题，然后 Agent 根据反馈迭代优化，直到输出满足质量门槛或达到最大迭代次数。

```
用户任务 → [生成器] 初始响应
               ↓
          [评估器] 打分 + 问题列表
               ↓ (若不满足要求)
          [改进器] 针对性优化
               ↓
          [评估器] 再次评估 → 循环直到通过
               ↓ (通过)
            最终答案
```

### 核心组件

```
04-reflexion-agent/
├── src/
│   ├── index.ts          # 入口
│   ├── generator.ts      # 初始内容生成器
│   ├── evaluator.ts      # 自我评估器（打分 + 问题识别）
│   ├── refiner.ts        # 针对性改进器
│   ├── loop.ts           # 反思循环控制
│   └── types.ts          # ReflectionResult 等类型
├── package.json
├── tsconfig.json
└── .env.example
```

## 工作原理

1. **生成**：基于用户任务生成初始响应
2. **评估**：从正确性、完整性、清晰度等维度打分（0-100）
3. **判断**：若分数 ≥ 阈值（如 85）或达到最大迭代次数，退出循环
4. **改进**：将评估中识别的具体问题作为上下文，生成改进版本
5. **重复**第 2-4 步

## 特点

| 项目 | 描述 |
|------|------|
| 输出质量 | ⭐⭐⭐⭐⭐ 迭代后质量显著提升 |
| Token 消耗 | 高（多轮生成+评估） |
| 自动化程度 | 高（无需人工干预） |
| 循环风险 | 需设置最大迭代次数防止死循环 |

## 适用场景

- **代码审查**与自动优化
- **学术写作**与论文润色
- **翻译质量**迭代提升
- **营销文案**多轮打磨
- **设计方案**评审与改进

## 快速开始

```bash
npm install
cp .env.example .env
npm run dev
```

## 参考资料

- [Reflexion: Language Agents with Verbal Reinforcement Learning（论文）](https://arxiv.org/abs/2303.11366)
- [Self-Refine: Iterative Refinement with Self-Feedback（论文）](https://arxiv.org/abs/2303.17651)
- [Constitutional AI（Anthropic）](https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback)
- [Critique-and-Revise Pattern](https://docs.anthropic.com/en/docs/build-with-claude/agents)
