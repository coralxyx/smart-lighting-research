import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";


const workbookPath = process.argv[2];
if (!workbookPath) {
  throw new Error("Usage: node scripts/verify_kano_v2_workbook.mjs <workbook.xlsx>");
}

const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const summary = await workbook.inspect({
  kind: "table",
  range: "场景汇总_帖子级!A1:AA10",
  include: "values,formulas",
  tableMaxRows: 10,
  tableMaxCols: 27,
  maxChars: 14000,
});
console.log(summary.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 200 },
  summary: "final formula error scan",
});
console.log(formulaErrors.ndjson);

const renderRanges = {
  "方法与参数": "A1:G20",
  "数据质量": "A1:D21",
  "场景汇总_帖子级": "A1:AA14",
  "词对明细_帖子级": "A1:O14",
  "Bootstrap稳定性": "A1:R14",
  "Legacy对照": "A1:N14",
  "帖子级投票": "A1:I14",
  "全局统计": "A1:F28",
};
for (const [sheetName, range] of Object.entries(renderRanges)) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  console.log(JSON.stringify({ sheetName, bytes: (await preview.arrayBuffer()).byteLength }));
}
