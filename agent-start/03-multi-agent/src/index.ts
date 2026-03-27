import Anthropic from "@anthropic-ai/sdk";
import "dotenv/config";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

// 专家 Agent 定义
interface SpecialistAgent {
  name: string;
  role: string;
  systemPrompt: string;
  keywords: string[];
}

const specialists: Record<string, SpecialistAgent> = {
  research: {
    name: "研究专家",
    role: "research",
    systemPrompt: "你是一位信息研究专家，擅长收集、整理和分析信息，给出有据可查的研究结论。",
    keywords: ["研究", "查找", "信息", "资料", "了解", "什么是"],
  },
  analysis: {
    name: "分析专家",
    role: "analysis",
    systemPrompt: "你是一位数据分析专家，擅长从数据和信息中提取洞见、识别趋势和规律。",
    keywords: ["分析", "趋势", "对比", "评估", "优劣", "比较"],
  },
  coding: {
    name: "代码专家",
    role: "coding",
    systemPrompt: "你是一位资深软件工程师，精通 TypeScript/JavaScript，能提供高质量的代码示例和架构建议。",
    keywords: ["代码", "实现", "编程", "函数", "示例", "开发"],
  },
  writing: {
    name: "写作专家",
    role: "writing",
    systemPrompt: "你是一位专业技术写作专家，擅长将复杂概念用清晰、简洁的语言表达出来。",
    keywords: ["写作", "文章", "报告", "总结", "文档", "描述"],
  },
};

// Supervisor：路由决策
async function supervisorRoute(query: string): Promise<string[]> {
  const response = await client.messages.create({
    model: "claude-opus-4-6",
    max_tokens: 256,
    system: `你是一个任务路由器。根据用户查询，选择最合适的专家 Agent。
可用专家：research（研究）, analysis（分析）, coding（代码）, writing（写作）
返回 JSON 数组，如：["research", "coding"]（只包含专家名称，不含其他文字）`,
    messages: [{ role: "user", content: `查询：${query}` }],
  });

  const text = response.content[0].type === "text" ? response.content[0].text : "[]";
  const match = text.match(/\[[\s\S]*?\]/);
  return JSON.parse(match?.[0] ?? '["research"]');
}

// 调用单个专家 Agent
async function callSpecialist(agentKey: string, query: string): Promise<string> {
  const agent = specialists[agentKey];
  if (!agent) return `未知专家：${agentKey}`;

  console.log(`  [${agent.name}] 处理中...`);

  const response = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 1024,
    system: agent.systemPrompt,
    messages: [{ role: "user", content: query }],
  });

  return response.content[0].type === "text" ? response.content[0].text : "";
}

// Supervisor：聚合结果
async function supervisorAggregate(
  query: string,
  specialistResults: Record<string, string>
): Promise<string> {
  const context = Object.entries(specialistResults)
    .map(([key, result]) => `【${specialists[key]?.name ?? key}】\n${result}`)
    .join("\n\n---\n\n");

  const response = await client.messages.create({
    model: "claude-opus-4-6",
    max_tokens: 2048,
    system: "你是一个结果整合专家，将多位专家的意见综合成统一、连贯的最终答案。",
    messages: [
      {
        role: "user",
        content: `用户原始问题：${query}\n\n各专家意见：\n${context}`,
      },
    ],
  });

  return response.content[0].type === "text" ? response.content[0].text : "";
}

// 主流程
async function multiAgent(query: string): Promise<void> {
  console.log(`\n用户查询：${query}\n${"=".repeat(50)}`);

  // 1. 路由决策
  const selectedAgents = await supervisorRoute(query);
  console.log(`\n[Supervisor] 路由到专家：${selectedAgents.join(", ")}`);

  // 2. 并发调用专家 Agent
  console.log("\n[并发执行专家 Agent]");
  const resultEntries = await Promise.all(
    selectedAgents.map(async (agentKey) => {
      const result = await callSpecialist(agentKey, query);
      return [agentKey, result] as const;
    })
  );

  const specialistResults = Object.fromEntries(resultEntries);

  // 3. 聚合结果
  console.log("\n[Supervisor] 聚合结果...");
  const finalAnswer = await supervisorAggregate(query, specialistResults);

  console.log(`\n${"=".repeat(50)}\n[最终答案]\n${finalAnswer}`);
}

// 入口
multiAgent("请帮我分析 TypeScript 在企业级开发中的优势，并给出一个实际的代码示例说明类型安全的好处。");
