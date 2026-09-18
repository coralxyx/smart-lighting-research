from __future__ import annotations

import csv
import json
from pathlib import Path
import random
import shutil
from statistics import mean
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'analysis' / 'approach-comparison'
SCENE_TASK = {'study': 'T01', 'bedroom': 'T02', 'living_room': 'T03'}
TASK_SCENE = {value: key for key, value in SCENE_TASK.items()}
TASK_TITLE = {'T01': '书房：专注与视觉舒适', 'T02': '卧室：睡前放松', 'T03': '客厅：舒适休闲与层次'}
INPUTS = {
    'study': BASE / 'inputs' / 'T01-study.jpg',
    'bedroom': BASE / 'inputs' / 'T02-bedroom.jpg',
    'living_room': BASE / 'inputs' / 'T03-living-room.jpg',
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def read_yolo(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def direct_runs() -> list[dict[str, Any]]:
    manifest = {row['task_id']: row for row in load_json(BASE / 'heldout-manifest.json')}
    designs = {row['task_id']: row for row in load_json(BASE / 'agent-traces' / '02-designer.json')['designs']}
    critic = {row['task_id']: row for row in load_json(BASE / 'agent-traces' / '03-critic.json')['reviews']}
    records = []
    for task_id in sorted(designs):
        design = designs[task_id]
        item = manifest[task_id]
        recommendation = dict(design['recommendation'])
        if critic[task_id]['verdict'] == 'revise':
            recommendation['control_strategy'] = critic[task_id]['approved_control_strategy']
        for repeat in (1, 2):
            scene = item['scene']
            generated = BASE / 'images' / scene / f'direct-multi-agent-r{repeat:02d}.png'
            width, height = image_dimensions(generated)
            records.append({
                'schema_version': '1.0',
                'run_id': f'{task_id}-direct_multi_agent-r{repeat:02d}',
                'task_id': task_id,
                'method': 'direct_multi_agent',
                'repeat': repeat,
                'input': {'image_id': item['image_id'], 'image_sha256': item['sha256'], 'scene': scene, 'user_brief': item['user_brief']},
                'observed_problems': design['observed_problems'],
                'recommendation': recommendation,
                'evidence': [],
                'uncertainties': design['uncertainties'],
                'image_prompt': design['image_prompt'],
                'negative_constraints': design['negative_constraints'],
                'generated_image': {'path': generated.relative_to(ROOT).as_posix(), 'width': width, 'height': height},
                'agent_trace': [
                    {'role': 'observer', 'output_path': 'analysis/approach-comparison/agent-traces/01-observer.json'},
                    {'role': 'designer', 'output_path': 'analysis/approach-comparison/agent-traces/02-designer.json'},
                    {'role': 'critic', 'output_path': 'analysis/approach-comparison/agent-traces/03-critic.json'},
                ],
                'runtime': {'generation_attempts': 1, 'api_cost': 0},
            })
    return records


def update_pipeline_dimensions(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for record in records:
        path = ROOT / record['generated_image']['path']
        width, height = image_dimensions(path)
        record['generated_image']['width'] = width
        record['generated_image']['height'] = height
        record['runtime']['api_cost'] = 0
    return records


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


def cv_read(path: Path) -> np.ndarray:
    data = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f'Cannot decode {path}')
    return image


def orb_preservation(source: Path, result: Path) -> dict[str, float | int]:
    left = cv_read(source)
    right = cv_read(result)
    target_width = 900
    left = cv2.resize(left, (target_width, round(left.shape[0] * target_width / left.shape[1])))
    right = cv2.resize(right, (target_width, round(right.shape[0] * target_width / right.shape[1])))
    left_gray = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY)
    right_gray = cv2.cvtColor(right, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=2500)
    kp1, des1 = orb.detectAndCompute(left_gray, None)
    kp2, des2 = orb.detectAndCompute(right_gray, None)
    if des1 is None or des2 is None:
        return {'source_keypoints': len(kp1), 'result_keypoints': len(kp2), 'good_matches': 0, 'match_ratio': 0.0, 'homography_inlier_ratio': 0.0}
    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(des1, des2, k=2)
    good = [first for first, second in pairs if first.distance < 0.75 * second.distance]
    inlier_ratio = 0.0
    if len(good) >= 8:
        src = np.float32([kp1[match.queryIdx].pt for match in good]).reshape(-1, 1, 2)
        dst = np.float32([kp2[match.trainIdx].pt for match in good]).reshape(-1, 1, 2)
        _, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
        if mask is not None:
            inlier_ratio = float(mask.mean())
    return {
        'source_keypoints': len(kp1),
        'result_keypoints': len(kp2),
        'good_matches': len(good),
        'match_ratio': round(len(good) / max(1, min(len(kp1), len(kp2))), 6),
        'homography_inlier_ratio': round(inlier_ratio, 6),
    }


def class_set(record: dict[str, Any]) -> set[str]:
    return {item['class_name'] for item in record['detections'] if item['is_indoor_relevant']}


def jaccard(left: set[str], right: set[str]) -> float:
    return 1.0 if not left and not right else len(left & right) / len(left | right)


def target_scores(task_id: str, light: dict[str, Any], clip: dict[str, Any], input_light: dict[str, Any]) -> dict[str, Any]:
    attr = clip['attributes']
    scores = {
        'warm': attr['色温感知']['scores']['暖色照明'],
        'neutral': attr['色温感知']['scores']['中性色照明'],
        'soft': attr['光线柔和度']['scores']['柔和漫射'],
        'indirect': attr['照明方式']['scores']['间接照明'],
        'layered': attr['光照层次']['scores']['层次丰富'],
        'bright': attr['明暗氛围']['scores']['明亮通透'],
    }
    if task_id == 'T01':
        directions = [
            ('neutral', scores['neutral'] >= max(scores['warm'], 0.2)),
            ('brighter', light['mean_luminance'] > input_light['mean_luminance']),
            ('less_dark', light['dark_area_ratio'] < input_light['dark_area_ratio']),
            ('layering_preserved', light['spatial_layering_std'] >= input_light['spatial_layering_std'] * 0.9),
        ]
    elif task_id == 'T02':
        directions = [
            ('warm', scores['warm'] >= 0.5),
            ('soft', scores['soft'] >= 0.5),
            ('indirect', scores['indirect'] >= 0.5),
            ('low_brightness', light['mean_luminance'] <= input_light['mean_luminance'] * 1.25),
        ]
    else:
        directions = [
            ('warm', scores['warm'] >= 0.5),
            ('soft', scores['soft'] >= 0.5),
            ('layered', scores['layered'] >= 0.5),
            ('not_darker', light['mean_luminance'] >= input_light['mean_luminance']),
        ]
    return {
        'openclip_scores': {key: round(float(value), 6) for key, value in scores.items()},
        'direction_checks': {name: passed for name, passed in directions},
        'direction_hit_rate': round(sum(passed for _, passed in directions) / len(directions), 6),
    }


def build_evaluation(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    input_light = {row['room']: row for row in load_json(BASE / 'evaluation' / 'input' / 'lighting' / 'metrics.json')}
    output_light = {row['image_id']: row for row in load_json(BASE / 'evaluation' / 'output' / 'lighting' / 'metrics.json')}
    output_clip = {row['image_id']: row for row in load_json(BASE / 'evaluation' / 'output' / 'openclip' / 'predictions.json')}
    input_yolo = {row['room']: row for row in read_yolo(BASE / 'evaluation' / 'input' / 'yolo' / 'predictions.jsonl')}
    output_yolo = {row['image_id']: row for row in read_yolo(BASE / 'evaluation' / 'output' / 'yolo' / 'predictions.jsonl')}
    rows = []
    for run in runs:
        scene = run['input']['scene']
        relative = f"{scene}/{Path(run['generated_image']['path']).name}"
        light = output_light[relative]
        source_light = input_light[scene]
        source_classes = class_set(input_yolo[scene])
        result_classes = class_set(output_yolo[relative])
        result_path = ROOT / run['generated_image']['path']
        rows.append({
            'run_id': run['run_id'],
            'task_id': run['task_id'],
            'method': run['method'],
            'repeat': run['repeat'],
            'result_path': run['generated_image']['path'],
            'lighting': light,
            'lighting_delta': {
                key: round(float(light[key]) - float(source_light[key]), 6)
                for key in ['mean_luminance', 'dark_area_ratio', 'warm_pixel_ratio', 'warmth_index', 'local_contrast_mean', 'spatial_layering_std']
            },
            'targets': target_scores(run['task_id'], light, output_clip[relative], source_light),
            'object_preservation': {
                'source_classes': sorted(source_classes),
                'result_classes': sorted(result_classes),
                'class_jaccard': round(jaccard(source_classes, result_classes), 6),
                'source_relevant_count': input_yolo[scene]['relevant_detection_count'],
                'result_relevant_count': output_yolo[relative]['relevant_detection_count'],
            },
            'structure_preservation': {
                **orb_preservation(INPUTS[scene], result_path),
                'dhash_distance_from_input': hamming(dhash(INPUTS[scene]), dhash(result_path)),
            },
            'process': {
                'evidence_count': len(run['evidence']),
                'trace_role_count': len(run['agent_trace']),
                'source_locatable': all(item.get('source_file') and item.get('source_key') for item in run['evidence']) if run['evidence'] else None,
            },
        })
    return rows


def summarize(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    method_summary: dict[str, Any] = {}
    for method in ['evidence_pipeline', 'direct_multi_agent']:
        rows = [row for row in evaluations if row['method'] == method]
        method_summary[method] = {
            'output_count': len(rows),
            'mean_direction_hit_rate': round(mean(row['targets']['direction_hit_rate'] for row in rows), 6),
            'mean_yolo_class_jaccard': round(mean(row['object_preservation']['class_jaccard'] for row in rows), 6),
            'mean_orb_match_ratio': round(mean(row['structure_preservation']['match_ratio'] for row in rows), 6),
            'mean_homography_inlier_ratio': round(mean(row['structure_preservation']['homography_inlier_ratio'] for row in rows), 6),
            'mean_dhash_distance_from_input': round(mean(row['structure_preservation']['dhash_distance_from_input'] for row in rows), 6),
            'mean_evidence_count': round(mean(row['process']['evidence_count'] for row in rows), 3),
            'locatable_evidence_rate': round(mean(1.0 if row['process']['source_locatable'] else 0.0 for row in rows), 6),
        }
    paired = []
    for task_id in sorted(TASK_SCENE):
        for method in ['evidence_pipeline', 'direct_multi_agent']:
            rows = sorted([row for row in evaluations if row['task_id'] == task_id and row['method'] == method], key=lambda row: row['repeat'])
            paired.append({
                'task_id': task_id,
                'method': method,
                'direction_hit_rate_gap': round(abs(rows[0]['targets']['direction_hit_rate'] - rows[1]['targets']['direction_hit_rate']), 6),
                'mean_luminance_gap': round(abs(rows[0]['lighting']['mean_luminance'] - rows[1]['lighting']['mean_luminance']), 6),
                'warmth_index_gap': round(abs(rows[0]['lighting']['warmth_index'] - rows[1]['lighting']['warmth_index']), 6),
                'repeat_dhash_distance': hamming(dhash(ROOT / rows[0]['result_path']), dhash(ROOT / rows[1]['result_path'])),
            })
    return {
        'experiment_size': {'tasks': 3, 'methods': 2, 'repeats': 2, 'outputs': 12},
        'method_summary': method_summary,
        'repeat_stability': paired,
        'interpretation_guardrail': '小样本描述统计；人工盲评未完成前不宣布总体优胜，不进行显著性推断。',
    }


def build_blind_assets(runs: list[dict[str, Any]]) -> None:
    blind = BASE / 'blind-review'
    image_dir = blind / 'images'
    image_dir.mkdir(parents=True, exist_ok=True)
    shuffled = list(runs)
    random.Random(20260919).shuffle(shuffled)
    mapping = []
    review_rows = []
    for index, run in enumerate(shuffled, 1):
        alias = f'S{index:02d}'
        source = ROOT / run['generated_image']['path']
        target = image_dir / f'{alias}.png'
        shutil.copy2(source, target)
        recommendation = run['recommendation']
        text = '；'.join([
            recommendation['color_temperature']['description'],
            recommendation['brightness_strategy'],
            recommendation['lighting_distribution'],
            recommendation['glare_control'],
            recommendation['control_strategy'],
        ])
        mapping.append({'sample_alias': alias, 'run_id': run['run_id'], 'method': run['method'], 'task_id': run['task_id']})
        review_rows.append({
            'reviewer_id': '', 'reviewer_background': '', 'sample_alias': alias,
            'task_id': run['task_id'], 'task_title': TASK_TITLE[run['task_id']], 'display_order': index,
            'source_image': INPUTS[run['input']['scene']].relative_to(ROOT).as_posix(),
            'result_image': target.relative_to(ROOT).as_posix(), 'recommendation_text': text,
            'need_match_score': '', 'spatial_specificity_score': '', 'parameter_clarity_score': '',
            'lighting_plausibility_score': '', 'text_image_consistency_score': '', 'image_realism_score': '',
            'space_preservation_score': '', 'overall_score': '', 'confidence_score': '',
            'major_problem': '', 'comments': '',
        })
    save_json(blind / 'private-mapping.json', mapping)
    with (blind / 'blind-review.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(review_rows[0]))
        writer.writeheader()
        writer.writerows(review_rows)


def font(size: int) -> ImageFont.ImageFont:
    for candidate in [Path('C:/Windows/Fonts/msyh.ttc'), Path('C:/Windows/Fonts/simhei.ttf')]:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def build_overview(runs: list[dict[str, Any]]) -> None:
    tile_w, tile_h = 330, 270
    canvas = Image.new('RGB', (tile_w * 5, tile_h * 3), '#E5E7EB')
    draw = ImageDraw.Draw(canvas)
    title_font, small = font(18), font(13)
    run_map = {(run['task_id'], run['method'], run['repeat']): run for run in runs}
    for row, task_id in enumerate(['T01', 'T02', 'T03']):
        scene = TASK_SCENE[task_id]
        columns = [
            ('原图', INPUTS[scene]),
            ('证据流程 R1', ROOT / run_map[(task_id, 'evidence_pipeline', 1)]['generated_image']['path']),
            ('证据流程 R2', ROOT / run_map[(task_id, 'evidence_pipeline', 2)]['generated_image']['path']),
            ('直接多Agent R1', ROOT / run_map[(task_id, 'direct_multi_agent', 1)]['generated_image']['path']),
            ('直接多Agent R2', ROOT / run_map[(task_id, 'direct_multi_agent', 2)]['generated_image']['path']),
        ]
        for column, (label, path) in enumerate(columns):
            with Image.open(path) as source:
                image = ImageOps.fit(source.convert('RGB'), (tile_w, tile_h - 46), method=Image.Resampling.LANCZOS)
            x, y = column * tile_w, row * tile_h
            canvas.paste(image, (x, y))
            draw.rectangle((x, y + tile_h - 46, x + tile_w, y + tile_h), fill='white')
            draw.text((x + 8, y + tile_h - 40), f'{task_id} {label}', fill='#111827', font=title_font)
            draw.text((x + 8, y + tile_h - 19), TASK_TITLE[task_id], fill='#4B5563', font=small)
    canvas.save(BASE / 'overview.jpg', quality=92)


def write_report(summary: dict[str, Any]) -> None:
    evidence = summary['method_summary']['evidence_pipeline']
    direct = summary['method_summary']['direct_multi_agent']
    content = f'''# 证据流程 vs 直接多 Agent：无 API 对照试验

## 已完成

- 3 张全新 Pexels 留出底图，已用 SHA-256 与 dHash 对既有 30 张图片去重。
- 直接多 Agent 采用观察 → 设计/提示词 → 批判三段协作，且与项目数据隔离。
- 两组各生成 6 张图：3 场景 × 2 次重复，共 12 张。
- 两组使用相同底图、同一内置生图后端、同一生成次数和同等级空间保持约束。
- 全部结果统一运行光照分析、OpenCLIP 和 YOLO，并计算 ORB/单应性、dHash 与对象类别保持代理。
- 盲评图片、随机别名和 CSV 评分表已生成。

## 当前自动结果

| 指标 | 证据流程 | 直接多 Agent |
|---|---:|---:|
| 冻结目标方向命中率 | {evidence['mean_direction_hit_rate']:.1%} | {direct['mean_direction_hit_rate']:.1%} |
| YOLO 类别 Jaccard | {evidence['mean_yolo_class_jaccard']:.3f} | {direct['mean_yolo_class_jaccard']:.3f} |
| ORB 结构匹配率 | {evidence['mean_orb_match_ratio']:.3f} | {direct['mean_orb_match_ratio']:.3f} |
| 单应性内点率 | {evidence['mean_homography_inlier_ratio']:.3f} | {direct['mean_homography_inlier_ratio']:.3f} |
| 每条建议平均证据数 | {evidence['mean_evidence_count']:.1f} | {direct['mean_evidence_count']:.1f} |
| 可定位证据比例 | {evidence['locatable_evidence_rate']:.1%} | {direct['locatable_evidence_rate']:.1%} |

这些指标不能单独决定哪组图更好。尤其证据数属于过程质量，不能混入图像盲评总分。人工盲评完成前，只能得出：两组都能产生可用灯光调整；项目流程额外提供可定位的数据依据和确定性映射，而直接多 Agent 更依赖通用推理。

## 如何盲评

打开 blind-review/blind-review.csv，按 1–5 分填写需求匹配、空间针对性、参数清晰度、照明合理性、图文一致、真实感、空间保持和总体分。评审者只查看 S01 等别名，不查看 private-mapping.json。至少 3 位评审，先独立打分，再做同任务成对偏好判断。

## 重要限制

- 样本仅 3 个场景，不做显著性宣称。
- 内置生图没有暴露随机种子，当前结果可审计但不能像固定 API 参数那样逐像素复现。
- OpenCLIP、YOLO 与 sRGB 光照指标都是代理测量，不是真实照度/色温或用户满意度。
- 多 Agent 观察工具本轮无法直接打开本地大图，因此观察 Agent 使用了主 Agent 对原图预览的事实描述，并已在 trace 中披露。
'''
    (BASE / 'README.md').write_text(content, encoding='utf-8')


def main() -> None:
    direct = direct_runs()
    pipeline = update_pipeline_dimensions(load_json(BASE / 'runs' / 'evidence-pipeline.json'))
    save_json(BASE / 'runs' / 'direct-multi-agent.json', direct)
    save_json(BASE / 'runs' / 'evidence-pipeline.json', pipeline)
    all_runs = pipeline + direct
    save_json(BASE / 'runs' / 'all-runs.json', all_runs)
    evaluations = build_evaluation(all_runs)
    save_json(BASE / 'evaluation' / 'comparison-metrics.json', evaluations)
    summary = summarize(evaluations)
    save_json(BASE / 'evaluation' / 'summary.json', summary)
    build_blind_assets(all_runs)
    build_overview(all_runs)
    write_report(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
