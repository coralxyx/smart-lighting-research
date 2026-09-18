# YOLO 室内对象检测 baseline

## 目标

验证项目的室内图片批量目标检测、结构化输出和可视化链路，为后续光照分析、灯具标注和 Web 图片理解提供空间对象位置。

该阶段使用 COCO 预训练 `yolo11n.pt`，没有重新训练模型，也不替代后续灯具细分类。

## 输入与参数

- 输入：`data/raw/base_images/` 中 24 张底图。
- 配置：`config/yolo_baseline.json`。
- 图像尺寸：640。
- 置信度阈值：0.25。
- IoU 阈值：0.70。
- 推理设备：CPU。

## 输出

- `analysis/yolo-baseline/predictions.jsonl`：一行一张图，保留尺寸、速度和全部检测框。
- `analysis/yolo-baseline/detections.csv`：一行一个检测框，坐标已经归一化，可直接供 Web 使用。
- `analysis/yolo-baseline/summary.json`：覆盖率、类别、空间和速度汇总。
- `analysis/yolo-baseline/environment.json`：Python、Ultralytics、PyTorch 和设备信息。
- `analysis/yolo-baseline/annotated/`：24 张检测标注图。
- `analysis/yolo-baseline/overview.jpg`：全部底图的检测概览。

## baseline 结果

| 指标 | 数值 |
|---|---:|
| 输入图片 | 24 |
| 检测到任意对象的图片 | 19 |
| 检测覆盖率 | 79.2% |
| 检测框 | 73 |
| 室内相关检测框 | 71 |
| 平均 CPU 推理时间 | 30.1 ms/图 |

高频类别为椅子、沙发、盆栽、床、电视和餐桌。卧室、客厅和书房均为 6/6 图片检测到对象；走廊只有 1/6。

## 方法边界

COCO 类别没有吊灯、台灯、落地灯、灯带和射灯，因此本阶段准确名称是“室内对象检测 baseline”，不能写成“灯具检测模型”。

检测框可用于：

- 判断床、沙发、桌椅和电视等功能区域；
- 为光照区域分析提供对象参照；
- 为 Web 上传图片生成可解释的空间对象层；
- 帮助确定后续灯具数据集需要补充的类别。

后续若开展灯具检测，应建立自定义标注集，并报告独立验证集上的 precision、recall 和 mAP；当前无人工真值，因此不能报告检测准确率。

## 一键运行

```powershell
python scripts/run_yolo_baseline.py
```
