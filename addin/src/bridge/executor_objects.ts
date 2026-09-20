/* global Excel */
import { getWorksheetSafe } from "./helpers";

const AGG: Record<string, Excel.AggregationFunction> = {
  sum: "Sum" as Excel.AggregationFunction,
  count: "Count" as Excel.AggregationFunction,
  average: "Average" as Excel.AggregationFunction,
  avg: "Average" as Excel.AggregationFunction,
  max: "Max" as Excel.AggregationFunction,
  min: "Min" as Excel.AggregationFunction,
};

export async function execPivotCreate(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const srcSheet = await getWorksheetSafe(context, params.source_sheet, false);
    const srcRange = srcSheet.getRange(params.source_address);
    const destSheet = await getWorksheetSafe(context, params.dest_sheet, true);
    destSheet.activate();
    const destRange = destSheet.getRange(params.dest_cell || "A3");
    const name = params.name || `Pivot_${Date.now() % 100000}`;
    const existing = destSheet.pivotTables.getItemOrNullObject(name);
    existing.load("name");
    await context.sync();
    if (!existing.isNullObject) {
      return { name, sheet: params.dest_sheet, existed: true };
    }
    const pt = destSheet.pivotTables.add(name, srcRange, destRange);
    pt.hierarchies.load("items/name");
    await context.sync();

    const available = pt.hierarchies.items.map((h) => h.name);
    const missing: string[] = [];
    const pick = (field: string) => {
      const exact = available.find((a) => a === field);
      const loose =
        exact || available.find((a) => a.toLowerCase().trim() === String(field).toLowerCase().trim());
      if (!loose) missing.push(field);
      return loose;
    };

    for (const f of params.rows || []) {
      const h = pick(f);
      if (h) pt.rowHierarchies.add(pt.hierarchies.getItem(h));
    }
    for (const f of params.columns || []) {
      const h = pick(f);
      if (h) pt.columnHierarchies.add(pt.hierarchies.getItem(h));
    }
    const agg = AGG[String(params.aggregation || "sum").toLowerCase()] || AGG.sum;
    for (const f of params.values || []) {
      const h = pick(f);
      if (h) {
        const dh = pt.dataHierarchies.add(pt.hierarchies.getItem(h));
        dh.summarizeBy = agg;
      }
    }
    await context.sync();
    return { name, sheet: params.dest_sheet, fields_available: available, fields_missing: missing };
  });
}

export async function execPivotAddField(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const sheet = await getWorksheetSafe(context, params.sheet, false);
    const pt = sheet.pivotTables.getItem(params.name);
    const hier = pt.hierarchies.getItem(params.field);
    if (params.area === "value") {
      const dh = pt.dataHierarchies.add(hier);
      dh.summarizeBy = AGG[String(params.aggregation || "sum").toLowerCase()] || AGG.sum;
    } else if (params.area === "column") {
      pt.columnHierarchies.add(hier);
    } else {
      pt.rowHierarchies.add(hier);
    }
    await context.sync();
    return { success: true, name: params.name, field: params.field, area: params.area };
  });
}

export async function execPivotRefresh(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const sheet = await getWorksheetSafe(context, params.sheet, false);
    sheet.pivotTables.getItem(params.name).refresh();
    await context.sync();
    return { success: true };
  });
}

export async function execChartCreate(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const srcSheet = await getWorksheetSafe(context, params.source_sheet, false);
    const range = srcSheet.getRange(params.source_address);
    const destName = params.dest_sheet || params.source_sheet;
    const destSheet = await getWorksheetSafe(context, destName, true);
    const type = (params.type || "ColumnClustered") as Excel.ChartType;
    const chart = destSheet.charts.add(type, range, "Auto" as Excel.ChartSeriesBy);
    if (params.title) chart.title.text = params.title;
    if (params.position) {
      chart.setPosition(destSheet.getRange(params.position));
    } else if (destName === params.source_sheet) {
      range.load("columnCount,rowIndex,columnIndex");
      await context.sync();
      chart.setPosition(
        srcSheet.getRangeByIndexes(range.rowIndex, range.columnIndex + range.columnCount + 1, 1, 1)
      );
    }
    chart.load("name");
    await context.sync();
    return { name: chart.name, sheet: destName, type };
  });
}


