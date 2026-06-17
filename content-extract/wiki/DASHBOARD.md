# 知识库 Dashboard

## 最近更新的概念（全库，过去 7 天）

```dataview
TABLE file.mtime AS "更新时间", sources AS "来源", related AS "关联"
FROM "investing/concepts" OR "learning/concepts" OR "hai-docs/concepts" OR "spartacus"
SORT file.mtime DESC
LIMIT 20
```

---

## 各领域概念数量

```dataview
TABLE length(rows) AS "概念数"
FROM "investing/concepts" OR "learning/concepts" OR "hai-docs/concepts" OR "spartacus"
GROUP BY file.folder
```

---

## 待追问的问题（gap 清单）

```dataview
LIST
FROM "investing/concepts" OR "learning/concepts" OR "hai-docs/concepts"
WHERE contains(file.content, "未解答的问题")
SORT file.mtime DESC
LIMIT 30
```

---

## 孤立概念（无 related 连线）

```dataview
LIST
FROM "investing/concepts" OR "learning/concepts" OR "hai-docs/concepts"
WHERE !related
SORT file.name ASC
```

---

## 可操作方法（学习技巧）

```dataview
LIST
FROM "learning/concepts"
WHERE is_actionable = true
SORT file.name ASC
```

---

## 领域子 Dashboard 入口

| 领域 | 入口 | 内容 |
|------|------|------|
| 投资 | [[investing/INDEX]] | 刘伯涛 + 无忌心法学，47 个概念 |
| 学习方法 | [[learning/INDEX]] | 上瘾式学习，9 个概念 |
| 工作工具 | [[hai-docs/INDEX]] | Hyperspace AI 产品文档，8 个概念 |
| 代码工程 | [[spartacus/架构总览]] | SAP Spartacus，4 个架构页面 |
