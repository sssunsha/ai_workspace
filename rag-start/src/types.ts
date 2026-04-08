// 统一类型定义

/** 原始文档（摄入前） */
export interface RawDocument {
  id: string;
  title: string;
  content: string;
  source: string;
  metadata?: Record<string, string>;
}

/** 分块后的文档片段 */
export interface Chunk {
  id: string;
  docId: string;
  docTitle: string;
  content: string;
  index: number;           // 在原文中的片段序号
  source: string;
  metadata?: Record<string, string>;
}

/** 带向量的 Chunk（存入向量库后） */
export interface EmbeddedChunk extends Chunk {
  embedding: number[];
}

/** 检索结果（带相关性得分） */
export interface SearchResult {
  chunk: EmbeddedChunk;
  score: number;           // 余弦相似度，0~1
  rank: number;
}

/** 生成的最终答案 */
export interface RAGResult {
  question: string;
  answer: string;
  sources: Array<{
    docId: string;
    docTitle: string;
    chunkId: string;
    source: string;
    score: number;
  }>;
  retrievedChunks: number;
  rerankApplied: boolean;
}

/** 分块配置 */
export interface ChunkConfig {
  chunkSize: number;       // 每块字符数
  chunkOverlap: number;    // 相邻块重叠字符数
}

/** 检索配置 */
export interface RetrievalConfig {
  topK: number;            // 初始检索数量
  rerankTopK: number;      // 重排序后保留数量
  useRerank: boolean;      // 是否启用 LLM 重排序
  scoreThreshold: number;  // 相关性得分阈值（低于此值过滤）
}
