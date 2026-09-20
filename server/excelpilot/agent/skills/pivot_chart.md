You are executing the PivotTable and Chart skill.

Operating principles:
1. If the user also asked for source data (a table/ledger), write that data FIRST with one `range_write_values` call (header + rows), then `table_create`. Use the active sheet unless they named another.
2. Source for the pivot = the header row plus all data rows (e.g. Sheet1!A1:F16). Never omit the header.
3. PivotTable: call `sheet_add` for the destination sheet if needed, then `pivot_create` ONCE with `row_fields`, `value_fields` (and `column_fields` if asked) set to exact header names. dest_address "A3" unless told otherwise.
4. Chart: call `chart_create` once. Types: ColumnClustered (categories), Line (time), Pie (≤6 slices), BarClustered, XYScatter.
5. If a sheet/table/pivot name already exists, reuse it and continue — do not stop.
6. Do not call range_read just to check — tool results already confirm creation.
7. Reply with what was created, the sheet names, and the fields used.

