import Anthropic from "@anthropic-ai/sdk";
import type { SearchResult, RetrievalConfig } from "../types.js";
import { VectorStore } from "./vectorStore.js";
import { embedText } from "../embedding/embedder.js";

const DEFAULT_CONFIG: RetrievalConfig = {
  topK: 6,
  rerankTopK: 3,
  useRerank: true,
  scoreThreshold: 0,
};

/**
 * LLM 重排序
 * 对初步检索结果按与问题的相关性重新打分，提升 Top-K 精度
 *
 * 生产环境可替换为：
 * - Cohere Rerank API（性能更高，延迟更低）
 *   import { CohereClient } from "cohere-ai";
 *   const cohere = new CohereClient({ token: process.env.COHERE_API_KEY });
 *   const reranked = await cohere.rerank({ query, documents, topN: rerankTopK });
 */
async function rerankWithLLM(
  client: Anthropic,
  question: string,
  results: SearchResult[],
  topK: number
): Promise<SearchResult[]> {
  if (results.length === 0) return [];

  const docsText = results
    .map((r, i) => `[文档${i + 1}] (来源: ${r.chunk.docTitle})\n${r.chunk.content}`)
    .join("\n\n");

  const response = await client.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 256,
    system: `你是一个相关性评估专家。为每篇文档与问题的相关程度打分（0-10整数）。
只输出 JSON 数组，格式：[{"index": 0, "score": 8}, {"index": 1, "score": 3}, ...]
index 从 0 开始，对应文档编号减 1。`,
    messages: [
      {
        role: "user",
        content: `问题：${question}\n\n文档列表：\n${docsText}`,
      },
    ],
  });

  const text = response.content[0].type === "text" ? response.content[0].text : "[]";
  const match = text.match(/\[[\s\S]*\]/);

  try {
    const scores: Array<{ index: number; score: number }> = JSON.parse(match?.[0] ?? "[]");
    const reranked = scores
      .map(({ index, score }) => ({
        ...results[index],
        score: score / 10,   // 归一化到 0~1
      }))
      .sort((a, b) => b.score - a.score)
      .slice(0, topK)
      .map((r, i) => ({ ...r, rank: i + 1 }));

    return reranked;
  } catch {
    // 重排序失败时降级为原始排序
    return results.slice(0, topK).map((r, i) => ({ ...r, rank: i + 1 }));
  }
}

/**
 * 检索器：向量检索 + 可选重排序
 */
export async function retrieve(
  client: Anthropic,
  vectorStore: VectorStore,
  question: string,
  config: RetrievalConfig = DEFAULT_CONFIG
): Promise<{ results: SearchResult[]; rerankApplied: boolean }> {
  // 1. 查询向量化
  const queryEmbedding = embedText(question);

  // 2. 向量相似度检索
  const candidates = vectorStore.search(queryEmbedding, config.topK, config.scoreThreshold);
  console.log(`  [Retriever] 向量检索: ${candidates.length} 个候选`);

  // 3. 可选重排序
  if (config.useRerank && candidates.length > config.rerankTopK) {
    console.log(`  [Reranker] LLM 重排序 → 保留 Top-${config.rerankTopK}`);
    const reranked = await rerankWithLLM(client, question, candidates, config.rerankTopK);
    return { results: reranked, rerankApplied: true };
  }

  return {
    results: candidates.slice(0, config.rerankTopK),
    rerankApplied: false,
  };
}
