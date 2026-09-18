import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'analysis' / 'controlled-generation'


class ControlledGenerationOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads((OUTPUT / 'experiment.json').read_text(encoding='utf-8'))

    def test_three_pairs_and_six_generated_images_exist(self) -> None:
        self.assertEqual(3, len(self.report['experiments']))
        self.assertEqual(6, self.report['image_count'])
        variants = [variant for item in self.report['experiments'] for variant in item['variants']]
        self.assertEqual(6, len(variants))
        for variant in variants:
            self.assertTrue((OUTPUT / variant['file']).is_file(), variant['file'])

    def test_color_temperature_pair_has_expected_direction(self) -> None:
        experiment = self.report['experiments'][0]
        warm, cool = experiment['variants']
        self.assertGreater(warm['lighting_metrics']['warmth_index'], cool['lighting_metrics']['warmth_index'])
        self.assertEqual('暖色照明', warm['openclip_attributes']['色温感知']['label'])

    def test_hard_light_has_more_local_contrast(self) -> None:
        experiment = self.report['experiments'][1]
        soft, hard = experiment['variants']
        self.assertGreater(hard['lighting_metrics']['local_contrast_mean'], soft['lighting_metrics']['local_contrast_mean'])
        self.assertGreater(hard['lighting_metrics']['dynamic_range_p95_p05'], soft['lighting_metrics']['dynamic_range_p95_p05'])

    def test_task_focus_has_higher_roi_ratio_than_uniform(self) -> None:
        experiment = self.report['experiments'][2]
        focused, uniform = experiment['variants']
        self.assertGreater(focused['task_roi_metrics']['task_to_background_ratio'], uniform['task_roi_metrics']['task_to_background_ratio'])


if __name__ == '__main__':
    unittest.main()
