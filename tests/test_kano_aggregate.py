import unittest

from src.kano.aggregate import build_aggregates, stable_post_id
from src.kano.input import TaggedRecord


class KanoAggregateTests(unittest.TestCase):
    def test_stable_post_id_is_deterministic(self):
        self.assertEqual(stable_post_id("同一篇帖子"), stable_post_id("同一篇帖子"))
        self.assertNotEqual(stable_post_id("帖子A"), stable_post_id("帖子B"))

    def test_build_aggregates_counts_sentiment_and_posts(self):
        records = [
            TaggedRecord(2, "帖子A", "句子1", "睡眠", "照明", "舒适", "正向"),
            TaggedRecord(3, "帖子A", "句子2", "睡眠", "照明", "舒适", "负向"),
            TaggedRecord(4, "帖子B", "句子3", "工作", "照明", "专注", "中性"),
        ]
        result = build_aggregates(records)
        self.assertEqual(result["record_count"], 3)
        self.assertEqual(result["unique_post_count"], 2)
        self.assertEqual(result["records_per_post"]["median"], 1.5)
        sleeping = next(
            row
            for row in result["scene_aesthetic"]
            if row["scene"] == "睡眠" and row["aesthetic"] == "照明"
        )
        self.assertEqual(sleeping["count"], 2)
        self.assertEqual(sleeping["positive_count"], 1)
        self.assertEqual(sleeping["negative_count"], 1)


if __name__ == "__main__":
    unittest.main()
