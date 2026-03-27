import Anthropic from "@anthropic-ai/sdk";
import "dotenv/config";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

// 工具定义（会传给 LLM 的 Schema）
const tools: Anthropic.Messages.Tool[] = [
  {
    name: "get_weather",
    description: "获取指定城市的当前天气信息",
    input_schema: {
      type: "object" as const,
      properties: {
        city: { type: "string", description: "城市名称，如：北京、上海、深圳" },
      },
      required: ["city"],
    },
  },
  {
    name: "get_time",
    description: "获取当前日期和时间",
    input_schema: {
      type: "object" as const,
      properties: {
        timezone: { type: "string", description: "时区，如：Asia/Shanghai（可选，默认本地时间）" },
      },
      required: [],
    },
  },
  {
    name: "query_database",
    description: "查询数据库中的用户或订单信息",
    input_schema: {
      type: "object" as const,
      properties: {
        table: { type: "string", enum: ["users", "orders"], description: "要查询的表名" },
        id: { type: "string", description: "记录 ID" },
      },
      required: ["table", "id"],
    },
  },
];

// 工具执行器（模拟实现，生产环境替换为真实 API 调用）
function executeTool(name: string, input: Record<string, string>): string {
  switch (name) {
    case "get_weather":
      return JSON.stringify({
        city: input.city,
        temperature: "22°C",
        condition: "晴朗",
        humidity: "45%",
        wind: "东北风 3 级",
      });

    case "get_time":
      return JSON.stringify({
        datetime: new Date().toLocaleString("zh-CN", {
          timeZone: input.timezone ?? "Asia/Shanghai",
        }),
        timezone: input.timezone ?? "Asia/Shanghai",
      });

    case "query_database":
      if (input.table === "users") {
        return JSON.stringify({ id: input.id, name: "张三", email: "zhangsan@example.com", plan: "Pro" });
      }
      return JSON.stringify({ id: input.id, product: "Claude API 订阅", amount: "¥99", status: "已支付" });

    default:
      return JSON.stringify({ error: `未知工具：${name}` });
  }
}

// 工具调用 Agent 主循环
async function toolUseAgent(userQuery: string): Promise<void> {
  console.log(`\n用户请求：${userQuery}\n${"=".repeat(50)}`);

  const messages: Anthropic.Messages.MessageParam[] = [
    { role: "user", content: userQuery },
  ];

  while (true) {
    const response = await client.messages.create({
      model: "claude-opus-4-6",
      max_tokens: 2048,
      tools,
      messages,
    });

    // 打印文本内容
    const textBlocks = response.content.filter(
      (b): b is Anthropic.Messages.TextBlock => b.type === "text"
    );
    if (textBlocks.length > 0) {
      console.log(`\n[LLM] ${textBlocks.map((b) => b.text).join("")}`);
    }

    // 完成
    if (response.stop_reason === "end_turn") break;

    // 处理工具调用
    const toolUses = response.content.filter(
      (b): b is Anthropic.Messages.ToolUseBlock => b.type === "tool_use"
    );
    if (toolUses.length === 0) break;

    messages.push({ role: "assistant", content: response.content });

    const toolResults: Anthropic.Messages.ToolResultBlockParam[] = toolUses.map((toolUse) => {
      const result = executeTool(toolUse.name, toolUse.input as Record<string, string>);
      console.log(`\n[工具] ${toolUse.name}(${JSON.stringify(toolUse.input)})`);
      console.log(`[结果] ${result}`);
      return {
        type: "tool_result" as const,
        tool_use_id: toolUse.id,
        content: result,
      };
    });

    messages.push({ role: "user", content: toolResults });
  }

  // 最终回答
  const lastMessage = messages[messages.length - 1];
  if (lastMessage.role === "assistant") {
    const finalText = Array.isArray(lastMessage.content)
      ? lastMessage.content
          .filter((b): b is Anthropic.Messages.TextBlock => b.type === "text")
          .map((b) => b.text)
          .join("")
      : String(lastMessage.content);
    console.log(`\n${"=".repeat(50)}\n[最终答案]\n${finalText}`);
  }
}

// 入口
toolUseAgent("帮我查一下北京今天的天气，同时告诉我现在的时间，另外查询用户 ID 为 U-001 的账户信息。");
