import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";


const workbookPath = process.argv[2];
if (!workbookPath) {
  throw new Error("Usage: node scripts/verify_kano_workbook.mjs <workbook.xlsx>");
}

const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const keyRange = await workbook.inspect({
  kind: "table",
  range: "Kano汇总!A1:O8",
  include: "values,formulas",
  tableMaxRows: 8,
  tableMaxCols: 15,
  maxChars: 8000,
});
console.log(keyRange.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(formulaErrors.ndjson);

const renderRanges = {
  "方法说明": "A1:E10",
  "Kano_亲子互动陪伴": "A1:O11",
  "Kano_日常基础照明": "A1:O13",
  "Kano_睡眠与起居": "A1:O13",
  "Kano_休闲娱乐": "A1:O13",
  "Kano_学习工作": "A1:O13",
  "Kano_智能托管": "A1:O13",
  "Kano汇总": "A1:O15",
  "词对明细": "A1:M15",
  "全局统计": "A1:K20",
  "复现对照": "A1:D10",
};
for (const [sheetName, range] of Object.entries(renderRanges)) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  console.log(
    JSON.stringify({
      sheetName,
      renderedBytes: (await preview.arrayBuffer()).byteLength,
    })
  );
}
