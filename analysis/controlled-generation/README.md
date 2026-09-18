# 受控灯光生图实验

本目录保存三组单变量 A/B 图像编辑实验，共 6 张生成图。

- `images/`：生成图；
- `experiment.json`：实验设计、逐图光照指标、OpenCLIP 属性和局限；
- `overview.jpg`：原图、A、B 三列对照；
- `evaluation/lighting/`：生成图的可解释光照分析；
- `evaluation/openclip/`：生成图的 OpenCLIP 零样本分析。

运行 `python scripts/build_controlled_generation_report.py` 可根据已有图像与评估结果重建结构化报告和总览图。生成图本身由内置图像编辑模型产生，不能仅靠本地脚本重新生成完全相同的像素结果。
