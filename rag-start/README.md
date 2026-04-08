# RAG Start — 检索增强生成完整脚手架

基于 `@anthropic-ai/sdk` 的生产级 RAG（Retrieval-Augmented Generation）TypeScript 脚手架，覆盖从文档摄入到答案生成的完整管道。

---

## 目录

- [架构概览](#架构概览)
- [工程结构](#工程结构)
- [核心模块说明](#核心模块说明)
  - [类型定义](#1-类型定义-srctypests)
  - [知识库数据](#2-知识库数据-dataknowledge-basets)
  - [文档摄入与分块](#3-文档摄入与分块-srcingestionchunkerts)
  - [嵌入向量化](#4-嵌入向量化-srcembeddingembedderts)
  - [向量存储](#5-向量存储-srcretrievalvectorstorets)
  - [检索与重排序](#6-检索与重排序-srcretrievalretrieverts)
  - [答案生成](#7-答案生成-srcgenerationgeneratorts)
  - [入口文件](#8-入口文件-srcindexts)
- [两大阶段：离线索引 vs 在线查询](#两大阶段离线索引-vs-在线查询)
- [生产化替换指南](#生产化替换指南)
- [快速开始](#快速开始)
- [高级技术扩展方向](#高级技术扩展方向)
- [参考资料](#参考资料)

---

## 架构概览

```
┌──────────────────────────────────────────────────────────────┐
│                    离线索引阶段（Indexing）                     │
│                                                              │
│  原始文档                                                      │
│  RawDocument[]  ──→  [Chunker]  ──→  [Embedder]  ──→  [VectorStore] │
│  (docs/data)       分块+重叠       向量化           存储向量     │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    在线查询阶段（Querying）                     │
│                                                              │
│  用户问题                                                      │
│  Question  ──→  [Embedder]  ──→  [VectorStore]  ──→  Top-K 候选 │
│                  查询向量化        余弦相似度检索                │
│                                       ↓                      │
│                                  [Reranker]                  │
│                                  LLM 精排序                   │
│                                       ↓                      │
│                                  [Generator]                 │
│                                  带引用的答案生成               │
│                                       ↓                      │
│                                  RAGResult                   │
│                             答案 + 来源列表                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 工程结构

```
rag-start/
├── README.md                          # 本文件：架构文档
├── package.json                       # 依赖配置
├── tsconfig.json                      # TypeScript 编译配置
├── .env.example                       # 环境变量模板
│
├── data/
│   └── knowledge-base.ts              # 示例知识库（5 篇文档）
│
└── src/
    ├── index.ts                       # 入口：完整 RAG 管道演示
    ├── types.ts                       # 统一类型定义
    │
    ├── ingestion/
    │   └── chunker.ts                 # 文档分块（固定大小+重叠）
    │
    ├── embedding/
    │   └── embedder.ts                # 文本向量化（含替换指南）
    │
    ├── retrieval/
    │   ├── vectorStore.ts             # 内存向量库（含余弦相似度）
    │   └── retriever.ts               # 检索器 + LLM 重排序
    │
    └── generation/
        └── generator.ts               # 答案生成（带来源引用）
```

---

## 核心模块说明

### 1. 类型定义 `src/types.ts`

定义贯穿整个管道的核心数据结构：

| 类型 | 说明 |
|------|------|
| `RawDocument` | 原始输入文档（id / title / content / source） |
| `Chunk` | 分块后的文档片段，携带 docId / 片段序号 |
| `EmbeddedChunk` | 附加嵌入向量的 Chunk |
| `SearchResult` | 检索结果（含余弦相似度得分 + 排名） |
| `RAGResult` | 最终输出（答案 + 来源列表 + 元信息） |
| `ChunkConfig` | 分块参数（chunkSize / chunkOverlap） |
| `RetrievalConfig` | 检索参数（topK / rerankTopK / useRerank / scoreThreshold） |

---

### 2. 知识库数据 `data/knowledge-base.ts`

5 篇示例文档，内容涵盖：
- RAG 技术概述（优势与挑战）
- 向量数据库选型（Pinecone / Weaviate / Qdrant / pgvector / Chroma）
- 文本分块策略（固定大小 / 递归 / 语义 / 结构化）
- 嵌入模型选择（Voyage AI / OpenAI / Cohere / 本地模型）
- 高级 RAG 技术（HyDE / 混合检索 / 上下文压缩 / Graph RAG）

**生产环境替换**：将 `RawDocument[]` 替换为从文件系统、数据库或 API 加载的真实文档。

---

### 3. 文档摄入与分块 `src/ingestion/chunker.ts`

**策略**：固定大小分块 + 滑动窗口重叠

```
原文：[─────────────────────────────────────────]
分块：[Chunk 0──────][Chunk 1──────][Chunk 2────]
重叠：         [overlap][overlap]
```

**关键参数**：
- `chunkSize`：每块字符数，默认 300（生产建议 512~1024 tokens）
- `chunkOverlap`：相邻块重叠字符数，默认 50（防止关键信息被切断）

**生产替换**：可换为语义分块或 LangChain `RecursiveCharacterTextSplitter`。

---

### 4. 嵌入向量化 `src/embedding/embedder.ts`

> ⚠️ 当前使用**字符频率模拟向量**，仅供本地演示，无真实语义能力。

**生产环境替换方案（代码注释中均有示例）**：

| 方案 | 模型 | 推荐场景 |
|------|------|---------|
| **Voyage AI**（首选） | `voyage-3` / `voyage-3-lite` | 与 Claude 配合最佳 |
| OpenAI | `text-embedding-3-small/large` | 生态最完善 |
| Cohere | `embed-multilingual-v3.0` | 多语言场景 |
| Ollama（本地） | `nomic-embed-text` | 数据隐私要求高 |

---

### 5. 向量存储 `src/retrieval/vectorStore.ts`

**内存实现**，支持：
- `upsert(chunks)`：批量写入，相同 id 覆盖
- `search(queryEmbedding, topK, scoreThreshold)`：余弦相似度 Top-K 检索
- `deleteByDocId(docId)`：按文档删除所有相关片段
- `size()`：获取库中向量总数

**生产替换指南**：

| 向量库 | 适用规模 | 特点 |
|--------|---------|------|
| **pgvector** | 中小型（< 1M 向量） | 无需额外基础设施 |
| **Qdrant** | 大型（> 1M 向量） | 高性能，Rust 实现 |
| **Pinecone** | 任意规模 | 托管服务，运维成本低 |
| **Weaviate** | 任意规模 | 内置混合检索 |

---

### 6. 检索与重排序 `src/retrieval/retriever.ts`

**两步检索流程**：

```
步骤 1：向量粗排（topK=6）
  embedText(question) → vectorStore.search() → Top-6 候选

步骤 2：LLM 精排（rerankTopK=3）
  claude-haiku 对每个候选文档与问题的相关度打分（0-10）
  → 取 Top-3 作为最终上下文
```

**重排序降级**：若 LLM 调用失败，自动降级为向量得分排序。

**生产替换**：可将 LLM 重排序替换为 Cohere Rerank API（延迟更低，成本更可控）。

---

### 7. 答案生成 `src/generation/generator.ts`

**System Prompt 设计原则**：
1. 优先使用文档内容，用【来源X】明确引用
2. 文档不足时补充通用知识，需注明
3. 无关问题直接说明，避免幻觉

**输出结构（`RAGResult`）**：
```typescript
{
  question: string,
  answer: string,          // 带来源标注的答案
  sources: [{              // 引用文档列表
    docTitle, chunkId, score, ...
  }],
  retrievedChunks: number, // 使用的 Chunk 数量
  rerankApplied: boolean   // 是否经过重排序
}
```

---

### 8. 入口文件 `src/index.ts`

演示完整 RAG 管道，包含 4 个测试问题：
1. RAG 的优势与挑战
2. 向量数据库选型
3. 文本分块策略
4. 混合检索原理

---

## 两大阶段：离线索引 vs 在线查询

| 阶段 | 触发时机 | 涉及模块 | 是否调用 LLM |
|------|---------|---------|------------|
| **离线索引** | 文档入库 / 更新时 | chunker → embedder → vectorStore | ❌（仅嵌入模型） |
| **在线查询** | 每次用户提问 | embedder → vectorStore → retriever → generator | ✅（重排序 + 生成） |

---

## 生产化替换指南

按需替换以下组件，无需修改其他代码：

```
src/embedding/embedder.ts    ← 替换为 Voyage AI / OpenAI 嵌入
src/retrieval/vectorStore.ts ← 替换为 Pinecone / pgvector / Qdrant
src/retrieval/retriever.ts   ← 重排序替换为 Cohere Rerank API
data/knowledge-base.ts       ← 替换为真实文档加载逻辑
```

---

## 快速开始

```bash
# 1. 安装依赖
npm install

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY=sk-ant-...

# 3. 运行完整管道演示
npm run dev
```

预期输出：
```
🚀 RAG 管道启动
📥 [阶段 1] 文档摄入与分块...
  分块完成：5 篇文档 → N 个 Chunk
🔢 [阶段 2] 文本向量化...
🔍 [阶段 3] 开始在线查询...
...（4 个问答结果）
```

---

## 高级技术扩展方向

| 技术 | 说明 | 难度 |
|------|------|------|
| **HyDE** | 先生成假设答案再检索，提升召回率 | ⭐⭐ |
| **Multi-Query** | 生成多个查询变体取并集 | ⭐⭐ |
| **混合检索** | 向量 + BM25，RRF 融合 | ⭐⭐⭐ |
| **上下文压缩** | LLMLingua 压缩 prompt | ⭐⭐⭐ |
| **Graph RAG** | 知识图谱支持多跳推理 | ⭐⭐⭐⭐ |
| **RAPTOR** | 递归摘要多粒度索引树 | ⭐⭐⭐⭐ |
| **流式输出** | Anthropic streaming API | ⭐ |
| **评估框架** | RAGAS 自动化 RAG 质量评估 | ⭐⭐⭐ |

---

## 参考资料

- [RAG 原始论文](https://arxiv.org/abs/2005.11401) — Lewis et al., 2020
- [Anthropic Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval) — 官方最佳实践
- [Voyage AI 嵌入模型](https://docs.voyageai.com/) — Anthropic 推荐嵌入方案
- [Advanced RAG Techniques（综述）](https://arxiv.org/abs/2312.10997)
- [RAGAS：RAG 评估框架](https://github.com/explodinggradients/ragas)
- [Graph RAG（微软）](https://github.com/microsoft/graphrag)
- [RAPTOR 论文](https://arxiv.org/abs/2401.18059)
- [Anthropic Tool Use 文档](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
