---
name: review-writer
description: 将论文笔记和对比矩阵综合为结构化学术文献综述，含 BibTeX 引用
metadata: {"openclaw": {}}
---

# Review Writer Skill

将分析结果综合为高质量文献综述。仅由 review-lead subagent 或 Mac_Javis 主 agent 使用。

> ⚠️ 写综述前，完整阅读本文件。遵循模板结构和质量清单。

## 输入文件

开始写作前，必须读取所有这些文件：

```
exec: ls ~/research/[PROJECT]/notes/
read: ~/research/[PROJECT]/matrix.csv
read: ~/research/[PROJECT]/candidates.csv
read: ~/research/[PROJECT]/search_log.md
```

然后逐个读取 `notes/` 目录下的每个笔记文件。

## 综述结构模板

写入 `~/research/[PROJECT]/review.md`：

```markdown
# Literature Review: [Topic]

**Generated**: [YYYY-MM-DD]
**Papers Analyzed**: [N]
**Sources**: arXiv, Semantic Scholar, OpenAlex, ...
**Search Queries**: [list main queries used]

## 1. Introduction

[研究背景和动机。为什么这个主题重要？
本综述的范围是什么？2-3 段。]

## 2. Taxonomy

[提出一个分类体系来组织综述文献。]

| Category | Representative Papers | Core Idea |
|----------|----------------------|-----------|
| [Cat A]  | [cite1, cite2]       | [1-sentence] |
| [Cat B]  | [cite3, cite4]       | [1-sentence] |

## 3. Detailed Analysis

### 3.1 [Category A]

[该类别共有的方法特征
跨论文的方法对比（引用 matrix.csv 数据）
优缺点分析
时间线上的演进趋势]

### 3.2 [Category B]

[同上结构]

## 4. Cross-Cutting Analysis

### 4.1 Common Datasets and Benchmarks
[哪些数据集出现最频繁？是否有标准化 benchmark？]

### 4.2 Methodological Trends
[跨类别的趋势]

### 4.3 Open Challenges
[整个领域共同面对的开放问题]

## 5. Research Gaps and Future Directions

[基于分析识别：
- 覆盖不足的子主题
- 方法论空白
- 未被探索的组合
每个空白引用揭示它的论文。]

## 6. Conclusion

[2-3 段总结。]

## References

[见 references.bib]
```

## BibTeX 生成

写入 `~/research/[PROJECT]/references.bib`：

- 从所有笔记文件收集 BibTeX 条目
- 按 citekey 字母排序
- 去重（按 paper_id）
- 确保 review.md 中每个 \cite{} 在 bib 中都有对应条目

## 质量自检清单

完成综述后，逐项验证：

- [ ] 每个事实主张都引用了至少一篇论文
- [ ] notes/ 下的每篇论文都在综述中被提及或有排除理由
- [ ] 分类框架类别之间互斥且完全覆盖
- [ ] 研究空白基于证据而非猜测
- [ ] references.bib 条目与正文引用一一对应
- [ ] 无编造信息
- [ ] review.md 独立可读

## 写作规范

- 学术语气，第三人称
- 一般性论述用现在时（"X demonstrates that..."）
- 具体实验结果用过去时（"Y achieved 95% accuracy on..."）
- 精确表述："improves by 3.2%" 而非 "significantly improves"
- 公平对待每篇论文的局限性
- 默认英文写作，除非人类明确要求中文
