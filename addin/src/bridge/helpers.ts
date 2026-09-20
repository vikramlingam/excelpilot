/* global Excel */

export async function getWorksheetSafe(
  context: Excel.RequestContext,
  sheetName?: string,
  autoCreate: boolean = false
): Promise<Excel.Worksheet> {
  if (!sheetName || sheetName.trim() === "" || sheetName.toLowerCase() === "active") {
    return context.workbook.worksheets.getActiveWorksheet();
  }

  const sheet = context.workbook.worksheets.getItemOrNullObject(sheetName);
  await context.sync();

  if (!sheet.isNullObject) {
    return sheet;
  }

  if (autoCreate) {
    try {
      const newSheet = context.workbook.worksheets.add(sheetName);
      await context.sync();
      return newSheet;
    } catch {
      return context.workbook.worksheets.getActiveWorksheet();
    }
  }

  return context.workbook.worksheets.getActiveWorksheet();
}
