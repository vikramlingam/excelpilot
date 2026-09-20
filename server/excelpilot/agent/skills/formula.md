You are executing the Formula Authoring skill.

Operating principles:
1. Prefer modern Excel functions (XLOOKUP, FILTER, UNIQUE, LET, LAMBDA) when applicable.
2. If working inside an Excel table, prefer structured references like [@Revenue] or [Revenue].
3. For complex formulas, dry-run or verify on 2 or 3 sample rows before applying across the full column.
4. When diagnosing errors, clearly explain the cause:
   - #N/A: lookup value not found
   - #REF!: invalid cell reference
   - #VALUE!: wrong data type in argument
   - #DIV/0!: division by zero or empty cell
   - #SPILL!: blocked range for dynamic array
