import Anthropic from "@anthropic-ai/sdk";
import "dotenv/config";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

// 工具定义
const tools: Anthropic.Messages.Tool[] = [
  {
    name: "search",
    description: "搜索互联网上的信息",
    input_schema: {
      type: "object" as const,
      properties: {
        query: { type: "string", description: "搜索关键词" },
      },
      required: ["query"],
    },
  },
  {
    name: "calculator",
    description: "执行数学计算",
    input_schema: {
      type: "object" as const,
      properties: {
        expression: { type: "string", description: "数学表达式，如 '2 + 3 * 4'" },
      },
      required: ["expression"],
    },
  },
];

// 模拟工具执行
function executeTool(name: string, input: Record<string, string>): string {
  if (name === "search") {
    return `搜索"${input.query}"的结果：[模拟数据] Claude 是由 Anthropic 于 2023 年发布的 AI 助手。`;
  }
  if (name === "calculator") {
    try {
      // 仅用于演示，生产环境请使用安全的表达式解析器
      const result = Function(`"use strict"; return (${input.expression})`)();
      return `计算结果：${input.expression} = ${result}`;
    } catch {
      return `计算失败：表达式无效`;
    }
  }
  return `未知工具：${name}`;
}

// ReAct 主循环
async function reactAgent(userQuery: string): Promise<void> {
  console.log(`\n用户问题：${userQuery}\n${"=".repeat(50)}`);

  const messages: Anthropic.Messages.MessageParam[] = [
    { role: "user", content: userQuery },
  ];

  let step = 0;

  while (true) {
    step++;
    console.log(`\n[步骤 ${step}] 调用 LLM...`);

    const response = await client.messages.create({
      model: "claude-opus-4-6",
      max_tokens: 4096,
      system: `你是一个 ReAct Agent，在回答前需要逐步推理并使用工具收集信息。
推理格式：
- 先输出思考过程（Thought）
- 再决定使用哪个工具（Action）
- 观察工具结果（Observation）
- 最后给出最终答案`,
      tools,
      messages,
    });

    // 打印文本内容（思考链）
    for (const block of response.content) {
      if (block.type === "text" && block.text.trim()) {
        console.log(`\n[思考]\n${block.text}`);
      }
    }

    // 结束：无工具调用
    if (response.stop_reason === "end_turn") {
      const finalText = response.content
        .filter((b): b is Anthropic.Messages.TextBlock => b.type === "text")
        .map((b) => b.text)
        .join("");
      console.log(`\n${"=".repeat(50)}\n[最终答案]\n${finalText}`);
      break;
    }

    // 处理工具调用
    const toolUses = response.content.filter(
      (b): b is Anthropic.Messages.ToolUseBlock => b.type === "tool_use"
    );

    if (toolUses.length === 0) break;

    messages.push({ role: "assistant", content: response.content });

    const toolResults: Anthropic.Messages.ToolResultBlockParam[] = [];

    for (const toolUse of toolUses) {
      const result = executeTool(toolUse.name, toolUse.input as Record<string, string>);
      console.log(`\n[工具调用] ${toolUse.name}(${JSON.stringify(toolUse.input)})`);
      console.log(`[观察] ${result}`);
      toolResults.push({
        type: "tool_result",
        tool_use_id: toolUse.id,
        content: result,
      });
    }

    messages.push({ role: "user", content: toolResults });
  }
}

// 入口
reactAgent("Claude 是什么时候发布的？另外帮我计算 (15 * 8 + 120) / 6 的结果。");
