import Anthropic from "@anthropic-ai/sdk";
import "dotenv/config";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

interface EvaluationResult {
  score: number;
  issues: string[];
  passed: boolean;
}

// 生成初始响应
async function generate(task: string): Promise<string> {
  const response = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 1024,
    messages: [{ role: "user", content: task }],
  });
  return response.content[0].type === "text" ? response.content[0].text : "";
}

// 自我评估
async function evaluate(task: string, response: string): Promise<EvaluationResult> {
  const evalResponse = await client.messages.create({
    model: "claude-opus-4-6",
    max_tokens: 512,
    system: `你是一个严格的质量评审专家。评估以下维度：
1. 正确性（是否有事实错误）
2. 完整性（是否覆盖所有要点）
3. 清晰度（表达是否清晰易懂）
4. 相关性（是否切题）

输出严格 JSON（不含其他文字）：
{"score": <0-100整数>, "issues": ["问题1", "问题2"], "passed": <true/false>}

通过标准：score >= 80，issues 为空或极少。`,
    messages: [
      {
        role: "user",
        content: `任务：${task}\n\n待评估响应：\n${response}`,
      },
    ],
  });

  const text = evalResponse.content[0].type === "text" ? evalResponse.content[0].text : "{}";
  const match = text.match(/\{[\s\S]*\}/);

  try {
    return JSON.parse(match?.[0] ?? '{"score": 0, "issues": ["解析失败"], "passed": false}');
  } catch {
    return { score: 0, issues: ["评估解析失败"], passed: false };
  }
}

// 针对问题改进
async function refine(task: string, current: string, issues: string[]): Promise<string> {
  const response = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 1024,
    system: "你是一个内容改进专家，根据指出的具体问题对内容进行针对性优化。",
    messages: [
      {
        role: "user",
        content: `原始任务：${task}

当前版本：
${current}

需要改进的问题：
${issues.map((issue, i) => `${i + 1}. ${issue}`).join("\n")}

请输出改进后的完整版本：`,
      },
    ],
  });
  return response.content[0].type === "text" ? response.content[0].text : current;
}

// Reflexion 主循环
async function reflexionAgent(task: string, maxIterations = 3): Promise<void> {
  console.log(`\n任务：${task}\n${"=".repeat(50)}`);

  // 初始生成
  let current = await generate(task);
  console.log(`\n[第 0 轮] 初始版本：\n${current}`);

  for (let i = 1; i <= maxIterations; i++) {
    console.log(`\n${"─".repeat(40)}\n[评估第 ${i} 轮]`);

    const evaluation = await evaluate(task, current);
    console.log(`  评分：${evaluation.score}/100`);
    console.log(`  通过：${evaluation.passed ? "✅" : "❌"}`);
    if (evaluation.issues.length > 0) {
      console.log(`  问题：\n${evaluation.issues.map((p) => `    - ${p}`).join("\n")}`);
    }

    if (evaluation.passed) {
      console.log(`\n✅ 质量达标，结束迭代（${i - 1} 次改进）`);
      break;
    }

    if (i === maxIterations) {
      console.log(`\n⚠️  已达最大迭代次数（${maxIterations}），使用当前最优版本`);
      break;
    }

    // 针对性改进
    console.log(`\n[改进第 ${i} 轮]`);
    current = await refine(task, current, evaluation.issues);
    console.log(`  改进完成`);
  }

  console.log(`\n${"=".repeat(50)}\n[最终输出]\n${current}`);
}

// 入口
reflexionAgent("用简洁的语言解释什么是 TypeScript 泛型，并给出一个实用的代码示例，要求：面向初学者、包含注释、示例完整可运行");
