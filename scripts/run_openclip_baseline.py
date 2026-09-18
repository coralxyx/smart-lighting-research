from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import statistics
from typing import Any

import open_clip
from PIL import Image, ImageDraw, ImageFont, ImageOps
import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / 'config' / 'openclip_baseline.json'
DEFAULT_INPUT = PROJECT_ROOT / 'data' / 'raw' / 'base_images'
DEFAULT_OUTPUT = PROJECT_ROOT / 'analysis' / 'openclip-baseline'
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run OpenCLIP zero-shot lighting-aesthetics baseline.')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--input-dir', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def find_images(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.rglob('*') if path.suffix.lower() in IMAGE_SUFFIXES)


def encode_label_features(model: Any, tokenizer: Any, attributes: dict[str, Any], device: str) -> dict[str, tuple[list[str], torch.Tensor]]:
    encoded: dict[str, tuple[list[str], torch.Tensor]] = {}
    with torch.no_grad():
        for group_name, labels in attributes.items():
            label_names: list[str] = []
            label_features: list[torch.Tensor] = []
            for label_name, prompts in labels.items():
                tokens = tokenizer(prompts).to(device)
                features = model.encode_text(tokens)
                features = features / features.norm(dim=-1, keepdim=True)
                feature = features.mean(dim=0)
                feature = feature / feature.norm()
                label_names.append(label_name)
                label_features.append(feature)
            encoded[group_name] = (label_names, torch.stack(label_features))
    return encoded


def classify_batch(image_features: torch.Tensor, text_features: dict[str, tuple[list[str], torch.Tensor]]) -> list[dict[str, Any]]:
    batch_results: list[dict[str, Any]] = [dict() for _ in range(image_features.shape[0])]
    for group_name, (labels, features) in text_features.items():
        probabilities = (100.0 * image_features @ features.T).softmax(dim=-1).cpu()
        for index in range(image_features.shape[0]):
            scores = {label: round(float(probabilities[index, label_index]), 6) for label_index, label in enumerate(labels)}
            top_label = max(scores, key=scores.get)
            batch_results[index][group_name] = {
                'label': top_label,
                'confidence': scores[top_label],
                'scores': scores,
            }
    return batch_results


def run_predictions(config: dict[str, Any], input_dir: Path) -> list[dict[str, Any]]:
    device = str(config['device'])
    model, _, preprocess = open_clip.create_model_and_transforms(
        str(config['model_name']),
        pretrained=str(config['pretrained']),
        device=device,
    )
    model.eval()
    tokenizer = open_clip.get_tokenizer(str(config['model_name']))
    text_features = encode_label_features(model, tokenizer, config['attributes'], device)
    paths = find_images(input_dir)
    records: list[dict[str, Any]] = []
    batch_size = int(config['batch_size'])
    for start in range(0, len(paths), batch_size):
        batch_paths = paths[start:start + batch_size]
        tensors = torch.stack([preprocess(Image.open(path).convert('RGB')) for path in batch_paths]).to(device)
        with torch.no_grad():
            image_features = model.encode_image(tensors)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        predictions = classify_batch(image_features, text_features)
        for path, prediction in zip(batch_paths, predictions):
            relative = path.relative_to(input_dir)
            try:
                source_path = path.relative_to(PROJECT_ROOT).as_posix()
            except ValueError:
                source_path = path.resolve().as_posix()
            records.append({
                'image_id': relative.as_posix(),
                'room': relative.parts[0],
                'source_path': source_path,
                'attributes': prediction,
            })
    return records


def build_summary(records: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    confidences: dict[str, list[float]] = defaultdict(list)
    room_counts: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    for record in records:
        room = str(record['room'])
        for group_name, result in record['attributes'].items():
            label = str(result['label'])
            counts[group_name][label] += 1
            confidences[group_name].append(float(result['confidence']))
            room_counts[room][group_name][label] += 1
    return {
        'method_name': config['method_name'],
        'method_version': config['method_version'],
        'model_name': config['model_name'],
        'pretrained': config['pretrained'],
        'device': config['device'],
        'image_count': len(records),
        'attribute_summary': {
            group_name: {
                'label_counts': dict(counts[group_name]),
                'mean_top_confidence': round(statistics.mean(confidences[group_name]), 6),
            }
            for group_name in config['attributes']
        },
        'room_label_counts': {
            room: {group: dict(counter) for group, counter in groups.items()}
            for room, groups in sorted(room_counts.items())
        },
        'limitations': config['limitations'],
    }


def write_outputs(records: list[dict[str, Any]], summary: dict[str, Any], output_dir: Path, attributes: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'predictions.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output_dir / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    fieldnames = ['image_id', 'room']
    for group_name in attributes:
        fieldnames.extend([f'{group_name}_标签', f'{group_name}_置信度'])
    with (output_dir / 'predictions.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row: dict[str, Any] = {'image_id': record['image_id'], 'room': record['room']}
            for group_name, result in record['attributes'].items():
                row[f'{group_name}_标签'] = result['label']
                row[f'{group_name}_置信度'] = result['confidence']
            writer.writerow(row)


def load_chinese_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        Path('C:/Windows/Fonts/msyh.ttc'),
        Path('C:/Windows/Fonts/simhei.ttf'),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def build_overview(records: list[dict[str, Any]], input_dir: Path, output_dir: Path) -> None:
    columns = 4
    tile_width, tile_height = 340, 285
    rows = (len(records) + columns - 1) // columns
    overview = Image.new('RGB', (columns * tile_width, rows * tile_height), '#E5E7EB')
    draw = ImageDraw.Draw(overview)
    font = load_chinese_font(12)
    small_font = load_chinese_font(11)
    for index, record in enumerate(records):
        source = input_dir / str(record['image_id'])
        image = Image.open(source).convert('RGB')
        image = ImageOps.fit(image, (tile_width, 180), method=Image.Resampling.LANCZOS)
        x = (index % columns) * tile_width
        y = (index // columns) * tile_height
        overview.paste(image, (x, y))
        draw.rectangle((x, y + 180, x + tile_width, y + tile_height), fill='#FFFFFF')
        draw.text((x + 6, y + 185), str(record['image_id']), fill='#111827', font=font)
        line_y = y + 205
        for group_name, result in record['attributes'].items():
            label = '{}：{} {:.0%}'.format(group_name, result['label'], result['confidence'])
            draw.text((x + 6, line_y), label, fill='#374151', font=small_font)
            line_y += 15
    overview.save(output_dir / 'overview.jpg', quality=90)


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    records = run_predictions(config, args.input_dir)
    summary = build_summary(records, config)
    write_outputs(records, summary, args.output_dir, config['attributes'])
    build_overview(records, args.input_dir, args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
