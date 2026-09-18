from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path
import statistics
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / 'config' / 'lighting_analysis.json'
DEFAULT_INPUT = PROJECT_ROOT / 'data' / 'raw' / 'base_images'
DEFAULT_OUTPUT = PROJECT_ROOT / 'analysis' / 'lighting-baseline'
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run interpretable lighting analysis on base images.')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--input-dir', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def find_images(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.rglob('*') if path.suffix.lower() in IMAGE_SUFFIXES)


def read_image(path: Path) -> np.ndarray:
    data = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f'Cannot decode image: {path}')
    return image


def normalized_entropy(gray: np.ndarray) -> float:
    histogram = cv2.calcHist([(gray * 255).astype(np.uint8)], [0], None, [256], [0, 256]).ravel()
    probabilities = histogram[histogram > 0] / histogram.sum()
    entropy = -float(np.sum(probabilities * np.log2(probabilities)))
    return entropy / 8.0


def bright_components(mask: np.ndarray, minimum_area: float) -> tuple[int, float]:
    cleaned = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    count, _, stats, _ = cv2.connectedComponentsWithStats(cleaned, connectivity=8)
    areas = [int(stats[index, cv2.CC_STAT_AREA]) for index in range(1, count) if int(stats[index, cv2.CC_STAT_AREA]) >= minimum_area]
    if not areas:
        return 0, 0.0
    return len(areas), max(areas) / sum(areas)


def grid_luminance(gray: np.ndarray, rows: int, columns: int) -> list[float]:
    height, width = gray.shape
    values: list[float] = []
    for row in range(rows):
        for column in range(columns):
            y1, y2 = row * height // rows, (row + 1) * height // rows
            x1, x2 = column * width // columns, (column + 1) * width // columns
            values.append(float(gray[y1:y2, x1:x2].mean()))
    return values


def analyze_image(path: Path, input_dir: Path, config: dict[str, Any]) -> tuple[dict[str, Any], np.ndarray]:
    image = read_image(path)
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    dark_mask = gray <= float(config['dark_threshold'])
    bright_mask = gray >= float(config['bright_threshold'])
    highlight_mask = gray >= float(config['highlight_threshold'])
    local_mean = cv2.blur(gray, (31, 31))
    local_square_mean = cv2.blur(gray * gray, (31, 31))
    local_std = np.sqrt(np.maximum(local_square_mean - local_mean * local_mean, 0.0))
    grid_values = grid_luminance(gray, int(config['grid_rows']), int(config['grid_columns']))
    minimum_area = width * height * float(config['minimum_bright_component_area_ratio'])
    component_count, concentration = bright_components(highlight_mask, minimum_area)
    ys, xs = np.where(highlight_mask)
    highlight_center = [round(float(xs.mean() / width), 6), round(float(ys.mean() / height), 6)] if len(xs) else None
    relative = path.relative_to(input_dir)
    try:
        source_path = path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        source_path = path.resolve().as_posix()
    metrics = {
        'image_id': relative.as_posix(),
        'room': relative.parts[0],
        'source_path': source_path,
        'width': width,
        'height': height,
        'mean_luminance': round(float(gray.mean()), 6),
        'luminance_std': round(float(gray.std()), 6),
        'luminance_p05': round(float(np.percentile(gray, 5)), 6),
        'luminance_p95': round(float(np.percentile(gray, 95)), 6),
        'dynamic_range_p95_p05': round(float(np.percentile(gray, 95) - np.percentile(gray, 5)), 6),
        'dark_area_ratio': round(float(dark_mask.mean()), 6),
        'bright_area_ratio': round(float(bright_mask.mean()), 6),
        'highlight_area_ratio': round(float(highlight_mask.mean()), 6),
        'local_contrast_mean': round(float(local_std.mean()), 6),
        'spatial_layering_std': round(float(statistics.pstdev(grid_values)), 6),
        'luminance_entropy': round(normalized_entropy(gray), 6),
        'warm_pixel_ratio': round(float(((lab[:, :, 2] >= int(config['warm_lab_b_threshold'])) & (gray > 0.2)).mean()), 6),
        'warmth_index': round(float((lab[:, :, 2].astype(np.float32).mean() - 128.0) / 127.0), 6),
        'bright_region_count': component_count,
        'bright_region_concentration': round(concentration, 6),
        'highlight_center_normalized': highlight_center,
        'grid_luminance': [round(value, 6) for value in grid_values],
    }
    return metrics, gray


