import datetime
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import zstandard as zstd

from excelpilot.config import settings


class Store:
    """SQLite database for undo snapshots, audit trail, and daily cost tracking."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or (settings.resolved_data_dir / "excelpilot.sqlite")
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    sheet TEXT,
                    address TEXT,
                    values_blob BLOB,
                    formulas_blob BLOB,
                    numfmt_blob BLOB,
                    created_at TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TIMESTAMP,
                    session_id TEXT,
                    tool TEXT,
                    args_hash TEXT,
                    args_safe_view TEXT,
                    jev_backend TEXT,
                    jev_probs TEXT,
                    outcome TEXT,
                    snapshot_id TEXT,
                    model TEXT,
                    cost_usd REAL,
                    latency_ms REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS costs (
                    session_id TEXT,
                    day TEXT,
                    cost_usd REAL
                )
                """
            )
            conn.commit()

    def create_snapshot(
        self,
        session_id: str,
        sheet: str,
        address: str,
        values: list[list[Any]],
        formulas: list[list[Any]] | None = None,
        number_formats: list[list[Any]] | None = None,
    ) -> str:
        compressor = zstd.ZstdCompressor(level=3)
        v_bytes = compressor.compress(json.dumps(values).encode("utf-8"))
        f_bytes = compressor.compress(json.dumps(formulas or []).encode("utf-8"))
        n_bytes = compressor.compress(json.dumps(number_formats or []).encode("utf-8"))

        snap_id = f"snap_{int(datetime.datetime.now(datetime.UTC).timestamp()*1000)}"
        now = datetime.datetime.now(datetime.UTC)

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO snapshots (id, session_id, sheet, address, values_blob, formulas_blob, numfmt_blob, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (snap_id, session_id, sheet, address, v_bytes, f_bytes, n_bytes, now.isoformat()),
            )
            conn.commit()

        return snap_id

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)
            ).fetchone()
            if not row:
                return None

            decompressor = zstd.ZstdDecompressor()
            values = json.loads(decompressor.decompress(row["values_blob"]).decode("utf-8"))
            formulas = json.loads(decompressor.decompress(row["formulas_blob"]).decode("utf-8"))
            numfmt = json.loads(decompressor.decompress(row["numfmt_blob"]).decode("utf-8"))

            return {
                "id": row["id"],
                "session_id": row["session_id"],
                "sheet": row["sheet"],
                "address": row["address"],
                "values": values,
                "formulas": formulas,
                "number_formats": numfmt,
                "created_at": row["created_at"],
            }

    def record_audit(
        self,
        session_id: str,
        tool: str,
        args: dict[str, Any],
        outcome: str,
        jev_backend: str = "offline",
        jev_probs: dict[str, float] | None = None,
        snapshot_id: str | None = None,
        model: str = "",
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
    ) -> None:
        args_str = json.dumps(args, sort_keys=True)
        args_hash = hashlib.sha256(args_str.encode("utf-8")).hexdigest()[:16]
        # Keep safe preview for UI audit log
        safe_view = json.dumps({k: str(v)[:80] for k, v in args.items() if "secret" not in k})
        probs_str = json.dumps(jev_probs or {})
        now = datetime.datetime.now(datetime.UTC)

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO audit (ts, session_id, tool, args_hash, args_safe_view, jev_backend, jev_probs, outcome, snapshot_id, model, cost_usd, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now.isoformat(),
                    session_id,
                    tool,
                    args_hash,
                    safe_view,
                    jev_backend,
                    probs_str,
                    outcome,
                    snapshot_id,
                    model,
                    cost_usd,
                    latency_ms,
                ),
            )
            conn.commit()

    def record_cost(self, session_id: str, cost_usd: float) -> None:
        today = datetime.date.today().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO costs (session_id, day, cost_usd) VALUES (?, ?, ?)",
                (session_id, today, cost_usd),
            )
            conn.commit()

    def get_daily_cost(self) -> float:
        today = datetime.date.today().isoformat()
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT SUM(cost_usd) as total FROM costs WHERE day = ?", (today,)
            ).fetchone()
            if row and row["total"] is not None:
                return float(row["total"])
        return 0.0


store = Store()
