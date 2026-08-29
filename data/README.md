# 数据目录

## `raw/`

- `smzdm-smart-light-posts.xlsx`：526 条智能灯相关帖子，包含标题、作者、发布时间、正文与来源链接。

## `interim/`

- `valid-original-text-results.jsonl`：366 条通过原词校验的抽取结果，每条包含原文和合并后的三元组。
- `extraction-with-validation.xlsx`：4,794 条分句级抽取记录，保留原句、模型输入、三元组、原词校验和完整 JSON。

运行 `src/format_extraction_results.py` 后会在本目录生成结构化 Excel；该可复现文件默认不纳入 Git。

## `processed/`

- `expert-clustered.xlsx`：2,696 条专家校正后的场景、美学指标和用户感受聚类结果，并附分类汇总。
- `tagged-results.xlsx`：4,747 条已完成场景、美学指标和用户感受标签的记录。
- `tagged-results-with-sentiment.xlsx`：在标签结果上补充正向、中性、负向情感强度。

行数均不含表头。数据源含第三方用户生成内容，使用与发布前请检查来源平台条款和隐私要求。
