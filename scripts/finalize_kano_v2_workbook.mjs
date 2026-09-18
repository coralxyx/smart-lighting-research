import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";


const workbookPath = process.argv[2];
if (!workbookPath) {
  throw new Error("Usage: node scripts/finalize_kano_v2_workbook.mjs <workbook.xlsx>");
}

const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const sheet = workbook.worksheets.getItem("方法与参数");
sheet.getRange("B8").format.numberFormat = "#,##0";
sheet.getRange("B10").format.numberFormat = "#,##0";
sheet.getRange("B11").format.numberFormat = "0%";
sheet.getRange("B12").format.numberFormat = "#,##0";
sheet.getRange("B13:B14").format.numberFormat = "0%";

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(workbookPath);
