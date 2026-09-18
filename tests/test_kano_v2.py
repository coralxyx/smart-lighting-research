from __future__ import annotations

import unittest

from src.kano.input import TaggedRecord
from src.kano.v2 import build_post_votes, classify_rates, resolve_sentiment


class KanoV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "minimum_post_count": 5,
            "classification_thresholds": {
                "must_be_negative_rate": 0.2,
                "one_dimensional_positive_rate": 0.4,
                "one_dimensional_negative_rate": 0.1,
                "attractive_positive_rate": 0.55,
                "attractive_negative_rate_max_exclusive": 0.1,
                "indifferent_neutral_rate": 0.5,
            },
        }

    def test_conflict_resolution_uses_majority_then_precedence(self) -> None:
        self.assertEqual(resolve_sentiment(["正向", "正向", "负向"]), ("正向", True))
        self.assertEqual(resolve_sentiment(["正向", "负向"]), ("负向", True))
        self.assertEqual(resolve_sentiment(["中性", "正向"]), ("正向", True))

    def test_post_votes_collapse_duplicate_records(self) -> None:
        records = [
            TaggedRecord(2, "same post", "a", "学习工作", "照明与色调", "舒适感", "正向"),
            TaggedRecord(3, "same post", "b", "学习工作", "照明与色调", "舒适感", "正向"),
        ]
        votes = build_post_votes(records, ("scene", "aesthetic"))
        self.assertEqual(len(votes), 1)
        self.assertEqual(votes[0]["raw_record_count"], 2)
        self.assertEqual(votes[0]["duplicate_records_collapsed"], 1)

    def test_classification_precedence(self) -> None:
        self.assertEqual(classify_rates(4, 0.75, 0.25, 0.0, self.config), "样本不足")
        self.assertEqual(classify_rates(10, 0.3, 0.4, 0.3, self.config), "基础型/风险项（M-inspired）")
        self.assertEqual(classify_rates(10, 0.7, 0.2, 0.1, self.config), "期望型（O-inspired）")
        self.assertEqual(classify_rates(10, 0.6, 0.4, 0.0, self.config), "魅力型（A-inspired）")
        self.assertEqual(classify_rates(10, 0.3, 0.6, 0.1, self.config), "无差异型（I-inspired）")


if __name__ == "__main__":
    unittest.main()
