from typing import Any

import duckdb
import pandas as pd

from excelpilot.bridge.router import router


async def sheet_sql(sheet: str, query: str) -> list[dict[str, Any]]:
    """Execute a read-only SQL query over a sheet using in-memory DuckDB."""
    used = await router.used_range(sheet)
    data = await router.read(used, values=True)
    if not data.values or len(data.values) < 2:
        return []

    headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(data.values[0])]
    df = pd.DataFrame(data.values[1:], columns=headers)

    conn = duckdb.connect(":memory:")
    conn.register(sheet, df)
    res_df = conn.execute(query).fetchdf()
    return res_df.to_dict(orient="records")


async def sheet_profile(sheet: str) -> dict[str, Any]:
    """Compute per-column profile including types, null counts, and distinct value counts."""
    used = await router.used_range(sheet)
    data = await router.read(used, values=True)
    if not data.values or len(data.values) < 2:
        return {"columns": []}

    headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(data.values[0])]
    df = pd.DataFrame(data.values[1:], columns=headers)

    profile_cols = []
    for col in df.columns:
        s = df[col]
        profile_cols.append(
            {
                "column": col,
                "null_count": int(s.isnull().sum()),
                "distinct_count": int(s.nunique()),
                "sample_values": [str(v) for v in s.dropna().unique()[:3]],
            }
        )

    return {"sheet": sheet, "total_rows": len(df), "columns": profile_cols}
