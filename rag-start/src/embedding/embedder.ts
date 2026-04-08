import type { Chunk, EmbeddedChunk } from "../types.js";

/**
 * 嵌入接口——替换此实现接入真实向量模型
 *
 * 推荐替换方案：
 * 1. Voyage AI（Anthropic 推荐）
 *    import VoyageAI from "voyageai";
 *    const client = new VoyageAI({ apiKey: process.env.VOYAGE_API_KEY });
 *    const result = await client.embed({ input: texts, model: "voyage-3" });
 *
 * 2. OpenAI Embeddings
 *    import OpenAI from "openai";
 *    const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
 *    const result = await openai.embeddings.create({ model: "text-embedding-3-small", input: texts });
 */

/**
 * 模拟嵌入：基于字符频率生成伪向量
 * 仅用于本地演示，不具备真实语义相似度能力
 */
function mockEmbed(text: string, dim = 64): number[] {
  const vector = new Array(dim).fill(0);
  for (let i = 0; i < text.length; i++) {
    vector[i % dim] += text.charCodeAt(i) / 1000;
  }
  // L2 归一化
  const norm = Math.sqrt(vector.reduce((s, v) => s + v * v, 0)) || 1;
  return vector.map((v) => v / norm);
}

/**
 * 单条文本嵌入
 * 替换为真实嵌入 API 时，注意改为 async
 */
export function embedText(text: string): number[] {
  return mockEmbed(text);
}

/**
 * 批量嵌入 Chunk 列表
 * 生产环境中真实 API 支持批量调用，效率更高
 */
export function embedChunks(chunks: Chunk[]): EmbeddedChunk[] {
  console.log(`  [Embedder] 嵌入 ${chunks.length} 个 Chunk...`);
  return chunks.map((chunk) => ({
    ...chunk,
    embedding: embedText(chunk.content),
  }));
}
