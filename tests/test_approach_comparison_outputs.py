import csv
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'analysis' / 'approach-comparison'


class ApproachComparisonOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((OUTPUT / 'heldout-manifest.json').read_text(encoding='utf-8'))
        cls.runs = json.loads((OUTPUT / 'runs' / 'all-runs.json').read_text(encoding='utf-8'))
        cls.metrics = json.loads((OUTPUT / 'evaluation' / 'comparison-metrics.json').read_text(encoding='utf-8'))
        cls.summary = json.loads((OUTPUT / 'evaluation' / 'summary.json').read_text(encoding='utf-8'))

    def test_three_new_nonduplicate_heldout_images(self) -> None:
        self.assertEqual(3, len(self.manifest))
        self.assertEqual({'T01', 'T02', 'T03'}, {row['task_id'] for row in self.manifest})
        for row in self.manifest:
            self.assertTrue((ROOT / row['file']).is_file())
            self.assertFalse(row['duplicate_check']['exact_duplicate'])
            self.assertFalse(row['duplicate_check']['near_duplicate'])
            self.assertGreater(row['duplicate_check']['minimum_dhash_distance'], row['duplicate_check']['near_duplicate_threshold'])

    def test_balanced_twelve_run_design(self) -> None:
        self.assertEqual(12, len(self.runs))
        combinations = {(run['task_id'], run['method'], run['repeat']) for run in self.runs}
        self.assertEqual(12, len(combinations))
        self.assertEqual({'evidence_pipeline', 'direct_multi_agent'}, {run['method'] for run in self.runs})
        for run in self.runs:
            self.assertTrue((ROOT / run['generated_image']['path']).is_file())
            self.assertGreater(run['generated_image']['width'], 0)
            self.assertGreater(run['generated_image']['height'], 0)

    def test_information_separation_is_explicit(self) -> None:
        evidence = [run for run in self.runs if run['method'] == 'evidence_pipeline']
        direct = [run for run in self.runs if run['method'] == 'direct_multi_agent']
        self.assertTrue(all(run['evidence'] for run in evidence))
        self.assertTrue(all(all(item['source_file'] and item['source_key'] for item in run['evidence']) for run in evidence))
        self.assertTrue(all(run['evidence'] == [] for run in direct))
        self.assertTrue(all(len(run['agent_trace']) == 3 for run in direct))

    def test_metrics_and_summary_are_complete(self) -> None:
        self.assertEqual(12, len(self.metrics))
        self.assertEqual(12, self.summary['experiment_size']['outputs'])
        for method in ('evidence_pipeline', 'direct_multi_agent'):
            row = self.summary['method_summary'][method]
            self.assertEqual(6, row['output_count'])
            self.assertGreaterEqual(row['mean_direction_hit_rate'], 0)
            self.assertLessEqual(row['mean_direction_hit_rate'], 1)
            self.assertGreaterEqual(row['mean_yolo_class_jaccard'], 0)
            self.assertLessEqual(row['mean_yolo_class_jaccard'], 1)

    def test_blind_review_assets_hide_method_names(self) -> None:
        mapping = json.loads((OUTPUT / 'blind-review' / 'private-mapping.json').read_text(encoding='utf-8'))
        with (OUTPUT / 'blind-review' / 'blind-review.csv').open(encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(12, len(mapping))
        self.assertEqual(12, len(rows))
        self.assertTrue(all(row['sample_alias'].startswith('S') for row in rows))
        self.assertTrue(all('method' not in row for row in rows))
        self.assertTrue(all((ROOT / row['result_image']).is_file() for row in rows))


if __name__ == '__main__':
    unittest.main()
