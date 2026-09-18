# 智能家居灯光 Feature–Perception 映射项目

本项目从智能灯具相关用户内容中抽取“使用场景—美学指标—用户感受”三元组，完成标签标准化、聚类与情感标注，再通过 Kano 统计把用户洞察转化为可落地的居家灯光方案。

## 项目产出

- 数据集：525 篇智能灯相关帖子，以及抽取、校验、分类和情感标注后的过程数据。
- 分析结果：按日常基础照明、睡眠与起居、学习工作、智能托管、休闲娱乐和亲子互动陪伴等场景进行 Kano 触点分析。
- 设计方案：以“自然渐进式柔光系统”为主题，将舒适基础光、睡前暖光和夜起路径光组织为连续体验。
- 方法资料：项目推进方案、智能照明抽取提示词和美学指标体系。

最终汇报见 [`deliverables/natural-progressive-soft-light-system.pptx`](deliverables/natural-progressive-soft-light-system.pptx)，核心统计见 [`analysis/kano-pair-statistics.xlsx`](analysis/kano-pair-statistics.xlsx)。

## 工作流

```text
原始帖子
  → LLM 三元组抽取与原词校验
  → 场景 / 美学指标 / 用户感受分类与情感标注
  → Kano 词对统计
  → 灯光方案与项目汇报
```

## 仓库结构

```text
.
├─ analysis/                  # Kano 词对统计与汇总分析
├─ data/
│  ├─ raw/                   # 原始帖子数据
│  ├─ interim/               # 抽取、校验等中间数据
│  └─ processed/             # 聚类、人工校正与情感标注结果
├─ deliverables/
│  ├─ assets/                # 客厅、卧室方案图与标注图
│  └─ *.pptx                 # 最终项目汇报
├─ docs/                     # 项目方案、提示词与指标体系
├─ experiments/
│  └─ sev-appearance/        # 早期智能汽车外观迁移实验（与主流程隔离）
├─ src/                      # 抽取结果整理脚本
├─ requirements.txt
└─ README.md
```

更详细的数据说明见 [`data/README.md`](data/README.md)，交付物说明见 [`deliverables/README.md`](deliverables/README.md)。

需要制作流程图、Sankey、Kano 气泡图或数据仪表盘时，请从 [`docs/visualization-pipeline.md`](docs/visualization-pipeline.md) 开始；机器可读字段与模块契约见 [`docs/pipeline-data-contract.json`](docs/pipeline-data-contract.json)。

## 快速开始

建议使用 Python 3.10 或更高版本。

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python src/format_extraction_results.py
```

如果出现 `ModuleNotFoundError`，请确认已经在当前虚拟环境中执行过依赖安装命令。

该脚本将 JSONL 三元组展开为结构化表格，便于抽查原始抽取结果。正式统计和可视化使用 `data/processed/tagged-results-with-sentiment.xlsx`。

## 文档索引

- [`docs/smart-home-fp-mapping-project-plan.docx`](docs/smart-home-fp-mapping-project-plan.docx)：从数据准备到决策支持的完整项目推进方案。
- [`docs/smart-lighting-extraction-prompt.docx`](docs/smart-lighting-extraction-prompt.docx)：用于抽取三元组的提示词与示例。
- [`docs/aesthetic-indicators.docx`](docs/aesthetic-indicators.docx)：形体、动效交互、色彩、材料与表面处理等美学指标体系。
- [`docs/visualization-pipeline.md`](docs/visualization-pipeline.md)：模块输入输出、字段粒度、连接规则和推荐图表。
- [`docs/pipeline-data-contract.json`](docs/pipeline-data-contract.json)：供前端、BI 或 ETL 直接读取的数据契约。

## 数据与合规说明

数据中可能包含公开平台上的用户生成内容。使用、再分发或公开发布前，请自行确认原平台条款、个人信息保护要求和研究伦理要求。本仓库未声明这些第三方文本或图片的再授权许可；在没有完成权利核查前，建议将远程仓库设为私有。

## 安全说明

- 不要将 API Key、访问令牌或 `.env` 文件提交到仓库。
- 独立的 SEV 外观实验通过 `DEEPSEEK_API_KEY` 环境变量读取密钥，详见 [`experiments/sev-appearance/README.md`](experiments/sev-appearance/README.md)。
- 若密钥曾经写入源码，即使之后删除，也应立即在服务商控制台撤销并重新生成。
