from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web'


class IdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids = set()
        self.sources = []

    def handle_starttag(self, tag, attrs) -> None:
        values = dict(attrs)
        if 'id' in values:
            self.ids.add(values['id'])
        if tag in {'img', 'script', 'link'}:
            source = values.get('src') or values.get('href')
            if source:
                self.sources.append(source)


class WebAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (WEB / 'index.html').read_text(encoding='utf-8')
        cls.script = (WEB / 'app.js').read_text(encoding='utf-8')
        cls.parser = IdCollector()
        cls.parser.feed(cls.html)

    def test_required_sections_and_mount_points_exist(self) -> None:
        required = {
            'overview', 'comparison', 'vision', 'generation', 'approach', 'kpi-grid',
            'scene-select', 'priority-bars', 'touchpoint-body',
            'comparison-body', 'vision-kpis', 'experiment-grid', 'approach-kpis', 'approach-body',
        }
        self.assertTrue(required.issubset(self.parser.ids))

    def test_local_assets_exist(self) -> None:
        for source in self.parser.sources:
            if source.startswith('http'):
                continue
            self.assertTrue((WEB / source).resolve().is_file(), source)

    def test_script_references_all_data_contracts(self) -> None:
        expected = {
            '../analysis/web-data/dashboard-data.json',
            '../analysis/yolo-baseline/summary.json',
            '../analysis/lighting-baseline/summary.json',
            '../analysis/openclip-baseline/summary.json',
            '../analysis/controlled-generation/experiment.json',
            '../analysis/approach-comparison/evaluation/summary.json',
        }
        for path in expected:
            self.assertIn(path, self.script)
            self.assertTrue((WEB / path).resolve().is_file(), path)


if __name__ == '__main__':
    unittest.main()
