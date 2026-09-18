# Web 数据包

本目录由 `python scripts/export_defense_charts_and_web_data.py` 从正式标签表、Legacy Kano 工作簿和 Kano-inspired v2 工作簿生成。

## 使用方式

- `dashboard-data.json`：首屏仪表盘所需的紧凑组合数据。
- `legacy-summary.json`、`legacy-pairs.json`：记录级现有成果，默认展示口径。
- `v2-summary.json`、`v2-pairs.json`：帖子级 Kano-inspired 结果。
- `v2-stability.json`：Bootstrap 置信区间和分类稳定率。
- `legacy-v2-comparison.json`：两种口径的分类对照。
- `post-votes.json`：帖子票审计数据，不包含原帖正文。
- `metadata.json`、`manifest.json`：维度、规模、模式和文件粒度。

前端必须用 `analysis_mode` 区分 `legacy_record` 与 `v2_post`，不得混用两种口径的分母。