def save_heatmap(gray: np.ndarray, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    luminance = (np.clip(gray, 0.0, 1.0) * 255).astype(np.uint8)
    colored = cv2.applyColorMap(luminance, cv2.COLORMAP_INFERNO)
    success, encoded = cv2.imencode('.jpg', colored, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not success:
        raise RuntimeError(f'Cannot encode heatmap: {destination}')
    encoded.tofile(destination)


def write_outputs(records: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'metrics.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    fieldnames = [key for key in records[0] if key not in {'grid_luminance', 'highlight_center_normalized'}]
    fieldnames.extend(['highlight_center_x', 'highlight_center_y'])
    with (output_dir / 'metrics.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = {key: value for key, value in record.items() if key in fieldnames}
            center = record['highlight_center_normalized'] or [None, None]
            row['highlight_center_x'], row['highlight_center_y'] = center
            writer.writerow(row)


def build_summary(records: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    metric_names = [
        'mean_luminance', 'luminance_std', 'dynamic_range_p95_p05', 'dark_area_ratio',
        'bright_area_ratio', 'highlight_area_ratio', 'local_contrast_mean',
        'spatial_layering_std', 'luminance_entropy', 'warm_pixel_ratio', 'warmth_index',
        'bright_region_count', 'bright_region_concentration',
    ]
    room_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        room_records[str(record['room'])].append(record)

    def aggregate(rows: list[dict[str, Any]]) -> dict[str, float]:
        return {name: round(statistics.mean(float(row[name]) for row in rows), 6) for name in metric_names}

    brightest = max(records, key=lambda row: float(row['mean_luminance']))
    darkest = min(records, key=lambda row: float(row['mean_luminance']))
    most_layered = max(records, key=lambda row: float(row['spatial_layering_std']))
    warmest = max(records, key=lambda row: float(row['warmth_index']))
    return {
        'method_name': config['method_name'],
        'method_version': config['method_version'],
        'image_count': len(records),
        'global_mean': aggregate(records),
        'room_mean': {room: aggregate(rows) for room, rows in sorted(room_records.items())},
        'extremes': {
            'brightest': {'image_id': brightest['image_id'], 'mean_luminance': brightest['mean_luminance']},
            'darkest': {'image_id': darkest['image_id'], 'mean_luminance': darkest['mean_luminance']},
            'most_spatially_layered': {'image_id': most_layered['image_id'], 'spatial_layering_std': most_layered['spatial_layering_std']},
            'warmest_proxy': {'image_id': warmest['image_id'], 'warmth_index': warmest['warmth_index']},
        },
        'parameters': {key: value for key, value in config.items() if key not in {'limitations', 'method_name', 'method_version'}},
        'limitations': config['limitations'],
    }


def build_overview(records: list[dict[str, Any]], output_dir: Path) -> None:
    columns = 4
    tile_width, tile_height = 320, 210
    rows = math.ceil(len(records) / columns)
    overview = Image.new('RGB', (columns * tile_width, rows * tile_height), '#E5E7EB')
    draw = ImageDraw.Draw(overview)
    for index, record in enumerate(records):
        heatmap_path = output_dir / 'heatmaps' / Path(str(record['image_id'])).with_suffix('.jpg')
        image = Image.open(heatmap_path).convert('RGB')
        image = ImageOps.fit(image, (tile_width, tile_height - 28), method=Image.Resampling.LANCZOS)
        x = (index % columns) * tile_width
        y = (index // columns) * tile_height
        overview.paste(image, (x, y))
        draw.rectangle((x, y + tile_height - 28, x + tile_width, y + tile_height), fill='#FFFFFF')
        label = '{}  L={:.2f}'.format(record['image_id'], record['mean_luminance'])
        draw.text((x + 6, y + tile_height - 21), label, fill='#111827')
    overview.save(output_dir / 'overview.jpg', quality=90)


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    records: list[dict[str, Any]] = []
    for path in find_images(args.input_dir):
        metrics, gray = analyze_image(path, args.input_dir, config)
        records.append(metrics)
        destination = args.output_dir / 'heatmaps' / Path(str(metrics['image_id'])).with_suffix('.jpg')
        save_heatmap(gray, destination)
    if not records:
        raise RuntimeError('No images were analyzed.')
    write_outputs(records, args.output_dir)
    summary = build_summary(records, config)
    (args.output_dir / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    build_overview(records, args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
