# SEV 外观 Feature–Perception 迁移实验

这是主项目前期的独立验证实验：从智能汽车评论中抽取“外观特征—用户感受”词对，用于验证方法迁移的可行性。它不属于智能家居灯光主数据流程，因此单独存放。

## 目录

- `prompt.docx`：汽车外观抽取提示词。
- `data/raw/vehicle-review-data.csv`：原始车辆评论数据（GBK 编码）。
- `data/interim/appearance-features.jsonl`：模型抽取结果。
- `data/processed/appearance-output.xlsx`：整理后的外观、感受与原始内容。
- `src/extract_appearance_features.py`：调用 DeepSeek 兼容接口的抽取脚本。

## 运行

先在 PowerShell 中设置临时环境变量，再运行脚本：

```powershell
$env:DEEPSEEK_API_KEY = "your-key"
python experiments/sev-appearance/src/extract_appearance_features.py
```

不要把真实密钥写入脚本、README 或 `.env` 并提交到 Git。
