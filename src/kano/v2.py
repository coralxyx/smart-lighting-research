from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import math
import random
from typing import Iterable

from .aggregate import stable_post_id
from .input import TaggedRecord


SENTIMENTS = ("正向", "中性", "负向")
CONFLICT_PRECEDENCE = ("负向", "正向", "中性")


def resolve_sentiment(sentiments: Iterable[str]) -> tuple[str, bool]:
    counts = Counter(sentiments)
    maximum = max(counts.values())
    winners = {label for label, count in counts.items() if count == maximum}
    resolved = next(label for label in CONFLICT_PRECEDENCE if label in winners)
    return resolved, len(counts) > 1


def build_post_votes(
    records: list[TaggedRecord], key_fields: tuple[str, ...]
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, ...], list[str]] = defaultdict(list)
    first_row: dict[tuple[str, ...], int] = {}
    for record in records:
        post_id = stable_post_id(record.full_text)
        key = (post_id, *(getattr(record, field) for field in key_fields))
        grouped[key].append(record.sentiment)
        first_row.setdefault(key, record.row_number)

    votes = []
    for key, sentiments in grouped.items():
        resolved, conflict = resolve_sentiment(sentiments)
        row = {"post_id": key[0]}
        row.update(dict(zip(key_fields, key[1:])))
        row.update(
            {
                "sentiment": resolved,
                "raw_record_count": len(sentiments),
                "duplicate_records_collapsed": len(sentiments) - 1,
                "conflict": conflict,
                "source_first_row": first_row[key],
            }
        )
        votes.append(row)
    return sorted(votes, key=lambda row: int(row["source_first_row"]))


def classify_rates(
    post_count: int,
    positive_rate: float,
    neutral_rate: float,
    negative_rate: float,
    config: dict[str, object],
) -> str:
    if post_count < int(config["minimum_post_count"]):
        return "样本不足"
    thresholds = config["classification_thresholds"]
    if negative_rate >= float(thresholds["must_be_negative_rate"]):
        return "基础型/风险项（M-inspired）"
    if (
        positive_rate >= float(thresholds["one_dimensional_positive_rate"])
        and negative_rate >= float(thresholds["one_dimensional_negative_rate"])
    ):
        return "期望型（O-inspired）"
    if (
        positive_rate >= float(thresholds["attractive_positive_rate"])
        and negative_rate
        < float(thresholds["attractive_negative_rate_max_exclusive"])
    ):
        return "魅力型（A-inspired）"
    if neutral_rate >= float(thresholds["indifferent_neutral_rate"]):
        return "无差异型（I-inspired）"
    return "混合/待复核"


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _bootstrap_group(
    sentiments: list[str], point_class: str, group_key: tuple[str, ...], config: dict[str, object]
) -> dict[str, object]:
    bootstrap = config["bootstrap"]
    iterations = int(bootstrap["iterations"])
    confidence = float(bootstrap["confidence_level"])
    alpha = (1.0 - confidence) / 2
    seed_material = "|".join(group_key).encode("utf-8")
    group_seed = int.from_bytes(sha256(seed_material).digest()[:4], "big")
    rng = random.Random(int(bootstrap["random_seed"]) + group_seed)
    rates = {label: [] for label in SENTIMENTS}
    classes: Counter[str] = Counter()
    size = len(sentiments)

    for _ in range(iterations):
        sample = [sentiments[rng.randrange(size)] for _ in range(size)]
        counts = Counter(sample)
        positive_rate = counts["正向"] / size
        neutral_rate = counts["中性"] / size
        negative_rate = counts["负向"] / size
        rates["正向"].append(positive_rate)
        rates["中性"].append(neutral_rate)
        rates["负向"].append(negative_rate)
        classes[
            classify_rates(
                size, positive_rate, neutral_rate, negative_rate, config
            )
        ] += 1

    modal_class, modal_count = classes.most_common(1)[0]
    return {
        "positive_ci_low": _percentile(rates["正向"], alpha),
        "positive_ci_high": _percentile(rates["正向"], 1 - alpha),
        "neutral_ci_low": _percentile(rates["中性"], alpha),
        "neutral_ci_high": _percentile(rates["中性"], 1 - alpha),
        "negative_ci_low": _percentile(rates["负向"], alpha),
        "negative_ci_high": _percentile(rates["负向"], 1 - alpha),
        "classification_stability": classes[point_class] / iterations,
        "bootstrap_modal_class": modal_class,
        "bootstrap_modal_rate": modal_count / iterations,
        "bootstrap_class_counts": dict(classes),
    }


