# OpenCLIP baseline

由 `python scripts/run_openclip_baseline.py` 从 `data/raw/base_images/` 生成。

- `predictions.json` / `predictions.csv`：逐图属性、组内概率和最高分标签；
- `summary.json`：总体及房间类型标签分布；
- `overview.jpg`：24 张图片及预测标签总览。

这是零样本探索性结果，不是人工标注真值。模型和提示词见 `config/openclip_baseline.json`。
