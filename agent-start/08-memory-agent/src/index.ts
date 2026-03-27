import Anthropic from "@anthropic-ai/sdk";
import "dotenv/config";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

// 记忆条目类型
interface MemoryEntry {
  id: string;
  type: "偏好" | "事实" | "技能" | "决策";
  content: string;
  timestamp: number;
  accessCount: number;
}

// 用户记忆库（生产环境持久化到数据库或文件）
class MemoryStore {
  private memories: MemoryEntry[] = [];
  private nextId = 1;

  // 添加记忆
  add(type: MemoryEntry["type"], content: string): void {
    this.memories.push({
      id: `m${this.nextId++}`,
      type,
      content,
      timestamp: Date.now(),
      accessCount: 0,
    });
  }

  // 检索相关记忆（关键词匹配，生产环境用向量搜索）
  retrieve(query: string, topK = 5): MemoryEntry[] {
    const words = query.toLowerCase().split(/\s+/);
    const scored = this.memories.map((m) => {
      const score = words.filter((w) => m.content.toLowerCase().includes(w)).length;
      return { memory: m, score };
    });

    return scored
      .filter((s) => s.score > 0)
      .sort((a, b) => {
        // 综合相关性 + 新鲜度排序
        const freshnessA = 1 / (1 + (Date.now() - a.memory.timestamp) / 86400000);
        const freshnessB = 1 / (1 + (Date.now() - b.memory.timestamp) / 86400000);
        return b.score + freshnessB - (a.score + freshnessA);
      })
      .slice(0, topK)
      .map((s) => {
        s.memory.accessCount++;
        return s.memory;
      });
  }

  // 获取所有记忆摘要
  summary(): string {
    if (this.memories.length === 0) return "（暂无记忆）";
    return this.memories
      .map((m) => `[${m.type}] ${m.content}`)
      .join("\n");
  }

  count(): number {
    return this.memories.length;
  }
}

// 从对话中提取新记忆
async function extractMemories(
  userMessage: string,
  assistantResponse: string
): Promise<Array<{ type: MemoryEntry["type"]; content: string }>> {
  const response = await client.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 256,
    system: `从对话中提取关于用户的关键信息。
只提取明确表达的信息，不要推测。
返回 JSON 数组（可为空数组）：
[{"type": "偏好|事实|技能|决策", "content": "具体描述"}]
不含其他文字。`,
    messages: [
      {
        role: "user",
        content: `用户说：${userMessage}\nAI 回复：${assistantResponse}`,
      },
    ],
  });

  const text = response.content[0].type === "text" ? response.content[0].text : "[]";
  const match = text.match(/\[[\s\S]*\]/);
  try {
    return JSON.parse(match?.[0] ?? "[]");
  } catch {
    return [];
  }
}

// 记忆增强 Agent 主逻辑
class MemoryAgent {
  private store = new MemoryStore();
  private userId: string;

  constructor(userId: string) {
    this.userId = userId;
  }

  async chat(message: string): Promise<string> {
    console.log(`\n[用户 ${this.userId}] ${message}`);

    // 检索相关记忆
    const relevantMemories = this.store.retrieve(message);
    const memoryContext = relevantMemories.length > 0
      ? `关于用户的已知信息：\n${relevantMemories.map((m) => `- [${m.type}] ${m.content}`).join("\n")}`
      : "";

    if (relevantMemories.length > 0) {
      console.log(`  检索到 ${relevantMemories.length} 条相关记忆`);
    }

    // 生成响应
    const response = await client.messages.create({
      model: "claude-opus-4-6",
      max_tokens: 1024,
      system: `你是一个有记忆的个人助手，能记住用户的偏好和历史信息，提供个性化服务。
${memoryContext}

根据已知的用户信息提供个性化回答，自然地融入记忆（无需明说"我记得..."）。`,
      messages: [{ role: "user", content: message }],
    });

    const reply = response.content[0].type === "text" ? response.content[0].text : "";
    console.log(`[助手] ${reply}`);

    // 提取并存储新记忆
    const newMemories = await extractMemories(message, reply);
    for (const mem of newMemories) {
      this.store.add(mem.type, mem.content);
      console.log(`  💾 新记忆：[${mem.type}] ${mem.content}`);
    }

    return reply;
  }

  showMemories(): void {
    console.log(`\n📚 用户 ${this.userId} 的记忆库（共 ${this.store.count()} 条）：\n${this.store.summary()}`);
  }
}

// 入口：模拟多轮对话
async function main() {
  const agent = new MemoryAgent("user-001");
  console.log("=".repeat(50));

  await agent.chat("你好！我是一名前端开发者，主要用 TypeScript 和 React。");
  await agent.chat("我最近在学 AI Agent 开发，对 ReAct 架构很感兴趣。");
  await agent.chat("能给我推荐一个适合我的 Agent 学习路径吗？");

  agent.showMemories();
}

main();
