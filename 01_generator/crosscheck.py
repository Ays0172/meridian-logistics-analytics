"""Third-pass cross-checks: the angles validate.py and audit.py both miss.

    python crosscheck.py

`validate.py` checks the contract's stated targets.
`audit.py` checks internal consistency the contract does not state.
This checks a third category: relationships BETWEEN tables, statistical
artefacts that betray synthetic generation, dimension-member usage, and whether
the live feed's rows are distributionally continuous with the history they
extend. Anything here that fails is something two previous checkers agreed was
fine.
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from meridian.config import FACT_END_DATE, RAW_DIR, VALIDATION_DIR

findings: list[dict] = []


def chk(name: str, ok: bool, detail: str, sev: str = "error") -> None:
    findings.append({"check": name, "pass": bool(ok), "detail": detail, "severity": sev})
    mark = "ok  " if ok else ("WARN" if sev == "warn" else "FAIL")
    print(f"  [{mark}] {name}: {detail}")


def L(t, c=None):
    return pd.read_parquet(RAW_DIR / t, columns=c)


def D(t, c=None):
    return pd.read_parquet(RAW_DIR / t / "part-000.parquet", columns=c)


def dk(s):
    v = pd.to_numeric(s, errors="coerce")
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    m = v > 0
    out[m] = pd.to_datetime(v[m].astype("int64").astype(str), format="%Y%m%d")
    return out


def main() -> None:
    print("Cross-check pass — relationships, artefacts, member usage, live continuity\n")

    # ================= 1. cross-table relationships =================
    print("Cross-table relationships")

    sh = L("FactShipment", ["ShipmentKey", "Teu", "Ffe", "ContainerCount",
                            "IsTranshipped", "VoyageKey", "ShipmentDateKey",
                            "Revenue_usd", "GrossWeightKg", "ModeKey"])
    cm = L("FactContainerMove", ["ShipmentKey", "Teu", "ContainerNo", "MoveSequence",
                                 "DemurrageDays", "DetentionDays", "IsRepositioning"])

    # A container journey is one box: distinct ContainerNo per shipment should
    # not exceed the shipment's own container count.
    linked = cm[cm["ShipmentKey"] != -1]
    boxes = linked.groupby("ShipmentKey")["ContainerNo"].nunique()
    counts = sh.set_index("ShipmentKey")["ContainerCount"].reindex(boxes.index)
    over = int((boxes > counts).sum())
    chk("container journeys per shipment <= its ContainerCount", over == 0,
        f"{over} shipments have more distinct boxes than containers booked")

    # Every move on a journey should carry the same TEU factor as the shipment's
    # equipment implies per box.
    per_box = (sh.set_index("ShipmentKey")["Teu"] /
               sh.set_index("ShipmentKey")["ContainerCount"].clip(lower=1))
    mv_teu = linked.groupby("ShipmentKey")["Teu"].max()
    j = pd.concat([per_box.reindex(mv_teu.index), mv_teu], axis=1).dropna()
    j.columns = ["expected", "actual"]
    mismatch = int((~np.isclose(j["expected"], j["actual"], atol=0.01)).sum())
    chk("container move TEU matches the shipment's per-box TEU", mismatch == 0,
        f"{mismatch} of {len(j):,} shipments disagree")

    # Demurrage charge lines must only exist where a box actually ran past free
    # time. This is the single most important cross-fact tie in the model.
    fc = L("FactFreightCharge", ["ShipmentKey", "IsDemurrage", "IsDetention",
                                 "RevenueAmount_usd", "ChargeableDays"])
    dem_ships = set(cm.loc[cm["DemurrageDays"] > 0, "ShipmentKey"].unique())
    det_ships = set(cm.loc[cm["DetentionDays"] > 0, "ShipmentKey"].unique())
    bad_dem = int((~fc.loc[fc["IsDemurrage"] == 1, "ShipmentKey"].isin(dem_ships)).sum())
    bad_det = int((~fc.loc[fc["IsDetention"] == 1, "ShipmentKey"].isin(det_ships)).sum())
    tot_dem = int((fc["IsDemurrage"] == 1).sum())
    chk("every demurrage line ties to a container past free time",
        bad_dem == 0, f"{bad_dem} of {tot_dem:,} demurrage lines unsupported")
    chk("every detention line ties to a container past free time",
        bad_det == 0, f"{bad_det} of {int((fc['IsDetention'] == 1).sum()):,} unsupported")

    # A port call cannot load more slots than the vessel has.
    pc = L("FactPortCall", ["VesselKey", "SlotsUsedTeu", "SlotCapacityTeu",
                            "TotalMoves", "CranesDeployed", "AtaDateKey",
                            "TurnaroundHours", "BerthOccupancyHours"])
    ves = D("DimVessel", ["VesselKey", "NominalTeuCapacity", "LoaMetres",
                          "VesselClass", "ReeferPlugCount"])
    pv = pc.merge(ves, on="VesselKey", how="left")
    over_cap = int((pv["SlotsUsedTeu"] > pv["NominalTeuCapacity"]).sum())
    chk("slots used never exceed the vessel's nominal capacity", over_cap == 0,
        f"{over_cap} of {len(pv):,} calls over capacity")
    mismatch_cap = int((pv["SlotCapacityTeu"] != pv["NominalTeuCapacity"]).sum())
    chk("SlotCapacityTeu equals the vessel's nominal capacity",
        mismatch_cap == 0, f"{mismatch_cap} calls disagree", sev="warn")

    # Turnaround must be at least the berth occupancy it contains.
    bad_turn = int((pc["TurnaroundHours"] < pc["BerthOccupancyHours"]).sum())
    chk("turnaround >= berth occupancy", bad_turn == 0,
        f"{bad_turn} of {len(pc):,} calls violate")

    # ================= 2. dimension internal quality =================
    print("\nDimension internal quality")

    com = D("DimCommodity", ["HsCode6", "HsCode4", "HsCode2", "CommodityKey",
                             "IsTemperatureControlled", "IsDangerousGoods",
                             "ImdgClass", "AvgDensityKgPerCbm"])
    real = com[com["CommodityKey"] > 0]
    h6 = real["HsCode6"].astype(str).str.zfill(6)
    bad_h4 = int((h6.str[:4] != real["HsCode4"].astype(str).str.zfill(4)).sum())
    bad_h2 = int((h6.str[:2] != real["HsCode2"].astype(str).str.zfill(2)).sum())
    chk("HS code hierarchy is internally consistent", bad_h4 == 0 and bad_h2 == 0,
        f"{bad_h4} HsCode4 and {bad_h2} HsCode2 mismatches of {len(real)}")
    dg_no_class = int(((real["IsDangerousGoods"] == 1) &
                       (real["ImdgClass"].astype(str) == "#NA")).sum())
    chk("dangerous goods all carry an IMDG class", dg_no_class == 0,
        f"{dg_no_class} DG commodities with no class")

    sku = D("DimSku", ["SkuKey", "UnitCostUsd", "UnitPriceUsd", "UnitWeightKg",
                       "UnitVolumeCbm", "RequiresColdChain", "StorageType"])
    rs = sku[sku["SkuKey"] > 0]
    inverted = int((rs["UnitPriceUsd"] <= rs["UnitCostUsd"]).sum())
    chk("SKU price exceeds cost", inverted == 0,
        f"{inverted} of {len(rs):,} SKUs priced at or below cost")
    implied_density = rs["UnitWeightKg"] / rs["UnitVolumeCbm"].clip(lower=1e-6)
    absurd = int(((implied_density > 8000) | (implied_density < 5)).sum())
    chk("SKU implied density is physically plausible (5-8000 kg/m3)",
        absurd == 0, f"{absurd} of {len(rs):,} SKUs outside range", sev="warn")

    eq = D("DimEquipment", ["EquipmentKey", "EquipmentTypeCode", "LengthFt",
                            "TeuFactor", "FfeFactor", "MaxPayloadKg", "TareWeightKg",
                            "InternalCbm", "IsReefer"])
    re_ = eq[eq["EquipmentKey"] > 0]
    expect_teu = re_["LengthFt"].map({20: 1.0, 40: 2.0, 45: 2.25})
    bad_teu = int((~np.isclose(re_["TeuFactor"], expect_teu, atol=0.01)).sum())
    chk("equipment TeuFactor follows its length", bad_teu == 0,
        f"{bad_teu} of {len(re_)} equipment types wrong")
    bad_ffe = int((~np.isclose(re_["FfeFactor"], re_["TeuFactor"] / 2.0, atol=0.01)).sum())
    chk("FfeFactor is exactly half TeuFactor", bad_ffe == 0,
        f"{bad_ffe} of {len(re_)} wrong")
    bad_payload = int((re_["MaxPayloadKg"] <= re_["TareWeightKg"]).sum())
    chk("max payload exceeds tare weight", bad_payload == 0,
        f"{bad_payload} equipment types inverted")

    # Vessel physical coherence: bigger ships are longer. Landmine #8 injects
    # implausible-capacity outliers on purpose (a 350 TEU "Handysize", a 99,999
    # TEU ship), and including them drags the correlation from 0.93 to 0.68 — so
    # the check measures the fleet the landmine has NOT sabotaged, and separately
    # confirms the landmine is still there.
    rv = ves[ves["VesselKey"] > 0]
    outlier = (rv["NominalTeuCapacity"] > 25000) | (rv["NominalTeuCapacity"] < 500)
    clean = rv[~outlier]
    corr = float(np.corrcoef(clean["NominalTeuCapacity"], clean["LoaMetres"])[0, 1])
    chk("vessel length correlates with capacity (excl. landmine #8 outliers)",
        corr > 0.85, f"Pearson r = {corr:.3f} over {len(clean)} vessels")
    chk("landmine #8 capacity outliers still present", int(outlier.sum()) >= 2,
        f"{int(outlier.sum())} implausible-capacity vessels")

    loc = D("DimLocation", ["LocationKey", "LocationCode", "CountryCode",
                            "Latitude", "Longitude", "LocationType", "TradeRegion"])
    rl = loc[loc["LocationKey"] > 0]
    oob = int(((rl["Latitude"].abs() > 90) | (rl["Longitude"].abs() > 180)).sum())
    chk("coordinates within valid earth bounds", oob == 0, f"{oob} out of range")
    # UN/LOCODE country prefix must match CountryCode.
    prefix_bad = int((rl["LocationCode"].astype(str).str[:2] != rl["CountryCode"]).sum())
    chk("UN/LOCODE prefix matches CountryCode", prefix_bad == 0,
        f"{prefix_bad} of {len(rl)} locations disagree")

    # ================= 3. dimension member usage =================
    print("\nDimension member usage (a dimension nothing uses is dead weight)")
    usage = [
        ("DimCommodity", "CommodityKey", "FactShipment"),
        ("DimLocation", "LocationKeyPod", "FactShipment"),
        ("DimCarrier", "CarrierKey", "FactShipment"),
        ("DimVessel", "VesselKey", "FactPortCall"),
        ("DimSku", "SkuKey", "FactWarehouseTask"),
        ("DimEmployee", "EmployeeKey", "FactWarehouseTask"),
        ("DimChargeType", "ChargeTypeKey", "FactFreightCharge"),
        ("DimEquipment", "EquipmentKey", "FactShipment"),
        ("DimVoyage", "VoyageKey", "FactPortCall"),
        ("DimMilestone", "MilestoneKey", "FactContainerMove"),
    ]
    for dim, col, fact in usage:
        dimkey = dim.replace("Dim", "") + "Key"
        dimkey = {"LocationKeyPod": "LocationKey"}.get(col, dimkey)
        avail = len(D(dim)[D(dim, [dimkey])[dimkey] > 0])
        used = L(fact, [col])[col]
        used_n = int(used[used > 0].nunique())
        pct = used_n / max(avail, 1) * 100
        chk(f"{dim} members used by {fact}", pct >= 25.0,
            f"{used_n}/{avail} ({pct:.0f}%)",
            sev="warn" if pct >= 10 else "error")

    # ================= 4. statistical artefacts =================
    print("\nStatistical artefacts of synthetic generation")
    tl = L("FactTransportLeg", ["DistanceKm", "TotalCostUsd", "LoadedKm", "EmptyKm"])
    cpk = tl["TotalCostUsd"] / tl["DistanceKm"].clip(lower=0.1)
    # A uniform draw leaves a hard edge; check the top 0.1% is not piled on one value.
    top = cpk.quantile(0.999)
    pile = int((np.isclose(cpk, cpk.max(), rtol=1e-6)).sum())
    chk("cost per km has no single piled-up ceiling value", pile <= 5,
        f"max {cpk.max():.3f}, {pile} rows exactly at max, p99.9 {top:.3f}",
        sev="warn")

    # Money columns should be right-skewed, not symmetric.
    for tbl, col in [("FactShipment", "Revenue_usd"),
                     ("FactFreightCharge", "RevenueAmount_usd")]:
        v = L(tbl, [col])[col]
        v = v[v > 0]
        skew = float(((v - v.mean()) ** 3).mean() / v.std() ** 3)
        chk(f"{tbl}.{col} is right-skewed like real money", skew > 0.3,
            f"skew = {skew:.2f}")

    # Sentinel leakage: -1 must appear only in key/date columns, never a measure.
    print("\nSentinel leakage into measures")
    measure_like = {
        "FactShipment": ["Revenue_usd", "DirectCost_usd", "GrossWeightKg", "Teu"],
        "FactContainerMove": ["MoveCostUsd", "GrossWeightKg", "Teu"],
        "FactPortCall": ["TotalMoves", "PortCostUsd", "CraneHoursNet"],
        "FactWarehouseTask": ["LinesProcessed", "LabourHours", "LabourCostUsd"],
        "FactInventorySnapshot": ["OnHandUnits", "OnHandValueUsd"],
    }
    leaks = []
    for t, cols in measure_like.items():
        df = L(t, cols)
        for c in cols:
            n = int((df[c] == -1).sum())
            if n:
                leaks.append(f"{t}.{c}={n}")
    chk("no -1 sentinel in measure columns", not leaks,
        "clean" if not leaks else "; ".join(leaks))

    # ================= 5. dtype headroom =================
    print("\nDtype headroom (would the stress scale overflow?)")
    limits = {"int8": 127, "int16": 32767, "int32": 2147483647}
    tight = []
    for t in ["FactBooking", "FactShipment", "FactContainerMove", "FactPortCall",
              "FactFreightCharge", "FactTransportLeg", "FactWarehouseTask",
              "FactInventorySnapshot"]:
        df = L(t)
        for c in df.columns:
            dt = str(df[c].dtype)
            if dt in limits and len(df):
                mx = float(pd.to_numeric(df[c], errors="coerce").max())
                head = mx / limits[dt]
                if head > 0.5:
                    tight.append(f"{t}.{c} ({dt}) at {head:.0%} of range (max {mx:.0f})")
    chk("no integer column above 50% of its dtype range", not tight,
        "clean" if not tight else "; ".join(tight[:6]), sev="warn")

    # ================= 6. live-feed continuity =================
    print("\nLive-feed continuity with the history it extends")
    wm_path = RAW_DIR.parent / "_state" / "watermark.json"
    if not wm_path.exists():
        chk("live feed state present", False, "no watermark; skipping", sev="warn")
    else:
        wm = json.loads(wm_path.read_text())
        hend = pd.Timestamp(wm["history_end"])
        shf = L("FactShipment", ["ShipmentDateKey", "Revenue_usd", "Teu", "ModeKey",
                                 "IsOnTime", "IsPerfectOrder", "GrossMarginPct",
                                 "ActualTransitDays", "ContainerCount"])
        d = dk(shf["ShipmentDateKey"])
        hist = shf[(d > hend - pd.Timedelta(days=30)) & (d <= hend)]
        live = shf[d > hend]
        chk("live rows exist", len(live) > 0, f"{len(live):,} live shipment rows")
        for col, tol in [("Revenue_usd", 0.30), ("Teu", 0.25),
                         ("GrossMarginPct", 0.15), ("ActualTransitDays", 0.25),
                         ("ContainerCount", 0.25)]:
            h, l = hist[col].mean(), live[col].mean()
            rel = abs(l - h) / max(abs(h), 1e-9)
            chk(f"live vs history mean of {col} within {tol:.0%}", rel <= tol,
                f"history {h:.3f} vs live {l:.3f} ({rel:+.1%})",
                sev="warn")
        for col in ["IsOnTime", "IsPerfectOrder"]:
            h, l = hist[col].mean(), live[col].mean()
            chk(f"live vs history rate of {col} within 8pp",
                abs(l - h) <= 0.08, f"history {h:.3f} vs live {l:.3f}", sev="warn")
        hm = hist["ModeKey"].value_counts(normalize=True)
        lm = live["ModeKey"].value_counts(normalize=True).reindex(hm.index).fillna(0)
        drift = float(np.abs(hm - lm).sum() / 2)
        chk("mode mix drift between history and live under 10%", drift < 0.10,
            f"total variation distance {drift:.3f}", sev="warn")

    # ================= 7. weekly time series =================
    print("\nWeekly time-series health across the full span")
    bk = L("FactBooking", ["BookingDateKey"])
    bd = dk(bk["BookingDateKey"])
    wk = bd.dt.to_period("W").value_counts().sort_index()
    interior = wk.iloc[1:-1]
    zero_weeks = int((interior == 0).sum())
    chk("no dead weeks in the interior of the series", zero_weeks == 0,
        f"{zero_weeks} interior weeks with zero bookings")
    cv = float(interior.std() / interior.mean())
    chk("weekly volume variation is realistic (CV 0.05-0.45)",
        0.05 <= cv <= 0.45, f"coefficient of variation {cv:.3f}")
    # Growth: first full year vs last full year
    yr = bd.dt.year.value_counts().sort_index()
    full = yr.loc[[y for y in (2022, 2023, 2024, 2025) if y in yr.index]]
    growth = (full.iloc[-1] / full.iloc[0]) ** (1 / (len(full) - 1)) - 1
    chk("compound annual growth between 2 and 10%", 0.02 <= growth <= 0.10,
        f"{growth:.2%} per year across {list(full.index)}")

    # ================= report =================
    errs = [f for f in findings if not f["pass"] and f["severity"] == "error"]
    warns = [f for f in findings if not f["pass"] and f["severity"] == "warn"]
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    (VALIDATION_DIR / "crosscheck_report.json").write_text(
        json.dumps({"checks": len(findings), "errors": len(errs),
                    "warnings": len(warns), "findings": findings}, indent=2))
    print(f"\n{len(findings) - len(errs) - len(warns)}/{len(findings)} clean, "
          f"{len(errs)} errors, {len(warns)} warnings")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
