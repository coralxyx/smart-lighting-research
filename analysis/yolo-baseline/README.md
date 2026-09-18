# YOLO baseline 输出

运行 `python scripts/run_yolo_baseline.py` 可重新生成本目录。

- `summary.json`：总体结果与局限。
- `environment.json`：运行环境。
- `predictions.jsonl`：图片级结果。
- `detections.csv`：检测框级结果，适合前端叠框。
- `annotated/`：逐图标注结果。
- `overview.jpg`：24张底图概览。

本目录是 COCO 室内对象 baseline，不包含灯具自定义类别，也没有人工真值准确率。
