from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
HELDOUT = ROOT / 'data' / 'evaluation' / 'heldout-images'
OUT = ROOT / 'analysis' / 'approach-comparison'
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}


SOURCES = {
    'living_room/living_heldout_01_pexels_31751141.jpg': {
        'image_id': 'living_heldout_01',
        'task_id': 'T03',
        'scene': 'living_room',
        'scene_cn': '休闲娱乐',
        'user_brief': '提升舒适休闲氛围，同时保持空间层次且不过暗。',
        'author': 'Natalia S',
        'source_page': 'https://www.pexels.com/photo/modern-minimalist-living-room-with-ambient-lighting-31751141/',
        'source_id': '31751141',
    },
    'bedroom/bedroom_heldout_01_pexels_36639777.jpg': {
        'image_id': 'bedroom_heldout_01',
        'task_id': 'T02',
        'scene': 'bedroom',
        'scene_cn': '睡眠与起居',
        'user_brief': '支持睡前放松、降低刺激，同时保留基本可见度。',
        'author': 'Irina Novikova',
        'source_page': 'https://www.pexels.com/photo/cozy-bedroom-interior-with-warm-lighting-36639777/',
        'source_id': '36639777',
    },
    'study/study_heldout_01_pexels_7014764.jpg': {
        'image_id': 'study_heldout_01',
        'task_id': 'T01',
        'scene': 'study',
        'scene_cn': '学习工作',
        'user_brief': '提高专注和视觉舒适，保证桌面任务照明并控制眩光。',
        'author': 'cottonbro studio',
        'source_page': 'https://www.pexels.com/photo/interior-design-of-a-home-office-7014764/',
        'source_id': '7014764',
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def dhash(path: Path) -> str:
    with Image.open(path) as image:
        gray = np.asarray(image.convert('L').resize((9, 8), Image.Resampling.LANCZOS))
    bits = gray[:, 1:] > gray[:, :-1]
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return f'{value:016x}'


def hamming(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


def image_paths(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob('*') if path.suffix.lower() in IMAGE_SUFFIXES)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def build_manifest() -> list[dict[str, Any]]:
    comparison_roots = [ROOT / 'data' / 'raw' / 'base_images', ROOT / 'analysis' / 'controlled-generation' / 'images']
    comparison = []
    for root in comparison_roots:
        for path in image_paths(root):
            comparison.append((path, sha256(path), dhash(path)))

    records = []
    for relative, source in SOURCES.items():
        path = HELDOUT / relative
        current_sha = sha256(path)
        current_hash = dhash(path)
        distances = [(hamming(current_hash, candidate_hash), candidate) for candidate, _, candidate_hash in comparison]
        min_distance, nearest = min(distances, key=lambda item: item[0])
        with Image.open(path) as image:
            width, height = image.size
        record = {
            **source,
            'file': path.relative_to(ROOT).as_posix(),
            'license': 'Pexels License',
            'license_url': 'https://www.pexels.com/license/',
            'sha256': current_sha,
            'dhash': current_hash,
            'width': width,
            'height': height,
            'duplicate_check': {
                'exact_duplicate': any(current_sha == candidate_sha for _, candidate_sha, _ in comparison),
                'near_duplicate': min_distance <= 5,
                'minimum_dhash_distance': min_distance,
                'nearest_existing_file': nearest.relative_to(ROOT).as_posix(),
                'comparison_count': len(comparison),
                'near_duplicate_threshold': 5,
            },
        }
        records.append(record)
    return sorted(records, key=lambda item: item['task_id'])


def select_kano(scene_cn: str) -> list[dict[str, Any]]:
    dashboard = load_json(ROOT / 'analysis' / 'web-data' / 'dashboard-data.json')
    rows = [row for row in dashboard['v2_summary'] if row['使用场景'] == scene_cn]
    rows.sort(key=lambda row: (int(row['优先级']), -int(row['帖子数'])))
    return rows[:4]


def build_pipeline_runs(manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lighting = {row['room']: row for row in load_json(OUT / 'evaluation' / 'input' / 'lighting' / 'metrics.json')}
    clip = {row['room']: row for row in load_json(OUT / 'evaluation' / 'input' / 'openclip' / 'predictions.json')}
    yolo_rows = [json.loads(line) for line in (OUT / 'evaluation' / 'input' / 'yolo' / 'predictions.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    yolo = {row['room']: row for row in yolo_rows}

    targets = {
        'study': {
            'target_feelings': ['专注', '视觉舒适'],
            'color_temperature': {'min_kelvin': 3500, 'max_kelvin': 4000, 'description': '中性偏暖白光，避免冷蓝压迫感'},
            'brightness_strategy': '提高桌面与键盘区域可见度，同时保留背景较低亮度。',
            'lighting_distribution': '保留台灯作为任务光，补充柔和环境光形成两层照明。',
            'directness': 'mixed',
            'glare_control': '限制灯罩高光与屏幕反射，避免裸露强光源。',
            'control_strategy': '工作模式一键联动任务光与低亮环境光。',
        },
        'bedroom': {
            'target_feelings': ['舒适感', '放松'],
            'color_temperature': {'min_kelvin': 2400, 'max_kelvin': 2700, 'description': '低色温暖光'},
            'brightness_strategy': '保持低照度，只适度抬升床侧与行走区域可见度。',
            'lighting_distribution': '以床头漫射光和低位间接光为主，不增加顶面强光。',
            'directness': 'indirect',
            'glare_control': '光源不直视，控制枕部和床面高光。',
            'control_strategy': '设置睡前渐暗情景，支持低亮夜间模式。',
        },
        'living_room': {
            'target_feelings': ['舒适感', '愉悦与氛围感'],
            'color_temperature': {'min_kelvin': 2700, 'max_kelvin': 3200, 'description': '暖中性色温'},
            'brightness_strategy': '在不过曝的前提下略抬升沙发活动区亮度。',
            'lighting_distribution': '保留柜体层次光，增加柔和环境光并维持明暗层次。',
            'directness': 'mixed',
            'glare_control': '避免柜体灯带出现刺眼亮线或大面积高光。',
            'control_strategy': '休闲模式联动柜体、环境与局部重点照明。',
        },
    }

    records = []
    for item in manifest:
        room = item['scene']
        target = targets[room]
        observed = [
            f"平均亮度={lighting[room]['mean_luminance']:.3f}，暗区比例={lighting[room]['dark_area_ratio']:.3f}",
            'OpenCLIP：' + '；'.join(f"{key}={value['label']}({value['confidence']:.2f})" for key, value in clip[room]['attributes'].items()),
            'YOLO 保留对象：' + '、'.join(sorted({d['class_name'] for d in yolo[room]['detections'] if d['is_indoor_relevant']})),
        ]
        evidence = []
        for row in select_kano(item['scene_cn']):
            evidence.append({
                'claim': f"{row['美学指标']}在{row['使用场景']}中为{row['v2分类']}，帖子数{row['帖子数']}，稳定率{row['分类稳定率']:.3f}",
                'source_type': 'kano_inspired_v2',
                'source_file': 'analysis/web-data/v2-summary.json',
                'source_key': f"{row['使用场景']}|{row['美学指标']}",
                'source_value': {'classification': row['v2分类'], 'posts': row['帖子数'], 'stability': row['分类稳定率']},
                'verified': True,
            })
        for source_type, source_file, source_key, source_value in [
            ('lighting_baseline', 'analysis/approach-comparison/evaluation/input/lighting/metrics.json', item['file'], lighting[room]),
            ('openclip_baseline', 'analysis/approach-comparison/evaluation/input/openclip/predictions.json', item['file'], clip[room]['attributes']),
            ('yolo_baseline', 'analysis/approach-comparison/evaluation/input/yolo/predictions.jsonl', item['file'], {'classes': sorted({d['class_name'] for d in yolo[room]['detections']})}),
        ]:
            evidence.append({'claim': source_type, 'source_type': source_type, 'source_file': source_file, 'source_key': source_key, 'source_value': source_value, 'verified': True})

        for repeat in (1, 2):
            prompt = (
                f"Edit this {room} photograph only by changing the lighting. User need: {item['user_brief']} "
                f"Use {target['color_temperature']['min_kelvin']}-{target['color_temperature']['max_kelvin']} K perceived lighting; "
                f"{target['brightness_strategy']} {target['lighting_distribution']} {target['glare_control']} "
                'Keep the exact camera viewpoint, crop, architecture, wall colors, furniture, decorations, object identities, object count and object positions. '
                'Do not add or remove lamps, furniture, windows, people, text or decorative objects. Preserve photorealism and natural material colors.'
            )
            records.append({
                'schema_version': '1.0',
                'run_id': f"{item['task_id']}-evidence_pipeline-r{repeat:02d}",
                'task_id': item['task_id'],
                'method': 'evidence_pipeline',
                'repeat': repeat,
                'input': {'image_id': item['image_id'], 'image_sha256': item['sha256'], 'scene': room, 'user_brief': item['user_brief']},
                'observed_problems': observed,
                'recommendation': {**target, 'preservation_constraints': ['视角与裁切', '建筑结构', '家具与物体', '材质与色彩身份']},
                'evidence': evidence,
                'uncertainties': ['图像指标是 sRGB 代理值，不是照度或色温实测。', 'OpenCLIP 分数是候选提示词间的相对相似度。'],
                'image_prompt': prompt,
                'negative_constraints': ['no geometry change', 'no object addition or removal', 'no text', 'no people'],
                'generated_image': {'path': f"analysis/approach-comparison/images/{room}/evidence-pipeline-r{repeat:02d}.png", 'width': 0, 'height': 0},
                'agent_trace': [],
                'runtime': {'generation_attempts': 1},
            })
    return records


def main() -> None:
    manifest = build_manifest()
    json_dump(OUT / 'heldout-manifest.json', manifest)
    json_dump(OUT / 'runs' / 'evidence-pipeline.json', build_pipeline_runs(manifest))
    print(json.dumps({'heldout_images': len(manifest), 'pipeline_runs': len(manifest) * 2, 'duplicate_checks': [row['duplicate_check'] for row in manifest]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
