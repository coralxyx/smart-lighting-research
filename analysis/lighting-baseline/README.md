# Lighting analysis baseline

由 `python scripts/run_lighting_analysis.py` 从 `data/raw/base_images/` 生成。

- `metrics.json` / `metrics.csv`：逐图光照指标；
- `summary.json`：全局、房间类型与极值摘要；
- `heatmaps/`：逐图亮度热力图；
- `overview.jpg`：24 张热力图总览。

这是可解释的像素统计 baseline，不是语义分割结果。参数与局限见 `config/lighting_analysis.json`。
