from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import statistics
from typing import Any

from PIL import Image, ImageDraw, ImageOps
import torch
from ultralytics import YOLO
import ultralytics


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / 'config' / 'yolo_baseline.json'
DEFAULT_INPUT = PROJECT_ROOT / 'data' / 'raw' / 'base_images'
DEFAULT_OUTPUT = PROJECT_ROOT / 'analysis' / 'yolo-baseline'
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run the indoor-object YOLO baseline.')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--input-dir', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def find_images(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.rglob('*') if path.suffix.lower() in IMAGE_SUFFIXES)


def image_room(path: Path, input_dir: Path) -> str:
    relative = path.relative_to(input_dir)
    return relative.parts[0] if len(relative.parts) > 1 else 'unknown'


def box_record(box: Any, names: dict[int, str], width: int, height: int, relevant: set[str]) -> dict[str, Any]:
    x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].cpu().tolist()]
    confidence = float(box.conf[0].cpu().item())
    class_id = int(box.cls[0].cpu().item())
    class_name = str(names[class_id])
    box_width = max(0.0, x2 - x1)
    box_height = max(0.0, y2 - y1)
    return {
        'class_id': class_id,
        'class_name': class_name,
        'confidence': round(confidence, 6),
        'is_indoor_relevant': class_name in relevant,
        'bbox_xyxy': [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
        'bbox_normalized': [
            round(x1 / width, 6),
            round(y1 / height, 6),
            round(x2 / width, 6),
            round(y2 / height, 6),
        ],
        'center_normalized': [round((x1 + x2) / (2 * width), 6), round((y1 + y2) / (2 * height), 6)],
        'area_ratio': round((box_width * box_height) / (width * height), 6),
    }


def save_annotated(result: Any, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    plotted_bgr = result.plot(labels=True, conf=True, line_width=2)
    Image.fromarray(plotted_bgr[:, :, ::-1]).save(destination, quality=92)


def run_predictions(config: dict[str, Any], input_dir: Path, output_dir: Path) -> list[dict[str, Any]]:
    images = find_images(input_dir)
    if not images:
        raise RuntimeError(f'No images found under {input_dir}')
    relevant = set(config['relevant_coco_classes'])
    model = YOLO(str(config['model']))
    results = model.predict(
        source=[str(path) for path in images],
        imgsz=int(config['image_size']),
        conf=float(config['confidence_threshold']),
        iou=float(config['iou_threshold']),
        device=str(config['device']),
        verbose=False,
    )

    records: list[dict[str, Any]] = []
    for image_path, result in zip(images, results):
        height, width = result.orig_shape
        detections = [box_record(box, result.names, width, height, relevant) for box in result.boxes]
        relative = image_path.relative_to(input_dir)
        annotated_path = output_dir / 'annotated' / relative.with_suffix('.jpg')
        save_annotated(result, annotated_path)
        records.append({
            'image_id': relative.as_posix(),
            'room': image_room(image_path, input_dir),
            'source_path': (Path('data') / 'raw' / 'base_images' / relative).as_posix(),
            'annotated_path': annotated_path.relative_to(PROJECT_ROOT).as_posix(),
            'width': width,
            'height': height,
            'detection_count': len(detections),
            'relevant_detection_count': sum(bool(item['is_indoor_relevant']) for item in detections),
            'speed_ms': {key: round(float(value), 3) for key, value in result.speed.items()},
            'detections': detections,
        })
    return records


def summarize(records: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    class_counts: Counter[str] = Counter()
    class_confidences: dict[str, list[float]] = defaultdict(list)
    room_stats: dict[str, dict[str, int]] = defaultdict(lambda: {'images': 0, 'detected_images': 0, 'detections': 0, 'relevant_detections': 0})
    inference_times: list[float] = []
    for record in records:
        room = str(record['room'])
        room_stats[room]['images'] += 1
        room_stats[room]['detected_images'] += int(int(record['detection_count']) > 0)
        room_stats[room]['detections'] += int(record['detection_count'])
        room_stats[room]['relevant_detections'] += int(record['relevant_detection_count'])
        inference_times.append(float(record['speed_ms'].get('inference', 0.0)))
        for detection in record['detections']:
            name = str(detection['class_name'])
            class_counts[name] += 1
            class_confidences[name].append(float(detection['confidence']))

    total_detections = sum(class_counts.values())
    detected_images = sum(int(int(record['detection_count']) > 0) for record in records)
    relevant_images = sum(int(int(record['relevant_detection_count']) > 0) for record in records)
    class_summary = [
        {
            'class_name': name,
            'count': count,
            'mean_confidence': round(statistics.mean(class_confidences[name]), 6),
            'is_indoor_relevant': name in set(config['relevant_coco_classes']),
        }
        for name, count in class_counts.most_common()
    ]
    return {
        'method_name': config['method_name'],
        'method_version': config['method_version'],
        'model': config['model'],
        'task': config['task'],
        'analysis_scope': 'COCO pretrained indoor-object context baseline',
        'image_count': len(records),
        'detected_image_count': detected_images,
        'detection_coverage': round(detected_images / len(records), 6),
        'relevant_detected_image_count': relevant_images,
        'relevant_detection_coverage': round(relevant_images / len(records), 6),
        'total_detection_count': total_detections,
        'relevant_detection_count': sum(int(record['relevant_detection_count']) for record in records),
        'mean_inference_ms': round(statistics.mean(inference_times), 3),
        'median_inference_ms': round(statistics.median(inference_times), 3),
        'class_summary': class_summary,
        'room_summary': dict(sorted(room_stats.items())),
        'parameters': {
            'image_size': config['image_size'],
            'confidence_threshold': config['confidence_threshold'],
            'iou_threshold': config['iou_threshold'],
            'device': config['device'],
        },
        'limitations': config['limitations'],
    }


def write_prediction_files(records: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / 'predictions.jsonl'
    jsonl_path.write_text(''.join(json.dumps(record, ensure_ascii=False) + '\n' for record in records), encoding='utf-8')
    fieldnames = [
        'image_id', 'room', 'class_id', 'class_name', 'confidence', 'is_indoor_relevant',
        'x1', 'y1', 'x2', 'y2', 'center_x', 'center_y', 'area_ratio',
    ]
    with (output_dir / 'detections.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            for detection in record['detections']:
                x1, y1, x2, y2 = detection['bbox_normalized']
                center_x, center_y = detection['center_normalized']
                writer.writerow({
                    'image_id': record['image_id'],
                    'room': record['room'],
                    'class_id': detection['class_id'],
                    'class_name': detection['class_name'],
                    'confidence': detection['confidence'],
                    'is_indoor_relevant': detection['is_indoor_relevant'],
                    'x1': x1,
                    'y1': y1,
                    'x2': x2,
                    'y2': y2,
                    'center_x': center_x,
                    'center_y': center_y,
                    'area_ratio': detection['area_ratio'],
                })


def build_overview(records: list[dict[str, Any]], output_dir: Path) -> None:
    columns = 4
    tile_width, tile_height = 320, 210
    rows = (len(records) + columns - 1) // columns
    overview = Image.new('RGB', (columns * tile_width, rows * tile_height), '#E5E7EB')
    draw = ImageDraw.Draw(overview)
    for index, record in enumerate(records):
        annotated = PROJECT_ROOT / str(record['annotated_path'])
        image = Image.open(annotated).convert('RGB')
        image = ImageOps.fit(image, (tile_width, tile_height - 28), method=Image.Resampling.LANCZOS)
        x = (index % columns) * tile_width
        y = (index // columns) * tile_height
        overview.paste(image, (x, y))
        draw.rectangle((x, y + tile_height - 28, x + tile_width, y + tile_height), fill='#FFFFFF')
        label = '{}  n={}'.format(record['image_id'], record['detection_count'])
        draw.text((x + 6, y + tile_height - 21), label, fill='#111827')
    overview.save(output_dir / 'overview.jpg', quality=90)


def environment_payload(config: dict[str, Any]) -> dict[str, Any]:
    return {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(),
        'platform': platform.platform(),
        'ultralytics': ultralytics.__version__,
        'torch': torch.__version__,
        'cuda_available': torch.cuda.is_available(),
        'configured_device': config['device'],
    }


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    records = run_predictions(config, args.input_dir, args.output_dir)
    summary = summarize(records, config)
    write_prediction_files(records, args.output_dir)
    write_json(args.output_dir / 'summary.json', summary)
    write_json(args.output_dir / 'environment.json', environment_payload(config))
    build_overview(records, args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
