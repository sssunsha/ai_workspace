import Anthropic from "@anthropic-ai/sdk";
import "dotenv/config";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

interface JudgmentResult {
  totalScore: number;
  dimensions: Record<string, number>;
  feedback: string;
  strengths: string[];
  weaknesses: string[];
  passed: boolean;
  recommendation: "发布" | "修改后发布" | "拒绝";
}

// 评分细则（Rubric）
const contentRubric = `
评估维度及权重：
1. 准确性（30分）：信息是否正确、无事实错误
2. 完整性（25分）：是否覆盖主题的关键要点
3. 清晰度（20分）：表达是否清晰、结构是否合理
4. 相关性（15分）：内容是否切题、无无关信息
5. 可读性（10分）：语言是否流畅、易于理解

通过标准：总分 >= 75，且准确性 >= 20
判决选项：发布 / 修改后发布 / 拒绝
`;

// Judge Agent：单篇评估
async function judgeContent(content: string, topic: string): Promise<JudgmentResult> {
  const response = await client.messages.create({
    model: "claude-opus-4-6",
    max_tokens: 1024,
    system: `你是一个严格、公正的内容评审专家。严格按照评分细则评估内容。
${contentRubric}

输出严格 JSON（不含其他文字）：
{
  "totalScore": <0-100整数>,
  "dimensions": {
    "准确性": <0-30>,
    "完整性": <0-25>,
    "清晰度": <0-20>,
    "相关性": <0-15>,
    "可读性": <0-10>
  },
  "feedback": "<总体评价>",
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["缺点1", "缺点2"],
  "passed": <true/false>,
  "recommendation": "<发布|修改后发布|拒绝>"
}`,
    messages: [
      {
        role: "user",
        content: `主题：${topic}\n\n待评估内容：\n${content}`,
      },
    ],
  });

  const text = response.content[0].type === "text" ? response.content[0].text : "{}";
  const match = text.match(/\{[\s\S]*\}/);

  return JSON.parse(match?.[0] ?? "{}") as JudgmentResult;
}

// 批量评估
async function batchJudge(
  items: Array<{ content: string; topic: string; label: string }>
): Promise<void> {
  console.log(`\n开始批量评估 ${items.length} 条内容...\n${"=".repeat(50)}`);

  const results = await Promise.all(
    items.map(async (item) => {
      const result = await judgeContent(item.content, item.topic);
      return { ...item, result };
    })
  );

  // 输出评估报告
  for (const { label, result } of results) {
    console.log(`\n【${label}】`);
    console.log(`  总分：${result.totalScore}/100`);
    console.log(`  维度：${Object.entries(result.dimensions).map(([k, v]) => `${k}=${v}`).join(", ")}`);
    console.log(`  判决：${result.recommendation}（${result.passed ? "✅ 通过" : "❌ 未通过"}）`);
    console.log(`  反馈：${result.feedback}`);
    if (result.weaknesses.length > 0) {
      console.log(`  改进点：${result.weaknesses.join("；")}`);
    }
  }

  // 统计摘要
  const passCount = results.filter((r) => r.result.passed).length;
  const avgScore = results.reduce((acc, r) => acc + r.result.totalScore, 0) / results.length;
  console.log(`\n${"=".repeat(50)}`);
  console.log(`[批量评估摘要] 总计：${results.length} | 通过：${passCount} | 平均分：${avgScore.toFixed(1)}`);
}

// 入口：演示批量评估
batchJudge([
  {
    label: "内容A（高质量）",
    topic: "TypeScript 泛型",
    content: `TypeScript 泛型是一种强大的类型系统特性，允许编写可复用的类型安全代码。
泛型通过类型参数（如 <T>）实现，在调用时由编译器推断或手动指定具体类型。
例如：function identity<T>(arg: T): T { return arg; }
泛型广泛用于数组、Promise、React 组件等场景，是 TypeScript 类型系统的核心。`,
  },
  {
    label: "内容B（低质量）",
    topic: "TypeScript 泛型",
    content: "泛型就是用 T 来表示类型。用起来很方便，可以写很多代码。",
  },
]);
