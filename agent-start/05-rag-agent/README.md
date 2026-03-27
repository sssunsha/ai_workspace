# RAG Agent（检索增强生成）

## 架构说明

RAG（Retrieval-Augmented Generation）Agent 在生成答案前，先从外部知识库（向量数据库、文档库）中检索相关内容，将检索结果作为上下文注入 LLM，使生成的答案**有据可查、可追溯**，大幅降低幻觉。

```
用户问题 → [嵌入模型] 向量化
               ↓
         [向量数据库] 相似度检索 → Top-K 文档
               ↓
         [LLM] 基于文档上下文生成答案（含引用）
               ↓
           答案 + 来源引用
```

### 核心组件

```
05-rag-agent/
├── src/
│   ├── index.ts           # 入口
│   ├── retriever.ts       # 检索器：向量相似度搜索
│   ├── embedder.ts        # 嵌入：文本向量化
│   ├── vectorStore.ts     # 向量库（内存版，可替换为 Pinecone/Weaviate）
│   ├── generator.ts       # 生成器：带上下文的 LLM 调用
│   ├── reranker.ts        # 重排序：提升检索精度（可选）
│   └── types.ts           # Document、SearchResult 等类型
├── data/
│   └── sample-docs.json   # 示例文档
├── package.json
├── tsconfig.json
└── .env.example
```

## 工作原理

1. **索引阶段**（离线）：将文档分块 → 向量化 → 存入向量数据库
2. **检索阶段**：将用户问题向量化 → 在库中检索 Top-K 相似文档
3. **（可选）重排序**：用 Cross-Encoder 对候选文档重新排序
4. **生成阶段**：将检索到的文档作为上下文，指示 LLM 基于证据回答
5. **引用追踪**：答案中标注来源文档 ID

## 特点

| 项目 | 描述 |
|------|------|
| 幻觉抑制 | ⭐⭐⭐⭐⭐ 答案锚定在真实文档 |
| 知识实时性 | ✅ 更新文档库即可更新知识 |
| Token 效率 | 高（只注入相关文档） |
| 依赖项 | 需向量数据库 + 嵌入模型 |

## 适用场景

- **企业知识库**问答（内部文档、产品手册）
- **法律/医学**文献检索与解读
- **客服机器人**（基于 FAQ 和工单历史）
- **代码文档**智能搜索
- **合规审查**（基于规章制度库）

## 快速开始

```bash
npm install
cp .env.example .env
npm run dev
```

## 参考资料

- [Retrieval-Augmented Generation（RAG 原始论文）](https://arxiv.org/abs/2005.11401)
- [Anthropic Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- [pgvector（PostgreSQL 向量扩展）](https://github.com/pgvector/pgvector)
- [Pinecone 向量数据库](https://www.pinecone.io/)
- [Advanced RAG Techniques](https://arxiv.org/abs/2312.10997)
