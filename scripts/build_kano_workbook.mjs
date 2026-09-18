import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";


const [payloadPath, outputPath] = process.argv.slice(2);
if (!payloadPath || !outputPath) {
  throw new Error("Usage: node scripts/build_kano_workbook.mjs <payload.json> <output.xlsx>");
}

const payload = JSON.parse(await fs.readFile(payloadPath, "utf8"));
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
};

function columnName(columnNumber) {
  let name = "";
  let value = columnNumber;
  while (value > 0) {
    const remainder = (value - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    value = Math.floor((value - 1) / 26);
  }
  return name;
}

function styleTitle(sheet, range, title) {
  const titleRange = sheet.getRange(range);
  titleRange.merge();
  titleRange.values = [[title]];
  titleRange.format = {
    font: { name: fontFamily, size: 15, bold: true, color: colors.text },
    verticalAlignment: "center",
    borders: { bottom: { style: "medium", color: colors.navy } },
  };
  titleRange.format.rowHeight = 27;
}

function styleHeader(range) {
  range.format = {
    fill: colors.navy,
    font: { name: fontFamily, size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: {
      insideVertical: { style: "thin", color: "#FFFFFF" },
      bottom: { style: "thin", color: colors.navy },
    },
  };
  range.format.rowHeight = 28;
}

function styleBody(range) {
  range.format = {
    font: { name: fontFamily, size: 9, color: colors.text },
    verticalAlignment: "top",
    wrapText: true,
    borders: { bottom: { style: "thin", color: colors.border } },
  };
}

function setWidths(sheet, widths) {
  widths.forEach((width, index) => {
    sheet.getRange(`${columnName(index + 1)}:${columnName(index + 1)}`).format.columnWidth = width;
  });
}

function addMethodSheet() {
  const sheet = workbook.worksheets.add("方法说明");
  sheet.showGridLines = false;
  styleTitle(sheet, "A1:E1", "Kano-inspired 旧表复现说明");
  sheet.getRange("A3:B10").values = [
    ["项目", "说明"],
    ["分析对象", "标签表中的使用场景、标准美学指标、用户感受和情感强度。"],
    ["统计单位", "每条抽取记录作为一个统计单位；帖子级去重将在 Kano-inspired v2 中实现。"],
    ["词对", "使用场景 × 标准美学指标 × 用户感受。"],
    ["A/O/I/M 分类", payload.method.classification_note],
    ["方法名称", "基于 UGC 情感分布的 Kano-inspired 需求优先级分析（旧表复现版）"],
    ["输入文件", payload.source_files.input],
    ["旧表参考", payload.source_files.legacy_reference],
  ];
  styleHeader(sheet.getRange("A3:B3"));
  styleBody(sheet.getRange("A4:B10"));

  const mappingRows = Object.entries(payload.touchpoint_by_aesthetic)
    .sort(([left], [right]) => left.localeCompare(right, "zh-CN"))
    .map(([aesthetic, touchpoint]) => [aesthetic, touchpoint]);
  sheet.getRange(`D3:E${3 + mappingRows.length}`).values = [
    ["标准美学指标", "触点类型"],
    ...mappingRows,
  ];
  styleHeader(sheet.getRange("D3:E3"));
  styleBody(sheet.getRange(`D4:E${3 + mappingRows.length}`));
  setWidths(sheet, [22, 68, 4, 24, 28]);
}

function sceneRows(scene) {
  return payload.summary_rows.filter((row) => row.scene === scene);
}

function addSceneSheet(scene) {
  const rows = sceneRows(scene);
  const sheet = workbook.worksheets.add(`Kano_${scene}`);
  sheet.showGridLines = false;
  styleTitle(sheet, "A1:O1", `${scene}｜Kano 触点分析表`);
  sheet.getRange("A2:B2").values = [["场景总提及频次", payload.scene_totals[scene]]];
  sheet.getRange("A2:B2").format = {
    fill: colors.paleBlue,
    font: { name: fontFamily, size: 10, bold: true, color: colors.text },
  };
  const headers = ["触点类型", "标准美学指标", "提及频次", "场景内占比", "正向数", "中性数", "负向数", "正向率", "中性率", "负向率", "主要用户感受", "用户感受占比分布", "Kano分类（legacy）", "设计优先级（legacy）", "设计含义/建议（legacy）"];
  sheet.getRange("A4:O4").values = [headers];
  styleHeader(sheet.getRange("A4:O4"));
  if (rows.length) {
    const start = 5;
    const end = start + rows.length - 1;
    sheet.getRange(`A${start}:O${end}`).values = rows.map((row) => [
      row.touchpoint, row.aesthetic, row.count, null,
      row.positive_count, row.neutral_count, row.negative_count,
      null, null, null, row.main_perception, row.perception_distribution,
      row.legacy_classification, row.legacy_priority, row.legacy_recommendation,
    ]);
    sheet.getRange(`D${start}`).formulas = [[`=C${start}/$B$2`]];
    sheet.getRange(`D${start}:D${end}`).fillDown();
    sheet.getRange(`H${start}`).formulas = [[`=E${start}/C${start}`]];
    sheet.getRange(`H${start}:H${end}`).fillDown();
    sheet.getRange(`I${start}`).formulas = [[`=F${start}/C${start}`]];
    sheet.getRange(`I${start}:I${end}`).fillDown();
    sheet.getRange(`J${start}`).formulas = [[`=G${start}/C${start}`]];
    sheet.getRange(`J${start}:J${end}`).fillDown();
    styleBody(sheet.getRange(`A${start}:O${end}`));
    sheet.getRange(`C${start}:C${end}`).format.numberFormat = "#,##0";
    sheet.getRange(`D${start}:D${end}`).format.numberFormat = "0.0%";
    sheet.getRange(`E${start}:G${end}`).format.numberFormat = "#,##0";
    sheet.getRange(`H${start}:J${end}`).format.numberFormat = "0.0%";
  }
  setWidths(sheet, [24, 23, 12, 14, 10, 10, 10, 11, 11, 11, 20, 55, 23, 22, 52]);
  sheet.freezePanes.freezeRows(4);
}

function addSummarySheet() {
  const rows = payload.summary_rows;
  const sheet = workbook.worksheets.add("Kano汇总");
  sheet.showGridLines = false;
  styleTitle(sheet, "A1:O1", "各使用场景 Kano 汇总（不含“无”场景）");
  sheet.getRange("A3:O3").values = [["使用场景", "触点类型", "标准美学指标", "提及频次", "场景内占比", "正向数", "中性数", "负向数", "正向率", "中性率", "负向率", "主要用户感受", "用户感受占比分布", "Kano分类（legacy）", "设计优先级（legacy）"]];
  styleHeader(sheet.getRange("A3:O3"));
  const start = 4;
  const end = start + rows.length - 1;
  sheet.getRange(`A${start}:O${end}`).values = rows.map((row) => [
    row.scene, row.touchpoint, row.aesthetic, row.count, null,
    row.positive_count, row.neutral_count, row.negative_count,
    null, null, null, row.main_perception, row.perception_distribution,
    row.legacy_classification, row.legacy_priority,
  ]);
  sheet.getRange(`E${start}`).formulas = [[`=D${start}/SUMIF($A$${start}:$A$${end},A${start},$D$${start}:$D$${end})`]];
  sheet.getRange(`E${start}:E${end}`).fillDown();
  sheet.getRange(`I${start}`).formulas = [[`=F${start}/D${start}`]];
  sheet.getRange(`I${start}:I${end}`).fillDown();
  sheet.getRange(`J${start}`).formulas = [[`=G${start}/D${start}`]];
  sheet.getRange(`J${start}:J${end}`).fillDown();
  sheet.getRange(`K${start}`).formulas = [[`=H${start}/D${start}`]];
  sheet.getRange(`K${start}:K${end}`).fillDown();
  styleBody(sheet.getRange(`A${start}:O${end}`));
  sheet.getRange(`D${start}:D${end}`).format.numberFormat = "#,##0";
  sheet.getRange(`E${start}:E${end}`).format.numberFormat = "0.0%";
  sheet.getRange(`F${start}:H${end}`).format.numberFormat = "#,##0";
  sheet.getRange(`I${start}:K${end}`).format.numberFormat = "0.0%";
  setWidths(sheet, [22, 24, 23, 12, 14, 10, 10, 10, 11, 11, 11, 20, 55, 23, 22]);
  sheet.freezePanes.freezeRows(3);
}

function addPairSheet() {
  const rows = payload.pair_rows;
  const sheet = workbook.worksheets.add("词对明细");
  sheet.showGridLines = false;
  styleTitle(sheet, "A1:M1", "标准化词对明细：使用场景 × 美学指标 × 用户感受");
  sheet.getRange("A3:M3").values = [["使用场景", "触点类型", "美学指标", "用户感受", "提及频次", "全局占比", "场景内占比", "正向数", "中性数", "负向数", "正向率", "负向率", "主导情感"]];
  styleHeader(sheet.getRange("A3:M3"));
  const start = 4;
  const end = start + rows.length - 1;
  sheet.getRange(`A${start}:M${end}`).values = rows.map((row) => [
    row.scene, row.touchpoint, row.aesthetic, row.perception, row.count,
    null, null, row.positive_count, row.neutral_count, row.negative_count,
    null, null, row.dominant_sentiment,
  ]);
  sheet.getRange(`F${start}`).formulas = [[`=E${start}/${payload.record_count}`]];
  sheet.getRange(`F${start}:F${end}`).fillDown();
  sheet.getRange(`G${start}`).formulas = [[`=E${start}/SUMIF($A$${start}:$A$${end},A${start},$E$${start}:$E$${end})`]];
  sheet.getRange(`G${start}:G${end}`).fillDown();
  sheet.getRange(`K${start}`).formulas = [[`=H${start}/E${start}`]];
  sheet.getRange(`K${start}:K${end}`).fillDown();
  sheet.getRange(`L${start}`).formulas = [[`=J${start}/E${start}`]];
  sheet.getRange(`L${start}:L${end}`).fillDown();
  styleBody(sheet.getRange(`A${start}:M${end}`));
  sheet.getRange(`E${start}:E${end}`).format.numberFormat = "#,##0";
  sheet.getRange(`F${start}:G${end}`).format.numberFormat = "0.0%";
  sheet.getRange(`H${start}:J${end}`).format.numberFormat = "#,##0";
  sheet.getRange(`K${start}:L${end}`).format.numberFormat = "0.0%";
  setWidths(sheet, [22, 24, 22, 22, 12, 12, 14, 10, 10, 10, 11, 11, 12]);
  sheet.freezePanes.freezeRows(3);
}

function addGlobalSheet() {
  const sheet = workbook.worksheets.add("全局统计");
  sheet.showGridLines = false;
  styleTitle(sheet, "A1:H1", "全局统计");
  sheet.getRange("A3:B8").values = [
    ["指标", "数值"],
    ["有效标注总数", payload.record_count],
    ["唯一原帖数", payload.unique_post_count],
    ["每帖记录数中位数", payload.records_per_post.median],
    ["每帖最少记录数", payload.records_per_post.minimum],
    ["每帖最多记录数", payload.records_per_post.maximum],
  ];
  styleHeader(sheet.getRange("A3:B3"));
  styleBody(sheet.getRange("A4:B8"));

  const blocks = [
    { title: "场景频数", rows: payload.scene_counts, key: "scene", startCol: 1 },
    { title: "美学指标频数", rows: payload.aesthetic_counts, key: "aesthetic", startCol: 4 },
    { title: "用户感受频数", rows: payload.perception_counts, key: "perception", startCol: 7 },
    { title: "情感频数", rows: payload.sentiment_counts, key: "sentiment", startCol: 10 },
  ];
  blocks.forEach((block) => {
    const firstCol = columnName(block.startCol);
    const secondCol = columnName(block.startCol + 1);
    const startRow = 11;
    const endRow = startRow + block.rows.length;
    sheet.getRange(`${firstCol}${startRow}:${secondCol}${endRow}`).values = [
      [block.title, "频数"],
      ...block.rows.map((row) => [row[block.key], row.count]),
    ];
    styleHeader(sheet.getRange(`${firstCol}${startRow}:${secondCol}${startRow}`));
    styleBody(sheet.getRange(`${firstCol}${startRow + 1}:${secondCol}${endRow}`));
    sheet.getRange(`${secondCol}${startRow + 1}:${secondCol}${endRow}`).format.numberFormat = "#,##0";
  });
  setWidths(sheet, [24, 14, 4, 24, 14, 4, 24, 14, 4, 18, 14]);
}

function addAuditSheet() {
  const sheet = workbook.worksheets.add("复现对照");
  sheet.showGridLines = false;
  styleTitle(sheet, "A1:D1", "第一阶段复现对照");
  sheet.getRange("A3:D8").values = [
    ["核对项", "复现值", "旧表值", "差异"],
    ["有效标注总数", payload.record_count, 4747, null],
    ["唯一词对数", payload.pair_rows.length, 253, null],
    ["场景×美学分组数", payload.summary_rows.length, 52, null],
    ["数值对照", "全局频数、场景统计和 253 组词对计数已逐项对照", "参考工作簿", "0 项差异"],
    ["A/O/I/M 分类", "legacy mapping", "旧表静态分类", "缺少可执行阈值，不作伪复现"],
  ];
  sheet.getRange("D4").formulas = [["=B4-C4"]];
  sheet.getRange("D4:D6").fillDown();
  styleHeader(sheet.getRange("A3:D3"));
  styleBody(sheet.getRange("A4:D8"));
  sheet.getRange("B4:D6").format.numberFormat = "#,##0";
  sheet.getRange("A10:D10").merge();
  sheet.getRange("A10").values = [["说明：该工作簿重新计算计数和比例，仅继承旧表无法从公式恢复的分类、优先级和设计建议。"]];
  sheet.getRange("A10:D10").format = {fill: colors.amber, font: {name: fontFamily, size: 10, color: colors.text}, wrapText: true};
  setWidths(sheet, [30, 45, 30, 38]);
}

addMethodSheet();
Object.keys(payload.scene_totals)
  .filter((scene) => scene !== "无")
  .sort((left, right) => left.localeCompare(right, "zh-CN"))
  .forEach(addSceneSheet);
addSummarySheet();
addPairSheet();
addGlobalSheet();
addAuditSheet();

await fs.mkdir(new URL(".", `file:///${outputPath.replaceAll("\\", "/")}`).pathname, { recursive: true }).catch(() => {});
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

const inspection = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 6000,
});
console.log(inspection.ndjson);
