/* global Excel */
import {
  execFormatNumber,
  execFormatRange,
  execRangeClear,
  execRangeRead,
  execRangeWrite,
} from "./executor_ranges";

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
        const sheet = context.workbook.worksheets.getItem(params.sheet);
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
        const s = context.workbook.worksheets.getItem(params.sheet);
        s.delete();
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
        const sheet = context.workbook.worksheets.getItem(params.sheet);
        const range = sheet.getRange(params.address);
        const table = sheet.tables.add(range, params.has_headers ?? true);
        if (params.name) table.name = params.name;
        table.load("name");
        await context.sync();
        return { name: table.name };
      });

    case "bridge.table.list":
      return await Excel.run(async (context) => {
        const sheet = context.workbook.worksheets.getItem(params.sheet);
        const tables = sheet.tables;
        tables.load("items/name,items/id");
        await context.sync();
        return tables.items.map((t) => ({ name: t.name, id: t.id }));
      });

    case "bridge.chart.create":
      return await Excel.run(async (context) => {
        const sheet = context.workbook.worksheets.getItem(params.source_sheet);
        const range = sheet.getRange(params.source_address);
        const chart = sheet.charts.add(params.type || "ColumnClustered", range, "Auto");
        if (params.title) chart.title.text = params.title;
        chart.load("name");
        await context.sync();
        return { name: chart.name };
      });

    case "bridge.chart.list":
      return await Excel.run(async (context) => {
        const sheet = context.workbook.worksheets.getItem(params.sheet);
        const charts = sheet.charts;
        charts.load("items/name,items/id");
        await context.sync();
        return charts.items.map((c) => ({ name: c.name, id: c.id }));
      });

    case "bridge.format.range":
      return await execFormatRange(params);

    case "bridge.format.number":
      return await execFormatNumber(params);

    case "bridge.view.select":
      return await Excel.run(async (context) => {
        const sheet = context.workbook.worksheets.getItem(params.sheet);
        const range = sheet.getRange(params.address);
        range.select();
        await context.sync();
        return { success: true };
      });

    case "bridge.view.highlight":
      return await Excel.run(async (context) => {
        const sheet = context.workbook.worksheets.getItem(params.sheet);
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

    default:
      throw { code: "MethodNotFound", message: `Bridge method ${method} not implemented` };
  }
}
