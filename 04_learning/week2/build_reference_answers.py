#!/usr/bin/env python
"""Recompute every ground-truth value quoted in the Week 1-2 modules and
solutions, and write them to _reference_answers.json.

Why this exists as a script rather than a one-off: the numbers in the learning
material are only useful if they match the dataset the learner actually built.
Any change to the generator moves them. Before ADR-002 these values were
computed ad hoc, which meant a generator change silently invalidated the
answer key — the learner's correct measure would disagree with the book and
they would conclude they were wrong. Run this after any rebuild.

    cd 04_learning/week2 && python build_reference_answers.py

Every value is computed with pandas from 02_data/raw, deliberately duplicating
no logic from the generator: if a figure here disagrees with the DAX the learner
writes, one of the two is wrong and that is the point.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parents[2] / "02_data" / "raw"
OUT = Path(__file__).resolve().parent / "_reference_answers.json"

CONGESTION_PORTS = ("NLRTM", "USLAX")
R = {}


def r2(x) -> float:
    return round(float(x), 2)


def r4(x) -> float:
    return round(float(x), 4)


def r5(x) -> float:
    return round(float(x), 5)


def load(table: str, cols: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(RAW / table, columns=cols)


def pooled(num: pd.Series, den: pd.Series) -> float:
    d = den.sum()
    return float(num.sum() / d) if d else float("nan")


def naive(num: pd.Series, den: pd.Series) -> float:
    """Mean of per-row ratios, blanks (zero denominator) SKIPPED — matching
    what AVERAGEX does with DIVIDE's blank."""
    m = den > 0
    return float((num[m] / den[m]).mean())


