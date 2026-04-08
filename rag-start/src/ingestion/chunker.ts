import type { RawDocument, Chunk, ChunkConfig } from "../types.js";

const DEFAULT_CONFIG: ChunkConfig = {
  chunkSize: 300,      // 每块字符数（生产环境建议 512~1024 tokens）
  chunkOverlap: 50,    // 相邻块重叠字符数，减少上下文丢失
};

/**
 * 固定大小分块（带重叠）
 * 生产环境可替换为：
 * - LangChain RecursiveCharacterTextSplitter
 * - semantic-chunker（基于嵌入相似度切分）
 */
function chunkText(text: string, config: ChunkConfig): string[] {
  const { chunkSize, chunkOverlap } = config;
  const chunks: string[] = [];
  let start = 0;

  while (start < text.length) {
    const end = Math.min(start + chunkSize, text.length);
    chunks.push(text.slice(start, end).trim());
    if (end >= text.length) break;
    start += chunkSize - chunkOverlap;
  }

  return chunks.filter((c) => c.length > 0);
}

/**
 * 将原始文档切分为 Chunk 列表
 */
export function ingestDocument(doc: RawDocument, config: ChunkConfig = DEFAULT_CONFIG): Chunk[] {
  const textChunks = chunkText(doc.content, config);

  return textChunks.map((content, index) => ({
    id: `${doc.id}-chunk-${index}`,
    docId: doc.id,
    docTitle: doc.title,
    content,
    index,
    source: doc.source,
    metadata: doc.metadata,
  }));
}

/**
 * 批量摄入多个文档
 */
export function ingestDocuments(docs: RawDocument[], config?: ChunkConfig): Chunk[] {
  return docs.flatMap((doc) => ingestDocument(doc, config));
}
