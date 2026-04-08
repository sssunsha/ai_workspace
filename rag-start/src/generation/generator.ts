import Anthropic from "@anthropic-ai/sdk";
import type { SearchResult, RAGResult } from "../types.js";

/**
 * 基于检索结果生成答案
 * - 将 Top-K 文档注入上下文
 * - 要求模型标注引用来源
 * - 当文档不足时明确告知，避免幻觉
 */
export async function generate(
  client: Anthropic,
  question: string,
  results: SearchResult[],
  rerankApplied: boolean
): Promise<RAGResult> {
  const context = results
    .map(
      (r, i) =>
        `【来源${i + 1}】${r.chunk.docTitle}（相关度: ${(r.score * 100).toFixed(0)}%）\n${r.chunk.content}`
    )
    .join("\n\n---\n\n");

  const response = await client.messages.create({
    model: "claude-opus-4-6",
    max_tokens: 1024,
    system: `你是一个基于知识库的问答助手。请严格遵循以下规则：

1. 优先基于提供的参考文档回答，用【来源X】标注引用
2. 若文档内容不足，可补充通用知识，但需注明"（通用知识）"
3. 若问题与所有文档均无关，直接说明"知识库中未找到相关信息"
4. 回答要简洁、准确、有条理`,
    messages: [
      {
        role: "user",
        content: `参考文档：\n${context}\n\n问题：${question}`,
      },
    ],
  });

  const answer = response.content[0].type === "text" ? response.content[0].text : "";

  return {
    question,
    answer,
    sources: results.map((r) => ({
      docId: r.chunk.docId,
      docTitle: r.chunk.docTitle,
      chunkId: r.chunk.id,
      source: r.chunk.source,
      score: r.score,
    })),
    retrievedChunks: results.length,
    rerankApplied,
  };
}