def main() -> None:
    # ------------------------------------------------------------------ load
    sh = load(
        "FactShipment",
        [
            "ShipmentKey", "ShipmentDateKey", "DeliveryDateKey", "Revenue_usd",
            "DirectCost_usd", "GrossProfit_usd", "GrossMarginPct", "Ffe", "Teu",
            "ContainerCount", "EquipmentKey", "CustomerKey", "VoyageKey",
            "ServiceKey", "ModeKey", "IsOnTime", "IsPerfectOrder",
            "ActualTransitDays", "IsTranshipped",
        ],
    )
    pc = load(
        "FactPortCall",
        ["AtaDateKey", "LocationKey", "IsOnTimeArrival", "WaitingForBerthHours",
         "TotalMoves", "CraneHoursNet", "MovesPerCraneHourNet"],
    )
    wt = load(
        "FactWarehouseTask",
        ["TaskDateKey", "LinesProcessed", "LabourHours", "EmployeeKey",
         "ShiftKey", "IsAccurate"],
    )
    cm = load(
        "FactContainerMove",
        ["EventDateKey", "IsLaden", "DwellHours", "EquipmentKey"],
    )
    svc = load("DimService", ["ServiceKey", "ServiceCode", "TradeLane"])
    voy = load("DimVoyage", ["VoyageKey", "Direction"])
    mode = load("DimMode", ["ModeKey", "ModeCode", "ModeGroup"])
    loc = load("DimLocation", ["LocationKey", "LocationCode"])
    dd = load("DimDate", ["DateKey", "Date", "Year", "Month", "ISOWeekLabel"])

    sh = sh.merge(svc, on="ServiceKey", how="left").merge(
        voy, on="VoyageKey", how="left"
    ).merge(mode, on="ModeKey", how="left")
    sh["Year"] = sh["ShipmentDateKey"] // 10000
    sh["Month"] = (sh["ShipmentDateKey"] // 100) % 100
    ocean = sh[sh["Ffe"] > 0]
    air = sh[sh["ModeCode"] == "AIR"]

    # ------------------------------------------------- headline totals (D08)
    R["total_revenue_usd"] = float(sh["Revenue_usd"].sum())
    R["total_ffe"] = r2(sh["Ffe"].sum())
    R["total_teu"] = r2(sh["Teu"].sum())
    R["revenue_per_ffe_all"] = r2(pooled(sh["Revenue_usd"], sh["Ffe"]))
    for d in ("Headhaul", "Backhaul"):
        s = ocean[ocean["Direction"] == d]
        R[f"revenue_per_ffe_{d.lower()}"] = r2(pooled(s["Revenue_usd"], s["Ffe"]))
    R["NAIVE_avg_of_ratios"] = r2(naive(sh["Revenue_usd"], sh["Ffe"]))
    R["CORRECT_pooled_ratio"] = r2(pooled(ocean["Revenue_usd"], ocean["Ffe"]))

    rev_by_year = sh.groupby("Year")["Revenue_usd"].sum()
    for y in (2021, 2022, 2023, 2024, 2025, 2026):
        if y in rev_by_year.index:
            R[f"revenue_{y}"] = float(rev_by_year[y])
    R["yoy_2024_vs_2023_pct"] = round(
        (rev_by_year[2024] / rev_by_year[2023] - 1) * 100, 3
    )
    R["yoy_2025_vs_2024_pct"] = round(
        (rev_by_year[2025] / rev_by_year[2024] - 1) * 100, 3
    )

    R["gross_margin_pooled"] = r5(
        sh["GrossProfit_usd"].sum() / sh["Revenue_usd"].sum()
    )
    R["NAIVE_avg_margin_per_shipment"] = r5(sh["GrossMarginPct"].mean())
    R["loss_making_shipment_share"] = r5((sh["GrossMarginPct"] < 0).mean())

    R["transit_mean"] = r2(sh["ActualTransitDays"].mean())
    R["transit_median"] = r2(sh["ActualTransitDays"].median())
    R["transit_p90"] = r2(sh["ActualTransitDays"].quantile(0.90))
    R["on_time_delivery_rate"] = r5(sh["IsOnTime"].mean())
    R["perfect_order_rate"] = r5(sh["IsPerfectOrder"].mean())

    cust = sh.groupby("CustomerKey")["Revenue_usd"].sum().sort_values(ascending=False)
    R["top10_customer_revenue_share_pct"] = round(
        cust.head(10).sum() / cust.sum() * 100, 3
    )

    # ----------------------------------------------------- lanes (D09 / D10)
    lane_rpf = (
        ocean.groupby("TradeLane")
        .apply(lambda g: pooled(g["Revenue_usd"], g["Ffe"]), include_groups=False)
        .sort_values(ascending=False)
    )
    R["revenue_per_ffe_by_lane"] = {k: r2(v) for k, v in lane_rpf.items()}
    R["lane_rank_by_revenue_per_ffe"] = R["revenue_per_ffe_by_lane"]
    lane_rev = (
        sh.groupby("TradeLane")["Revenue_usd"].sum().sort_values(ascending=False) / 1e6
    )
    R["lane_rank_by_total_revenue"] = {k: r2(v) for k, v in lane_rev.items()}
    R["best_yield_lane"] = str(lane_rpf.index[0])
    R["worst_yield_lane"] = str(lane_rpf.index[-1])
    R["top_revenue_lane"] = str(lane_rev.index[0])

    for lane in ("Asia–N Europe", "Transpacific East"):
        s = sh[sh["TradeLane"] == lane]["ActualTransitDays"]
        if len(s):
            R[f"transit_{lane}_p50"] = r2(s.median())
            R[f"transit_{lane}_p90"] = r2(s.quantile(0.90))
            R[f"transit_{lane}_mean"] = r2(s.mean())

    # -------------------------------------------- operations rates (D09/D10)
    R["schedule_reliability_all"] = r5(pc["IsOnTimeArrival"].mean())
    R["CORRECT_pooled_mpch"] = r2(pooled(pc["TotalMoves"], pc["CraneHoursNet"]))
    R["NAIVE_avg_of_mpch"] = r2(pc["MovesPerCraneHourNet"].mean())
    R["empty_share"] = r5(1 - cm["IsLaden"].mean())
    R["dwell_mean_positive"] = r2(cm.loc[cm["DwellHours"] > 0, "DwellHours"].mean())

    R["CORRECT_lines_per_labour_hour"] = r2(
        pooled(wt["LinesProcessed"], wt["LabourHours"])
    )
    R["NAIVE_avg_of_per_task_lph"] = r2(naive(wt["LinesProcessed"], wt["LabourHours"]))
    R["pick_accuracy_pooled"] = r5(wt["IsAccurate"].mean())
    R["accuracy_by_shift"] = {
        str(k): r5(v) for k, v in wt.groupby("ShiftKey")["IsAccurate"].mean().items()
    }

    # ------------------------------------------- the averaging trap, measured
    R["trap_lane_unweighted_mean_of_ratios"] = r2(lane_rpf.mean())
    R["trap_lane_pooled"] = R["CORRECT_pooled_ratio"]
    R["trap_lane_error_pct"] = round(
        (lane_rpf.mean() / R["CORRECT_pooled_ratio"] - 1) * 100, 2
    )

    cust_margin = sh.groupby("CustomerKey").apply(
        lambda g: pooled(g["GrossProfit_usd"], g["Revenue_usd"]), include_groups=False
    )
    R["trap_customer_unweighted_mean_margin"] = r5(cust_margin.mean())
    R["trap_customer_pooled_margin"] = R["gross_margin_pooled"]

    pcw = pc.merge(dd, left_on="AtaDateKey", right_on="DateKey", how="left")
    R["trap_reliability_unweighted_week_mean"] = r5(
        pcw.groupby("ISOWeekLabel")["IsOnTimeArrival"].mean().mean()
    )
    R["trap_reliability_pooled"] = R["schedule_reliability_all"]
    R["trap_reliability_unweighted_port_mean"] = r5(
        pc.groupby("LocationKey")["IsOnTimeArrival"].mean().mean()
    )

    emp_lph = wt.groupby("EmployeeKey").apply(
        lambda g: pooled(g["LinesProcessed"], g["LabourHours"]), include_groups=False
    )
    R["trap_lph_unweighted_employee_mean"] = r2(emp_lph.mean())
    R["trap_lph_pooled"] = R["CORRECT_lines_per_labour_hour"]
    R["trap_lph_error_pct"] = round(
        (R["NAIVE_avg_of_per_task_lph"] / R["CORRECT_lines_per_labour_hour"] - 1) * 100,
        2,
    )

    # the mechanism: correlation between each per-row ratio and its denominator
    m = wt["LabourHours"] > 0
    R["corr_ratio_vs_denominator_warehouse"] = r4(
        np.corrcoef(
            wt.loc[m, "LinesProcessed"] / wt.loc[m, "LabourHours"],
            wt.loc[m, "LabourHours"],
        )[0, 1]
    )
    m = sh["Ffe"] > 0
    R["corr_ratio_vs_denominator_ocean"] = r4(
        np.corrcoef(
            sh.loc[m, "Revenue_usd"] / sh.loc[m, "Ffe"], sh.loc[m, "Ffe"]
        )[0, 1]
    )
    R["cv_of_Ffe"] = r4(sh.loc[m, "Ffe"].std() / sh.loc[m, "Ffe"].mean())
    R["cv_of_LabourHours"] = r4(wt["LabourHours"].std() / wt["LabourHours"].mean())

    # --------------------------------------------- the mismatched-scope trap
    R["rpf_MISMATCHED_all_rev_over_ocean_ffe"] = R["revenue_per_ffe_all"]
    R["rpf_CORRECT_ocean_only"] = R["CORRECT_pooled_ratio"]
    R["rpf_mismatch_overstatement_pct"] = round(
        (R["revenue_per_ffe_all"] / R["CORRECT_pooled_ratio"] - 1) * 100, 2
    )
    R["air_shipment_rows"] = int(len(air))
    R["air_revenue_usd"] = float(air["Revenue_usd"].sum())
    R["air_share_of_revenue_pct"] = round(
        air["Revenue_usd"].sum() / sh["Revenue_usd"].sum() * 100, 2
    )
    R["rpf_naive_blanks_skipped"] = R["NAIVE_avg_of_ratios"]
    R["rpf_naive_n_nonblank"] = int((sh["Ffe"] > 0).sum())
    R["rpf_naive_n_total_rows"] = int(len(sh))
    ratios = np.where(sh["Ffe"] > 0, sh["Revenue_usd"] / sh["Ffe"].replace(0, np.nan), 0.0)
    R["rpf_naive_blanks_as_zero"] = r2(np.nan_to_num(ratios).mean())

    # -------------------------------------------------- time intelligence (D11)
    def rolling8(as_of: str, mask=None) -> tuple[float, int]:
        end = pd.Timestamp(as_of)
        start = end - pd.Timedelta(days=55)
        p = pc.merge(loc, on="LocationKey", how="left")
        ts = pd.to_datetime(p["AtaDateKey"].astype(str), format="%Y%m%d", errors="coerce")
        sel = ts.between(start, end)
        if mask == "crisis":
            sel &= p["LocationCode"].isin(CONGESTION_PORTS)
        elif mask == "other":
            sel &= ~p["LocationCode"].isin(CONGESTION_PORTS)
        w = p[sel]
        return (float(w["IsOnTimeArrival"].mean()), int(len(w))) if len(w) else (float("nan"), 0)

    for as_of in ("2025-08-31", "2026-06-30"):
        val, n = rolling8(as_of)
        R[f"rolling8wk_reliability_{as_of}"] = r5(val)
        R[f"rolling8wk_calls_{as_of}"] = n

    net, n_net = rolling8("2025-08-31")
    cri, n_cri = rolling8("2025-08-31", "crisis")
    oth, n_oth = rolling8("2025-08-31", "other")
    R["roll8_2025_08_31_network"] = r5(net)
    R["roll8_2025_08_31_crisis_ports"] = r5(cri)
    R["roll8_2025_08_31_other_ports"] = r5(oth)
    R["roll8_2025_08_31_n_crisis"] = n_cri
    R["roll8_2025_08_31_n_total"] = n_net
    R["roll8_crisis_vs_other_pct_worse"] = round((1 - cri / oth) * 100, 1)
    R["roll8_network_vs_other_pct_below"] = round((1 - net / oth) * 100, 2)

    p = pc.merge(loc, on="LocationKey", how="left")
    ts = pd.to_datetime(p["AtaDateKey"].astype(str), format="%Y%m%d", errors="coerce")
    win = ts.between("2025-07-07", "2025-08-31")
    crisis = p["LocationCode"].isin(CONGESTION_PORTS)
    R["roll8_2025_08_31_wait_crisis"] = r2(
        p.loc[win & crisis, "WaitingForBerthHours"].mean()
    )
    R["roll8_2025_08_31_wait_other"] = r2(
        p.loc[win & ~crisis, "WaitingForBerthHours"].mean()
    )

    # Lunar New Year: monthly FFE, January against February
    ffe_m = sh.groupby(["Year", "Month"])["Ffe"].sum()
    for y in (2023, 2024, 2025, 2026):
        for mo in (1, 2, 9, 11):
            if (y, mo) in ffe_m.index:
                R[f"ffe_{y}_{mo:02d}"] = r2(ffe_m[(y, mo)])
    R["ffe_feb_2025_vs_2024_yoy_pct"] = round(
        (ffe_m[(2025, 2)] / ffe_m[(2024, 2)] - 1) * 100, 2
    )
    for y in (2023, 2024, 2025, 2026):
        R[f"ffe_feb_over_jan_{y}"] = r4(ffe_m[(y, 2)] / ffe_m[(y, 1)])

    # YTD comparisons
    def rev_between(a: int, b: int) -> float:
        m = sh["ShipmentDateKey"].between(a, b)
        return float(sh.loc[m, "Revenue_usd"].sum())

    R["revenue_ytd_2026_h1"] = rev_between(20260101, 20260630)
    R["revenue_2025_h1"] = rev_between(20250101, 20250630)
    R["yoy_h1_pct"] = round(
        (R["revenue_ytd_2026_h1"] / R["revenue_2025_h1"] - 1) * 100, 2
    )
    R["revenue_ytd_2026_to_0620"] = rev_between(20260101, 20260620)
    R["revenue_same_period_2025"] = rev_between(20250101, 20250620)

    # Containers in transit — the event-in-progress pattern
    ms = load(
        "FactShipmentMilestone", ["VesselLoadDateKey", "VesselDischargeDateKey"]
    )
    as_of = 20260401
    in_transit = (
        (ms["VesselLoadDateKey"] > 0)
        & (ms["VesselLoadDateKey"] <= as_of)
        & ((ms["VesselDischargeDateKey"] > as_of) | (ms["VesselDischargeDateKey"] == -1))
    )
    R["containers_in_transit_2026_04_01"] = int(in_transit.sum())

    # -------------------------------------------------------------- write out
    OUT.write_text(json.dumps(R, indent=2, ensure_ascii=False, default=float) + "\n")
    print(f"wrote {len(R)} reference values -> {OUT}")
    for k in (
        "total_revenue_usd", "CORRECT_pooled_ratio", "revenue_per_ffe_all",
        "schedule_reliability_all", "on_time_delivery_rate", "perfect_order_rate",
        "CORRECT_lines_per_labour_hour", "NAIVE_avg_of_per_task_lph",
        "roll8_2025_08_31_network", "roll8_2025_08_31_crisis_ports",
        "containers_in_transit_2026_04_01",
    ):
        print(f"  {k:38s} {R[k]}")


if __name__ == "__main__":
    main()
