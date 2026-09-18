from __future__ import annotations

import unittest

from src.kano.workbook_data import build_workbook_payload


class WorkbookPayloadTests(unittest.TestCase):
    def test_builds_perception_summary_and_legacy_fields(self) -> None:
        aggregates = {
            "record_count": 3,
            "unique_post_count": 1,
            "records_per_post": {"minimum": 3, "maximum": 3, "median": 3.0},
            "scene_counts": [{"scene": "学习工作", "count": 3}],
            "aesthetic_counts": [{"aesthetic": "照明与色调", "count": 3}],
            "perception_counts": [{"perception": "舒适感", "count": 2}],
            "sentiment_counts": [{"sentiment": "正向", "count": 2}],
            "scene_aesthetic": [{"scene": "学习工作", "aesthetic": "照明与色调", "count": 3, "positive_count": 2, "neutral_count": 1, "negative_count": 0}],
            "scene_pair": [
                {"scene": "学习工作", "aesthetic": "照明与色调", "perception": "舒适感", "count": 2, "positive_count": 2, "neutral_count": 0, "negative_count": 0},
                {"scene": "学习工作", "aesthetic": "照明与色调", "perception": "专注", "count": 1, "positive_count": 0, "neutral_count": 1, "negative_count": 0},
            ],
        }
        legacy = {
            "touchpoint_by_aesthetic": {"照明与色调": "视觉触点"},
            "scene_aesthetic": {
                ("学习工作", "照明与色调"): {
                    "touchpoint": "视觉触点",
                    "classification": "魅力型（A）",
                    "priority": "强化为卖点",
                    "recommendation": "示例建议",
                }
            },
        }

        payload = build_workbook_payload(aggregates, legacy)

        self.assertEqual(payload["summary_rows"][0]["main_perception"], "舒适感")
        self.assertEqual(payload["summary_rows"][0]["perception_distribution"], "舒适感 66.7%；专注 33.3%")
        self.assertEqual(payload["summary_rows"][0]["legacy_classification"], "魅力型（A）")
        self.assertEqual(payload["pair_rows"][0]["dominant_sentiment"], "正向")


if __name__ == "__main__":
    unittest.main()
