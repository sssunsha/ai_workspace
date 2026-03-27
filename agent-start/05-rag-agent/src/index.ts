import Anthropic from "@anthropic-ai/sdk";
import "dotenv/config";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

// 文档类型定义
interface Document {
  id: string;
  title: string;
  content: string;
  tags: string[];
}

// 模拟知识库（生产环境替换为向量数据库如 Pinecone/pgvector）
const knowledgeBase: Document[] = [
  {
    id: "doc-1",
    title: "Claude 简介",
    content: "Claude 是由 Anthropic 公司于 2023 年发布的 AI 助手。Anthropic 成立于 2021 年，由前 OpenAI 研究员创立，专注于 AI 安全研究。Claude 以安全性和有用性著称。",
    tags: ["claude", "anthropic", "ai助手"],
  },
  {
    id: "doc-2",
    title: "Claude API 能力",
    content: "Claude API 支持工具调用（Tool Use）、视觉理解（Vision）、流式响应（Streaming）、长上下文处理（最高 200K tokens）。支持 Python 和 TypeScript SDK。",
    tags: ["api", "工具调用", "视觉", "流式"],
  },
  {
    id: "doc-3",
    title: "RAG 技术概述",
    content: "RAG（Retrieval-Augmented Generation）是一种将信息检索与生成模型结合的架构。通过检索相关文档作为上下文，有效降低 LLM 的幻觉问题，并支持知识库的动态更新。",
    tags: ["rag", "检索", "幻觉", "知识库"],
  },
  {
    id: "doc-4",
    title: "Agent 架构对比",
    content: "主流 Agent 架构包括：ReAct（推理+行动）、Plan-Execute（计划执行）、Multi-Agent（多智能体）、RAG（检索增强）等。各架构有不同的适用场景和性能特点。",
    tags: ["agent", "架构", "react", "multi-agent"],
  },
];

// 简单关键词检索（生产环境替换为向量相似度搜索）
function retrieve(query: string, topK = 2): Document[] {
  const queryWords = query.toLowerCase().split(/\s+/);

  const scored = knowledgeBase.map((doc) => {
    const text = `${doc.title} ${doc.content} ${doc.tags.join(" ")}`.toLowerCase();
    const score = queryWords.reduce((acc, word) => {
      return acc + (text.includes(word) ? 1 : 0);
    }, 0);
    return { doc, score };
  });

  return scored
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, topK)
    .map((s) => s.doc);
}

// 基于检索结果生成答案
async function ragQuery(question: string): Promise<void> {
  console.log(`\n问题：${question}`);

  // 检索相关文档
  const relevantDocs = retrieve(question);

  if (relevantDocs.length === 0) {
    console.log("未在知识库中找到相关文档，将依靠模型自身知识回答。");
  } else {
    console.log(`\n[检索到 ${relevantDocs.length} 篇相关文档]`);
    relevantDocs.forEach((doc, i) => {
      console.log(`  [${i + 1}] ${doc.title} (ID: ${doc.id})`);
    });
  }

  // 构建上下文
  const context = relevantDocs
    .map((doc, i) => `【来源 ${i + 1}】${doc.title}（文档 ID: ${doc.id}）\n${doc.content}`)
    .join("\n\n");

  // 生成答案
  const response = await client.messages.create({
    model: "claude-opus-4-6",
    max_tokens: 1024,
    system: `你是一个基于知识库的问答助手。请优先根据提供的文档内容回答问题。
- 回答时请引用来源，格式为【来源 X】
- 如果文档不足以完整回答，可适当补充通用知识，但需注明
- 如果文档与问题无关，请如实告知`,
    messages: [
      {
        role: "user",
        content: relevantDocs.length > 0
          ? `参考文档：\n${context}\n\n问题：${question}`
          : `（知识库中无相关文档）问题：${question}`,
      },
    ],
  });

  const answer = response.content[0].type === "text" ? response.content[0].text : "";
  console.log(`\n${"=".repeat(50)}\n[答案]\n${answer}`);
}

// 入口
async function main() {
  await ragQuery("Claude 是什么时候发布的，由哪家公司开发？");
  await ragQuery("Claude API 支持哪些功能特性？");
}

main();
