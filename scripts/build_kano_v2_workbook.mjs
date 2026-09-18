import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";


const [payloadPath, outputPath] = process.argv.slice(2);
if (!payloadPath || !outputPath) {
  throw new Error("Usage: node scripts/build_kano_v2_workbook.mjs <payload.json> <output.xlsx>");
}

const data = JSON.parse(await fs.readFile(payloadPath, "utf8"));
const workbook = Workbook.create();
const fontFamily = "Arial";
const colors = {
  navy: "#1F4E78",
  blue: "#5B9BD5",
  paleBlue: "#D9EAF7",
  paleGray: "#F3F6F9",
  border: "#D9E1F2",
  text: "#20242A",
  amber: "#FFF2CC",
  red: "#FCE8E6",
  green: "#E2F0D9",
};

function columnName(number) {
  let result = "";
  for (let value = number; value > 0; value = Math.floor((value - 1) / 26)) {
    result = String.fromCharCode(65 + ((value - 1) % 26)) + result;
  }
  return result;
}

function setWidths(sheet, widths) {
  widths.forEach((width, index) => {
    const column = columnName(index + 1);
    sheet.getRange(`${column}:${column}`).format.columnWidth = width;
  });
}

function styleTitle(sheet, lastColumn, title, subtitle) {
  sheet.getRange("A1").values = [[title]];
  sheet.getRange("A1").format = {
    font: { name: fontFamily, size: 15, bold: true, color: colors.text },
  };
  sheet.getRange(`A1:${lastColumn}1`).format.borders = {
    bottom: { style: "medium", color: colors.navy },
  };
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${lastColumn}2`).format = {
    font: { name: fontFamily, size: 9, italic: true, color: "#666666" },
    wrapText: true,
  };
  sheet.getRange("A1:A2").format.rowHeight = 24;
}

function styleHeader(range) {
  range.format = {
    fill: colors.navy,
    font: { name: fontFamily, size: 9, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: {
      insideVertical: { style: "thin", color: "#FFFFFF" },
      bottom: { style: "thin", color: colors.navy },
    },
  };
  range.format.rowHeight = 30;
}

function styleBody(range) {
  range.format = {
    font: { name: fontFamily, size: 9, color: colors.text },
    verticalAlignment: "top",
    wrapText: true,
    borders: { bottom: { style: "thin", color: colors.border } },
  };
}

function addMethodSheet() {
  const sheet = workbook.worksheets.add("方法与参数");
  sheet.showGridLines = false;
  styleTitle(
    sheet,
    "H",
    "Kano-inspired v2 方法与参数",
    "基于 UGC 情感分布的需求优先级启发式分析；不等同于经典 Kano 正反问题问卷。"
  );
  const thresholds = data.config.classification_thresholds;
  const bootstrap = data.config.bootstrap;
  const parameterRows = [
    ["参数", "值", "说明"],
    ["方法版本", data.config.method_version, data.config.method_name],
    ["统计单位", "帖子", "同帖同场景×美学指标只计一票"],
    ["排除场景", data.config.excluded_scene, "不进入正式场景分类"],
    ["最小帖子数", data.config.minimum_post_count, "低于此值标记为样本不足"],
    ["同帖冲突解决", "多数票，平票时负向>正向>中性", "优先保留风险信号"],
    ["Bootstrap 次数", bootstrap.iterations, "在每个场景×指标组内对帖子票重采样"],
    ["置信水平", bootstrap.confidence_level, "输出情感比例置信区间"],
    ["随机种子", bootstrap.random_seed, "确保结果可复现"],
    ["低稳定率阈值", bootstrap.low_stability_threshold, "低于此值标记为分类不稳定"],
    ["宽区间阈值", bootstrap.wide_interval_threshold, "任一情感区间宽度超过此值则标记"],
  ];
  sheet.getRange(`A4:C${3 + parameterRows.length}`).values = parameterRows;
  styleHeader(sheet.getRange("A4:C4"));
  styleBody(sheet.getRange(`A5:C${3 + parameterRows.length}`));
  sheet.getRange("B8:B8").format.numberFormat = "#,##0";
  sheet.getRange("B9:B9").format.numberFormat = "0%";
  sheet.getRange("B11:B12").format.numberFormat = "0%";

  const rules = [
    ["顺序", "类型", "可执行条件"],
    [1, "样本不足", `帖子数 < ${data.config.minimum_post_count}`],
    [2, "基础型/风险项（M-inspired）", `负向率 ≥ ${(thresholds.must_be_negative_rate * 100).toFixed(0)}%`],
    [3, "期望型（O-inspired）", `正向率 ≥ ${(thresholds.one_dimensional_positive_rate * 100).toFixed(0)}% 且负向率 ≥ ${(thresholds.one_dimensional_negative_rate * 100).toFixed(0)}%；优先级低于 M`],
    [4, "魅力型（A-inspired）", `正向率 ≥ ${(thresholds.attractive_positive_rate * 100).toFixed(0)}% 且负向率 < ${(thresholds.attractive_negative_rate_max_exclusive * 100).toFixed(0)}%`],
    [5, "无差异型（I-inspired）", `中性率 ≥ ${(thresholds.indifferent_neutral_rate * 100).toFixed(0)}%`],
    [6, "混合/待复核", "不满足以上条件"],
  ];
  sheet.getRange(`E4:G${3 + rules.length}`).values = rules;
  styleHeader(sheet.getRange("E4:G4"));
  styleBody(sheet.getRange(`E5:G${3 + rules.length}`));
  sheet.getRange("A17:C20").values = [
    ["来源", "文件", "用途"],
    ["标签数据", data.source_files.input, "重建帖子级投票和统计"],
    ["Legacy 工作簿", data.source_files.legacy_reference, "仅用于分类对照"],
    ["配置", data.source_files.configuration, "阈值、优先级、随机种子和触点映射"],
  ];
  styleHeader(sheet.getRange("A17:C17"));
  styleBody(sheet.getRange("A18:C20"));
  setWidths(sheet, [24, 28, 58, 4, 10, 32, 64, 4]);
}

function addQualitySheet() {
  const sheet = workbook.worksheets.add("数据质量");
  sheet.showGridLines = false;
  styleTitle(sheet, "F", "数据质量", "原始抽取记录与帖子级投票的数量关系。");
  sheet.getRange("A4:D14").values = [
    ["指标", "数值", "比率", "说明"],
    ["原始标签记录", data.raw_record_count, null, "包含“无”场景"],
    ["正式场景记录", data.formal_record_count, null, "排除“无”场景"],
    ["全部唯一帖子", data.unique_post_count, null, "使用原文稳定哈希识别"],
    ["正式场景唯一帖子", data.formal_unique_post_count, null, "至少包含一条正式场景记录"],
    ["场景×指标帖子票", data.scene_post_vote_count, null, "分类和 bootstrap 的基础单位"],
    ["场景×指标合并的重复记录", data.scene_duplicate_records_collapsed, null, "同帖同场景同指标的额外记录"],
    ["场景×指标冲突帖子票", data.scene_conflict_post_votes, null, "同一帖子票内出现多种情感"],
    ["词对帖子票", data.pair_post_vote_count, null, "场景×指标×感受的帖子级投票"],
    ["词对合并的重复记录", data.pair_duplicate_records_collapsed, null, "同帖同词对的额外记录"],
    ["词对冲突帖子票", data.pair_conflict_post_votes, null, "同一词对帖子票内出现多种情感"],
  ];
  styleHeader(sheet.getRange("A4:D4"));
  styleBody(sheet.getRange("A5:D14"));
  sheet.getRange("C10").formulas = [["=B10/(B9+B10)"]];
  sheet.getRange("C11").formulas = [["=B11/B9"]];
  sheet.getRange("C13").formulas = [["=B13/(B12+B13)"]];
  sheet.getRange("C14").formulas = [["=B14/B12"]];
  sheet.getRange("B5:B14").format.numberFormat = "#,##0";
  sheet.getRange("C5:C14").format.numberFormat = "0.0%";
  sheet.getRange("A17:D21").values = [
    ["质量问题", "状态", "影响", "处理"],
    ["作者标识", "缺失", "无法生成作者级权重", "仅报告帖子级和记录级结果"],
    ["帖子标识", "代理构建", "相同原文被视为同一帖子", "使用原文 SHA-256 前 16 位"],
    ["同帖情感冲突", "存在", "一帖子中可出现多种情感", "多数票；平票时负向>正向>中性"],
    ["Legacy Kano 阈值", "缺失", "不能声称 v2 是旧规则的直接恢复", "v2 使用独立、公开阈值"],
  ];
  styleHeader(sheet.getRange("A17:D17"));
  styleBody(sheet.getRange("A18:D21"));
  setWidths(sheet, [38, 16, 22, 64, 4, 4]);
}

function addSummarySheet() {
  const rows = data.summary_rows;
  const sheet = workbook.worksheets.add("场景汇总_帖子级");
  sheet.showGridLines = false;
  styleTitle(sheet, "AA", "场景汇总（帖子级）", "每篇帖子对同一场景×美学指标只贡献一票。");
  const headers = ["使用场景", "触点类型", "美学指标", "原始记录", "帖子数", "合并重复", "冲突帖子", "正向票", "中性票", "负向票", "正向率", "中性率", "负向率", "v2分类", "优先级", "建议", "正向CI下限", "正向CI上限", "中性CI下限", "中性CI上限", "负向CI下限", "负向CI上限", "分类稳定率", "Bootstrap众数类型", "质量标记", "Legacy分类", "分类变化"];
  sheet.getRange("A4:AA4").values = [headers];
  styleHeader(sheet.getRange("A4:AA4"));
  const start = 5;
  const end = start + rows.length - 1;
  sheet.getRange(`A${start}:AA${end}`).values = rows.map((row) => [
    row.scene, row.touchpoint, row.aesthetic, row.raw_record_count, row.post_count,
    row.duplicate_records_collapsed, row.conflict_post_count,
    row.positive_count, row.neutral_count, row.negative_count,
    null, null, null, row.classification, row.priority_rank, row.recommended_action,
    row.positive_ci_low, row.positive_ci_high, row.neutral_ci_low, row.neutral_ci_high,
    row.negative_ci_low, row.negative_ci_high, row.classification_stability,
    row.bootstrap_modal_class, row.quality_flags, row.legacy_classification,
    row.classification_changed ? "是" : "否",
  ]);
  sheet.getRange(`K${start}`).formulas = [[`=H${start}/E${start}`]];
  sheet.getRange(`K${start}:K${end}`).fillDown();
  sheet.getRange(`L${start}`).formulas = [[`=I${start}/E${start}`]];
  sheet.getRange(`L${start}:L${end}`).fillDown();
  sheet.getRange(`M${start}`).formulas = [[`=J${start}/E${start}`]];
  sheet.getRange(`M${start}:M${end}`).fillDown();
  styleBody(sheet.getRange(`A${start}:AA${end}`));
  sheet.getRange(`D${start}:J${end}`).format.numberFormat = "#,##0";
  sheet.getRange(`K${start}:M${end}`).format.numberFormat = "0.0%";
  sheet.getRange(`Q${start}:W${end}`).format.numberFormat = "0.0%";
  sheet.getRange(`W${start}:W${end}`).conditionalFormats.add("cellIs", {
    operator: "lessThan",
    formula: data.config.bootstrap.low_stability_threshold,
    format: { fill: colors.red, font: { color: "#9C0006" } },
  });
  sheet.getRange(`AA${start}:AA${end}`).conditionalFormats.add("containsText", {
    text: "是",
    format: { fill: colors.amber, font: { bold: true, color: "#9C6500" } },
  });
  setWidths(sheet, [20, 22, 21, 11, 10, 11, 11, 9, 9, 9, 10, 10, 10, 26, 10, 34, 11, 11, 11, 11, 11, 11, 12, 26, 32, 23, 10]);
  sheet.freezePanes.freezeRows(4);
}

function addPairSheet() {
  const rows = data.pair_rows;
  const sheet = workbook.worksheets.add("词对明细_帖子级");
  sheet.showGridLines = false;
  styleTitle(sheet, "O", "词对明细（帖子级）", "使用场景×美学指标×用户感受的去重帖子票。");
  sheet.getRange("A4:O4").values = [["使用场景", "触点类型", "美学指标", "用户感受", "原始记录", "帖子数", "合并重复", "冲突帖子", "正向票", "中性票", "负向票", "正向率", "中性率", "负向率", "主导情感"]];
  styleHeader(sheet.getRange("A4:O4"));
  const start = 5;
  const end = start + rows.length - 1;
  sheet.getRange(`A${start}:O${end}`).values = rows.map((row) => {
    const sentiments = [[row.positive_count, "正向"], [row.neutral_count, "中性"], [row.negative_count, "负向"]];
    sentiments.sort((left, right) => right[0] - left[0]);
    return [row.scene, row.touchpoint, row.aesthetic, row.perception, row.raw_record_count, row.post_count, row.duplicate_records_collapsed, row.conflict_post_count, row.positive_count, row.neutral_count, row.negative_count, null, null, null, sentiments[0][1]];
  });
  sheet.getRange(`L${start}`).formulas = [[`=I${start}/F${start}`]];
  sheet.getRange(`L${start}:L${end}`).fillDown();
  sheet.getRange(`M${start}`).formulas = [[`=J${start}/F${start}`]];
  sheet.getRange(`M${start}:M${end}`).fillDown();
  sheet.getRange(`N${start}`).formulas = [[`=K${start}/F${start}`]];
  sheet.getRange(`N${start}:N${end}`).fillDown();
  styleBody(sheet.getRange(`A${start}:O${end}`));
  sheet.getRange(`E${start}:K${end}`).format.numberFormat = "#,##0";
  sheet.getRange(`L${start}:N${end}`).format.numberFormat = "0.0%";
  setWidths(sheet, [20, 22, 21, 21, 11, 10, 11, 11, 9, 9, 9, 10, 10, 10, 12]);
  sheet.freezePanes.freezeRows(4);
}

function addStabilitySheet() {
  const rows = data.summary_rows;
  const sheet = workbook.worksheets.add("Bootstrap稳定性");
  sheet.showGridLines = false;
  styleTitle(sheet, "R", "Bootstrap 稳定性", `${data.config.bootstrap.iterations} 次组内帖子重采样，置信水平 ${(data.config.bootstrap.confidence_level * 100).toFixed(0)}%。`);
  sheet.getRange("A4:R4").values = [["使用场景", "美学指标", "帖子数", "点估计分类", "分类稳定率", "Bootstrap众数分类", "众数占比", "正向率", "正向CI下限", "正向CI上限", "中性率", "中性CI下限", "中性CI上限", "负向率", "负向CI下限", "负向CI上限", "冲突帖子", "质量标记"]];
  styleHeader(sheet.getRange("A4:R4"));
  const start = 5;
  const end = start + rows.length - 1;
  sheet.getRange(`A${start}:R${end}`).values = rows.map((row) => [row.scene, row.aesthetic, row.post_count, row.classification, row.classification_stability, row.bootstrap_modal_class, row.bootstrap_modal_rate, row.positive_rate, row.positive_ci_low, row.positive_ci_high, row.neutral_rate, row.neutral_ci_low, row.neutral_ci_high, row.negative_rate, row.negative_ci_low, row.negative_ci_high, row.conflict_post_count, row.quality_flags]);
  styleBody(sheet.getRange(`A${start}:R${end}`));
  sheet.getRange(`C${start}:C${end}`).format.numberFormat = "#,##0";
  sheet.getRange(`E${start}:P${end}`).format.numberFormat = "0.0%";
  sheet.getRange(`Q${start}:Q${end}`).format.numberFormat = "#,##0";
  sheet.getRange(`E${start}:E${end}`).conditionalFormats.add("cellIs", {
    operator: "lessThan",
    formula: data.config.bootstrap.low_stability_threshold,
    format: { fill: colors.red, font: { color: "#9C0006" } },
  });
  setWidths(sheet, [20, 21, 10, 27, 12, 27, 11, 10, 11, 11, 10, 11, 11, 10, 11, 11, 11, 34]);
  sheet.freezePanes.freezeRows(4);
}

function addLegacySheet() {
  const rows = data.summary_rows;
  const sheet = workbook.worksheets.add("Legacy对照");
  sheet.showGridLines = false;
  styleTitle(sheet, "N", "Legacy 与 v2 对照", "Legacy 基于记录级情感比例；v2 基于去重帖子票和公开阈值。");
  sheet.getRange("A4:N4").values = [["使用场景", "美学指标", "原始记录", "帖子数", "正向票", "中性票", "负向票", "正向率", "中性率", "负向率", "Legacy分类", "v2分类", "是否变化", "分类稳定率"]];
  styleHeader(sheet.getRange("A4:N4"));
  const start = 5;
  const end = start + rows.length - 1;
  sheet.getRange(`A${start}:N${end}`).values = rows.map((row) => [row.scene, row.aesthetic, row.raw_record_count, row.post_count, row.positive_count, row.neutral_count, row.negative_count, null, null, null, row.legacy_classification, row.classification, row.classification_changed ? "是" : "否", row.classification_stability]);
  sheet.getRange(`H${start}`).formulas = [[`=E${start}/D${start}`]];
  sheet.getRange(`H${start}:H${end}`).fillDown();
  sheet.getRange(`I${start}`).formulas = [[`=F${start}/D${start}`]];
  sheet.getRange(`I${start}:I${end}`).fillDown();
  sheet.getRange(`J${start}`).formulas = [[`=G${start}/D${start}`]];
  sheet.getRange(`J${start}:J${end}`).fillDown();
  styleBody(sheet.getRange(`A${start}:N${end}`));
  sheet.getRange(`C${start}:G${end}`).format.numberFormat = "#,##0";
  sheet.getRange(`H${start}:J${end}`).format.numberFormat = "0.0%";
  sheet.getRange(`N${start}:N${end}`).format.numberFormat = "0.0%";
  sheet.getRange(`M${start}:M${end}`).conditionalFormats.add("containsText", {
    text: "是",
    format: { fill: colors.amber, font: { bold: true, color: "#9C6500" } },
  });
  setWidths(sheet, [20, 21, 11, 10, 9, 9, 9, 10, 10, 10, 24, 28, 10, 12]);
  sheet.freezePanes.freezeRows(4);
}

function addVotesSheet() {
  const rows = data.scene_votes;
  const sheet = workbook.worksheets.add("帖子级投票");
  sheet.showGridLines = false;
  styleTitle(sheet, "I", "帖子级投票", "用于场景×美学指标分类的可审计中间数据。");
  sheet.getRange("A4:I4").values = [["帖子ID", "使用场景", "触点类型", "美学指标", "解决后情感", "原始记录数", "合并重复", "是否冲突", "首条来源行"]];
  styleHeader(sheet.getRange("A4:I4"));
  const start = 5;
  const end = start + rows.length - 1;
  sheet.getRange(`A${start}:I${end}`).values = rows.map((row) => [row.post_id, row.scene, data.config.touchpoint_mapping[row.aesthetic] || "", row.aesthetic, row.sentiment, row.raw_record_count, row.duplicate_records_collapsed, row.conflict ? "是" : "否", row.source_first_row]);
  styleBody(sheet.getRange(`A${start}:I${end}`));
  sheet.getRange(`F${start}:G${end}`).format.numberFormat = "#,##0";
  sheet.getRange(`I${start}:I${end}`).format.numberFormat = "#,##0";
  sheet.getRange(`H${start}:H${end}`).conditionalFormats.add("containsText", {
    text: "是",
    format: { fill: colors.amber, font: { color: "#9C6500" } },
  });
  setWidths(sheet, [20, 20, 22, 21, 13, 12, 11, 11, 11]);
  sheet.freezePanes.freezeRows(4);
}

function addGlobalSheet() {
  const sheet = workbook.worksheets.add("全局统计");
  sheet.showGridLines = false;
  styleTitle(sheet, "H", "全局统计", "Kano-inspired v2 的样本、分类和稳定性概览。");
  sheet.getRange("A4:B12").values = [
    ["指标", "数值"],
    ["原始标签记录", data.raw_record_count],
    ["正式场景记录", data.formal_record_count],
    ["全部唯一帖子", data.unique_post_count],
    ["正式场景唯一帖子", data.formal_unique_post_count],
    ["场景×指标组合", data.summary_rows.length],
    ["词对组合", data.pair_rows.length],
    ["Legacy与v2分类不同", data.legacy_change_count],
    ["低分类稳定率组合", data.low_stability_count],
  ];
  styleHeader(sheet.getRange("A4:B4"));
  styleBody(sheet.getRange("A5:B12"));
  sheet.getRange("B5:B12").format.numberFormat = "#,##0";
  const classRows = Object.entries(data.class_counts)
    .sort((left, right) => data.config.class_priority[left[0]] - data.config.class_priority[right[0]])
    .map(([label, count]) => [label, count, count / data.summary_rows.length]);
  sheet.getRange(`D4:F${4 + classRows.length}`).values = [
    ["v2分类", "组合数", "占比"],
    ...classRows,
  ];
  styleHeader(sheet.getRange("D4:F4"));
  styleBody(sheet.getRange(`D5:F${4 + classRows.length}`));
  sheet.getRange(`E5:E${4 + classRows.length}`).format.numberFormat = "#,##0";
  sheet.getRange(`F5:F${4 + classRows.length}`).format.numberFormat = "0.0%";
  const topRows = [...data.summary_rows]
    .sort((left, right) => left.priority_rank - right.priority_rank || right.post_count - left.post_count)
    .slice(0, 12)
    .map((row) => [row.scene, row.aesthetic, row.classification, row.post_count, row.negative_rate, row.classification_stability]);
  sheet.getRange(`A16:F${16 + topRows.length}`).values = [
    ["使用场景", "美学指标", "v2分类", "帖子数", "负向率", "分类稳定率"],
    ...topRows,
  ];
  styleHeader(sheet.getRange("A16:F16"));
  styleBody(sheet.getRange(`A17:F${16 + topRows.length}`));
  sheet.getRange(`D17:D${16 + topRows.length}`).format.numberFormat = "#,##0";
  sheet.getRange(`E17:F${16 + topRows.length}`).format.numberFormat = "0.0%";
  setWidths(sheet, [28, 18, 4, 30, 12, 12, 4, 4]);
}

addMethodSheet();
addQualitySheet();
addSummarySheet();
addPairSheet();
addStabilitySheet();
addLegacySheet();
addVotesSheet();
addGlobalSheet();

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

const sheets = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 6000 });
console.log(sheets.ndjson);
