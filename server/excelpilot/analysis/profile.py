import re
from typing import Any

import pandas as pd

from excelpilot.bridge.router import router


async def profile_sheet_columns(sheet_name: str) -> list[dict[str, Any]]:
    """Profile column distributions, detect numbers-as-text, and identify whitespace."""
    used = await router.used_range(sheet_name)
    data = await router.read(used, values=True)
    if not data.values or len(data.values) < 2:
        return []

    headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(data.values[0])]
    df = pd.DataFrame(data.values[1:], columns=headers)

    col_profiles: list[dict[str, Any]] = []

    for col in df.columns:
        series = df[col]
        non_null = series.dropna()

        # Check for numbers stored as text strings
        text_numbers = 0
        trailing_whitespace = 0
        for val in non_null:
            if isinstance(val, str):
                if re.match(r"^-?\d+(\.\d+)?$", val.strip()) and not val.isdigit():
                    text_numbers += 1
                if val != val.strip():
                    trailing_whitespace += 1

        col_profiles.append(
            {
                "column": col,
                "total_count": len(series),
                "null_count": int(series.isnull().sum()),
                "distinct_count": int(series.nunique()),
                "numbers_stored_as_text": text_numbers,
                "cells_with_whitespace": trailing_whitespace,
                "sample_values": [str(v) for v in non_null.unique()[:3]],
            }
        )

    return col_profiles
