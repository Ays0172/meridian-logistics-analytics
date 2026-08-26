"""Fact-table IO — Hive-partitioned Parquet writes, per SCHEMA_CONTRACT.md section 0.

Facts land as ``02_data/raw/<Name>/year=YYYY/month=MM/part-000.parquet``.
The partition columns are derived from the table's primary date key, named in
``PRIMARY_DATE_KEY``, and are *not* duplicated inside the file — Power Query's
folder-combine and Parquet's Hive-partition discovery both recover them from the
path, which is one of the things Day 4 has the learner prove.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .config import FACT_END_DATE, RAW_DIR, VALIDATION_DIR
from .util import child_rng

PRIMARY_DATE_KEY: dict[str, str] = {
    "FactBooking": "BookingDateKey",
    "FactShipment": "ShipmentDateKey",
    "FactShipmentMilestone": "BookingConfirmedDateKey",
    "FactContainerMove": "EventDateKey",
    "FactPortCall": "AtaDateKey",
    "FactFreightCharge": "ChargeDateKey",
    "FactTransportLeg": "ActualPickupDateKey",
    "FactWarehouseTask": "TaskDateKey",
    "FactInventorySnapshot": "SnapshotDateKey",
    "FactExchangeRate": "RateDateKey",
    "FactTarget": "TargetMonthDateKey",
}

COMPRESSION = "snappy"

HORIZON = pd.Timestamp(FACT_END_DATE)


def clip_and_trim(
    df: pd.DataFrame, date_col: str, target: int, *, label: str
) -> pd.DataFrame:
    """Drop rows dated after the horizon, then trim to exactly ``target`` rows.

    Two separate problems solved in one place:

    1. Events anchored to a shipment's arrival can land past the dataset's
       horizon. A snapshot taken on 2026-08-31 cannot contain an event dated
       September. Dropping those rows is also what creates genuinely in-flight
       shipments -- departed, not yet arrived -- which the model needs.
    2. Trimming must not be ``head(target)``. The builders sort by date, so
       taking the head would delete the most recent months wholesale and leave a
       dataset that just stops. Excess rows are dropped at random instead, from
       a seeded generator so the result stays reproducible.
    """
    keys = pd.to_numeric(df[date_col], errors="coerce")
    ts = pd.to_datetime(
        keys.where(keys > 0, 19000101).astype("int64").astype(str), format="%Y%m%d"
    )
    future = (keys > 0) & (ts > HORIZON)
    if future.any():
        df = df.loc[~future]

    if len(df) > target:
        rng = child_rng(f"clip:{label}")
        drop = rng.choice(len(df), size=len(df) - target, replace=False)
        keep = np.ones(len(df), dtype=bool)
        keep[drop] = False
        df = df.loc[keep]

    return df.reset_index(drop=True)


def _drop_internal(df: pd.DataFrame) -> pd.DataFrame:
    """Remove carry-forward columns; anything prefixed ``_`` is internal."""
    return df[[c for c in df.columns if not c.startswith("_")]]


def write_fact(
    df: pd.DataFrame,
    name: str,
    *,
    shuffle_columns_for: str | None = None,
    mode: str = "overwrite",
    append_stamp: str | None = None,
) -> dict:
    """Write a fact table as Hive-partitioned Parquet and return a manifest entry.

    ``mode`` is the difference between a rebuild and a live append, and getting
    it wrong is silent and destructive in both directions:

    ``"overwrite"``
        Delete the table's directory first, then write. Without this, a rebuild
        whose date coverage or row count differs from the previous one leaves the
        old partition files in place, and every reader sees BOTH generations
        unioned together — duplicate primary keys, orphaned foreign keys, rows
        past the horizon. This is what a rebuild must always do.

    ``"append"``
        Never touch an existing file. New rows go into a fresh
        ``part-NNN.parquet`` inside their partition, numbered after whatever is
        already there. This is what the daily feed must always do, so that
        yesterday's rows are physically incapable of being rewritten.

    ``shuffle_columns_for`` takes a ``"year=YYYY/month=MM"`` partition path and
    writes that one partition with its columns in a different order. This is
    landmine #9 from the contract: it proves Parquet resolves columns by name on
    read where a CSV union would silently misalign them.
    """
    if mode not in ("overwrite", "append"):
        raise ValueError(f"mode must be 'overwrite' or 'append', got {mode!r}")
    df = _drop_internal(df)
    date_col = PRIMARY_DATE_KEY[name]
    if date_col not in df.columns:
        raise KeyError(f"{name}: primary date key {date_col!r} not in frame")

    keys = df[date_col].to_numpy(dtype=np.int64)
    # Rows with a sentinel date key (-1) go to an explicit unknown partition
    # rather than being silently dropped.
    known = keys > 0
    years = np.where(known, keys // 10000, 1900).astype(int)
    months = np.where(known, (keys // 100) % 100, 1).astype(int)

    root = RAW_DIR / name
    if mode == "overwrite" and root.exists():
        shutil.rmtree(root)
    written: list[dict] = []
    total_bytes = 0

    for (yr, mo) in sorted(set(zip(years.tolist(), months.tolist()))):
        mask = (years == yr) & (months == mo)
        part = df.loc[mask]
        rel = f"year={yr:04d}/month={mo:02d}"
        if shuffle_columns_for == rel:
            cols = list(part.columns)
            part = part[cols[len(cols) // 2:] + cols[: len(cols) // 2]]
        out_dir = root / rel
        out_dir.mkdir(parents=True, exist_ok=True)
        if mode == "append":
            # Date-stamped, NOT sequentially numbered. Numbering by
            # ``len(existing)`` is quietly destructive: delete part-002 and the
            # next append computes index 3 and overwrites part-003, silently
            # replacing a different day's data. Stamping the file with the
            # business date it carries makes collisions impossible, makes a
            # single day's files identifiable from their names alone, and makes
            # a redo safe even if the watermark is lost.
            stamp = append_stamp or "unknown"
            seq = 0
            while (out_dir / f"part-{stamp}-{seq:02d}.parquet").exists():
                seq += 1
            path = out_dir / f"part-{stamp}-{seq:02d}.parquet"
        else:
            path = out_dir / "part-000.parquet"
        table = pa.Table.from_pandas(part, preserve_index=False)
        pq.write_table(table, path, compression=COMPRESSION)
        size = path.stat().st_size
        total_bytes += size
        written.append({"partition": rel, "rows": int(mask.sum()), "bytes": size})

    return {
        "table": name,
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns),
        "partitions": len(written),
        "bytes": total_bytes,
        "partition_detail": written,
    }


def write_manifest(entries: list[dict], filename: str = "facts_manifest.json") -> Path:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    path = VALIDATION_DIR / filename
    payload = {
        "tables": {e["table"]: {k: v for k, v in e.items() if k != "partition_detail"}
                   for e in entries},
        "total_rows": sum(e["rows"] for e in entries),
        "total_bytes": sum(e["bytes"] for e in entries),
    }
    path.write_text(json.dumps(payload, indent=2))
    return path


def load_dims() -> dict[str, pd.DataFrame]:
    """Read every built dimension back from ``02_data/raw``."""
    dims: dict[str, pd.DataFrame] = {}
    for d in sorted(RAW_DIR.iterdir()):
        if d.is_dir() and d.name.startswith("Dim"):
            dims[d.name] = pd.read_parquet(d / "part-000.parquet")
    if not dims:
        raise FileNotFoundError(
            f"No dimensions found under {RAW_DIR}. Run build_dims.py first."
        )
    return dims
