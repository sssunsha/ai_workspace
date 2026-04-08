import Anthropic from "@anthropic-ai/sdk";
import "dotenv/config";
import { sampleDocuments } from "../data/knowledge-base.js";
import { ingestDocuments } from "./ingestion/chunker.js";
import { embedChunks } from "./embedding/embedder.js";
import { VectorStore } from "./retrieval/vectorStore.js";
import { retrieve } from "./retrieval/retriever.js";
import { generate } from "./generation/generator.js";
import type { RAGResult, RetrievalConfig } from "./types.js";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

/** 格式化打印 RAG 结果 */
function printResult(result: RAGResult): void {
  console.log(`\n${"=".repeat(60)}`);
  console.log(`❓ 问题：${result.question}`);
  console.log(`${"─".repeat(60)}`);
  console.log(`💬 答案：\n${result.answer}`);
  console.log(`${"─".repeat(60)}`);
  console.log(`📚 引用来源（共 ${result.retrievedChunks} 个片段，重排序: ${result.rerankApplied ? "✅" : "❌"}）：`);
  result.sources.forEach((s, i) => {
    console.log(`  [${i + 1}] ${s.docTitle} — 相关度 ${(s.score * 100).toFixed(0)}%`);
  });
}

async function main(): Promise<void> {
  console.log("🚀 RAG 管道启动\n");

  // ── 阶段 1：文档摄入（离线，仅首次或文档更新时执行） ──
  console.log("📥 [阶段 1] 文档摄入与分块...");
  const chunks = ingestDocuments(sampleDocuments, {
    chunkSize: 300,
    chunkOverlap: 50,
  });
  console.log(`  分块完成：${sampleDocuments.length} 篇文档 → ${chunks.length} 个 Chunk`);

  // ── 阶段 2：向量化并存入向量库 ──
  console.log("\n🔢 [阶段 2] 文本向量化...");
  const embeddedChunks = embedChunks(chunks);

  const vectorStore = new VectorStore();
  vectorStore.upsert(embeddedChunks);

  // ── 阶段 3：在线查询 ──
  console.log("\n🔍 [阶段 3] 开始在线查询...");

  const retrievalConfig: RetrievalConfig = {
    topK: 6,
    rerankTopK: 3,
    useRerank: true,
    scoreThreshold: 0,
  };

  const questions = [
    "RAG 有哪些主要优势和挑战？",
    "向量数据库应该怎么选型？",
    "文本分块有哪些策略，各自的优缺点是什么？",
    "高级 RAG 中的混合检索是什么原理？",
  ];

  for (const question of questions) {
    console.log(`\n🔎 检索中：${question}`);

    const { results, rerankApplied } = await retrieve(
      client,
      vectorStore,
      question,
      retrievalConfig
    );

    const ragResult = await generate(client, question, results, rerankApplied);
    printResult(ragResult);
  }
}

main().catch(console.error);
