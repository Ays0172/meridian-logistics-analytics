"""Build every fact table and land it as Hive-partitioned Parquet.

    python build_facts.py --scale prod

Order is not negotiable and is enforced below:

    FactExchangeRate      money conversion for everything downstream
      -> FactBooking      the commercial funnel starts here
      -> FactShipment     only confirmed and rolled bookings sail
      -> FactShipmentMilestone   accumulating snapshot over those shipments
      -> FactPortCall     independent of shipments, needs revised rotations
      -> FactContainerMove  needs shipments for journey anchors
      -> FactFreightCharge  needs shipments AND container moves, so that a
                            demurrage line only exists where a box ran past
                            free time
      -> FactTransportLeg / FactWarehouseTask / FactInventorySnapshot / FactTarget
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd
import yaml

from meridian import factio
from meridian.factio import PRIMARY_DATE_KEY, clip_and_trim
from meridian.config import CONFIG_DIR, VALIDATION_DIR
from meridian.facts_core import (
    build_fact_booking,
    build_fact_exchange_rate,
    build_fact_shipment,
    build_fact_shipment_milestone,
)
from meridian.facts_land import (
    build_fact_inventory_snapshot,
    build_fact_target,
    build_fact_transport_leg,
    build_fact_warehouse_task,
)
from meridian.facts_ops import (
    build_fact_container_move,
    build_fact_freight_charge,
    build_fact_port_call,
)

# The revision in revise_voyage_rotations.py must have been applied, or
# FactPortCall silently caps at ~31k rows. Fail loudly instead.
MIN_MEAN_ROTATION_LENGTH = 9.0

# Landmine #9: one partition is written with its columns reordered, to prove
# Parquet resolves by name where a CSV union would misalign silently.
SHUFFLED_PARTITION = ("FactContainerMove", "year=2023/month=07")


def _load_scale(scale: str) -> dict[str, int]:
    cfg = yaml.safe_load((CONFIG_DIR / "scale.yaml").read_text())
    if scale not in cfg["scales"]:
        raise SystemExit(f"Unknown scale {scale!r}; choose from {list(cfg['scales'])}")
    return cfg["scales"][scale]["facts"]


def _assert_rotations_revised(dims: dict[str, pd.DataFrame]) -> None:
    voy = dims["DimVoyage"]
    voy = voy[voy["VoyageKey"] > 0]
    mean_len = voy["RotationString"].fillna("").str.split("-").map(len).mean()
    if mean_len < MIN_MEAN_ROTATION_LENGTH:
        raise SystemExit(
            f"DimVoyage rotations average {mean_len:.2f} ports, below the "
            f"{MIN_MEAN_ROTATION_LENGTH} minimum. Run:\n"
            "    python revise_voyage_rotations.py\n"
            "See 00_docs/ADR/ADR-001-voyage-rotation-length.md"
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="prod", choices=["dev", "prod", "stress"])
    args = ap.parse_args()

    targets = _load_scale(args.scale)
    t_all = time.time()

    print(f"Loading dimensions ...")
    dims = factio.load_dims()
    _assert_rotations_revised(dims)
    print(f"  {len(dims)} dimensions loaded")

    entries: list[dict] = []
    timings: dict[str, float] = {}

    # Builders are asked for slightly more rows than the target, because clipping
    # to the horizon removes rows whose dates spill past the dataset's end. The
    # inflation factors are the observed clip rates plus a small margin.
    INFLATE = {
        "FactShipment": 1.03, "FactPortCall": 1.04, "FactContainerMove": 1.04,
        "FactFreightCharge": 1.03, "FactTransportLeg": 1.03,
    }

    def ask(name: str) -> int:
        return int(round(targets[name] * INFLATE.get(name, 1.0)))

    def finalise(name: str, df: pd.DataFrame) -> pd.DataFrame:
        """Clip to horizon and trim to target. Must run BEFORE the frame is
        handed to any downstream builder: FactShipment is the parent of five
        other facts, and clipping it after they had already referenced it left
        thousands of orphaned ShipmentKeys pointing at rows that no longer
        existed."""
        return clip_and_trim(df, PRIMARY_DATE_KEY[name], targets[name], label=name)

    def emit(name: str, df: pd.DataFrame, started: float) -> None:
        shuffle = SHUFFLED_PARTITION[1] if name == SHUFFLED_PARTITION[0] else None
        entry = factio.write_fact(df, name, shuffle_columns_for=shuffle)
        entries.append(entry)
        timings[name] = round(time.time() - started, 1)
        target = targets.get(name, 0)
        pct = f"{entry['rows'] / target * 100:5.1f}%" if target else "    --"
        print(
            f"  {name:24s} {entry['rows']:>9,} rows  {entry['columns']:>3} cols  "
            f"{entry['partitions']:>3} parts  {entry['bytes'] / 1e6:>7.1f} MB  "
            f"{pct} of target  {timings[name]:>6.1f}s"
        )

    print(f"\nBuilding facts at scale={args.scale}")

    t = time.time(); fx = build_fact_exchange_rate(dims); emit("FactExchangeRate", fx, t)
    t = time.time(); bk = finalise("FactBooking", build_fact_booking(dims, fx, targets["FactBooking"])); emit("FactBooking", bk, t)
    t = time.time()
    sh = finalise("FactShipment", build_fact_shipment(dims, bk, fx, ask("FactShipment")))
    emit("FactShipment", sh, t)
    t = time.time(); ms = finalise("FactShipmentMilestone", build_fact_shipment_milestone(dims, sh, bk)); emit("FactShipmentMilestone", ms, t)
    t = time.time(); pc = finalise("FactPortCall", build_fact_port_call(dims, ask("FactPortCall"))); emit("FactPortCall", pc, t)
    t = time.time(); cm = finalise("FactContainerMove", build_fact_container_move(dims, sh, ask("FactContainerMove"))); emit("FactContainerMove", cm, t)
    t = time.time(); fc = finalise("FactFreightCharge", build_fact_freight_charge(dims, sh, cm, fx, ask("FactFreightCharge"))); emit("FactFreightCharge", fc, t)
    t = time.time(); tl = finalise("FactTransportLeg", build_fact_transport_leg(dims, sh, ask("FactTransportLeg"))); emit("FactTransportLeg", tl, t)
    t = time.time(); wt = finalise("FactWarehouseTask", build_fact_warehouse_task(dims, sh, targets["FactWarehouseTask"])); emit("FactWarehouseTask", wt, t)
    t = time.time(); iv = finalise("FactInventorySnapshot", build_fact_inventory_snapshot(dims, targets["FactInventorySnapshot"])); emit("FactInventorySnapshot", iv, t)
    t = time.time(); tg = finalise("FactTarget", build_fact_target(dims, targets["FactTarget"])); emit("FactTarget", tg, t)

    manifest = factio.write_manifest(entries)
    total_rows = sum(e["rows"] for e in entries)
    total_mb = sum(e["bytes"] for e in entries) / 1e6

    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    (VALIDATION_DIR / "build_timings.json").write_text(
        json.dumps({"scale": args.scale, "seconds": timings}, indent=2)
    )

    print(
        f"\n{total_rows:,} fact rows  ·  {total_mb:,.1f} MB Parquet  ·  "
        f"{time.time() - t_all:.1f}s total"
    )
    print(f"manifest: {manifest}")


if __name__ == "__main__":
    main()
