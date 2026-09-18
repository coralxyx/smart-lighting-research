from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.kano.aggregate import build_aggregates  # noqa: E402
from src.kano.audit import audit_against_reference  # noqa: E402
from src.kano.input import load_tagged_records, validate_records  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Kano workbook reproducibility.")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "tagged-results-with-sentiment.xlsx",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=PROJECT_ROOT / "analysis" / "kano-pair-statistics.xlsx",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "analysis" / "generated",
    )
    return parser.parse_args()


def build_markdown(report: dict[str, object]) -> str:
    aggregate = report["aggregate_summary"]
    audit = report["reference_audit"]
    validation = report["input_validation"]
    lines = [
        "# Kano 第一阶段审计结果",
        "",
        "## 输入数据",
        "",
        f"- 有效记录：{aggregate['record_count']}",
        f"- 唯一原文：{aggregate['unique_post_count']}",
        f"- 每篇原文记录数中位数：{aggregate['records_per_post']['median']}",
        f"- 每篇原文最少记录数：{aggregate['records_per_post']['minimum']}",
        f"- 每篇原文最多记录数：{aggregate['records_per_post']['maximum']}",
        "",
        "## 完整性检查",
        "",
        f"- 缺失字段统计：`{json.dumps(validation['missing_by_field'], ensure_ascii=False)}`",
        f"- 非法情感标签行数：{len(validation['invalid_sentiment_rows'])}",
        "",
        "## 与现有工作簿对照",
        "",
        f"- 总记录数一致：{audit['record_count']['match']}",
        f"- 全局分类频次一致：{audit['checks']['global_counts_match']}",
        f"- 场景×美学指标×情感计数一致：{audit['checks']['scene_aesthetic_counts_match']}",
        "",
        "## 当前阻塞点",
        "",
        "现有工作簿中的 Kano 类型为静态单元格值，未发现可执行阈值公式。",
        "第一阶段可以从源标签完整重算计数和比例；Kano 类型需要继续逆向规则，",
        "或在复现版本中显式保留为 legacy 映射，再在 v2 中替换为配置化规则。",
        "",
        "## 旧分类数量",
        "",
    ]
    for label, count in sorted(audit["legacy_classification_counts"].items()):
        lines.append(f"- {label}：{count}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    records = load_tagged_records(args.input)
    aggregates = build_aggregates(records)
    validation = validate_records(records)
    audit = audit_against_reference(aggregates, args.reference)
    report = {
        "input_path": str(args.input),
        "reference_path": str(args.reference),
        "aggregate_summary": {
            key: aggregates[key]
            for key in (
                "record_count",
                "unique_post_count",
                "records_per_post",
                "scene_counts",
                "aesthetic_counts",
                "perception_counts",
                "sentiment_counts",
            )
        },
        "input_validation": validation,
        "reference_audit": audit,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "kano-phase1-audit.json"
    markdown_path = args.output_dir / "kano-phase1-audit.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    markdown_path.write_text(build_markdown(report), encoding="utf-8")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    print(json.dumps(audit["checks"], ensure_ascii=False))


if __name__ == "__main__":
    main()
