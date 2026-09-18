from __future__ import annotations

from collections import Counter
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.kano.input import load_tagged_records, validate_records  # noqa: E402
from src.kano.legacy import load_legacy_metadata  # noqa: E402
from src.kano.v2 import build_v2_analysis  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Kano-inspired v2 analysis.")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "tagged-results-with-sentiment.xlsx",
    )
    parser.add_argument(
        "--legacy-reference",
        type=Path,
        default=PROJECT_ROOT / "analysis" / "kano-pair-statistics.xlsx",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "config" / "kano_inspired_v2.json",
    )
    parser.add_argument(
        "--payload",
        type=Path,
        default=PROJECT_ROOT / "analysis" / "generated" / "kano-inspired-v2-data.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "kano_v2" / "kano-inspired-v2.xlsx",
    )
    return parser.parse_args()


def class_code(label: str) -> str:
    match = re.search(r"（([AOIM])(?:-inspired)?）", label)
    return match.group(1) if match else label


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    records = load_tagged_records(args.input)
    validation = validate_records(records)
    if any(validation["missing_by_field"].values()):
        raise ValueError(f"Missing values: {validation['missing_by_field']}")
    if validation["invalid_sentiment_rows"]:
        raise ValueError(
            f"Invalid sentiment rows: {validation['invalid_sentiment_rows'][:20]}"
        )

    analysis = build_v2_analysis(records, config)
    legacy = load_legacy_metadata(args.legacy_reference)["scene_aesthetic"]
    for row in analysis["summary_rows"]:
        metadata = legacy.get((str(row["scene"]), str(row["aesthetic"])), {})
        legacy_classification = str(metadata.get("classification", ""))
        row["legacy_classification"] = legacy_classification
        row["legacy_priority"] = str(metadata.get("priority", ""))
        row["classification_changed"] = (
            class_code(legacy_classification) != class_code(str(row["classification"]))
        )

    payload = {
        "config": config,
        "source_files": {
            "input": args.input.name,
            "legacy_reference": args.legacy_reference.name,
            "configuration": args.config.name,
        },
        "validation": validation,
        **analysis,
        "class_counts": dict(
            Counter(str(row["classification"]) for row in analysis["summary_rows"])
        ),
        "legacy_change_count": sum(
            bool(row["classification_changed"]) for row in analysis["summary_rows"]
        ),
        "low_stability_count": sum(
            float(row["classification_stability"])
            < float(config["bootstrap"]["low_stability_threshold"])
            for row in analysis["summary_rows"]
        ),
    }

    args.payload.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.payload.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    subprocess.run(
        [
            "node",
            str(PROJECT_ROOT / "scripts" / "build_kano_v2_workbook.mjs"),
            str(args.payload),
            str(args.output),
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )
    print(f"Workbook: {args.output}")
    print(f"Payload: {args.payload}")


if __name__ == "__main__":
    main()
