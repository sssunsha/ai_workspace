import Anthropic from "@anthropic-ai/sdk";
import "dotenv/config";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

interface Task {
  id: string;
  description: string;
  dependencies: string[];
  status: "pending" | "running" | "done";
  result?: string;
}

// 规划阶段：将目标分解为子任务
async function plan(goal: string): Promise<Task[]> {
  console.log(`\n[规划阶段] 目标：${goal}`);

  const response = await client.messages.create({
    model: "claude-opus-4-6",
    max_tokens: 2048,
    system: `你是一个任务规划专家。将用户目标分解为具体、可执行的子任务列表。
返回严格的 JSON 数组，格式如下（不要包含任何其他文字）：
[
  { "id": "t1", "description": "子任务描述", "dependencies": [] },
  { "id": "t2", "description": "子任务描述", "dependencies": ["t1"] }
]`,
    messages: [{ role: "user", content: `目标：${goal}` }],
  });

  const text = response.content[0].type === "text" ? response.content[0].text : "[]";
  const jsonMatch = text.match(/\[[\s\S]*\]/);

  const rawTasks: Omit<Task, "status">[] = JSON.parse(jsonMatch?.[0] ?? "[]");
  const tasks: Task[] = rawTasks.map((t) => ({ ...t, status: "pending" }));

  console.log(`[规划结果] 共 ${tasks.length} 个子任务：`);
  tasks.forEach((t) => console.log(`  - [${t.id}] ${t.description}`));

  return tasks;
}

// 执行单个子任务
async function executeTask(task: Task, context: Map<string, string>): Promise<string> {
  const depContext = task.dependencies
    .map((dep) => `[${dep}] ${context.get(dep) ?? ""}`)
    .join("\n");

  const response = await client.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 1024,
    system: "你是一个任务执行专家，请完成分配给你的具体子任务，输出简洁的结果。",
    messages: [
      {
        role: "user",
        content: `子任务：${task.description}${depContext ? `\n\n前置任务结果：\n${depContext}` : ""}`,
      },
    ],
  });

  return response.content[0].type === "text" ? response.content[0].text : "";
}

// 执行阶段：按拓扑顺序并发执行
async function execute(tasks: Task[]): Promise<Map<string, string>> {
  console.log(`\n[执行阶段] 开始执行...`);
  const results = new Map<string, string>();
  const remaining = [...tasks];

  while (remaining.some((t) => t.status !== "done")) {
    // 找出所有依赖已完成的待执行任务
    const ready = remaining.filter(
      (t) =>
        t.status === "pending" &&
        t.dependencies.every((dep) => results.has(dep))
    );

    if (ready.length === 0) break;

    // 并发执行所有就绪任务
    await Promise.all(
      ready.map(async (task) => {
        task.status = "running";
        console.log(`  执行中：[${task.id}] ${task.description}`);
        const result = await executeTask(task, results);
        results.set(task.id, result);
        task.status = "done";
        console.log(`  完成：[${task.id}]`);
      })
    );
  }

  return results;
}

// 聚合阶段：整合所有结果
async function aggregate(goal: string, results: Map<string, string>): Promise<string> {
  const allResults = Array.from(results.entries())
    .map(([id, result]) => `[${id}]：${result}`)
    .join("\n\n");

  const response = await client.messages.create({
    model: "claude-opus-4-6",
    max_tokens: 2048,
    system: "你是一个结果整合专家，请将所有子任务结果综合成连贯的最终答案。",
    messages: [
      {
        role: "user",
        content: `原始目标：${goal}\n\n各子任务结果：\n${allResults}`,
      },
    ],
  });

  return response.content[0].type === "text" ? response.content[0].text : "";
}

// 主流程
async function planAndExecute(goal: string): Promise<void> {
  const tasks = await plan(goal);
  const results = await execute(tasks);
  const finalAnswer = await aggregate(goal, results);

  console.log(`\n${"=".repeat(50)}\n[最终结果]\n${finalAnswer}`);
}

// 入口
planAndExecute("撰写一篇关于 AI Agent 技术趋势的简短报告，包括定义、主要架构、应用场景和未来展望");
