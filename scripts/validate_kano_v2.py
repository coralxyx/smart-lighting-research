from __future__ import annotations

from collections import Counter
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.kano.v2 import classify_rates  # noqa: E402


def main() -> None:
    payload_path = (
        PROJECT_ROOT / "analysis" / "generated" / "kano-inspired-v2-data.json"
    )
    output_path = (
        PROJECT_ROOT / "analysis" / "generated" / "kano-inspired-v2-validation.json"
    )
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    config = payload["config"]
    errors: list[str] = []

    for index, row in enumerate(payload["summary_rows"], start=1):
        vote_total = row["positive_count"] + row["neutral_count"] + row["negative_count"]
        if vote_total != row["post_count"]:
            errors.append(f"summary row {index}: vote total mismatch")
        rate_total = row["positive_rate"] + row["neutral_rate"] + row["negative_rate"]
        if abs(rate_total - 1.0) > 1e-12:
            errors.append(f"summary row {index}: rate total mismatch")
        expected_class = classify_rates(
            row["post_count"],
            row["positive_rate"],
            row["neutral_rate"],
            row["negative_rate"],
            config,
        )
        if expected_class != row["classification"]:
            errors.append(f"summary row {index}: classification mismatch")
        for field in (
            "positive_ci_low",
            "positive_ci_high",
            "neutral_ci_low",
            "neutral_ci_high",
            "negative_ci_low",
            "negative_ci_high",
            "classification_stability",
            "bootstrap_modal_rate",
        ):
            if not 0.0 <= float(row[field]) <= 1.0:
                errors.append(f"summary row {index}: {field} outside [0,1]")

    for index, row in enumerate(payload["pair_rows"], start=1):
        vote_total = row["positive_count"] + row["neutral_count"] + row["negative_count"]
        if vote_total != row["post_count"]:
            errors.append(f"pair row {index}: vote total mismatch")

    class_counts = Counter(row["classification"] for row in payload["summary_rows"])
    if dict(class_counts) != payload["class_counts"]:
        errors.append("class count summary mismatch")
    if len(payload["scene_votes"]) != payload["scene_post_vote_count"]:
        errors.append("scene vote row count mismatch")

    report = {
        "valid": not errors,
        "errors": errors,
        "summary_group_count": len(payload["summary_rows"]),
        "pair_group_count": len(payload["pair_rows"]),
        "scene_post_vote_count": payload["scene_post_vote_count"],
        "class_counts": dict(class_counts),
        "legacy_change_count": payload["legacy_change_count"],
        "low_stability_count": payload["low_stability_count"],
    }
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