export async function execSlicerAdd(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const destSheet = await getWorksheetSafe(context, params.dest_sheet, true);
    const srcSheet = await getWorksheetSafe(context, params.source_sheet, false);
    const pivot = srcSheet.pivotTables.getItemOrNullObject(params.source_name);
    const table = srcSheet.tables.getItemOrNullObject(params.source_name);
    await context.sync();
    const source: any = !pivot.isNullObject ? pivot : !table.isNullObject ? table : null;
    if (!source) {
      throw { code: "SourceNotFound", message: `No table or pivot named ${params.source_name}` };
    }
    const slicer = destSheet.slicers.add(source, params.field);
    if (params.dest_cell) {
      const anchor = destSheet.getRange(params.dest_cell);
      anchor.load("left,top");
      await context.sync();
      slicer.left = anchor.left;
      slicer.top = anchor.top;
    }
    slicer.load("name");
    await context.sync();
    return { name: slicer.name, field: params.field };
  });
}

export async function execTableAddColumn(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const sheet = await getWorksheetSafe(context, params.sheet, false);
    const table = sheet.tables.getItem(params.table);
    const col = table.columns.add(undefined, undefined, params.column);
    if (params.formula) {
      const body = col.getDataBodyRange();
      body.load(["rowCount", "columnCount"]);
      await context.sync();
      const formula = params.formula;
      body.formulas = Array.from({ length: Math.max(1, body.rowCount) }, () => [formula]);
    }
    await context.sync();
    return { success: true, column: params.column };
  });
}

export async function execConditionalFormatAdd(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const sheet = await getWorksheetSafe(context, params.sheet, false);
    const range = sheet.getRange(params.address);
    const rule = params.rule || {};
    const kind = String(rule.type || "cellValue").toLowerCase().replace("_", "");
    const fill = rule.fill_color || rule.color || "#FFC7CE";
    let cf: Excel.ConditionalFormat;
    if (kind === "colorscale") {
      cf = range.conditionalFormats.add(Excel.ConditionalFormatType.colorScale);
      cf.colorScale.criteria = {
        minimum: { formula: null as any, type: Excel.ConditionalFormatColorCriterionType.lowestValue, color: rule.min_color || "#F8696B" },
        midpoint: { formula: "50", type: Excel.ConditionalFormatColorCriterionType.percentile, color: rule.mid_color || "#FFEB84" },
        maximum: { formula: null as any, type: Excel.ConditionalFormatColorCriterionType.highestValue, color: rule.max_color || "#63BE7B" },
      };
    } else if (kind === "databar") {
      cf = range.conditionalFormats.add(Excel.ConditionalFormatType.dataBar);
      cf.dataBar.barDirection = Excel.ConditionalDataBarDirection.leftToRight;
    } else if (kind === "formula" || kind === "custom") {
      cf = range.conditionalFormats.add(Excel.ConditionalFormatType.custom);
      cf.custom.rule.formula = rule.formula;
      cf.custom.format.fill.color = fill;
      if (rule.font_color) cf.custom.format.font.color = rule.font_color;
    } else {
      cf = range.conditionalFormats.add(Excel.ConditionalFormatType.cellValue);
      cf.cellValue.format.fill.color = fill;
      if (rule.font_color) cf.cellValue.format.font.color = rule.font_color;
      cf.cellValue.rule = {
        formula1: String(rule.formula1 ?? rule.value ?? "0"),
        formula2: rule.formula2 !== undefined ? String(rule.formula2) : undefined,
        operator: (rule.operator || "LessThan") as any,
      };
    }
    cf.load("id");
    await context.sync();
    return { id: cf.id, success: true };
  });
}

export async function execConditionalFormatClear(params: any): Promise<any> {
  return await Excel.run(async (context) => {
    const sheet = await getWorksheetSafe(context, params.sheet, false);
    sheet.getRange(params.address).conditionalFormats.clearAll();
    await context.sync();
    return { success: true };
  });
}
