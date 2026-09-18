from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
import openpyxl


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TAGGED_PATH = PROJECT_ROOT / 'data' / 'processed' / 'tagged-results-with-sentiment.xlsx'
LEGACY_PATH = PROJECT_ROOT / 'analysis' / 'kano-pair-statistics.xlsx'
V2_PATH = PROJECT_ROOT / 'outputs' / 'kano_v2' / 'kano-inspired-v2.xlsx'
WEB_DIR = PROJECT_ROOT / 'analysis' / 'web-data'
CHART_DIR = PROJECT_ROOT / 'deliverables' / 'charts'

SCENES = ['日常基础照明', '睡眠与起居', '学习工作', '智能托管', '休闲娱乐', '亲子互动陪伴']
INDICATORS = ['照明与色调', '交互功能', '风格设计', '形体造型', '视觉舒适', '做工细节', '材料质感', '空间氛围', '色彩']
SENTIMENTS = ['正向', '中性', '负向']
CLASS_ORDER = [
    '基础型/风险项（M-inspired）',
    '期望型（O-inspired）',
    '魅力型（A-inspired）',
    '无差异型（I-inspired）',
    '混合/待复核',
    '样本不足',
]

COLORS = {
    'blue': '#2563EB',
    'cyan': '#0891B2',
    'green': '#059669',
    'amber': '#D97706',
    'red': '#DC2626',
    'purple': '#7C3AED',
    'gray': '#94A3B8',
    'ink': '#172033',
    'grid': '#DDE3EC',
    'background': '#FFFFFF',
}


def configure_matplotlib() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC', 'Arial Unicode MS']:
        if candidate in available:
            plt.rcParams['font.sans-serif'] = [candidate]
            break
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['figure.facecolor'] = COLORS['background']
    plt.rcParams['axes.facecolor'] = COLORS['background']
    plt.rcParams['text.color'] = COLORS['ink']
    plt.rcParams['axes.labelcolor'] = COLORS['ink']
    plt.rcParams['xtick.color'] = COLORS['ink']
    plt.rcParams['ytick.color'] = COLORS['ink']
    plt.rcParams['font.size'] = 11


def load_table(path: Path, sheet_name: str, header_row: int) -> list[dict[str, Any]]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook[sheet_name]
    headers = [cell.value for cell in sheet[header_row]]
    rows: list[dict[str, Any]] = []
    for values in sheet.iter_rows(min_row=header_row + 1, values_only=True):
        if not any(value is not None for value in values):
            continue
        row = {str(header): value for header, value in zip(headers, values) if header is not None}
        rows.append(row)
    workbook.close()
    return rows


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [json_ready(item) for item in value]
    if isinstance(value, float):
        return round(value, 6)
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_ready(value), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load_sources() -> dict[str, list[dict[str, Any]]]:
    return {
        'tagged': load_table(TAGGED_PATH, 'Sheet1', 1),
        'legacy_summary': load_table(LEGACY_PATH, 'Kano汇总', 3),
        'legacy_pairs': load_table(LEGACY_PATH, '词对明细', 3),
        'v2_summary': load_table(V2_PATH, '场景汇总_帖子级', 4),
        'v2_pairs': load_table(V2_PATH, '词对明细_帖子级', 4),
        'v2_stability': load_table(V2_PATH, 'Bootstrap稳定性', 4),
        'comparison': load_table(V2_PATH, 'Legacy对照', 4),
        'post_votes': load_table(V2_PATH, '帖子级投票', 4),
    }


