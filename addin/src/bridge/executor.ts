/* global Excel */
import {
  execFormatNumber,
  execFormatRange,
  execRangeClear,
  execRangeRead,
  execRangeWrite,
} from "./executor_ranges";
import {
  execChartCreate,
  execConditionalFormatAdd,
  execConditionalFormatClear,
  execPivotAddField,
  execPivotCreate,
  execPivotRefresh,
  execSlicerAdd,
  execTableAddColumn,
} from "./executor_objects";
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
        const wanted = params.name ? String(params.name) : "";
        if (wanted) {
          const existing = context.workbook.worksheets.getItemOrNullObject(wanted);
          existing.load(["name", "position"]);
          await context.sync();
          if (!existing.isNullObject) {
            return { name: existing.name, index: existing.position, visibility: "visible", existed: true };
          }
        }
        const s = context.workbook.worksheets.add(wanted || undefined);
        s.load(["name", "position"]);
        await context.sync();
        return { name: s.name, index: s.position, visibility: "visible", existed: false };
      });

    case "bridge.sheet.delete":
      return await Excel.run(async (context) => {
        const sheet = await getWorksheetSafe(context, params.sheet, false);
        sheet.delete();
        await context.sync();
        return { success: true };
      });

    case "bridge.workbook.reset":
      return await Excel.run(async (context) => {
        const keepName = params.keep_name || "Sheet1";
        const sheets = context.workbook.worksheets;
        sheets.load("items/name");
        await context.sync();
        const names = sheets.items.map((s) => s.name);
        let keeper = sheets.getItemOrNullObject(keepName);
        keeper.load("name");
        await context.sync();
        if (keeper.isNullObject) {
          keeper = sheets.add(keepName);
          await context.sync();
        }
        keeper.getUsedRangeOrNullObject().clear();
        const deleted: string[] = [];
        for (const n of names) {
          if (n !== keeper.name) {
            sheets.getItem(n).delete();
            deleted.push(n);
          }
        }
        keeper.activate();
        await context.sync();
        return { success: true, kept: keeper.name, deleted };
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
        if (params.name) {
          const existing = sheet.tables.getItemOrNullObject(params.name);
          existing.load("name");
          await context.sync();
          if (!existing.isNullObject) {
            return { name: existing.name, existed: true };
          }
        }
        const range = sheet.getRange(params.address);
        const table = sheet.tables.add(range, params.has_headers ?? true);
        if (params.name) table.name = params.name;
        table.load("name");
        await context.sync();
        return { name: table.name, existed: false };
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
      return await execPivotCreate(params);

    case "bridge.pivot.add_field":
      return await execPivotAddField(params);

    case "bridge.pivot.refresh":
      return await execPivotRefresh(params);

    case "bridge.slicer.add":
      return await execSlicerAdd(params);

    case "bridge.table.add_column":
      return await execTableAddColumn(params);

    case "bridge.format.conditional_add":
      return await execConditionalFormatAdd(params);

    case "bridge.format.conditional_clear":
      return await execConditionalFormatClear(params);

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
      return await execChartCreate(params);

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

    case "bridge.sheet.rename":
      return await Excel.run(async (context) => {
        const sheet = await getWorksheetSafe(context, params.old_name, false);
        sheet.name = params.new_name;
        sheet.load(["name", "position"]);
        await context.sync();
        return { name: sheet.name, index: sheet.position, visibility: "visible" };
      });

    case "bridge.sheet.set_visibility":
      return await Excel.run(async (context) => {
        const sheet = await getWorksheetSafe(context, params.sheet, false);
        sheet.visibility = params.visible ? "Visible" : "Hidden";
        await context.sync();
        return { success: true };
      });

    case "bridge.validation.add":
      return await Excel.run(async (context) => {
        const sheet = await getWorksheetSafe(context, params.sheet, false);
        const range = sheet.getRange(params.address);
        const rule = params.rule || {};
        const t = String(rule.type || "list").toLowerCase();
        if (t === "list") {
          range.dataValidation.rule = { list: { inCellDropDown: true, source: rule.formula1 } };
        } else if (t === "wholenumber" || t === "whole_number" || t === "decimal") {
          const key = t === "decimal" ? "decimal" : "wholeNumber";
          range.dataValidation.rule = {
            [key]: { formula1: rule.formula1, formula2: rule.formula2, operator: rule.operator || "Between" },
          } as any;
        } else if (t === "date") {
          range.dataValidation.rule = {
            date: { formula1: rule.formula1, formula2: rule.formula2, operator: rule.operator || "Between" },
          } as any;
        } else {
          range.dataValidation.rule = { custom: { formula: rule.formula1 } };
        }
        await context.sync();
        return { success: true };
      });

    case "bridge.view.screenshot":
      return await Excel.run(async (context) => {
        const target = String(params.target || "");
        const sheetName = target.includes("!") ? target.split("!")[0].replace(/'/g, "") : target;
        const addr = target.includes("!") ? target.split("!")[1] : null;
        const sheet = await getWorksheetSafe(context, sheetName, false);
        const range = addr ? sheet.getRange(addr) : sheet.getUsedRange();
        const img = range.getImage();
        await context.sync();
        return { image_bytes: img.value };
      });

    default:
      throw { code: "MethodNotSupported", message: `Bridge method ${method} is not implemented in the add-in` };
  }
}
