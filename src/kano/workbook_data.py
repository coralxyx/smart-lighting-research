from __future__ import annotations

from collections import defaultdict
from typing import Iterable


def _perception_summary(
    scene_pair_rows: Iterable[dict[str, object]],
) -> dict[tuple[str, str], dict[str, str]]:
    grouped: dict[tuple[str, str], list[tuple[str, int]]] = defaultdict(list)
    for row in scene_pair_rows:
        grouped[(str(row["scene"]), str(row["aesthetic"]))].append(
            (str(row["perception"]), int(row["count"]))
        )

    result: dict[tuple[str, str], dict[str, str]] = {}
    for key, values in grouped.items():
        ordered = sorted(values, key=lambda item: (-item[1], item[0]))
        total = sum(count for _, count in ordered)
        displayed = ordered[:4]
        remainder = sum(count for _, count in ordered[4:])
        parts = [f"{label} {count / total:.1%}" for label, count in displayed]
        if remainder:
            parts.append(f"其他 {remainder / total:.1%}")
        result[key] = {
            "main_perception": ordered[0][0],
            "perception_distribution": "；".join(parts),
        }
    return result


def build_workbook_payload(
    aggregates: dict[str, object], legacy: dict[str, object]
) -> dict[str, object]:
    touchpoints: dict[str, str] = legacy["touchpoint_by_aesthetic"]
    legacy_rows: dict[tuple[str, str], dict[str, str]] = legacy["scene_aesthetic"]
    perception_summary = _perception_summary(aggregates["scene_pair"])
    scene_totals = {
        str(row["scene"]): int(row["count"]) for row in aggregates["scene_counts"]
    }

    summary_rows = []
    for row in aggregates["scene_aesthetic"]:
        scene = str(row["scene"])
        aesthetic = str(row["aesthetic"])
        if scene == "无":
            continue
        metadata = legacy_rows.get((scene, aesthetic), {})
        summary_rows.append(
            {
                **row,
                "touchpoint": metadata.get(
                    "touchpoint", touchpoints.get(aesthetic, "")
                ),
                **perception_summary[(scene, aesthetic)],
                "legacy_classification": metadata.get("classification", ""),
                "legacy_priority": metadata.get("priority", ""),
                "legacy_recommendation": metadata.get("recommendation", ""),
            }
        )

    summary_rows.sort(
        key=lambda row: (str(row["scene"]), -int(row["count"]), str(row["aesthetic"]))
    )

    pair_rows = []
    for row in aggregates["scene_pair"]:
        positive = int(row["positive_count"])
        neutral = int(row["neutral_count"])
        negative = int(row["negative_count"])
        dominant = max(
            ((positive, "正向"), (neutral, "中性"), (negative, "负向")),
            key=lambda item: item[0],
        )[1]
        pair_rows.append(
            {
                **row,
                "touchpoint": touchpoints.get(str(row["aesthetic"]), ""),
                "dominant_sentiment": dominant,
            }
        )
    pair_rows.sort(
        key=lambda row: (-int(row["count"]), str(row["scene"]), str(row["aesthetic"]))
    )

    return {
        "method": {
            "name": "Kano-inspired 旧表复现",
            "classification_source": "legacy mapping",
            "classification_note": (
                "A/O/I/M 为旧工作簿静态结果；旧文件未保存可执行阈值公式。"
            ),
        },
        "record_count": aggregates["record_count"],
        "unique_post_count": aggregates["unique_post_count"],
        "records_per_post": aggregates["records_per_post"],
        "scene_totals": scene_totals,
        "scene_counts": aggregates["scene_counts"],
        "aesthetic_counts": aggregates["aesthetic_counts"],
        "perception_counts": aggregates["perception_counts"],
        "sentiment_counts": aggregates["sentiment_counts"],
        "touchpoint_by_aesthetic": touchpoints,
        "summary_rows": summary_rows,
        "pair_rows": pair_rows,
    }