def build_metadata(data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    tagged = data['tagged']
    scene_counts = Counter(str(row.get('使用场景分类')) for row in tagged)
    return {
        'schema_version': '1.0.0',
        'analysis_modes': {
            'legacy_record': '记录级现有成果，默认项目展示',
            'v2_post': '帖子级Kano-inspired稳健性分析',
        },
        'dimensions': {
            'scenes': SCENES,
            'indicators': INDICATORS,
            'sentiments': SENTIMENTS,
            'v2_classes': CLASS_ORDER,
        },
        'metrics': {
            'tagged_records': len(tagged),
            'formal_scene_records': sum(scene_counts[scene] for scene in SCENES),
            'excluded_no_scene_records': scene_counts['无'],
            'unique_posts': 425,
            'formal_unique_posts': 383,
            'legacy_combinations': len(data['legacy_summary']),
            'v2_combinations': len(data['v2_summary']),
            'v2_post_votes': sum(int(row['帖子数']) for row in data['v2_summary']),
            'changed_classifications': sum(str(row['是否变化']) == '是' for row in data['comparison']),
            'low_stability_combinations': sum(float(row['分类稳定率']) < 0.7 for row in data['v2_stability']),
        },
    }


def export_web_data(data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    metadata = build_metadata(data)
    files = {
        'metadata.json': metadata,
        'legacy-summary.json': data['legacy_summary'],
        'legacy-pairs.json': data['legacy_pairs'],
        'v2-summary.json': data['v2_summary'],
        'v2-pairs.json': data['v2_pairs'],
        'v2-stability.json': data['v2_stability'],
        'legacy-v2-comparison.json': data['comparison'],
        'post-votes.json': data['post_votes'],
    }
    for filename, payload in files.items():
        write_json(WEB_DIR / filename, payload)
    dashboard = {
        'metadata': metadata,
        'legacy_summary': data['legacy_summary'],
        'v2_summary': data['v2_summary'],
        'v2_stability': data['v2_stability'],
        'comparison': data['comparison'],
    }
    write_json(WEB_DIR / 'dashboard-data.json', dashboard)
    return metadata


def finish_figure(fig: plt.Figure, filename: str) -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    fig.set_size_inches(40 / 3, 7.5)
    fig.savefig(CHART_DIR / filename, dpi=144, facecolor=COLORS['background'])
    plt.close(fig)


def style_axis(axis: plt.Axes, grid_axis: str = 'x') -> None:
    axis.spines[['top', 'right', 'left']].set_visible(False)
    axis.spines['bottom'].set_color(COLORS['grid'])
    axis.grid(axis=grid_axis, color=COLORS['grid'], linewidth=0.8, alpha=0.8)
    axis.set_axisbelow(True)
    axis.tick_params(length=0)


def chart_scene_distribution(data: dict[str, list[dict[str, Any]]]) -> None:
    counts = Counter(str(row['使用场景分类']) for row in data['tagged'])
    values = [counts[scene] for scene in SCENES]
    order = sorted(range(len(SCENES)), key=lambda index: values[index])
    labels = [SCENES[index] for index in order]
    sorted_values = [values[index] for index in order]
    excluded_count = counts['无']

    fig, axis = plt.subplots(figsize=(13.333, 7.5))
    bars = axis.barh(labels, sorted_values, color=COLORS['blue'], height=0.62)
    maximum = max(sorted_values)
    for bar, value in zip(bars, sorted_values):
        axis.text(value + maximum * 0.015, bar.get_y() + bar.get_height() / 2, f'{value:,}', va='center', fontsize=12)
    axis.set_xlim(0, maximum * 1.16)
    axis.set_xlabel('最终标注记录数')
    axis.set_title('六类正式使用场景的用户反馈分布', loc='left', fontsize=20, fontweight='bold', pad=18)
    axis.text(0, 1.01, f'正式场景共 {sum(values):,} 条；“无”场景 {excluded_count:,} 条未进入场景 Kano 分类', transform=axis.transAxes, color='#526176')
    style_axis(axis)
    fig.subplots_adjust(left=0.17, right=0.96, top=0.84, bottom=0.13)
    finish_figure(fig, '01-scene-distribution.png')


def chart_scene_indicator_heatmap(data: dict[str, list[dict[str, Any]]]) -> None:
    lookup = {(str(row['使用场景']), str(row['标准美学指标'])): float(row['场景内占比']) for row in data['legacy_summary']}
    matrix = [[lookup.get((scene, indicator), 0.0) for indicator in INDICATORS] for scene in SCENES]
    cmap = LinearSegmentedColormap.from_list('lighting-blue', ['#F4F7FB', '#B8D4FA', COLORS['blue']])

    fig, axis = plt.subplots(figsize=(13.333, 7.5))
    image = axis.imshow(matrix, cmap=cmap, vmin=0, vmax=max(max(row) for row in matrix), aspect='auto')
    axis.set_xticks(range(len(INDICATORS)), INDICATORS, rotation=32, ha='right')
    axis.set_yticks(range(len(SCENES)), SCENES)
    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            color = '#FFFFFF' if value >= 0.32 else COLORS['ink']
            axis.text(column_index, row_index, f'{value:.0%}', ha='center', va='center', color=color, fontsize=10)
    axis.set_title('不同场景最受关注的美学触点', loc='left', fontsize=20, fontweight='bold', pad=18)
    axis.text(0, 1.01, 'Legacy 记录级口径；单元格为该指标在场景内的提及占比', transform=axis.transAxes, color='#526176')
    colorbar = fig.colorbar(image, ax=axis, fraction=0.025, pad=0.025)
    colorbar.ax.set_ylabel('场景内占比', rotation=270, labelpad=18)
    colorbar.ax.yaxis.set_major_formatter(lambda value, _: f'{value:.0%}')
    for spine in axis.spines.values():
        spine.set_color(COLORS['grid'])
    fig.subplots_adjust(left=0.15, right=0.91, top=0.84, bottom=0.22)
    finish_figure(fig, '02-scene-indicator-heatmap.png')


def chart_sentiment_structure(data: dict[str, list[dict[str, Any]]]) -> None:
    totals: dict[str, Counter[str]] = {scene: Counter() for scene in SCENES}
    for row in data['tagged']:
        scene = str(row['使用场景分类'])
        sentiment = str(row['情感强度'])
        if scene in totals and sentiment in SENTIMENTS:
            totals[scene][sentiment] += 1

    fig, axis = plt.subplots(figsize=(13.333, 7.5))
    left = [0.0] * len(SCENES)
    sentiment_colors = {'正向': COLORS['blue'], '中性': COLORS['gray'], '负向': COLORS['red']}
    for sentiment in SENTIMENTS:
        rates = []
        for scene in SCENES:
            total = sum(totals[scene].values())
            rates.append(totals[scene][sentiment] / total if total else 0.0)
        bars = axis.barh(SCENES, rates, left=left, color=sentiment_colors[sentiment], label=sentiment, height=0.62)
        for bar, rate, offset in zip(bars, rates, left):
            if rate >= 0.08:
                axis.text(offset + rate / 2, bar.get_y() + bar.get_height() / 2, f'{rate:.0%}', ha='center', va='center', color='#FFFFFF' if sentiment != '中性' else COLORS['ink'], fontsize=10)
        left = [start + rate for start, rate in zip(left, rates)]
    axis.set_xlim(0, 1)
    axis.xaxis.set_major_formatter(lambda value, _: f'{value:.0%}')
    axis.set_xlabel('场景内情感占比')
    axis.set_title('六类正式场景的情感结构', loc='left', fontsize=20, fontweight='bold', pad=18)
    axis.text(0, 1.01, '基于最终人工标签表；每一行合计为 100%', transform=axis.transAxes, color='#526176')
    axis.legend(ncol=3, frameon=False, loc='lower center', bbox_to_anchor=(0.5, -0.18))
    style_axis(axis)
    fig.subplots_adjust(left=0.17, right=0.96, top=0.84, bottom=0.2)
    finish_figure(fig, '03-scene-sentiment-structure.png')


def short_class(label: str) -> str:
    if 'M' in label or '基础型' in label:
        return 'M 基础/风险'
    if 'O' in label or '期望型' in label:
        return 'O 期望'
    if 'A' in label or '魅力型' in label:
        return 'A 魅力'
    if 'I' in label or '无差异型' in label:
        return 'I 无差异'
    if '样本不足' in label:
        return '样本不足'
    return '混合/待复核'


def chart_legacy_v2_transition(data: dict[str, list[dict[str, Any]]]) -> None:
    legacy_classes = ['M 基础/风险', 'O 期望', 'A 魅力', 'I 无差异', '样本不足']
    v2_classes = ['M 基础/风险', 'O 期望', 'A 魅力', 'I 无差异', '混合/待复核', '样本不足']
    counts: dict[tuple[str, str], int] = Counter()
    for row in data['comparison']:
        counts[(short_class(str(row['Legacy分类'])), short_class(str(row['v2分类'])))] += 1
    matrix = [[counts[(legacy, v2)] for v2 in v2_classes] for legacy in legacy_classes]
    cmap = LinearSegmentedColormap.from_list('transition-purple', ['#F7F5FC', '#C4B5FD', COLORS['purple']])

    fig, axis = plt.subplots(figsize=(13.333, 7.5))
    maximum = max(max(row) for row in matrix)
    image = axis.imshow(matrix, cmap=cmap, vmin=0, vmax=maximum, aspect='auto')
    axis.set_xticks(range(len(v2_classes)), v2_classes, rotation=25, ha='right')
    axis.set_yticks(range(len(legacy_classes)), legacy_classes)
    axis.set_xlabel('帖子级 v2 分类')
    axis.set_ylabel('Legacy 记录级分类')
    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            color = '#FFFFFF' if value >= maximum * 0.55 and maximum else COLORS['ink']
            axis.text(column_index, row_index, str(value), ha='center', va='center', color=color, fontsize=13)
    changed = sum(str(row['是否变化']) == '是' for row in data['comparison'])
    axis.set_title('统计口径变化会改变部分 Kano 类型', loc='left', fontsize=20, fontweight='bold', pad=18)
    axis.text(0, 1.01, f'52 个组合中 {changed} 个发生变化；差异用于稳健性检查，不表示 Legacy 结果错误', transform=axis.transAxes, color='#526176')
    colorbar = fig.colorbar(image, ax=axis, fraction=0.025, pad=0.025)
    colorbar.ax.set_ylabel('组合数', rotation=270, labelpad=16)
    fig.subplots_adjust(left=0.16, right=0.91, top=0.84, bottom=0.2)
    finish_figure(fig, '04-legacy-v2-transition.png')


def chart_v2_priority_bubble(data: dict[str, list[dict[str, Any]]]) -> None:
    class_colors = {
        'M 基础/风险': COLORS['red'],
        'O 期望': COLORS['amber'],
        'A 魅力': COLORS['blue'],
        'I 无差异': COLORS['gray'],
        '混合/待复核': COLORS['purple'],
        '样本不足': '#CBD5E1',
    }
    fig, axis = plt.subplots(figsize=(13.333, 7.5))
    for class_name, color in class_colors.items():
        rows = [row for row in data['v2_summary'] if short_class(str(row['v2分类'])) == class_name]
        if not rows:
            continue
        x = [float(row['负向率']) for row in rows]
        y = [float(row['正向率']) for row in rows]
        sizes = [45 + math.sqrt(int(row['帖子数'])) * 24 for row in rows]
        axis.scatter(x, y, s=sizes, color=color, alpha=0.78, edgecolors='#FFFFFF', linewidths=1.2, label=class_name)
    axis.axvline(0.2, color=COLORS['red'], linewidth=1, linestyle='--', alpha=0.7)
    axis.axhline(0.55, color=COLORS['blue'], linewidth=1, linestyle='--', alpha=0.7)
    axis.set_xlim(-0.015, max(0.34, max(float(row['负向率']) for row in data['v2_summary']) + 0.03))
    axis.set_ylim(-0.02, 1.02)
    axis.xaxis.set_major_formatter(lambda value, _: f'{value:.0%}')
    axis.yaxis.set_major_formatter(lambda value, _: f'{value:.0%}')
    axis.set_xlabel('负向帖子票占比')
    axis.set_ylabel('正向帖子票占比')
    axis.set_title('帖子级 Kano-inspired 需求优先级分布', loc='left', fontsize=20, fontweight='bold', pad=18)
    axis.text(0, 1.01, '气泡大小表示帖子数；虚线对应 M 风险阈值与 A 正向阈值', transform=axis.transAxes, color='#526176')
    axis.legend(frameon=False, ncol=3, loc='lower center', bbox_to_anchor=(0.5, -0.22))
    style_axis(axis, grid_axis='both')
    fig.subplots_adjust(left=0.1, right=0.96, top=0.84, bottom=0.23)
    finish_figure(fig, '05-v2-priority-bubble.png')


def chart_v2_stability(data: dict[str, list[dict[str, Any]]]) -> None:
    rows = sorted(data['v2_stability'], key=lambda row: float(row['分类稳定率']))
    unstable = [row for row in rows if float(row['分类稳定率']) < 0.7]
    shown = unstable[:15]
    labels = []
    for row in shown:
        labels.append('{} · {}'.format(row['使用场景'], row['美学指标']))
    values = [float(row['分类稳定率']) for row in shown]
    colors = [COLORS['red'] if value < 0.5 else COLORS['amber'] for value in values]

    fig, axes = plt.subplots(1, 2, figsize=(13.333, 7.5), gridspec_kw={'width_ratios': [1.7, 1]})
    left_axis, right_axis = axes
    positions = list(range(len(labels)))
    left_axis.scatter(values, positions, s=80, color=colors, zorder=3)
    for position, value in zip(positions, values):
        left_axis.hlines(position, 0, value, color=COLORS['grid'], linewidth=2, zorder=1)
        left_axis.text(value + 0.018, position, f'{value:.0%}', va='center', fontsize=10)
    left_axis.axvline(0.7, color=COLORS['red'], linestyle='--', linewidth=1.2)
    left_axis.set_xlim(0, 1)
    left_axis.set_yticks(positions, labels)
    left_axis.invert_yaxis()
    left_axis.xaxis.set_major_formatter(lambda value, _: f'{value:.0%}')
    left_axis.set_xlabel('分类稳定率')
    left_axis.set_title('低于 70% 的组合', loc='left', fontsize=15, fontweight='bold')
    style_axis(left_axis)

    bins = [0, 0.5, 0.7, 0.9, 1.0001]
    bin_labels = ['<50%', '50–70%', '70–90%', '≥90%']
    histogram = [0, 0, 0, 0]
    for row in rows:
        value = float(row['分类稳定率'])
        for index in range(len(bins) - 1):
            if bins[index] <= value < bins[index + 1]:
                histogram[index] += 1
                break
    bars = right_axis.bar(bin_labels, histogram, color=[COLORS['red'], COLORS['amber'], COLORS['cyan'], COLORS['blue']], width=0.68)
    for bar, value in zip(bars, histogram):
        right_axis.text(bar.get_x() + bar.get_width() / 2, value + 0.35, str(value), ha='center', fontsize=12)
    right_axis.set_ylabel('场景×指标组合数')
    right_axis.set_title('全部 52 个组合', loc='left', fontsize=15, fontweight='bold')
    style_axis(right_axis, grid_axis='y')

    fig.suptitle('Bootstrap 揭示分类的不确定性', x=0.06, ha='left', fontsize=20, fontweight='bold')
    fig.text(0.06, 0.91, f'1,000 次帖子级重采样；共有 {len(unstable)} 个组合的分类稳定率低于 70%', color='#526176')
    fig.subplots_adjust(top=0.82, bottom=0.12, left=0.2, right=0.97, wspace=0.32)
    finish_figure(fig, '06-v2-bootstrap-stability.png')


def write_manifests(metadata: dict[str, Any]) -> None:
    web_manifest = {
        'schema_version': '1.0.0',
        'default_analysis_mode': 'legacy_record',
        'robustness_analysis_mode': 'v2_post',
        'files': [
            {'path': 'metadata.json', 'grain': 'project metadata and dimensions'},
            {'path': 'legacy-summary.json', 'grain': 'scenario x indicator record aggregate'},
            {'path': 'legacy-pairs.json', 'grain': 'scenario x indicator x perception record aggregate'},
            {'path': 'v2-summary.json', 'grain': 'scenario x indicator post aggregate'},
            {'path': 'v2-pairs.json', 'grain': 'scenario x indicator x perception post aggregate'},
            {'path': 'v2-stability.json', 'grain': 'scenario x indicator bootstrap result'},
            {'path': 'legacy-v2-comparison.json', 'grain': 'scenario x indicator comparison'},
            {'path': 'post-votes.json', 'grain': 'auditable post vote'},
            {'path': 'dashboard-data.json', 'grain': 'compact combined dashboard payload'},
        ],
        'metrics': metadata['metrics'],
    }
    write_json(WEB_DIR / 'manifest.json', web_manifest)
    chart_manifest = {
        'schema_version': '1.0.0',
        'format': 'PNG 16:9, 144 dpi',
        'charts': [
            {'path': '01-scene-distribution.png', 'title': '六类正式使用场景的用户反馈分布', 'analysis_mode': 'final_tags'},
            {'path': '02-scene-indicator-heatmap.png', 'title': '不同场景最受关注的美学触点', 'analysis_mode': 'legacy_record'},
            {'path': '03-scene-sentiment-structure.png', 'title': '六类正式场景的情感结构', 'analysis_mode': 'final_tags'},
            {'path': '04-legacy-v2-transition.png', 'title': '统计口径变化会改变部分Kano类型', 'analysis_mode': 'comparison'},
            {'path': '05-v2-priority-bubble.png', 'title': '帖子级Kano-inspired需求优先级分布', 'analysis_mode': 'v2_post'},
            {'path': '06-v2-bootstrap-stability.png', 'title': 'Bootstrap揭示分类的不确定性', 'analysis_mode': 'v2_post'},
        ],
    }
    write_json(CHART_DIR / 'manifest.json', chart_manifest)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Export defense charts and normalized Web data.')
    parser.add_argument('--skip-charts', action='store_true', help='Only export JSON data.')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_matplotlib()
    data = load_sources()
    metadata = export_web_data(data)
    if not args.skip_charts:
        chart_scene_distribution(data)
        chart_scene_indicator_heatmap(data)
        chart_sentiment_structure(data)
        chart_legacy_v2_transition(data)
        chart_v2_priority_bubble(data)
        chart_v2_stability(data)
    write_manifests(metadata)
    print(json.dumps({
        'web_dir': str(WEB_DIR),
        'chart_dir': str(CHART_DIR),
        'metrics': metadata['metrics'],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
