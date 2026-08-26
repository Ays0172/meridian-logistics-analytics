"""Landside, warehouse and planning fact builders — SCHEMA_CONTRACT.md §2.7–2.9, 2.11.

    FactTransportLeg  ·  FactWarehouseTask  ·  FactInventorySnapshot  ·  FactTarget

The warehouse facts carry the structural quality effects of §3.4 — night shift
and new agency staff are measurably less accurate — so that "which shift has a
problem?" has a real answer rather than a random one.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import (
    CONGESTION_END_DATE as CONGESTION_END,
    CONGESTION_LOCATIONS as CONGESTION_PORTS,
    CONGESTION_START_DATE as CONGESTION_START,
    FACT_END_DATE as CALENDAR_END,
    FACT_START_DATE as CALENDAR_START,
)
from .util import child_rng, to_date_key

# --------------------------------------------------------------------------- #
# Transport leg — §2.7
# --------------------------------------------------------------------------- #

DRAYAGE_DISTANCE_KM = (18.0, 420.0)
RAIL_DISTANCE_KM = (250.0, 2200.0)
RAIL_SHARE = 0.22
EMPTY_LEG_SHARE = 0.19          # legs that are pure empty repositioning
COST_PER_KM_ROAD_USD = (0.85, 2.35)
COST_PER_KM_RAIL_USD = (0.28, 0.72)
FUEL_SURCHARGE_SHARE = (0.08, 0.24)
TOLL_SHARE = (0.0, 0.09)
ACCESSORIAL_SHARE = (0.0, 0.16)
AVG_SPEED_KMH_ROAD = (38.0, 68.0)
AVG_SPEED_KMH_RAIL = (22.0, 45.0)
LITRES_PER_100KM = (28.0, 42.0)
CO2_KG_PER_LITRE_DIESEL = 2.68

ON_TIME_PICKUP_TARGET = 0.902
ON_TIME_DELIVERY_TARGET = 0.887
FIRST_ATTEMPT_TARGET = 0.941
PICKUP_WINDOW_HOURS = 2.0
DELIVERY_WINDOW_HOURS = 4.0
SUBCONTRACT_SHARE = 0.38

TURN_TIME_MINUTES_MEAN = 78.0
CONGESTION_TURN_TIME_MULTIPLIER = 1.7
GATE_WAIT_MINUTES_MEAN = 26.0

# Deadhead: the share of total distance run empty. Higher on backhaul-poor lanes.
DEADHEAD_SHARE = (0.03, 0.22)

# --------------------------------------------------------------------------- #
# Warehouse task — §2.8
# --------------------------------------------------------------------------- #

TASK_TYPE_MIX = {
    "Pick": 0.42,
    "Putaway": 0.14,
    "Receive": 0.13,
    "Pack": 0.13,
    "Load": 0.09,
    "Replenish": 0.05,
    "Cycle Count": 0.03,
    "VAS": 0.01,
}

# §3.4 accuracy structure. These three numbers are the answer to the Week 4
# exercise, and they must be recoverable from the data rather than asserted.
PICK_ACCURACY_BASE = 0.991
PICK_ACCURACY_NIGHT_SHIFT = 0.974
PICK_ACCURACY_NEW_AGENCY = 0.982

LINES_PER_HOUR_BY_ROLE = {
    "Picker": 62.0,
    "Packer": 48.0,
    "Forklift Operator": 26.0,
    "Receiver": 34.0,
    "Checker": 55.0,
    "Team Lead": 30.0,
    "Supervisor": 14.0,
}
LINES_PER_HOUR_CV = 0.18
TENURE_PRODUCTIVITY = {
    "<6m": 0.82, "6–12m": 0.93, "1–2y": 1.00, "2–5y": 1.06, "5y+": 1.09,
}
LABOUR_COST_PER_HOUR_USD = (3.10, 9.40)
DOCK_TO_STOCK_MINUTES = (35.0, 340.0)
REWORK_RATE = 0.021
DAMAGE_ON_HANDLING_RATE = 0.004
SLA_RATE = 0.943

# --------------------------------------------------------------------------- #
# Inventory snapshot — §2.9
# --------------------------------------------------------------------------- #

DAILY_SNAPSHOT_MONTHS = 12       # most recent 12 months daily
WEEKLY_SNAPSHOT_MONTHS = 30      # the older period weekly
CYCLE_COUNT_DAY_OF_MONTH = 15
SHRINKAGE_RATE = 0.0016
OBSOLETE_RATE = 0.014
STOCKOUT_RATE = 0.037
OVERSTOCK_RATE = 0.092
INVENTORY_ACCURACY_TARGET = 0.9962

# --------------------------------------------------------------------------- #
# Target — §2.11
# --------------------------------------------------------------------------- #

TARGET_KPIS: tuple[tuple[str, str, str, int], ...] = (
    # code, name, unit, higher_is_better
    ("OCN.VOL.FFE", "FFE Volume", "FFE", 1),
    ("OCN.REV.FFE", "Revenue per FFE", "USD", 1),
    ("OCN.REL.SCHED", "Schedule Reliability", "Pct", 1),
    ("OCN.UTL.SLOT", "Slot Utilisation", "Pct", 1),
    ("OCN.OPS.ROLL", "Rollover Ratio", "Pct", 0),
    ("OCN.OPS.DWELL", "Container Port Dwell Hours", "Hours", 0),
    ("LND.CST.KM", "Cost per km", "USD", 0),
    ("LND.SVC.OTD", "On-Time Delivery", "Pct", 1),
    ("LND.UTL.DEADHEAD", "Deadhead Percentage", "Pct", 0),
    ("LND.UTL.EMPTYREPO", "Empty Repositioning Ratio", "Pct", 0),
    ("WHS.OPS.D2S", "Dock-to-Stock Minutes", "Days", 0),
    ("WHS.QLT.PICKACC", "Pick Accuracy", "Pct", 1),
    ("WHS.PRD.LPH", "Lines per Labour Hour", "Count", 1),
    ("WHS.QLT.OTIF", "OTIF", "Pct", 1),
    ("AIR.REV.YIELDKG", "Yield per kg", "USD", 1),
    ("XCT.QLT.PERFECT", "Perfect Order Rate", "Pct", 1),
    ("XCT.FIN.FCR", "Freight Cost as % of Revenue", "Pct", 0),
)
STRETCH_UPLIFT = 0.08
THRESHOLD_HAIRCUT = 0.12


def _congested_keys(locations: pd.DataFrame) -> np.ndarray:
    return locations[locations["LocationCode"].isin(CONGESTION_PORTS)][
        "LocationKey"
    ].to_numpy(np.int32)


def build_fact_transport_leg(
    dims: dict[str, pd.DataFrame], shipments: pd.DataFrame, n_rows: int
) -> pd.DataFrame:
    """One truck or rail movement — §2.7. Transaction grain.

    ``DeadheadPct`` is deliberately NOT stored: it is a ratio, and storing a
    ratio on a transaction fact invites someone to average it. ``LoadedKm`` and
    ``EmptyKm`` are stored instead, because those are additive and the ratio can
    be recomputed correctly at any grain.
    """
    rng = child_rng("FactTransportLeg")
    locations = dims["DimLocation"]
    carriers = dims["DimCarrier"]
    warehouses = dims["DimWarehouse"]
    congested = _congested_keys(locations)

    n_linked = int(round(n_rows * (1.0 - EMPTY_LEG_SHARE)))
    n_empty = n_rows - n_linked

    ocean = shipments[~shipments["_is_air"].to_numpy(dtype=bool)]
    pick = rng.choice(len(ocean), size=n_linked, replace=True)
    src = ocean.iloc[pick]

    haulier_types = ["Road Haulier", "Drayage", "Rail Operator"]
    pool = carriers[carriers["CarrierType"].isin(haulier_types)]
    if pool.empty:
        pool = carriers[carriers["CarrierKey"] > 0]
    carrier_pool = pool["CarrierKey"].to_numpy(np.int32)

    inland = locations[
        (locations["LocationKey"] > 0)
        & (locations["LocationType"].isin(["Inland Depot", "CFS", "Rail Terminal", "Warehouse"]))
    ]["LocationKey"].to_numpy(np.int32)
    if len(inland) == 0:
        inland = locations[locations["LocationKey"] > 0]["LocationKey"].to_numpy(np.int32)

    # ---- legs tied to a shipment: port <-> inland
    pod = src["LocationKeyPod"].to_numpy(np.int32)
    linked = pd.DataFrame(
        {
            "ShipmentKey": src["ShipmentKey"].to_numpy(np.int64),
            "LocationKeyOrigin": pod,
            "LocationKeyDestination": rng.choice(inland, size=n_linked, replace=True),
            "CustomerKey": src["CustomerKey"].to_numpy(np.int32),
            "EquipmentKey": src["EquipmentKey"].to_numpy(np.int32),
            "CurrencyKey": src["CurrencyKey"].to_numpy(np.int32),
            "WeightKg": src["GrossWeightKg"].to_numpy(np.float64),
            "Teu": src["Teu"].to_numpy(np.float64),
            "_base": pd.DatetimeIndex(src["_ata"]),
            "IsEmptyRepositioning": np.zeros(n_linked, dtype=np.int8),
        }
    )

    # ---- standalone empty repositioning legs
    days = rng.integers(
        0, (pd.Timestamp(CALENDAR_END) - pd.Timestamp(CALENDAR_START)).days, size=n_empty
    )
    empty = pd.DataFrame(
        {
            "ShipmentKey": np.full(n_empty, -1, dtype=np.int64),
            "LocationKeyOrigin": rng.choice(inland, size=n_empty, replace=True),
            "LocationKeyDestination": rng.choice(inland, size=n_empty, replace=True),
            "CustomerKey": np.full(n_empty, -1, dtype=np.int32),
            "EquipmentKey": rng.choice(
                dims["DimEquipment"][dims["DimEquipment"]["EquipmentKey"] > 0][
                    "EquipmentKey"
                ].to_numpy(np.int32),
                size=n_empty,
                replace=True,
            ),
            "CurrencyKey": np.full(
                n_empty,
                int(dims["DimCurrency"].query("CurrencyCode == 'USD'")["CurrencyKey"].iloc[0]),
                dtype=np.int32,
            ),
            "WeightKg": np.zeros(n_empty),
            "Teu": np.ones(n_empty),
            "_base": pd.Timestamp(CALENDAR_START) + pd.to_timedelta(days, unit="D"),
            "IsEmptyRepositioning": np.ones(n_empty, dtype=np.int8),
        }
    )

    df = pd.concat([linked, empty], ignore_index=True)
    n = len(df)

    is_rail = rng.random(n) < RAIL_SHARE
    distance = np.where(
        is_rail,
        rng.uniform(*RAIL_DISTANCE_KM, size=n),
        rng.uniform(*DRAYAGE_DISTANCE_KM, size=n),
    )
    deadhead_share = rng.uniform(*DEADHEAD_SHARE, size=n)
    # An empty repositioning leg is entirely non-revenue distance.
    deadhead_share = np.where(df["IsEmptyRepositioning"].to_numpy() == 1, 1.0, deadhead_share)
    empty_km = distance * deadhead_share
    loaded_km = distance - empty_km

    speed = np.where(
        is_rail,
        rng.uniform(*AVG_SPEED_KMH_RAIL, size=n),
        rng.uniform(*AVG_SPEED_KMH_ROAD, size=n),
    )
    planned_hours = distance / speed
    actual_hours = planned_hours * rng.lognormal(0.04, 0.22, size=n)

    base = pd.DatetimeIndex(df["_base"])
    planned_pickup = base + pd.to_timedelta(rng.uniform(2.0, 72.0, size=n), unit="h")
    pickup_slip = np.where(
        rng.random(n) < ON_TIME_PICKUP_TARGET,
        rng.uniform(-PICKUP_WINDOW_HOURS, PICKUP_WINDOW_HOURS, size=n),
        PICKUP_WINDOW_HOURS + rng.exponential(6.0, size=n),
    )
    actual_pickup = planned_pickup + pd.to_timedelta(pickup_slip, unit="h")
    planned_delivery = planned_pickup + pd.to_timedelta(planned_hours, unit="h")
    actual_delivery = actual_pickup + pd.to_timedelta(actual_hours, unit="h")

    delivery_slip = (actual_delivery - planned_delivery).total_seconds().to_numpy() / 3600.0
    is_otp = (np.abs(pickup_slip) <= PICKUP_WINDOW_HOURS).astype(np.int8)

    # On-time delivery is calibrated to its target rather than falling out of
    # accumulated noise, but stays correlated with how late the pickup was: a leg
    # that collected four hours late rarely delivers inside its window. Same
    # self-calibrating logistic used for shipment OTIF.
    beta = 0.22
    shifted = -beta * np.clip(np.abs(delivery_slip), 0.0, 48.0)
    lo, hi = -20.0, 20.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if float(np.mean(1.0 / (1.0 + np.exp(-(mid + shifted))))) < ON_TIME_DELIVERY_TARGET:
            lo = mid
        else:
            hi = mid
    p_otd = 1.0 / (1.0 + np.exp(-((lo + hi) / 2.0 + shifted)))
    is_otd = (rng.random(n) < p_otd).astype(np.int8)

    cong = (
        (base >= pd.Timestamp(CONGESTION_START))
        & (base <= pd.Timestamp(CONGESTION_END))
        & np.isin(df["LocationKeyOrigin"].to_numpy(), congested)
    )
    turn_time = rng.exponential(TURN_TIME_MINUTES_MEAN, size=n) * np.where(
        cong, CONGESTION_TURN_TIME_MULTIPLIER, 1.0
    )
    gate_wait = rng.exponential(GATE_WAIT_MINUTES_MEAN, size=n) * np.where(
        cong, CONGESTION_TURN_TIME_MULTIPLIER, 1.0
    )

    cost_per_km = np.where(
        is_rail,
        rng.uniform(*COST_PER_KM_RAIL_USD, size=n),
        rng.uniform(*COST_PER_KM_ROAD_USD, size=n),
    )
    freight_cost = distance * cost_per_km
    fuel = freight_cost * rng.uniform(*FUEL_SURCHARGE_SHARE, size=n)
    tolls = freight_cost * rng.uniform(*TOLL_SHARE, size=n)
    accessorial = freight_cost * rng.uniform(*ACCESSORIAL_SHARE, size=n)
    total_cost = freight_cost + fuel + tolls + accessorial
    revenue = np.where(
        df["IsEmptyRepositioning"].to_numpy() == 1,
        0.0,
        total_cost * rng.uniform(1.02, 1.34, size=n),
    )

    litres = distance * rng.uniform(*LITRES_PER_100KM, size=n) / 100.0
    litres = np.where(is_rail, litres * 0.35, litres)

    wh_pool = warehouses[warehouses["WarehouseKey"] > 0]["WarehouseKey"].to_numpy(np.int32)
    attempts = np.where(rng.random(n) < FIRST_ATTEMPT_TARGET, 1, rng.integers(2, 4, size=n))

    year2 = pd.DatetimeIndex(actual_pickup).year % 100
    out = pd.DataFrame(
        {
            "TransportLegKey": np.arange(1, n + 1, dtype=np.int64),
            "ShipmentKey": df["ShipmentKey"].to_numpy(np.int64),
            "TripNo": [f"TRP{y:02d}{i:08d}" for i, y in zip(range(1, n + 1), year2)],
            "PlannedPickupDateKey": to_date_key(planned_pickup),
            "ActualPickupDateKey": to_date_key(actual_pickup),
            "PlannedDeliveryDateKey": to_date_key(planned_delivery),
            "ActualDeliveryDateKey": to_date_key(actual_delivery),
            "CarrierKey": rng.choice(carrier_pool, size=n, replace=True),
            "LocationKeyOrigin": df["LocationKeyOrigin"].to_numpy(np.int32),
            "LocationKeyDestination": df["LocationKeyDestination"].to_numpy(np.int32),
            "EquipmentKey": df["EquipmentKey"].to_numpy(np.int32),
            "ModeKey": np.where(
                is_rail,
                int(dims["DimMode"].query("ModeCode == 'RAI'")["ModeKey"].iloc[0]),
                int(dims["DimMode"].query("ModeCode == 'ROA'")["ModeKey"].iloc[0]),
            ).astype(np.int32),
            "CustomerKey": df["CustomerKey"].to_numpy(np.int32),
            "WarehouseKey": rng.choice(wh_pool, size=n, replace=True),
            "CurrencyKey": df["CurrencyKey"].to_numpy(np.int32),
            "ContainerNo": "#NA",
            "DistanceKm": distance.astype(np.float32),
            "LoadedKm": loaded_km.astype(np.float32),
            "EmptyKm": empty_km.astype(np.float32),
            "PlannedDurationHours": planned_hours.astype(np.float32),
            "ActualDurationHours": actual_hours.astype(np.float32),
            "GateInWaitMinutes": gate_wait.astype(np.float32),
            "TurnTimeMinutes": turn_time.astype(np.float32),
            "DetentionAtSiteHours": rng.exponential(3.4, size=n).astype(np.float32),
            "FreightCostUsd": freight_cost.astype(np.float32),
            "FuelSurchargeUsd": fuel.astype(np.float32),
            "TollsUsd": tolls.astype(np.float32),
            "AccessorialUsd": accessorial.astype(np.float32),
            "TotalCostUsd": total_cost.astype(np.float32),
            "RevenueUsd": revenue.astype(np.float32),
            "FuelLitres": litres.astype(np.float32),
            "Co2Kg": (litres * CO2_KG_PER_LITRE_DIESEL).astype(np.float32),
            "WeightKg": df["WeightKg"].to_numpy(np.float32),
            "Teu": df["Teu"].to_numpy(np.float32),
            "DropCount": np.maximum(1, rng.poisson(1.3, size=n)).astype(np.int8),
            "DeliveryAttempts": attempts.astype(np.int8),
            "IsOnTimePickup": is_otp,
            "IsOnTimeDelivery": is_otd,
            "IsFirstAttemptSuccess": (attempts == 1).astype(np.int8),
            "IsEmptyRepositioning": df["IsEmptyRepositioning"].to_numpy(np.int8),
            "IsBackhaulUtilised": (rng.random(n) < 0.41).astype(np.int8),
            "IsSubcontracted": (rng.random(n) < SUBCONTRACT_SHARE).astype(np.int8),
            "LegStatus": np.where(
                actual_delivery > pd.Timestamp(CALENDAR_END), "In Progress", "Completed"
            ),
        }
    )
    return out.sort_values("ActualPickupDateKey", kind="stable").reset_index(drop=True)


def build_fact_warehouse_task(
    dims: dict[str, pd.DataFrame], shipments: pd.DataFrame, n_rows: int
) -> pd.DataFrame:
    """One receipt, pick, pack or ship line — §2.8.

    Accuracy is a function of shift and tenure, not a coin flip. Night shift and
    agency staff inside their first six months are measurably worse, which is
    what makes "find the shift pattern with a systematic problem" answerable.
    """
    rng = child_rng("FactWarehouseTask")
    employees = dims["DimEmployee"]
    emp = employees[employees["EmployeeKey"] > 0]
    skus = dims["DimSku"]
    sku = skus[skus["SkuKey"] > 0]
    warehouses = dims["DimWarehouse"]

    # The weekday effect drops Sunday and Saturday rows after generation, so
    # oversample by the expected survival rate to land on the contracted count.
    weekday_survival = (5 + 0.70 + 0.35) / 7.0
    n = int(round(n_rows / weekday_survival))
    e_idx = rng.choice(len(emp), size=n, replace=True)
    e = emp.iloc[e_idx]
    s_idx = rng.choice(len(sku), size=n, replace=True)
    s = sku.iloc[s_idx]

    days = rng.integers(
        0, (pd.Timestamp(CALENDAR_END) - pd.Timestamp(CALENDAR_START)).days + 1, size=n
    )
    task_date = pd.Timestamp(CALENDAR_START) + pd.to_timedelta(days, unit="D")
    # Weekday effect, same as the commercial facts.
    dow = pd.DatetimeIndex(task_date).dayofweek
    keep = rng.random(n) < np.where(dow == 6, 0.35, np.where(dow == 5, 0.70, 1.0))

    shift_name = e["ShiftName"].to_numpy()
    shift_key = e["ShiftKey"].to_numpy(np.int8)
    is_night = np.array([str(x).strip().upper().startswith("C") for x in shift_name])
    if not is_night.any():
        is_night = shift_key == shift_key.max()

    hour = np.where(
        is_night, rng.integers(22, 30, size=n) % 24, rng.integers(6, 22, size=n)
    )
    minute = rng.integers(0, 60, size=n)
    start_ts = pd.DatetimeIndex(task_date) + pd.to_timedelta(
        hour * 60 + minute, unit="m"
    )

    task_type = rng.choice(
        list(TASK_TYPE_MIX.keys()),
        size=n,
        p=np.array(list(TASK_TYPE_MIX.values())) / sum(TASK_TYPE_MIX.values()),
    )

    role = e["RoleName"].to_numpy()
    tenure = e["TenureBand"].to_numpy()
    emp_type = e["EmploymentType"].to_numpy()

    base_lph = np.array([LINES_PER_HOUR_BY_ROLE.get(r, 40.0) for r in role])
    tenure_mult = np.array([TENURE_PRODUCTIVITY.get(t, 1.0) for t in tenure])
    lph = base_lph * tenure_mult
    lph = np.maximum(rng.normal(lph, lph * LINES_PER_HOUR_CV), 4.0)

    lines = np.maximum(1, rng.poisson(9.0, size=n)).astype(np.int16)
    labour_hours = lines / lph
    labour_minutes = labour_hours * 60.0

    units_per_line = np.maximum(
        1, s["UnitsPerCarton"].to_numpy(np.float64) * rng.uniform(0.4, 2.6, size=n)
    )
    units = (lines * units_per_line).astype(np.int32)
    cartons_per_pallet = np.maximum(s["CartonsPerPallet"].to_numpy(np.float64), 1.0)
    pallets = lines * units_per_line / cartons_per_pallet / np.maximum(
        s["UnitsPerCarton"].to_numpy(np.float64), 1.0
    )

    weight = units * s["UnitWeightKg"].to_numpy(np.float64)
    volume = units * s["UnitVolumeCbm"].to_numpy(np.float64)

    # ---- accuracy: structural, not random
    is_new_agency = (emp_type == "Agency") & (tenure == "<6m")
    p_accurate = np.full(n, PICK_ACCURACY_BASE)
    p_accurate = np.where(is_night, PICK_ACCURACY_NIGHT_SHIFT, p_accurate)
    p_accurate = np.where(
        is_new_agency, np.minimum(p_accurate, PICK_ACCURACY_NEW_AGENCY), p_accurate
    )
    is_accurate = (rng.random(n) < p_accurate).astype(np.int8)
    errors = np.where(is_accurate == 0, rng.integers(1, 4, size=n), 0).astype(np.int16)

    is_receive_like = np.isin(task_type, ["Receive", "Putaway"])
    d2s = np.where(
        is_receive_like, rng.uniform(*DOCK_TO_STOCK_MINUTES, size=n), -1.0
    )

    labour_cost = labour_hours * rng.uniform(*LABOUR_COST_PER_HOUR_USD, size=n)

    wh_key = e["WarehouseKey"].to_numpy(np.int32)
    cust_codes = s["CustomerCode"].to_numpy()
    cust_lookup = (
        dims["DimCustomer"]
        .query("IsCurrent == 1")
        .drop_duplicates("CustomerCode")
        .set_index("CustomerCode")["CustomerKey"]
    )
    customer_key = cust_lookup.reindex(cust_codes).fillna(-1).to_numpy(np.int32)

    ship_pool = shipments["ShipmentKey"].to_numpy(np.int64)
    ship_key = np.where(
        rng.random(n) < 0.46,
        rng.choice(ship_pool, size=n, replace=True),
        np.int64(-1),
    )

    out = pd.DataFrame(
        {
            "WarehouseTaskKey": np.arange(1, n + 1, dtype=np.int64),
            "TaskNo": [f"TSK{i:09d}" for i in range(1, n + 1)],
            "OrderNo": [f"ORD{i // 3 + 1:09d}" for i in range(1, n + 1)],
            "TaskDateKey": to_date_key(task_date),
            "TaskStartTs": start_ts,
            "TaskEndTs": start_ts + pd.to_timedelta(labour_minutes, unit="m"),
            "TimeKey": (pd.DatetimeIndex(start_ts).hour * 100
                        + pd.DatetimeIndex(start_ts).minute).astype(np.int32),
            "WarehouseKey": wh_key,
            "SkuKey": s["SkuKey"].to_numpy(np.int32),
            "EmployeeKey": e["EmployeeKey"].to_numpy(np.int32),
            "CustomerKey": customer_key,
            "ShipmentKey": ship_key,
            "TaskType": task_type,
            "ShiftKey": shift_key,
            "LinesProcessed": lines,
            "UnitsProcessed": units,
            "PalletsProcessed": pallets.astype(np.float32),
            "WeightKg": weight.astype(np.float32),
            "VolumeCbm": volume.astype(np.float32),
            "LabourMinutes": labour_minutes.astype(np.float32),
            "LabourHours": labour_hours.astype(np.float32),
            "TravelMetres": (lines * rng.uniform(12.0, 95.0, size=n)).astype(np.float32),
            "DockToStockMinutes": d2s.astype(np.float32),
            "LabourCostUsd": labour_cost.astype(np.float32),
            "IsAccurate": is_accurate,
            "ErrorCount": errors,
            "IsRework": (rng.random(n) < REWORK_RATE).astype(np.int8),
            "IsDamagedOnHandling": (rng.random(n) < DAMAGE_ON_HANDLING_RATE).astype(np.int8),
            "IsWithinSla": (rng.random(n) < SLA_RATE).astype(np.int8),
            "TaskStatus": np.where(
                rng.random(n) < 0.006, "Exception",
                np.where(rng.random(n) < 0.004, "Cancelled", "Completed"),
            ),
        }
    )
    out = out[keep].reset_index(drop=True)
    if len(out) > n_rows:
        out = out.iloc[:n_rows].copy()
    out["WarehouseTaskKey"] = np.arange(1, len(out) + 1, dtype=np.int64)
    return out.sort_values("TaskDateKey", kind="stable").reset_index(drop=True)


def build_fact_inventory_snapshot(
    dims: dict[str, pd.DataFrame], n_rows: int
) -> pd.DataFrame:
    """One SKU at one site on one day — §2.9. Periodic snapshot.

    Weekly for the older period, daily for the most recent twelve months, which
    is a real pattern (history gets thinned) and forces the learner to notice
    that a naive COUNT over this table is meaningless.
    """
    rng = child_rng("FactInventorySnapshot")
    skus = dims["DimSku"]
    sku = skus[skus["SkuKey"] > 0]
    warehouses = dims["DimWarehouse"]
    wh = warehouses[warehouses["WarehouseKey"] > 0]

    end = pd.Timestamp(CALENDAR_END)
    daily_start = end - pd.DateOffset(months=DAILY_SNAPSHOT_MONTHS)
    weekly_dates = pd.date_range(CALENDAR_START, daily_start, freq="W-SUN")
    daily_dates = pd.date_range(daily_start + pd.Timedelta(days=1), end, freq="D")
    all_dates = weekly_dates.append(daily_dates)

    # Choose how many SKU-site pairs to carry so total rows land on target.
    pairs_needed = max(1, int(round(n_rows / len(all_dates))))
    sku_pick = rng.choice(sku["SkuKey"].to_numpy(np.int32), size=pairs_needed, replace=True)
    wh_pick = rng.choice(wh["WarehouseKey"].to_numpy(np.int32), size=pairs_needed, replace=True)

    cust_lookup = (
        dims["DimCustomer"].query("IsCurrent == 1").drop_duplicates("CustomerCode")
        .set_index("CustomerCode")["CustomerKey"]
    )
    sku_meta = sku.set_index("SkuKey")
    cust_for_sku = (
        cust_lookup.reindex(sku_meta["CustomerCode"].reindex(sku_pick)).fillna(-1)
        .to_numpy(np.int32)
    )
    commodity_for_sku = sku_meta["CommodityKey"].reindex(sku_pick).fillna(-1).to_numpy(np.int32)
    unit_cost = sku_meta["UnitCostUsd"].reindex(sku_pick).fillna(1.0).to_numpy(np.float64)
    unit_vol = sku_meta["UnitVolumeCbm"].reindex(sku_pick).fillna(0.01).to_numpy(np.float64)
    unit_wt = sku_meta["UnitWeightKg"].reindex(sku_pick).fillna(1.0).to_numpy(np.float64)

    n_dates = len(all_dates)
    date_rep = np.tile(all_dates.to_numpy(), pairs_needed)
    pair_rep = np.repeat(np.arange(pairs_needed), n_dates)

    # A random walk per pair so stock levels drift rather than jitter.
    level0 = rng.uniform(80, 4200, size=pairs_needed)
    walk = rng.normal(0.0, 0.045, size=(pairs_needed, n_dates)).cumsum(axis=1)
    on_hand = np.maximum(0, (level0[:, None] * np.exp(walk)).round()).astype(np.int64).ravel()

    n = len(on_hand)
    # A pure lognormal walk never actually reaches zero, so stockouts would never
    # occur and the stockout-rate KPI would be dead. Force the contracted share.
    stockout_mask = rng.random(n) < STOCKOUT_RATE
    on_hand = np.where(stockout_mask, 0, on_hand)
    allocated = (on_hand * rng.uniform(0.0, 0.35, size=n)).astype(np.int64)
    available = np.maximum(on_hand - allocated, 0)
    in_transit = (on_hand * rng.uniform(0.0, 0.22, size=n)).astype(np.int64)

    uc = unit_cost[pair_rep]
    uv = unit_vol[pair_rep]
    uw = unit_wt[pair_rep]

    dates_idx = pd.DatetimeIndex(date_rep)
    is_count_day = (dates_idx.day == CYCLE_COUNT_DAY_OF_MONTH)
    system_count = on_hand
    physical = np.where(
        is_count_day,
        np.maximum(
            0,
            (on_hand * rng.normal(INVENTORY_ACCURACY_TARGET, 0.006, size=n)).round(),
        ).astype(np.int64),
        -1,
    )

    daily_demand = np.maximum(on_hand * rng.uniform(0.01, 0.12, size=n), 0.1)

    out = pd.DataFrame(
        {
            "InventorySnapshotKey": np.arange(1, n + 1, dtype=np.int64),
            "SnapshotDateKey": to_date_key(dates_idx),
            "WarehouseKey": wh_pick[pair_rep],
            "SkuKey": sku_pick[pair_rep],
            "CustomerKey": cust_for_sku[pair_rep],
            "CommodityKey": commodity_for_sku[pair_rep],
            "OnHandUnits": on_hand.astype(np.int32),
            "OnHandPallets": (on_hand / 480.0).astype(np.float32),
            "AllocatedUnits": allocated.astype(np.int32),
            "AvailableUnits": available.astype(np.int32),
            "InTransitUnits": in_transit.astype(np.int32),
            "OnHandValueUsd": (on_hand * uc).astype(np.float32),
            "OnHandCbm": (on_hand * uv).astype(np.float32),
            "OnHandWeightKg": (on_hand * uw).astype(np.float32),
            "PalletPositionsUsed": (on_hand / 480.0).astype(np.float32),
            "PalletPositionsAvailable": rng.uniform(50, 900, size=n).astype(np.float32),
            "DaysOfSupply": (on_hand / daily_demand).astype(np.float32),
            "AgeDaysAvg": rng.gamma(3.0, 14.0, size=n).astype(np.float32),
            "SystemCountUnits": system_count.astype(np.int32),
            "PhysicalCountUnits": physical.astype(np.int32),
            "ShrinkageUnits": (on_hand * SHRINKAGE_RATE).astype(np.int32),
            "ObsoleteUnits": (on_hand * rng.uniform(0, OBSOLETE_RATE * 2, size=n)).astype(np.int32),
            "IsStockout": (on_hand == 0).astype(np.int8),
            "IsOverstock": (rng.random(n) < OVERSTOCK_RATE).astype(np.int8),
            "IsExpiringWithin30d": (rng.random(n) < 0.031).astype(np.int8),
        }
    )
    if len(out) > n_rows:
        out = out.iloc[:n_rows]
    return out.sort_values("SnapshotDateKey", kind="stable").reset_index(drop=True)


def build_fact_target(dims: dict[str, pd.DataFrame], n_rows: int) -> pd.DataFrame:
    """One KPI target per region per month per scenario — §2.11.

    Deliberately at a coarser grain than the facts it is compared against. That
    mismatch is the lesson: joining a monthly regional target to a daily
    transaction fact is a modelling problem, not a relationship you can draw.
    """
    rng = child_rng("FactTarget")
    scenarios = dims["DimScenario"]
    sc = scenarios[scenarios["ScenarioKey"] > 0] if (scenarios["ScenarioKey"] > 0).any() else scenarios
    locations = dims["DimLocation"]
    regions = sorted(locations[locations["LocationKey"] > 0]["TradeRegion"].dropna().unique())
    modes = dims["DimMode"][dims["DimMode"]["ModeKey"] > 0]
    warehouses = dims["DimWarehouse"]
    usd_key = int(dims["DimCurrency"].query("CurrencyCode == 'USD'")["CurrencyKey"].iloc[0])

    months = pd.date_range(CALENDAR_START, CALENDAR_END, freq="MS")
    # Ocean KPIs are also targeted per trade lane, which is how a trade manager
    # is actually held to account. That widens the combination space enough to
    # reach the contracted row count without inventing extra KPIs.
    lanes = sorted(
        dims["DimService"].query("ServiceKey > 0")["TradeLane"].dropna().unique()
    )
    combos = []
    for m in months:
        for s in sc["ScenarioKey"].to_numpy(np.int32):
            for r in regions:
                for k in TARGET_KPIS:
                    if k[0].startswith("OCN"):
                        for lane in lanes:
                            combos.append((m, s, r, k, lane))
                    else:
                        combos.append((m, s, r, k, "#NA"))
    if len(combos) > n_rows:
        idx = rng.choice(len(combos), size=n_rows, replace=False)
        combos = [combos[i] for i in sorted(idx)]
    n = len(combos)

    month_arr = pd.DatetimeIndex([c[0] for c in combos])
    scenario_arr = np.array([c[1] for c in combos], dtype=np.int32)
    region_arr = np.array([c[2] for c in combos])
    kpi_code = np.array([c[3][0] for c in combos])
    kpi_name = np.array([c[3][1] for c in combos])
    unit = np.array([c[3][2] for c in combos])
    lane_arr = np.array([c[4] for c in combos])
    higher_better = np.array([c[3][3] for c in combos], dtype=np.int8)

    # Plausible target magnitudes by unit.
    magnitude = np.where(
        unit == "Pct", rng.uniform(0.60, 0.98, size=n),
        np.where(unit == "USD", rng.uniform(900, 3200, size=n),
        np.where(unit == "FFE", rng.uniform(1500, 42000, size=n),
        np.where(unit == "Hours", rng.uniform(18, 96, size=n),
        np.where(unit == "Days", rng.uniform(1.0, 9.0, size=n),
                 rng.uniform(20, 80, size=n))))),
    )
    stretch = np.where(
        higher_better == 1, magnitude * (1 + STRETCH_UPLIFT), magnitude * (1 - STRETCH_UPLIFT)
    )
    threshold = np.where(
        higher_better == 1, magnitude * (1 - THRESHOLD_HAIRCUT), magnitude * (1 + THRESHOLD_HAIRCUT)
    )

    wh_pool = warehouses[warehouses["WarehouseKey"] > 0]["WarehouseKey"].to_numpy(np.int32)
    is_wh_kpi = np.char.startswith(kpi_code.astype(str), "WHS")

    out = pd.DataFrame(
        {
            "TargetKey": np.arange(1, n + 1, dtype=np.int64),
            "TargetMonthDateKey": to_date_key(month_arr),
            "ScenarioKey": scenario_arr,
            "KpiCode": kpi_code,
            "KpiName": kpi_name,
            "Region": region_arr,
            "TradeLane": lane_arr,
            "ModeKey": rng.choice(modes["ModeKey"].to_numpy(np.int32), size=n, replace=True),
            "WarehouseKey": np.where(
                is_wh_kpi, rng.choice(wh_pool, size=n, replace=True), np.int32(-1)
            ).astype(np.int32),
            "CurrencyKey": np.full(n, usd_key, dtype=np.int32),
            "TargetValue": magnitude.astype(np.float32),
            "StretchValue": stretch.astype(np.float32),
            "ThresholdValue": threshold.astype(np.float32),
            "TargetUnit": unit,
            "IsHigherBetter": higher_better,
        }
    )
    return out.sort_values("TargetMonthDateKey", kind="stable").reset_index(drop=True)
