# 智能灯光美学研究台

这是一个无构建步骤、只读的静态研究仪表盘。它直接加载仓库中的已验证 JSON 与图像产物，不在浏览器中重新计算 Kano 分类。

## 启动

在仓库根目录运行：

```bash
python -m http.server 8000
```

然后访问：

```text
http://localhost:8000/web/
```

不能直接双击 `index.html`，因为浏览器会限制 `file://` 页面读取相邻 JSON 文件。

## 页面结构

- 研究总览：Legacy 记录级与 v2 帖子级口径切换、场景筛选、情感结构和触点表；
- 稳健性对照：分类变化与 Bootstrap 低稳定组合；
- 视觉基线：YOLO、光照统计和 OpenCLIP 结果；
- 灯光方案：三组受控生图实验及量化验收。

## 数据来源

- `analysis/web-data/dashboard-data.json`
- `analysis/yolo-baseline/summary.json`
- `analysis/lighting-baseline/summary.json`
- `analysis/openclip-baseline/summary.json`
- `analysis/controlled-generation/experiment.json`

界面不写入任何研究数据。重新运行上游脚本后，刷新页面即可看到更新结果。
