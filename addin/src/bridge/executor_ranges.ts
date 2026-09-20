/* global Excel */
import { getWorksheetSafe } from "./helpers";

const HUGE_CELLS = 20000;

function asGrid(input: unknown): any[][] {
  if (input == null) return [[""]];
  if (!Array.isArray(input)) return [[input]];
  if (input.length === 0) return [[""]];
  if (!Array.isArray(input[0])) return [input];
  const cols = Math.max(1, ...input.map((r) => (Array.isArray(r) ? r.length : 1)));
  return input.map((row) => {
    const r = Array.isArray(row) ? row.slice() : [row];
    while (r.length < cols) r.push(null);
    return r.slice(0, cols);
  });
}

async function clipIfHuge(
  sheet: Excel.Worksheet,
  range: Excel.Range,
  context: Excel.RequestContext
): Promise<Excel.Range> {
  range.load(["rowCount", "columnCount", "rowIndex", "columnIndex"]);
  await context.sync();
  if (range.rowCount * range.columnCount <= HUGE_CELLS) return range;
  const used = sheet.getUsedRangeOrNullObject();
  used.load(["rowIndex", "rowCount", "columnIndex", "columnCount"]);
  await context.sync();
  if (used.isNullObject) {
    return sheet.getRangeByIndexes(range.rowIndex, range.columnIndex, Math.min(range.rowCount, 200), range.columnCount);
  }
  const r0 = Math.max(range.rowIndex, used.rowIndex);
  const c0 = Math.max(range.columnIndex, used.columnIndex);
  const r1 = Math.min(range.rowIndex + range.rowCount, used.rowIndex + used.rowCount);
  const c1 = Math.min(range.columnIndex + range.columnCount, used.columnIndex + used.columnCount);
  return sheet.getRangeByIndexes(r0, c0, Math.max(1, r1 - r0), Math.max(1, c1 - c0));
}

export async function execRangeRead(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const sheet = await getWorksheetSafe(context, params.sheet, false);
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
    const sheet = await getWorksheetSafe(context, params.sheet, true);
    let range = await clipIfHuge(sheet, sheet.getRange(params.address), context);
    range.load(["rowCount", "columnCount", "rowIndex", "columnIndex", "address"]);
    await context.sync();

    const isFormula = Boolean(params.formulas);
    const grid = asGrid(isFormula ? params.formulas : params.values);
    const rows = grid.length;
    const cols = grid[0]?.length || 1;

    const writeTo = (target: Excel.Range, data: any[][]) => {
      if (isFormula) target.formulas = data;
      else target.values = data;
    };

    if (rows === 1 && cols === 1 && (range.rowCount > 1 || range.columnCount > 1)) {
      const seed = range.getCell(0, 0);
      writeTo(seed, grid);
      await context.sync();
      if (isFormula) {
        try {
          seed.autoFill(range, Excel.AutoFillType.fillDefault);
        } catch {
          writeTo(range, Array.from({ length: range.rowCount }, () => Array(range.columnCount).fill(grid[0][0])));
        }
      } else {
        writeTo(range, Array.from({ length: range.rowCount }, () => Array(range.columnCount).fill(grid[0][0])));
      }
    } else if (rows === range.rowCount && cols === range.columnCount) {
      writeTo(range, grid);
    } else {
      const dest = sheet.getRangeByIndexes(range.rowIndex, range.columnIndex, rows, cols);
      writeTo(dest, grid);
      range = dest;
    }

    range.load(["cellCount", "address"]);
    await context.sync();

    return {
      success: true,
      address: range.address.replace(/.*!/, ""),
      cells_modified: range.cellCount,
    };
  });
}

export async function execRangeClear(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const sheet = await getWorksheetSafe(context, params.sheet, false);
    const range = sheet.getRange(params.address);
    range.clear();
    await context.sync();
    return { success: true };
  });
}

export async function execFormatRange(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const sheet = await getWorksheetSafe(context, params.sheet, false);
    const range = await clipIfHuge(sheet, sheet.getRange(params.address), context);

    if (params.fill && params.fill.color) {
      range.format.fill.color = params.fill.color;
    }
    if (params.font) {
      if (params.font.bold !== undefined) range.format.font.bold = params.font.bold;
      if (params.font.italic !== undefined) range.format.font.italic = params.font.italic;
      if (params.font.color) range.format.font.color = params.font.color;
      if (params.font.size) range.format.font.size = params.font.size;
      if (params.font.name) range.format.font.name = params.font.name;
      if (params.font.underline) range.format.font.underline = "Single";
    }
    if (params.alignment) {
      if (params.alignment.horizontal) range.format.horizontalAlignment = params.alignment.horizontal;
      if (params.alignment.vertical) range.format.verticalAlignment = params.alignment.vertical;
      if (params.alignment.wrap !== undefined) range.format.wrapText = params.alignment.wrap;
    }
    if (params.borders) {
      const style = (params.borders.style || "Continuous") as Excel.BorderLineStyle;
      const color = params.borders.color || "#000000";
      const edges: Excel.BorderIndex[] = params.borders.all
        ? ["EdgeTop", "EdgeBottom", "EdgeLeft", "EdgeRight", "InsideHorizontal", "InsideVertical"] as any
        : (["EdgeTop", "EdgeBottom", "EdgeLeft", "EdgeRight"] as any);
      for (const e of edges) {
        const b = range.format.borders.getItem(e);
        b.style = style;
        b.color = color;
      }
    }

    await context.sync();
    return { success: true };
  });
}

export async function execFormatNumber(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const sheet = await getWorksheetSafe(context, params.sheet, false);
    const range = await clipIfHuge(sheet, sheet.getRange(params.address), context);
    range.load(["rowCount", "columnCount"]);
    await context.sync();
    const code = params.format || "General";
    range.numberFormat = Array.from({ length: range.rowCount }, () => Array(range.columnCount).fill(code));
    await context.sync();
    return { success: true };
  });
}
