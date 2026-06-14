# content-extract 知识库项目

## 固定路径
项目根目录：/Users/I340818/Documents/ai_workspace/content-extract/

## 目录结构
- `raw/`：原始内容（由 content-extract TUI/CLI 生成，人不直接读）
  - `raw/<来源名>/`：每个来源一个子目录
  - `raw/topics/<topic名>/`：Topic 学习模式的主题目录
  - 文件名前缀含义：
    - `bili__`：Bilibili 视频转录
    - `web__`：网页爬取
    - `article__`：单篇文章（微信/头条/知乎等）
    - `epub__` / `pdf__`：电子书
    - `code__`：代码工程提取结果
    - `github__`：GitHub 仓库提取结果
    - `local__`：Topic 模式本地文件引用
- `wiki/`：结构化知识库（由 Claude Code 整理生成）
  - `wiki/concepts/`：核心概念页面
  - `wiki/by-source/`：按来源分类的摘要
  - `wiki/topics/<topic名>/`：Topic 学习模式的 wiki
  - `wiki/INDEX.md`：全局索引
- `wiki/changelog.md`：wiki 变更历史

## frontmatter 字段说明
每个 raw/ 文件包含：source / type / platform / extracted_at / content_hash
Topic 模式额外字段：topic（所属主题）/ topic_role（角色）

## 使用方式
分析和构建 wiki 时，调用 `/content-extract` Skill（别名：知识获取）。