def aggregate_post_votes(
    votes: list[dict[str, object]],
    key_fields: tuple[str, ...],
    config: dict[str, object],
    include_bootstrap: bool,
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
    for vote in votes:
        grouped[tuple(str(vote[field]) for field in key_fields)].append(vote)

    output = []
    for key, group_votes in grouped.items():
        counts = Counter(str(vote["sentiment"]) for vote in group_votes)
        post_count = len(group_votes)
        positive_rate = counts["正向"] / post_count
        neutral_rate = counts["中性"] / post_count
        negative_rate = counts["负向"] / post_count
        classification = classify_rates(
            post_count, positive_rate, neutral_rate, negative_rate, config
        )
        row: dict[str, object] = dict(zip(key_fields, key))
        row.update(
            {
                "raw_record_count": sum(
                    int(vote["raw_record_count"]) for vote in group_votes
                ),
                "post_count": post_count,
                "duplicate_records_collapsed": sum(
                    int(vote["duplicate_records_collapsed"])
                    for vote in group_votes
                ),
                "conflict_post_count": sum(bool(vote["conflict"]) for vote in group_votes),
                "positive_count": counts["正向"],
                "neutral_count": counts["中性"],
                "negative_count": counts["负向"],
                "positive_rate": positive_rate,
                "neutral_rate": neutral_rate,
                "negative_rate": negative_rate,
                "classification": classification,
                "priority_rank": int(config["class_priority"][classification]),
                "recommended_action": config["class_action"][classification],
            }
        )
        if include_bootstrap:
            row.update(
                _bootstrap_group(
                    [str(vote["sentiment"]) for vote in group_votes],
                    classification,
                    key,
                    config,
                )
            )
            flags = []
            stability = float(row["classification_stability"])
            if stability < float(config["bootstrap"]["low_stability_threshold"]):
                flags.append("分类稳定率低")
            maximum_width = max(
                float(row["positive_ci_high"]) - float(row["positive_ci_low"]),
                float(row["neutral_ci_high"]) - float(row["neutral_ci_low"]),
                float(row["negative_ci_high"]) - float(row["negative_ci_low"]),
            )
            if maximum_width > float(config["bootstrap"]["wide_interval_threshold"]):
                flags.append("置信区间较宽")
            if post_count < int(config["minimum_post_count"]):
                flags.append("样本不足")
            if int(row["conflict_post_count"]):
                flags.append("存在同帖情感冲突")
            row["quality_flags"] = "；".join(flags) if flags else "无"
        output.append(row)

    return sorted(
        output,
        key=lambda row: (
            *(str(row[field]) for field in key_fields[:-1]),
            int(row["priority_rank"]),
            -int(row["post_count"]),
            str(row[key_fields[-1]]),
        ),
    )


def build_v2_analysis(
    records: list[TaggedRecord], config: dict[str, object]
) -> dict[str, object]:
    excluded_scene = str(config["excluded_scene"])
    formal_records = [record for record in records if record.scene != excluded_scene]
    scene_votes = build_post_votes(formal_records, ("scene", "aesthetic"))
    pair_votes = build_post_votes(formal_records, ("scene", "aesthetic", "perception"))
    summary_rows = aggregate_post_votes(
        scene_votes, ("scene", "aesthetic"), config, include_bootstrap=True
    )
    pair_rows = aggregate_post_votes(
        pair_votes,
        ("scene", "aesthetic", "perception"),
        config,
        include_bootstrap=False,
    )
    touchpoints = config["touchpoint_mapping"]
    for row in summary_rows:
        row["touchpoint"] = touchpoints.get(str(row["aesthetic"]), "")
    for row in pair_rows:
        row["touchpoint"] = touchpoints.get(str(row["aesthetic"]), "")

    return {
        "raw_record_count": len(records),
        "formal_record_count": len(formal_records),
        "unique_post_count": len({stable_post_id(record.full_text) for record in records}),
        "formal_unique_post_count": len(
            {stable_post_id(record.full_text) for record in formal_records}
        ),
        "scene_post_vote_count": len(scene_votes),
        "scene_duplicate_records_collapsed": sum(
            int(vote["duplicate_records_collapsed"]) for vote in scene_votes
        ),
        "scene_conflict_post_votes": sum(bool(vote["conflict"]) for vote in scene_votes),
        "pair_post_vote_count": len(pair_votes),
        "pair_duplicate_records_collapsed": sum(
            int(vote["duplicate_records_collapsed"]) for vote in pair_votes
        ),
        "pair_conflict_post_votes": sum(bool(vote["conflict"]) for vote in pair_votes),
        "scene_votes": scene_votes,
        "summary_rows": summary_rows,
        "pair_rows": pair_rows,
    }
