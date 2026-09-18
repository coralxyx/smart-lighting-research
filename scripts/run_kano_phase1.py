from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.kano.aggregate import build_aggregates  # noqa: E402
from src.kano.input import load_tagged_records, validate_records  # noqa: E402
from src.kano.legacy import load_legacy_metadata  # noqa: E402
from src.kano.legacy_display import (  # noqa: E402
    apply_legacy_tie_order,
    load_legacy_perception_display,
)
from src.kano.workbook_data import build_workbook_payload  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild the phase-one Kano workbook.")
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
        "--output",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "kano_phase1" / "kano-phase1-reproduced.xlsx",
    )
    parser.add_argument(
        "--payload",
        type=Path,
        default=PROJECT_ROOT / "analysis" / "generated" / "kano-phase1-workbook-data.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_tagged_records(args.input)
    validation = validate_records(records)
    if any(validation["missing_by_field"].values()):
        raise ValueError(f"Missing values in required fields: {validation['missing_by_field']}")
    if validation["invalid_sentiment_rows"]:
        raise ValueError(
            f"Invalid sentiment labels at rows: {validation['invalid_sentiment_rows'][:20]}"
        )

    payload = build_workbook_payload(
        build_aggregates(records), load_legacy_metadata(args.reference)
    )
    apply_legacy_tie_order(
        payload, load_legacy_perception_display(args.reference)
    )
    payload["source_files"] = {
        "input": args.input.name,
        "legacy_reference": args.reference.name,
    }

    args.payload.parent.mkdir(parents=True, exist_ok=True)
    args.payload.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "node",
            str(PROJECT_ROOT / "scripts" / "build_kano_workbook.mjs"),
            str(args.payload),
            str(args.output),
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )
    print(f"Workbook: {args.output}")


if __name__ == "__main__":
    main()
