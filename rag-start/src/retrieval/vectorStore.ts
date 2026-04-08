import type { EmbeddedChunk, SearchResult } from "../types.js";

/** 计算两个向量的余弦相似度 */
function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) return 0;
  let dot = 0, normA = 0, normB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  const denom = Math.sqrt(normA) * Math.sqrt(normB);
  return denom === 0 ? 0 : dot / denom;
}

/**
 * 内存向量库
 * 生产环境替换为：Pinecone / Qdrant / Weaviate / pgvector
 *
 * 替换示例（Pinecone）：
 *   import { Pinecone } from "@pinecone-database/pinecone";
 *   const pc = new Pinecone({ apiKey: process.env.PINECONE_API_KEY });
 *   const index = pc.index("my-index");
 *   await index.upsert(vectors);
 *   const results = await index.query({ vector, topK });
 */
export class VectorStore {
  private chunks: EmbeddedChunk[] = [];

  /** 批量写入 Chunk（upsert 语义：相同 id 覆盖） */
  upsert(chunks: EmbeddedChunk[]): void {
    for (const chunk of chunks) {
      const idx = this.chunks.findIndex((c) => c.id === chunk.id);
      if (idx >= 0) {
        this.chunks[idx] = chunk;
      } else {
        this.chunks.push(chunk);
      }
    }
    console.log(`  [VectorStore] 已存储 ${this.chunks.length} 个向量`);
  }

  /**
   * 向量相似度检索
   * @param queryEmbedding 查询向量
   * @param topK 返回前 K 个结果
   * @param scoreThreshold 相关性阈值，低于此值过滤
   */
  search(queryEmbedding: number[], topK: number, scoreThreshold = 0): SearchResult[] {
    const scored = this.chunks
      .map((chunk) => ({
        chunk,
        score: cosineSimilarity(queryEmbedding, chunk.embedding),
      }))
      .filter((r) => r.score >= scoreThreshold)
      .sort((a, b) => b.score - a.score)
      .slice(0, topK);

    return scored.map((r, i) => ({
      chunk: r.chunk,
      score: r.score,
      rank: i + 1,
    }));
  }

  /** 获取库中存储的 Chunk 总数 */
  size(): number {
    return this.chunks.length;
  }

  /** 按文档 ID 删除所有相关 Chunk */
  deleteByDocId(docId: string): number {
    const before = this.chunks.length;
    this.chunks = this.chunks.filter((c) => c.docId !== docId);
    return before - this.chunks.length;
  }
}
