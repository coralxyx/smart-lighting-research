from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = ROOT / 'analysis' / 'controlled-generation'

EXPERIMENTS = [
    {
        'id': 'color-temperature',
        'title': '客厅：色温单变量',
        'source': 'data/raw/base_images/living_room/living_02_pexels_10161225.jpg',
        'controlled_variable': 'artificial-light color temperature',
        'constants': ['camera', 'geometry', 'furniture', 'object count', 'target exposure'],
        'variants': [
            {'id': 'warm-2700k', 'label': 'A 暖色 2700K', 'target': 'warm 2700 K', 'file': 'images/color-temperature/warm-2700k.png'},
            {'id': 'cool-5000k', 'label': 'B 冷中性 5000K', 'target': 'cool-neutral 5000 K', 'file': 'images/color-temperature/cool-5000k.png'},
        ],
    },
    {
        'id': 'light-distribution',
        'title': '卧室：光线分布单变量',
        'source': 'data/raw/base_images/bedroom/bedroom_06_pexels_3933240.jpg',
        'controlled_variable': 'incident-light softness and directionality',
        'constants': ['camera', 'geometry', 'objects', 'color temperature', 'target exposure'],
        'variants': [
            {'id': 'soft-diffuse', 'label': 'A 柔和漫射', 'target': 'soft diffuse window light', 'file': 'images/light-distribution/soft-diffuse.png'},
            {'id': 'hard-directional', 'label': 'B 硬朗定向', 'target': 'hard directional window light', 'file': 'images/light-distribution/hard-directional.png'},
        ],
    },
    {
        'id': 'task-focus',
        'title': '书房：任务区聚焦单变量',
        'source': 'data/raw/base_images/study/study_03_pexels_4307570.jpg',
        'controlled_variable': 'task-zone versus ambient lighting balance',
        'constants': ['camera', 'geometry', 'objects', 'fixtures', 'color temperature'],
        'task_roi_normalized': [0.23, 0.38, 0.49, 0.63],
        'variants': [
            {'id': 'focused-task', 'label': 'A 任务区聚焦', 'target': 'bright desk with restrained ambient', 'file': 'images/task-focus/focused-task.png'},
            {'id': 'uniform-ambient', 'label': 'B 均匀环境光', 'target': 'uniform general illumination', 'file': 'images/task-focus/uniform-ambient.png'},
        ],
    },
]


def load_font(size: int) -> ImageFont.ImageFont:
    for path in (Path('C:/Windows/Fonts/msyh.ttc'), Path('C:/Windows/Fonts/simhei.ttf')):
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def luminance(path: Path) -> np.ndarray:
    rgb = np.asarray(Image.open(path).convert('RGB'), dtype=np.float32) / 255.0
    return 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]


def roi_contrast(path: Path, roi: list[float]) -> dict[str, float]:
    gray = luminance(path)
    height, width = gray.shape
    x1, y1, x2, y2 = roi
    task = gray[int(y1 * height):int(y2 * height), int(x1 * width):int(x2 * width)]
    mask = np.ones_like(gray, dtype=bool)
    mask[int(y1 * height):int(y2 * height), int(x1 * width):int(x2 * width)] = False
    task_mean = float(task.mean())
    background_mean = float(gray[mask].mean())
    return {
        'task_mean_luminance': round(task_mean, 6),
        'background_mean_luminance': round(background_mean, 6),
        'task_to_background_ratio': round(task_mean / max(background_mean, 1e-6), 6),
    }


def build_report() -> dict[str, Any]:
    light_records = json.loads((EXPERIMENT_ROOT / 'evaluation' / 'lighting' / 'metrics.json').read_text(encoding='utf-8'))
    clip_records = json.loads((EXPERIMENT_ROOT / 'evaluation' / 'openclip' / 'predictions.json').read_text(encoding='utf-8'))
    light_by_id = {row['image_id']: row for row in light_records}
    clip_by_id = {row['image_id']: row for row in clip_records}
    report_experiments = []
    for experiment in EXPERIMENTS:
        item = dict(experiment)
        variants = []
        for variant in experiment['variants']:
            relative = variant['file'].removeprefix('images/')
            enriched = dict(variant)
            enriched['lighting_metrics'] = light_by_id[relative]
            enriched['openclip_attributes'] = clip_by_id[relative]['attributes']
            if experiment['id'] == 'task-focus':
                enriched['task_roi_metrics'] = roi_contrast(EXPERIMENT_ROOT / variant['file'], experiment['task_roi_normalized'])
            variants.append(enriched)
        item['variants'] = variants
        report_experiments.append(item)
    return {
        'method': 'built-in image generation edit mode',
        'design': 'three paired single-variable A/B experiments',
        'image_count': 6,
        'experiments': report_experiments,
        'limitations': [
            'Generated edits are visual design proposals rather than photometric simulations.',
            'Despite invariant prompts, generative editing may slightly change geometry, texture, crop, or small objects.',
            'Color-temperature values are target descriptions, not spectrometer measurements.',
            'OpenCLIP results are zero-shot similarities and are not ground-truth aesthetic labels.',
        ],
    }


def build_overview() -> None:
    columns = 3
    tile_width, image_height, caption_height = 560, 350, 54
    canvas = Image.new('RGB', (columns * tile_width, len(EXPERIMENTS) * (image_height + caption_height)), '#E5E7EB')
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(22)
    caption_font = load_font(17)
    for row, experiment in enumerate(EXPERIMENTS):
        entries = [
            ('原始底图', ROOT / experiment['source']),
            (experiment['variants'][0]['label'], EXPERIMENT_ROOT / experiment['variants'][0]['file']),
            (experiment['variants'][1]['label'], EXPERIMENT_ROOT / experiment['variants'][1]['file']),
        ]
        for column, (label, path) in enumerate(entries):
            image = Image.open(path).convert('RGB')
            image = ImageOps.fit(image, (tile_width, image_height), method=Image.Resampling.LANCZOS)
            x = column * tile_width
            y = row * (image_height + caption_height)
            canvas.paste(image, (x, y))
            draw.rectangle((x, y + image_height, x + tile_width, y + image_height + caption_height), fill='#FFFFFF')
            caption = experiment['title'] if column == 0 else label
            font = title_font if column == 0 else caption_font
            draw.text((x + 14, y + image_height + 13), caption, fill='#111827', font=font)
    canvas.save(EXPERIMENT_ROOT / 'overview.jpg', quality=92)


def main() -> None:
    report = build_report()
    (EXPERIMENT_ROOT / 'experiment.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    build_overview()
    print(json.dumps({'image_count': report['image_count'], 'experiment_count': len(report['experiments'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
