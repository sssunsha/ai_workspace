import type { RawDocument } from "../types.js";

/**
 * 示例知识库
 * 生产环境替换为从文件、数据库或 API 加载的真实文档
 */
export const sampleDocuments: RawDocument[] = [
  {
    id: "doc-001",
    title: "RAG 技术概述",
    source: "internal/ai-guide",
    content: `RAG（Retrieval-Augmented Generation，检索增强生成）是一种结合信息检索与大语言模型的 AI 架构。
其核心思想是：在 LLM 生成答案之前，先从外部知识库中检索相关文档，将检索结果作为上下文注入模型，使模型能够基于最新、最准确的外部知识进行回答。

RAG 的主要优势：
1. 降低幻觉（Hallucination）：答案锚定在真实文档中，可追溯来源
2. 知识可更新：无需重新训练模型，只需更新文档库
3. 领域适应：通过注入专业文档实现领域专业化
4. 成本效率：比微调模型成本低得多

RAG 的主要挑战：
1. 检索质量直接决定最终答案质量（GIGO 原则）
2. 上下文窗口限制，无法注入过多文档
3. 需要维护和更新向量数据库
4. 检索延迟影响整体响应速度`,
  },
  {
    id: "doc-002",
    title: "向量数据库选型指南",
    source: "internal/infrastructure",
    content: `向量数据库（Vector Database）是 RAG 架构的核心存储组件，专门为高维向量的高效存储和相似度搜索而设计。

主流向量数据库对比：

Pinecone：
- 托管服务，无需自维护
- 支持元数据过滤
- 适合生产环境快速上线
- 免费层限制较多

Weaviate：
- 开源，可自托管
- 原生支持混合搜索（向量+关键词）
- 内置模块化架构
- 社区活跃

Qdrant：
- 高性能 Rust 实现
- 支持向量的量化压缩
- 适合大规模部署
- REST 和 gRPC 双协议

pgvector（PostgreSQL 扩展）：
- 利用现有 PostgreSQL 基础设施
- 成本最低
- 适合中小规模（百万级向量）
- 与关系数据天然集成

Chroma：
- 专为 LLM 应用设计
- 本地优先，适合开发测试
- Python/TypeScript SDK 完善
- 适合快速原型`,
  },
  {
    id: "doc-003",
    title: "文本分块策略",
    source: "internal/ai-guide",
    content: `文本分块（Chunking）是 RAG 管道中的关键预处理步骤，直接影响检索质量。

主要分块策略：

1. 固定大小分块（Fixed-size Chunking）
   - 按字符数或 token 数切分
   - 使用重叠（overlap）减少上下文丢失
   - 实现简单，但可能切断语义单元
   - 推荐参数：chunk_size=512 tokens，overlap=50-100 tokens

2. 递归字符分块（Recursive Character Splitting）
   - 按段落→句子→词语的优先级递归切分
   - 尽量保留语义完整性
   - LangChain RecursiveCharacterTextSplitter 是典型实现

3. 语义分块（Semantic Chunking）
   - 根据嵌入相似度决定分块边界
   - 质量最高，但计算成本高
   - 适合高质量要求场景

4. 文档结构分块（Document-based Chunking）
   - 按 Markdown 标题、HTML 标签等结构切分
   - 天然保留文档逻辑结构
   - 适合有明确结构的文档

分块大小选择原则：
- 太小：丢失上下文，检索结果碎片化
- 太大：占用上下文窗口，引入噪音
- 经验值：512~1024 tokens 通常效果较好`,
  },
  {
    id: "doc-004",
    title: "嵌入模型选择",
    source: "internal/ai-guide",
    content: `嵌入模型（Embedding Model）将文本转换为高维稠密向量，是 RAG 检索质量的基础。

推荐嵌入模型：

Voyage AI（Anthropic 推荐）：
- voyage-3：通用高性能，1024 维
- voyage-3-lite：速度快，成本低，512 维
- voyage-code-3：专为代码优化
- voyage-finance-2：金融领域专用
- 与 Anthropic Claude 配合使用效果最佳

OpenAI Embeddings：
- text-embedding-3-large：3072 维，性能最强
- text-embedding-3-small：1536 维，性价比高
- 使用最广泛，生态最完善

Cohere Embeddings：
- embed-multilingual-v3.0：支持 100+ 语言
- 适合多语言场景

本地模型（通过 Ollama）：
- nomic-embed-text：轻量，768 维
- mxbai-embed-large：高质量，1024 维
- 适合数据隐私要求高的场景

选择原则：
1. 优先与生成模型同厂商的嵌入（语义空间一致）
2. 评估 MTEB 基准测试结果
3. 考虑延迟、成本、维度与存储的平衡`,
  },
  {
    id: "doc-005",
    title: "高级 RAG 技术",
    source: "internal/ai-guide",
    content: `高级 RAG 技术用于解决基础 RAG 的检索精度和生成质量问题。

主要高级技术：

1. 查询改写（Query Rewriting）
   - HyDE（Hypothetical Document Embeddings）：先让 LLM 生成假设答案，用假设答案的向量检索
   - Multi-Query：生成多个查询变体，取并集
   - Step-Back Prompting：将具体问题泛化为更高层次的问题

2. 重排序（Reranking）
   - Cross-Encoder 模型：精确计算 query-document 相关性
   - LLM-based Reranking：用 LLM 对候选文档打分
   - Cohere Rerank API：生产就绪的重排序服务

3. 混合检索（Hybrid Search）
   - 向量检索 + BM25 关键词检索
   - RRF（Reciprocal Rank Fusion）融合两路结果
   - 弥补纯向量检索对精确词匹配的不足

4. 上下文压缩（Context Compression）
   - LLMLingua：压缩 prompt，减少 token 消耗
   - 只提取每个文档中与问题最相关的句子

5. 图 RAG（Graph RAG）
   - 微软开源方案
   - 构建知识图谱，支持多跳推理
   - 适合关系复杂的企业知识库

6. RAPTOR（Recursive Abstractive Processing）
   - 递归聚类 + 摘要，构建多粒度索引树
   - 支持全局摘要和局部细节的统一检索`,
  },
];
