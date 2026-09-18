import csv
import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / 'analysis' / 'yolo-baseline'


class YoloBaselineOutputTests(unittest.TestCase):
    def test_summary_matches_prediction_outputs(self):
        summary = json.loads((OUTPUT_DIR / 'summary.json').read_text(encoding='utf-8'))
        records = [json.loads(line) for line in (OUTPUT_DIR / 'predictions.jsonl').read_text(encoding='utf-8').splitlines() if line]
        self.assertEqual(summary['image_count'], 24)
        self.assertEqual(len(records), 24)
        self.assertEqual(summary['total_detection_count'], sum(row['detection_count'] for row in records))
        self.assertEqual(summary['relevant_detection_count'], sum(row['relevant_detection_count'] for row in records))

    def test_detection_coordinates_are_normalized(self):
        with (OUTPUT_DIR / 'detections.csv').open(encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 73)
        for row in rows:
            for field in ['x1', 'y1', 'x2', 'y2', 'center_x', 'center_y', 'area_ratio']:
                value = float(row[field])
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)

    def test_every_image_has_an_annotated_output(self):
        records = [json.loads(line) for line in (OUTPUT_DIR / 'predictions.jsonl').read_text(encoding='utf-8').splitlines() if line]
        for record in records:
            self.assertTrue((PROJECT_ROOT / record['annotated_path']).exists())


if __name__ == '__main__':
    unittest.main()
