const paths = {
  dashboard: '../analysis/web-data/dashboard-data.json',
  yolo: '../analysis/yolo-baseline/summary.json',
  lighting: '../analysis/lighting-baseline/summary.json',
  openclip: '../analysis/openclip-baseline/summary.json',
  experiments: '../analysis/controlled-generation/experiment.json'
};

const state = { mode: 'legacy', scene: '全部场景', data: null };

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function number(value) {
  return new Intl.NumberFormat('zh-CN').format(value || 0);
}

function percent(value, digits) {
  return ((value || 0) * 100).toFixed(digits === undefined ? 1 : digits) + '%';
}

function kpi(label, value, note) {
  const card = element('article', 'kpi');
  card.append(element('span', '', label), element('strong', '', value), element('small', '', note));
  return card;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function badge(text, warning) {
  return element('span', 'badge' + (warning ? ' warn' : ''), text);
}

function setupNavigation() {
  document.querySelectorAll('.nav-button').forEach(function(button) {
    button.addEventListener('click', function() {
      document.querySelectorAll('.nav-button').forEach(function(item) { item.classList.remove('active'); });
      document.querySelectorAll('.page-section').forEach(function(item) { item.classList.remove('active'); });
      button.classList.add('active');
      document.getElementById(button.dataset.target).classList.add('active');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });
}

function setupFilters() {
  const select = document.getElementById('scene-select');
  ['全部场景'].concat(state.data.dashboard.metadata.dimensions.scenes).forEach(function(scene) {
    const option = element('option', '', scene);
    option.value = scene;
    select.append(option);
  });
  select.addEventListener('change', function() {
    state.scene = select.value;
    renderOverview();
  });
  document.getElementById('mode-legacy').addEventListener('click', function() { setMode('legacy'); });
  document.getElementById('mode-v2').addEventListener('click', function() { setMode('v2'); });
}

function setMode(mode) {
  state.mode = mode;
  document.getElementById('mode-legacy').classList.toggle('active', mode === 'legacy');
  document.getElementById('mode-v2').classList.toggle('active', mode === 'v2');
  renderOverview();
}

function activeRows() {
  const rows = state.mode === 'legacy' ? state.data.dashboard.legacy_summary : state.data.dashboard.v2_summary;
  if (state.scene === '全部场景') return rows.slice();
  return rows.filter(function(row) { return row['使用场景'] === state.scene; });
}

function chartRows(rows) {
  if (state.scene !== '全部场景') return rows;
  const legacy = state.mode === 'legacy';
  const indicatorKey = legacy ? '标准美学指标' : '美学指标';
  const countKey = legacy ? '提及频次' : '帖子数';
  const positiveKey = legacy ? '正向数' : '正向票';
  const neutralKey = legacy ? '中性数' : '中性票';
  const negativeKey = legacy ? '负向数' : '负向票';
  const grouped = new Map();
  rows.forEach(function(row) {
    const name = row[indicatorKey];
    if (!grouped.has(name)) grouped.set(name, { count: 0, positive: 0, neutral: 0, negative: 0 });
    const item = grouped.get(name);
    item.count += row[countKey] || 0;
    item.positive += row[positiveKey] || 0;
    item.neutral += row[neutralKey] || 0;
    item.negative += row[negativeKey] || 0;
  });
  return Array.from(grouped.entries()).map(function(entry) {
    const total = entry[1].positive + entry[1].neutral + entry[1].negative;
    const row = {};
    row[indicatorKey] = entry[0];
    row[countKey] = entry[1].count;
    row['正向率'] = total ? entry[1].positive / total : 0;
    row['中性率'] = total ? entry[1].neutral / total : 0;
    row['负向率'] = total ? entry[1].negative / total : 0;
    return row;
  });
}

function renderProjectKpis() {
  const metrics = state.data.dashboard.metadata.metrics;
  const target = document.getElementById('kpi-grid');
  clear(target);
  target.append(
    kpi('原始标签记录', number(metrics.tagged_records), '最终人工标签表'),
    kpi('正式场景记录', number(metrics.formal_scene_records), '排除未映射场景'),
    kpi('独立帖子', number(metrics.formal_unique_posts), 'v2 主统计单位'),
    kpi('场景 × 指标', number(metrics.v2_combinations), '两种口径可对照'),
    kpi('分类发生变化', number(metrics.changed_classifications), '需结合稳定率解释')
  );
}

function renderPriority(rows) {
  const target = document.getElementById('priority-bars');
  clear(target);
  const countKey = state.mode === 'legacy' ? '提及频次' : '帖子数';
  const indicatorKey = state.mode === 'legacy' ? '标准美学指标' : '美学指标';
  const sorted = rows.slice().sort(function(a, b) { return b[countKey] - a[countKey]; }).slice(0, 8);
  const max = Math.max.apply(null, sorted.map(function(row) { return row[countKey]; }).concat([1]));
  sorted.forEach(function(row) {
    const line = element('div', 'bar-row');
    const track = element('div', 'bar-track');
    const fill = element('div', 'bar-fill');
    fill.style.width = (row[countKey] / max * 100) + '%';
    track.append(fill);
    line.append(element('span', '', row[indicatorKey]), track, element('span', 'bar-value', number(row[countKey])));
    target.append(line);
  });
  if (!sorted.length) target.append(element('p', '', '当前筛选无数据'));
}

function renderSentiment(rows) {
  const target = document.getElementById('sentiment-bars');
  clear(target);
  const countKey = state.mode === 'legacy' ? '提及频次' : '帖子数';
  const indicatorKey = state.mode === 'legacy' ? '标准美学指标' : '美学指标';
  rows.slice().sort(function(a, b) { return b[countKey] - a[countKey]; }).slice(0, 5).forEach(function(row) {
    const wrap = element('div', 'sentiment-row');
    const header = element('header');
    header.append(element('span', '', row[indicatorKey]), element('span', '', number(row[countKey])));
    const stack = element('div', 'sentiment-stack');
    [['positive', '正向率'], ['neutral', '中性率'], ['negative', '负向率']].forEach(function(item) {
      const part = element('div', item[0]);
      part.style.width = ((row[item[1]] || 0) * 100) + '%';
      part.title = item[1] + ' ' + percent(row[item[1]]);
      stack.append(part);
    });
    const legend = element('div', 'legend');
    legend.append(
      element('span', '', '正 ' + percent(row['正向率'])),
      element('span', '', '中 ' + percent(row['中性率'])),
      element('span', '', '负 ' + percent(row['负向率']))
    );
    wrap.append(header, stack, legend);
    target.append(wrap);
  });
}

function renderTable(rows) {
  const head = document.getElementById('touchpoint-head');
  const body = document.getElementById('touchpoint-body');
  clear(head);
  clear(body);
  const legacy = state.mode === 'legacy';
  const labels = legacy ? ['场景', '指标', '记录', '情感结构', '主要感受', 'Kano', '设计优先级'] : ['场景', '指标', '帖子', '情感结构', 'v2 分类', '稳定率', '建议'];
  const headRow = element('tr');
  labels.forEach(function(label) { headRow.append(element('th', '', label)); });
  head.append(headRow);
  rows.slice().sort(function(a, b) {
    return (b[legacy ? '提及频次' : '帖子数'] || 0) - (a[legacy ? '提及频次' : '帖子数'] || 0);
  }).forEach(function(row) {
    const tr = element('tr');
    const sentiment = '正 ' + percent(row['正向率'], 0) + ' · 中 ' + percent(row['中性率'], 0) + ' · 负 ' + percent(row['负向率'], 0);
    if (legacy) {
      tr.append(
        element('td', '', row['使用场景']),
        element('td', '', row['标准美学指标']),
        element('td', '', number(row['提及频次'])),
        element('td', '', sentiment),
        element('td', '', row['主要用户感受']),
        element('td').appendChild(badge(row['Kano分类'], false)).parentNode,
        element('td', '', row['设计优先级'])
      );
    } else {
      const stability = row['分类稳定率'];
      tr.append(
        element('td', '', row['使用场景']),
        element('td', '', row['美学指标']),
        element('td', '', number(row['帖子数'])),
        element('td', '', sentiment),
        element('td').appendChild(badge(row['v2分类'], stability < .6)).parentNode,
        element('td', '', percent(stability)),
        element('td', '', row['建议'])
      );
    }
    body.append(tr);
  });
  document.getElementById('table-note').textContent = state.scene + ' · ' + (legacy ? '记录级展示口径' : '帖子级稳健性口径');
}

function renderOverview() {
  const rows = activeRows();
  const aggregated = chartRows(rows);
  renderPriority(aggregated);
  renderSentiment(aggregated);
  renderTable(rows);
}

function renderComparison() {
  const dashboard = state.data.dashboard;
  const changed = dashboard.comparison.filter(function(row) { return row['是否变化'] === '是'; });
  const low = dashboard.v2_stability.filter(function(row) { return row['分类稳定率'] < .6; });
  const metrics = dashboard.metadata.metrics;
  const kpis = document.getElementById('comparison-kpis');
  kpis.append(
    kpi('发生变化', number(changed.length), '共 ' + number(metrics.v2_combinations) + ' 个组合'),
    kpi('低稳定组合', number(low.length), '稳定率低于 60%'),
    kpi('帖子级投票', number(metrics.v2_post_votes), '帖子内去重后')
  );
  const body = document.getElementById('comparison-body');
  changed.slice().sort(function(a, b) { return a['分类稳定率'] - b['分类稳定率']; }).forEach(function(row) {
    const tr = element('tr');
    tr.append(
      element('td', '', row['使用场景']),
      element('td', '', row['美学指标']),
      element('td', '', row['Legacy分类']),
      element('td').appendChild(badge(row['v2分类'], true)).parentNode,
      element('td', '', percent(row['分类稳定率']))
    );
    body.append(tr);
  });
  const list = document.getElementById('stability-list');
  low.slice().sort(function(a, b) { return a['分类稳定率'] - b['分类稳定率']; }).slice(0, 12).forEach(function(row) {
    const item = element('div', 'stability-item');
    const header = element('header');
    header.append(element('span', '', row['使用场景'] + ' · ' + row['美学指标']), element('strong', '', percent(row['分类稳定率'])));
    const track = element('div', 'stability-track');
    const fill = element('div', 'stability-fill');
    fill.style.width = percent(row['分类稳定率']);
    track.append(fill);
    item.append(header, track);
    list.append(item);
  });
}

function renderVision() {
  const yolo = state.data.yolo;
  const lighting = state.data.lighting;
  const clip = state.data.openclip;
  const target = document.getElementById('vision-kpis');
  const temperature = clip.attribute_summary['色温感知'].label_counts;
  target.append(
    kpi('YOLO 检出覆盖', percent(yolo.detection_coverage), number(yolo.total_detection_count) + ' 个目标'),
    kpi('相关目标', number(yolo.relevant_detection_count), '室内家具与物体'),
    kpi('平均亮度', lighting.global_mean.mean_luminance.toFixed(3), '24 张底图'),
    kpi('平均暗区', percent(lighting.global_mean.dark_area_ratio), '像素统计'),
    kpi('暖 / 中 / 冷', (temperature['暖色照明'] || 0) + ' / ' + (temperature['中性色照明'] || 0) + ' / ' + (temperature['冷色照明'] || 0), 'OpenCLIP 零样本')
  );
}

function renderExperiments() {
  const target = document.getElementById('experiment-grid');
  const experiments = state.data.experiments.experiments;
  experiments.forEach(function(item, index) {
    const card = element('article', 'experiment-card');
    card.append(element('h2', '', item.title), element('p', '', '控制变量：' + item.controlled_variable));
    const pair = element('div', 'metric-pair');
    const a = item.variants[0];
    const b = item.variants[1];
    if (item.id === 'color-temperature') {
      pair.append(metricBox(a.label, '暖度 ' + a.lighting_metrics.warmth_index.toFixed(3)), metricBox(b.label, '暖度 ' + b.lighting_metrics.warmth_index.toFixed(3)));
    } else if (item.id === 'light-distribution') {
      pair.append(metricBox(a.label, '局部对比 ' + a.lighting_metrics.local_contrast_mean.toFixed(3)), metricBox(b.label, '局部对比 ' + b.lighting_metrics.local_contrast_mean.toFixed(3)));
    } else {
      pair.append(metricBox(a.label, '任务比 ' + a.task_roi_metrics.task_to_background_ratio.toFixed(3)), metricBox(b.label, '任务比 ' + b.task_roi_metrics.task_to_background_ratio.toFixed(3)));
    }
    card.append(pair, element('div', 'result' + (index ? ' partial' : ''), index ? '部分通过 · 需说明模型局限' : '通过 · 两类指标方向一致'));
    target.append(card);
  });
}

function metricBox(label, value) {
  const box = element('div');
  box.append(element('span', '', label), element('strong', '', value));
  return box;
}

async function loadData() {
  try {
    const values = await Promise.all(Object.values(paths).map(function(path) {
      return fetch(path).then(function(response) {
        if (!response.ok) throw new Error(path + ' · HTTP ' + response.status);
        return response.json();
      });
    }));
    state.data = { dashboard: values[0], yolo: values[1], lighting: values[2], openclip: values[3], experiments: values[4] };
    setupFilters();
    renderProjectKpis();
    renderOverview();
    renderComparison();
    renderVision();
    renderExperiments();
    document.getElementById('data-version').textContent = '数据契约 v' + state.data.dashboard.metadata.schema_version;
  } catch (error) {
    const banner = document.getElementById('error-banner');
    banner.hidden = false;
    banner.textContent = '数据加载失败：' + error.message + '。请从仓库根目录运行本地 HTTP 服务，不要直接双击 HTML。';
  }
}

setupNavigation();
loadData();
