#!/usr/bin/env python3
"""CLI entry point for the Meridian dimension-layer generator.

Builds all 19 dimensions in SCHEMA_CONTRACT.md SS1 order (respecting the
inter-dimension dependencies -- e.g. DimVessel needs DimCarrier,
DimVoyage needs DimVessel/DimService/DimLocation), writes each to
`02_data/raw/<Dim>/part-000.parquet` + `02_data/reference/<Dim>.csv` via
`meridian.util.write_dim`, and records a manifest at
`meridian/dims_manifest.json`.

Usage:
    python build_dims.py --scale prod
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from meridian import config as cfg_module  # noqa: E402
from meridian import dims  # noqa: E402
from meridian import util  # noqa: E402


def _manifest_entry(df: pd.DataFrame, name: str) -> dict[str, Any]:
    return {
        "rows": int(len(df)),
        "cols": int(len(df.columns)),
        "columns": list(df.columns),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "sample_rows": util.sample_rows(df, n=3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Meridian dimension layer.")
    parser.add_argument("--scale", choices=["dev", "prod", "stress"], default="prod")
    args = parser.parse_args()

    cfg = cfg_module.load_config(args.scale)
    print(f"[build_dims] scale={cfg.scale} seed={cfg.seed}")

    manifest: dict[str, Any] = {"scale": cfg.scale, "seed": cfg.seed, "dimensions": {}}
    t_start = time.time()

    def build_and_write(name: str, df: pd.DataFrame, csv_df: pd.DataFrame | None = None) -> pd.DataFrame:
        t0 = time.time()
        info = util.write_dim(df, name, csv_df=csv_df)
        manifest["dimensions"][name] = _manifest_entry(df, name)
        print(f"  {name:16s} rows={info['rows']:>7,d} cols={info['cols']:>3d}  ({time.time() - t0:.2f}s)")
        return df

    print("Building independent dimensions...")
    build_and_write("DimDate", dims.build_dim_date(cfg))
    build_and_write("DimTime", dims.build_dim_time(cfg))
    build_and_write("DimCurrency", dims.build_dim_currency(cfg))
    build_and_write("DimIncoterm", dims.build_dim_incoterm(cfg))
    build_and_write("DimChargeType", dims.build_dim_charge_type(cfg))
    build_and_write("DimMode", dims.build_dim_mode(cfg))
    build_and_write("DimScenario", dims.build_dim_scenario(cfg))
    build_and_write("DimMilestone", dims.build_dim_milestone(cfg))
    build_and_write("DimEquipment", dims.build_dim_equipment(cfg))
    dim_commodity = build_and_write("DimCommodity", dims.build_dim_commodity(cfg))
    dim_location = build_and_write("DimLocation", dims.build_dim_location(cfg))

    print("Building dimensions with dependencies...")
    dim_carrier = build_and_write("DimCarrier", dims.build_dim_carrier(cfg))
    dim_vessel = build_and_write("DimVessel", dims.build_dim_vessel(cfg, dim_carrier))
    dim_service = build_and_write("DimService", dims.build_dim_service(cfg))
    build_and_write("DimVoyage", dims.build_dim_voyage(cfg, dim_vessel, dim_service, dim_location))
    dim_warehouse = build_and_write("DimWarehouse", dims.build_dim_warehouse(cfg, dim_location))
    dim_customer = build_and_write("DimCustomer", dims.build_dim_customer(cfg))
    dim_sku, dim_sku_csv = dims.build_dim_sku(cfg, dim_commodity, dim_customer)
    build_and_write("DimSku", dim_sku, csv_df=dim_sku_csv)
    build_and_write("DimEmployee", dims.build_dim_employee(cfg, dim_warehouse))

    manifest["total_seconds"] = round(time.time() - t_start, 2)
    manifest_path = Path(__file__).resolve().parent / "meridian" / "dims_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    print(f"[build_dims] wrote manifest to {manifest_path}")
    print(f"[build_dims] done in {manifest['total_seconds']}s")


if __name__ == "__main__":
    main()
