/* global Excel */

export async function execRangeRead(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const sheet = context.workbook.worksheets.getItem(params.sheet);
    const range = sheet.getRange(params.address);

    if (params.values) range.load("values");
    if (params.formulas) range.load("formulas");
    if (params.formats) range.load("numberFormat");
    range.load(["rowCount", "columnCount", "address"]);

    await context.sync();

    return {
      address: range.address,
      values: params.values ? range.values : null,
      formulas: params.formulas ? range.formulas : null,
      formats: params.formats ? range.numberFormat : null,
      total_cells: range.rowCount * range.columnCount,
    };
  });
}

export async function execRangeWrite(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const sheet = context.workbook.worksheets.getItem(params.sheet);
    const range = sheet.getRange(params.address);

    if (params.formulas) {
      range.formulas = params.formulas;
    } else if (params.values) {
      range.values = params.values;
    }

    range.load("cellCount");
    await context.sync();

    return {
      success: true,
      address: params.address,
      cells_modified: range.cellCount,
    };
  });
}

export async function execRangeClear(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const sheet = context.workbook.worksheets.getItem(params.sheet);
    const range = sheet.getRange(params.address);
    range.clear();
    await context.sync();
    return { success: true };
  });
}

export async function execFormatRange(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const sheet = context.workbook.worksheets.getItem(params.sheet);
    const range = sheet.getRange(params.address);

    if (params.fill && params.fill.color) {
      range.format.fill.color = params.fill.color;
    }
    if (params.font) {
      if (params.font.bold !== undefined) range.format.font.bold = params.font.bold;
      if (params.font.color) range.format.font.color = params.font.color;
      if (params.font.size) range.format.font.size = params.font.size;
    }
    if (params.alignment && params.alignment.horizontal) {
      range.format.horizontalAlignment = params.alignment.horizontal;
    }

    await context.sync();
    return { success: true };
  });
}

export async function execFormatNumber(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const sheet = context.workbook.worksheets.getItem(params.sheet);
    const range = sheet.getRange(params.address);
    range.numberFormat = [[params.format]];
    await context.sync();
    return { success: true };
  });
}
