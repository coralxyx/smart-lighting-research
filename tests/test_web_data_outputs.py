import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = PROJECT_ROOT / 'analysis' / 'web-data'
CHART_DIR = PROJECT_ROOT / 'deliverables' / 'charts'


def load_json(filename: str):
    return json.loads((WEB_DIR / filename).read_text(encoding='utf-8'))


class WebDataOutputTests(unittest.TestCase):
    def test_web_data_metrics_match_validated_outputs(self):
        metadata = load_json('metadata.json')
        metrics = metadata['metrics']
        self.assertEqual(metrics['tagged_records'], 4747)
        self.assertEqual(metrics['formal_scene_records'], 2396)
        self.assertEqual(metrics['legacy_combinations'], 52)
        self.assertEqual(metrics['v2_combinations'], 52)
        self.assertEqual(metrics['v2_post_votes'], 1649)
        self.assertEqual(metrics['changed_classifications'], 33)
        self.assertEqual(metrics['low_stability_combinations'], 17)

    def test_web_manifest_files_exist_and_parse(self):
        manifest = load_json('manifest.json')
        for entry in manifest['files']:
            path = WEB_DIR / entry['path']
            self.assertTrue(path.exists())
            json.loads(path.read_text(encoding='utf-8'))

    def test_defense_chart_manifest_files_exist(self):
        manifest = json.loads((CHART_DIR / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(manifest['charts']), 6)
        for entry in manifest['charts']:
            path = CHART_DIR / entry['path']
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 10_000)


if __name__ == '__main__':
    unittest.main()
