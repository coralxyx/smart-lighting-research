from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from typing import Iterable

from .input import TaggedRecord


def stable_post_id(full_text: str) -> str:
    return sha256(full_text.encode("utf-8")).hexdigest()[:16]


def _counter_rows(counter: Counter[str], key_name: str) -> list[dict[str, object]]:
    return [
        {key_name: key, "count": count}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _group_records(
    records: Iterable[TaggedRecord], key_fields: tuple[str, ...]
) -> list[dict[str, object]]:
    groups: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    for record in records:
        key = tuple(getattr(record, field) for field in key_fields)
        groups[key][record.sentiment] += 1

    output: list[dict[str, object]] = []
    for key, sentiment_counts in groups.items():
        total = sum(sentiment_counts.values())
        row: dict[str, object] = dict(zip(key_fields, key))
        row.update(
            {
                "count": total,
                "positive_count": sentiment_counts["正向"],
                "neutral_count": sentiment_counts["中性"],
                "negative_count": sentiment_counts["负向"],
                "positive_rate": sentiment_counts["正向"] / total if total else 0.0,
                "neutral_rate": sentiment_counts["中性"] / total if total else 0.0,
                "negative_rate": sentiment_counts["负向"] / total if total else 0.0,
            }
        )
        output.append(row)

    return sorted(
        output,
        key=lambda row: (
            *(str(row[field]) for field in key_fields[:-1]),
            -int(row["count"]),
            str(row[key_fields[-1]]),
        ),
    )


def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[midpoint])
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2


def build_aggregates(records: list[TaggedRecord]) -> dict[str, object]:
    scene_counts = Counter(record.scene for record in records)
    aesthetic_counts = Counter(record.aesthetic for record in records)
    perception_counts = Counter(record.perception for record in records)
    sentiment_counts = Counter(record.sentiment for record in records)
    post_counts = Counter(stable_post_id(record.full_text) for record in records)

    return {
        "record_count": len(records),
        "unique_post_count": len(post_counts),
        "records_per_post": {
            "minimum": min(post_counts.values()) if post_counts else 0,
            "maximum": max(post_counts.values()) if post_counts else 0,
            "median": _median(list(post_counts.values())),
        },
        "scene_counts": _counter_rows(scene_counts, "scene"),
        "aesthetic_counts": _counter_rows(aesthetic_counts, "aesthetic"),
        "perception_counts": _counter_rows(perception_counts, "perception"),
        "sentiment_counts": _counter_rows(sentiment_counts, "sentiment"),
        "scene_aesthetic": _group_records(records, ("scene", "aesthetic")),
        "scene_pair": _group_records(records, ("scene", "aesthetic", "perception")),
        "global_pair": _group_records(records, ("aesthetic", "perception")),
    }
