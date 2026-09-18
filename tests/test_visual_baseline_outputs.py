import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LightingBaselineOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output = ROOT / 'analysis' / 'lighting-baseline'
        self.records = json.loads((self.output / 'metrics.json').read_text(encoding='utf-8'))
        self.summary = json.loads((self.output / 'summary.json').read_text(encoding='utf-8'))

    def test_has_one_record_and_heatmap_per_base_image(self) -> None:
        image_root = ROOT / 'data' / 'raw' / 'base_images'
        images = sorted(
            path.relative_to(image_root).as_posix()
            for path in image_root.rglob('*')
            if path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}
        )
        self.assertEqual(24, len(images))
        self.assertEqual(images, [record['image_id'] for record in self.records])
        self.assertEqual(len(images), len(list((self.output / 'heatmaps').rglob('*.jpg'))))
        self.assertEqual(len(images), self.summary['image_count'])

    def test_normalized_metrics_are_in_bounds(self) -> None:
        bounded = (
            'mean_luminance', 'luminance_std', 'luminance_p05', 'luminance_p95',
            'dynamic_range_p95_p05', 'dark_area_ratio', 'bright_area_ratio',
            'highlight_area_ratio', 'local_contrast_mean', 'spatial_layering_std',
            'luminance_entropy', 'warm_pixel_ratio', 'bright_region_concentration',
        )
        for record in self.records:
            for key in bounded:
                self.assertGreaterEqual(record[key], 0.0, (record['image_id'], key))
                self.assertLessEqual(record[key], 1.0, (record['image_id'], key))
            self.assertEqual(16, len(record['grid_luminance']))


class OpenClipBaselineOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output = ROOT / 'analysis' / 'openclip-baseline'
        self.records = json.loads((self.output / 'predictions.json').read_text(encoding='utf-8'))
        self.summary = json.loads((self.output / 'summary.json').read_text(encoding='utf-8'))

    def test_contains_all_images_and_attribute_groups(self) -> None:
        expected_groups = {'色温感知', '光线柔和度', '照明方式', '光照层次', '明暗氛围'}
        self.assertEqual(24, len(self.records))
        self.assertEqual(24, self.summary['image_count'])
        for record in self.records:
            self.assertEqual(expected_groups, set(record['attributes']))

    def test_each_attribute_is_a_probability_distribution(self) -> None:
        for record in self.records:
            for result in record['attributes'].values():
                self.assertIn(result['label'], result['scores'])
                self.assertAlmostEqual(1.0, sum(result['scores'].values()), places=5)
                self.assertAlmostEqual(result['scores'][result['label']], result['confidence'], places=6)

    def test_summary_counts_cover_all_images(self) -> None:
        for result in self.summary['attribute_summary'].values():
            self.assertEqual(24, sum(result['label_counts'].values()))


if __name__ == '__main__':
    unittest.main()
