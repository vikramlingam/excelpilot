/* global Excel */
import {
  execFormatNumber,
  execFormatRange,
  execRangeClear,
  execRangeRead,
  execRangeWrite,
} from "./executor_ranges";
import { getWorksheetSafe } from "./helpers";

export async function executeBridgeCall(method: string, params: any): Promise<any> {
  switch (method) {
    case "bridge.workbook.info":
      return await Excel.run(async (context) => {
        const sheets = context.workbook.worksheets;
        sheets.load("items/name,items/visibility");
        await context.sync();
        return {
          name: "ActiveWorkbook.xlsx",
          sheet_count: sheets.items.length,
          sheets: sheets.items.map((s, idx) => ({
            name: s.name,
            index: idx,
            visibility: s.visibility === "Visible" ? "visible" : "hidden",
          })),
        };
      });

    case "bridge.sheet.list":
      return await Excel.run(async (context) => {
        const sheets = context.workbook.worksheets;
        sheets.load("items/name,items/visibility");
        await context.sync();
        return sheets.items.map((s, idx) => ({
          name: s.name,
          index: idx,
          visibility: s.visibility === "Visible" ? "visible" : "hidden",
        }));
      });

    case "bridge.sheet.used_range":
      return await Excel.run(async (context) => {
        const sheet = await getWorksheetSafe(context, params.sheet, false);
        const used = sheet.getUsedRange();
        used.load("address");
        await context.sync();
        return { address: used.address.replace(/.*!/, "") };
      });

    case "bridge.sheet.add":
      return await Excel.run(async (context) => {
        const s = context.workbook.worksheets.add(params.name);
        s.load(["name", "position"]);
        await context.sync();
        return { name: s.name, index: s.position, visibility: "visible" };
      });

    case "bridge.sheet.delete":
      return await Excel.run(async (context) => {
        const sheet = await getWorksheetSafe(context, params.sheet, false);
        sheet.delete();
        await context.sync();
        return { success: true };
      });

    case "bridge.range.read":
      return await execRangeRead(params);

    case "bridge.range.write":
      return await execRangeWrite(params);

    case "bridge.range.clear":
      return await execRangeClear(params);

    case "bridge.table.create":
      return await Excel.run(async (context) => {
        const sheet = await getWorksheetSafe(context, params.sheet, true);
        const range = sheet.getRange(params.address);
        const table = sheet.tables.add(range, params.has_headers ?? true);
        if (params.name) table.name = params.name;
        table.load("name");
        await context.sync();
        return { name: table.name };
      });

    case "bridge.table.list":
      return await Excel.run(async (context) => {
        try {
          const sheet = await getWorksheetSafe(context, params.sheet, false);
          const tables = sheet.tables;
          tables.load("items/name,items/id");
          await context.sync();
          return tables.items.map((t) => ({ name: t.name, id: t.id }));
        } catch {
          return [];
        }
      });

    case "bridge.pivot.create":
      return await Excel.run(async (context) => {
        const srcSheet = await getWorksheetSafe(context, params.source_sheet, false);
        const srcRange = srcSheet.getRange(params.source_address);
        const destSheet = await getWorksheetSafe(context, params.dest_sheet, true);
        const destRange = destSheet.getRange(params.dest_cell || "A3");
        const pt = destSheet.pivotTables.add(params.name || "PivotTable1", srcRange, destRange);
        if (params.rows && Array.isArray(params.rows)) {
          for (const row of params.rows) {
            pt.rowHierarchies.add(pt.hierarchies.getItem(row));
          }
        }
        if (params.values && Array.isArray(params.values)) {
          for (const val of params.values) {
            pt.dataHierarchies.add(pt.hierarchies.getItem(val));
          }
        }
        pt.load("name");
        await context.sync();
        return { name: pt.name };
      });

    case "bridge.pivot.list":
      return await Excel.run(async (context) => {
        try {
          const sheet = await getWorksheetSafe(context, params.sheet, false);
          const pivots = sheet.pivotTables;
          pivots.load("items/name,items/id");
          await context.sync();
          return pivots.items.map((p) => ({ name: p.name, id: p.id }));
        } catch {
          return [];
        }
      });

    case "bridge.chart.create":
      return await Excel.run(async (context) => {
        const sheet = await getWorksheetSafe(context, params.source_sheet, false);
        const range = sheet.getRange(params.source_address);
        const chart = sheet.charts.add(params.type || "ColumnClustered", range, "Auto");
        if (params.title) chart.title.text = params.title;
        chart.load("name");
        await context.sync();
        return { name: chart.name };
      });

    case "bridge.chart.list":
      return await Excel.run(async (context) => {
        try {
          const sheet = await getWorksheetSafe(context, params.sheet, false);
          const charts = sheet.charts;
          charts.load("items/name,items/id");
          await context.sync();
          return charts.items.map((c) => ({ name: c.name, id: c.id }));
        } catch {
          return [];
        }
      });

    case "bridge.format.range":
      return await execFormatRange(params);

    case "bridge.format.number":
      return await execFormatNumber(params);

    case "bridge.view.select":
      return await Excel.run(async (context) => {
        const sheet = await getWorksheetSafe(context, params.sheet, false);
        const range = sheet.getRange(params.address);
        range.select();
        await context.sync();
        return { success: true };
      });

    case "bridge.view.highlight":
      return await Excel.run(async (context) => {
        const sheet = await getWorksheetSafe(context, params.sheet, false);
        const range = sheet.getRange(params.address);
        range.format.fill.color = params.color || "#FFF2B2";
        await context.sync();
        return { success: true };
      });

    case "bridge.script.run":
      return await Excel.run(async (context) => {
        // Execute dynamic TypeScript script inside Excel context
        const fn = new Function("context", "args", params.code);
        const result = await fn(context, params.args || {});
        await context.sync();
        return { success: true, output: JSON.stringify(result) };
      });

    case "bridge.format.autofit":
      return await Excel.run(async (context) => {
        const sheet = await getWorksheetSafe(context, params.sheet, false);
        const range = sheet.getRange(params.address);
        range.format.autofitColumns();
        range.format.autofitRows();
        await context.sync();
        return { success: true };
      });

    case "bridge.name.define":
      return await Excel.run(async (context) => {
        context.workbook.names.add(params.name, `${params.sheet}!${params.address}`);
        await context.sync();
        return { success: true };
      });

    case "bridge.name.list":
      return await Excel.run(async (context) => {
        try {
          const names = context.workbook.names;
          names.load("items/name,items/value");
          await context.sync();
          return names.items.map((n) => ({ name: n.name, value: n.value }));
        } catch {
          return [];
        }
      });

    case "bridge.comment.add":
      return await Excel.run(async (context) => {
        const sheet = await getWorksheetSafe(context, params.sheet, false);
        sheet.comments.add(params.cell, params.text);
        await context.sync();
        return { success: true };
      });

    case "bridge.view.freeze_panes":
      return await Excel.run(async (context) => {
        const sheet = await getWorksheetSafe(context, params.sheet, false);
        sheet.freezePanes.freezeRows(params.row || 1);
        await context.sync();
        return { success: true };
      });

    default:
      console.warn(`Bridge method ${method} not explicitly handled, returning empty success`);
      return { success: true };
  }
}
