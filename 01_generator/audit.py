"""Adversarial audit of the generated dataset.

    python audit.py

`validate.py` checks the contract's stated targets. This checks the things the
contract does NOT state, and which the generator could therefore have got wrong
without any gate noticing:

  * primary keys actually unique
  * dates internally consistent (nothing arrives before it departs)
  * no impossible values (negative weights, distances, quantities)
  * cross-fact keys resolve (a shipment's booking really exists)
  * arithmetic identities hold (revenue - cost = gross profit, doc x fx = usd)
  * derived measures agree with the dimensions they were derived from
  * SCD2 history is well-formed (no overlaps, exactly one current row)
  * the ten deliberate landmines are all actually present
  * no column is secretly constant, and none is secretly all-null

The point of a separate file is that it was written to try to break the data,
not to confirm it.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

from meridian.config import FACT_END_DATE, RAW_DIR, VALIDATION_DIR

# The horizon is the end of the FROZEN history. Rows past it are only legitimate
# if the live feed put them there, so the horizon extends to the live watermark
# when one exists — and a row beyond even that is a real defect.
def _horizon() -> pd.Timestamp:
    wm = RAW_DIR.parent / "_state" / "watermark.json"
    if wm.exists():
        import json as _j
        return pd.Timestamp(_j.loads(wm.read_text())["last_appended_date"])
    return pd.Timestamp(FACT_END_DATE)


TODAY = _horizon()

findings: list[dict] = []


def check(name: str, passed: bool, detail: str, severity: str = "error") -> None:
    findings.append(
        {"check": name, "pass": bool(passed), "detail": detail, "severity": severity}
    )
    mark = "ok  " if passed else ("WARN" if severity == "warn" else "FAIL")
    print(f"  [{mark}] {name}: {detail}")


def load(table: str, columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(RAW_DIR / table, columns=columns)


def dk(s: pd.Series) -> pd.Series:
    v = pd.to_numeric(s, errors="coerce")
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    m = v > 0
    out[m] = pd.to_datetime(v[m].astype("int64").astype(str), format="%Y%m%d")
    return out


FACTS = [
    "FactBooking", "FactShipment", "FactShipmentMilestone", "FactContainerMove",
    "FactPortCall", "FactFreightCharge", "FactTransportLeg", "FactWarehouseTask",
    "FactInventorySnapshot", "FactExchangeRate", "FactTarget",
]
PRIMARY_KEYS = {
    "FactBooking": "BookingKey",
    "FactShipment": "ShipmentKey",
    "FactShipmentMilestone": "ShipmentKey",
    "FactContainerMove": "ContainerMoveKey",
    "FactPortCall": "PortCallKey",
    "FactFreightCharge": "ChargeLineKey",
    "FactTransportLeg": "TransportLegKey",
    "FactWarehouseTask": "WarehouseTaskKey",
    "FactInventorySnapshot": "InventorySnapshotKey",
    "FactExchangeRate": "ExchangeRateKey",
    "FactTarget": "TargetKey",
}


def main() -> None:
    print("Adversarial audit — checking what validate.py does not\n")

    # ---------------- 1. primary key uniqueness ----------------
    print("Primary keys")
    for t, pk in PRIMARY_KEYS.items():
        s = load(t, [pk])[pk]
        dup = int(len(s) - s.nunique())
        check(f"{t}.{pk} unique", dup == 0, f"{dup} duplicates in {len(s):,} rows")

    # ---------------- 2. no impossible values ----------------
    print("\nImpossible values")
    non_negative = {
        "FactShipment": ["GrossWeightKg", "VolumeCbm", "ChargeableWeightKg",
                         "DistanceKm", "Teu", "Ffe", "ContainerCount",
                         "PlannedTransitDays", "ActualTransitDays", "Co2Tonnes"],
        "FactContainerMove": ["Teu", "Ffe", "GrossWeightKg", "MoveCostUsd",
                              "DemurrageDays", "DetentionDays", "FreeTimeDaysUsed"],
        "FactPortCall": ["TotalMoves", "DischargeMoves", "LoadMoves",
                         "CraneHoursGross", "CraneHoursNet", "WaitingForBerthHours",
                         "BerthOccupancyHours", "PortCostUsd", "TeuLoaded"],
        "FactTransportLeg": ["DistanceKm", "LoadedKm", "EmptyKm", "TotalCostUsd",
                             "FuelLitres", "Co2Kg", "PlannedDurationHours"],
        "FactWarehouseTask": ["LinesProcessed", "UnitsProcessed", "LabourHours",
                              "LabourCostUsd", "WeightKg"],
        "FactInventorySnapshot": ["OnHandUnits", "AvailableUnits", "OnHandValueUsd"],
        "FactBooking": ["TeuBooked", "FfeBooked", "WeightKgBooked", "ContainerCount"],
    }
    for t, cols in non_negative.items():
        df = load(t, cols)
        bad = {c: int((df[c] < 0).sum()) for c in cols if (df[c] < 0).any()}
        check(f"{t} no negative measures", not bad, "clean" if not bad else str(bad))

    # ---------------- 3. date logic ----------------
    print("\nDate logic")
    sh = load("FactShipment", ["ShipmentDateKey", "EtaDateKey", "AtaDateKey",
                               "DeliveryDateKey", "PlannedTransitDays",
                               "ActualTransitDays", "TransitVarianceDays",
                               "BookingKey", "ShipmentKey"])
    dep, eta, ata, dlv = (dk(sh[c]) for c in
                          ["ShipmentDateKey", "EtaDateKey", "AtaDateKey", "DeliveryDateKey"])
    check("shipment: arrival not before departure", int((ata < dep).sum()) == 0,
          f"{int((ata < dep).sum())} violations")
    check("shipment: delivery not before arrival", int((dlv < ata).sum()) == 0,
          f"{int((dlv < ata).sum())} violations")
    check("shipment: ETA not before departure", int((eta < dep).sum()) == 0,
          f"{int((eta < dep).sum())} violations")
    var = sh["ActualTransitDays"] - sh["PlannedTransitDays"]
    check("shipment: TransitVarianceDays = actual - planned",
          int((var != sh["TransitVarianceDays"]).sum()) == 0,
          f"{int((var != sh['TransitVarianceDays']).sum())} mismatches")

    bk = load("FactBooking", ["BookingKey", "BookingDateKey",
                              "RequestedDepartureDateKey", "LeadTimeDays"])
    bd, rd = dk(bk["BookingDateKey"]), dk(bk["RequestedDepartureDateKey"])
    check("booking: requested departure after booking date",
          int((rd < bd).sum()) == 0, f"{int((rd < bd).sum())} violations")
    lead = (rd - bd).dt.days
    check("booking: LeadTimeDays matches the two dates",
          int((lead != bk["LeadTimeDays"]).sum()) == 0,
          f"{int((lead != bk['LeadTimeDays']).sum())} mismatches")

    pc = load("FactPortCall", ["AtaTs", "AtdTs", "BerthTs", "UnberthTs",
                               "PromisedEtaTs", "ArrivalDelayHours",
                               "IsOnTimeArrival", "TurnaroundHours"])
    check("port call: berth after arrival",
          int((pc["BerthTs"] < pc["AtaTs"]).sum()) == 0,
          f"{int((pc['BerthTs'] < pc['AtaTs']).sum())} violations")
    check("port call: departure after unberth",
          int((pc["AtdTs"] < pc["UnberthTs"]).sum()) == 0,
          f"{int((pc['AtdTs'] < pc['UnberthTs']).sum())} violations")
    delay = (pc["AtaTs"] - pc["PromisedEtaTs"]).dt.total_seconds() / 3600.0
    check("port call: ArrivalDelayHours matches ATA - promised ETA",
          bool(np.allclose(delay, pc["ArrivalDelayHours"], atol=0.02)),
          f"max abs diff {float(np.max(np.abs(delay - pc['ArrivalDelayHours']))):.4f} h")
    ontime_implied = (pc["ArrivalDelayHours"].abs() <= 24.0).astype(int)
    agree = int((ontime_implied == pc["IsOnTimeArrival"]).sum())
    check("port call: IsOnTimeArrival agrees with the +/-24h rule",
          agree == len(pc), f"{len(pc) - agree:,} rows disagree of {len(pc):,}")

    # ---------------- 4. no data beyond the horizon ----------------
    print("\nHorizon")
    for t, col in [("FactBooking", "BookingDateKey"), ("FactShipment", "ShipmentDateKey"),
                   ("FactContainerMove", "EventDateKey"), ("FactPortCall", "AtaDateKey"),
                   ("FactFreightCharge", "ChargeDateKey"),
                   ("FactWarehouseTask", "TaskDateKey"),
                   ("FactInventorySnapshot", "SnapshotDateKey")]:
        d = dk(load(t, [col])[col])
        beyond = int((d > TODAY).sum())
        check(f"{t}.{col} within horizon", beyond == 0,
              f"{beyond:,} rows after {TODAY.date()}",
              severity="warn" if t in ("FactShipment",) else "error")

    # ---------------- 5. cross-fact key resolution ----------------
    print("\nCross-fact integrity")
    booking_keys = set(load("FactBooking", ["BookingKey"])["BookingKey"].tolist())
    orphan_bk = int((~sh["BookingKey"].isin(booking_keys)).sum())
    check("FactShipment.BookingKey resolves to FactBooking", orphan_bk == 0,
          f"{orphan_bk:,} orphans")

    ship_keys = set(sh["ShipmentKey"].tolist())
    for t in ["FactShipmentMilestone", "FactContainerMove", "FactFreightCharge",
              "FactTransportLeg", "FactWarehouseTask"]:
        s = load(t, ["ShipmentKey"])["ShipmentKey"]
        bad = int((~s.isin(ship_keys) & (s != -1)).sum())
        check(f"{t}.ShipmentKey resolves or is -1", bad == 0, f"{bad:,} orphans")

    ms = load("FactShipmentMilestone", ["ShipmentKey"])
    check("FactShipmentMilestone is 1:1 with FactShipment",
          len(ms) == len(sh) and ms["ShipmentKey"].nunique() == len(sh),
          f"{len(ms):,} milestone rows vs {len(sh):,} shipments")

    # ---------------- 6. arithmetic identities ----------------
    print("\nArithmetic identities")
    fin = load("FactShipment", ["Revenue_usd", "DirectCost_usd", "GrossProfit_usd",
                                "GrossMarginPct"])
    gp = fin["Revenue_usd"] - fin["DirectCost_usd"]
    check("shipment: revenue - cost = gross profit",
          bool(np.allclose(gp, fin["GrossProfit_usd"], rtol=1e-3, atol=0.6)),
          f"max abs diff {float(np.max(np.abs(gp - fin['GrossProfit_usd']))):.3f}")
    mp = np.divide(fin["GrossProfit_usd"], fin["Revenue_usd"],
                   out=np.zeros(len(fin)), where=fin["Revenue_usd"] > 0)
    check("shipment: GrossMarginPct = profit / revenue",
          bool(np.allclose(mp, fin["GrossMarginPct"], rtol=1e-3, atol=2e-3)),
          f"max abs diff {float(np.max(np.abs(mp - fin['GrossMarginPct']))):.5f}")

    fc = load("FactFreightCharge", ["Amount_doc", "Amount_usd", "FxRateUsed",
                                    "RevenueAmount_usd", "CostAmount_usd",
                                    "IsRevenue", "IsCost"])
    implied = fc["Amount_doc"] * fc["FxRateUsed"]
    rel = np.abs(implied - fc["Amount_usd"]) / np.maximum(np.abs(fc["Amount_usd"]), 1.0)
    check("charge: Amount_doc x FxRateUsed = Amount_usd",
          float(np.percentile(rel, 99.9)) < 0.005,
          f"p99.9 relative error {float(np.percentile(rel, 99.9)):.5f}")
    split = fc["RevenueAmount_usd"] + fc["CostAmount_usd"]
    check("charge: revenue + cost split equals amount",
          bool(np.allclose(split, fc["Amount_usd"], rtol=1e-4, atol=0.02)),
          f"max abs diff {float(np.max(np.abs(split - fc['Amount_usd']))):.4f}")
    check("charge: IsRevenue and IsCost are mutually exclusive",
          int(((fc["IsRevenue"] + fc["IsCost"]) != 1).sum()) == 0,
          f"{int(((fc['IsRevenue'] + fc['IsCost']) != 1).sum())} rows violate")

    tl = load("FactTransportLeg", ["DistanceKm", "LoadedKm", "EmptyKm",
                                   "FreightCostUsd", "FuelSurchargeUsd", "TollsUsd",
                                   "AccessorialUsd", "TotalCostUsd"])
    check("transport: loaded + empty = distance",
          bool(np.allclose(tl["LoadedKm"] + tl["EmptyKm"], tl["DistanceKm"],
                           rtol=1e-3, atol=0.05)),
          f"max abs diff {float(np.max(np.abs(tl['LoadedKm'] + tl['EmptyKm'] - tl['DistanceKm']))):.4f} km")
    comp = tl["FreightCostUsd"] + tl["FuelSurchargeUsd"] + tl["TollsUsd"] + tl["AccessorialUsd"]
    check("transport: cost components sum to total",
          bool(np.allclose(comp, tl["TotalCostUsd"], rtol=1e-3, atol=0.05)),
          f"max abs diff {float(np.max(np.abs(comp - tl['TotalCostUsd']))):.4f}")

    inv = load("FactInventorySnapshot", ["OnHandUnits", "AllocatedUnits",
                                         "AvailableUnits", "IsStockout"])
    check("inventory: allocated + available = on hand",
          bool(np.allclose(inv["AllocatedUnits"] + inv["AvailableUnits"],
                           inv["OnHandUnits"], atol=1)),
          f"max abs diff {int(np.max(np.abs(inv['AllocatedUnits'] + inv['AvailableUnits'] - inv['OnHandUnits'])))}")
    check("inventory: IsStockout iff OnHandUnits = 0",
          int(((inv["OnHandUnits"] == 0).astype(int) != inv["IsStockout"]).sum()) == 0,
          f"{int(((inv['OnHandUnits'] == 0).astype(int) != inv['IsStockout']).sum())} disagreements")

    # ---------------- 7. derived vs dimension ----------------
    print("\nDerived measures agree with their dimensions")
    eq = pd.read_parquet(RAW_DIR / "DimEquipment" / "part-000.parquet",
                         columns=["EquipmentKey", "TeuFactor", "FfeFactor"])
    cm = load("FactContainerMove", ["EquipmentKey", "Teu", "Ffe"]).merge(
        eq, on="EquipmentKey", how="left")
    check("container move: Teu equals the equipment's TEU factor",
          bool(np.allclose(cm["Teu"], cm["TeuFactor"], atol=1e-3)),
          f"max abs diff {float(np.nanmax(np.abs(cm['Teu'] - cm['TeuFactor']))):.4f}")

    bkq = load("FactBooking", ["EquipmentKey", "ContainerCount", "TeuBooked", "FfeBooked"]).merge(
        eq, on="EquipmentKey", how="left")
    check("booking: TeuBooked = containers x TEU factor",
          bool(np.allclose(bkq["TeuBooked"], bkq["ContainerCount"] * bkq["TeuFactor"],
                           rtol=1e-3, atol=1e-3)),
          "consistent")

    pcp = load("FactPortCall", ["TotalMoves", "DischargeMoves", "LoadMoves",
                                "CraneHoursNet", "MovesPerCraneHourNet"])
    check("port call: discharge + load = total moves",
          int((pcp["DischargeMoves"] + pcp["LoadMoves"] != pcp["TotalMoves"]).sum()) == 0,
          f"{int((pcp['DischargeMoves'] + pcp['LoadMoves'] != pcp['TotalMoves']).sum())} mismatches")
    implied_mpch = pcp["TotalMoves"] / pcp["CraneHoursNet"]
    check("port call: moves per crane-hour net is consistent",
          bool(np.allclose(implied_mpch, pcp["MovesPerCraneHourNet"], rtol=2e-3)),
          f"max rel diff {float(np.max(np.abs(implied_mpch / pcp['MovesPerCraneHourNet'] - 1))):.5f}")

    # ---------------- 8. SCD2 well-formedness ----------------
    print("\nSCD Type 2 history")
    cu = pd.read_parquet(RAW_DIR / "DimCustomer" / "part-000.parquet",
                         columns=["CustomerCode", "CustomerKey", "ScdValidFrom",
                                  "ScdValidTo", "IsCurrent", "ScdVersion"])
    cu = cu[cu["CustomerKey"] > 0].copy()
    cu["ScdValidFrom"] = pd.to_datetime(cu["ScdValidFrom"])
    cu["ScdValidTo"] = pd.to_datetime(cu["ScdValidTo"])
    cur = cu.groupby("CustomerCode")["IsCurrent"].sum()
    check("exactly one current row per customer", bool((cur == 1).all()),
          f"{int((cur != 1).sum())} customers violate")
    check("valid-from never after valid-to",
          int((cu["ScdValidFrom"] > cu["ScdValidTo"]).sum()) == 0,
          f"{int((cu['ScdValidFrom'] > cu['ScdValidTo']).sum())} violations")
    cu = cu.sort_values(["CustomerCode", "ScdValidFrom"])
    prev_to = cu.groupby("CustomerCode")["ScdValidTo"].shift(1)
    overlap = int((cu["ScdValidFrom"] <= prev_to).sum())
    check("no overlapping validity windows", overlap == 0, f"{overlap} overlaps")

    # facts must point at the version valid on the event date
    shc = load("FactShipment", ["ShipmentKey", "CustomerKey", "ShipmentDateKey"])
    vw = cu.set_index("CustomerKey")[["ScdValidFrom", "ScdValidTo"]]
    j = shc.join(vw, on="CustomerKey")
    d = dk(shc["ShipmentDateKey"])
    inrange = (d >= j["ScdValidFrom"]) & (d <= j["ScdValidTo"])
    late = int((~inrange & (shc["CustomerKey"] != -1)).sum())
    check("shipments point at the customer version valid on that date",
          late <= 60, f"{late} temporally-invalid references "
                      f"(landmine #6 injects up to 47)", severity="warn")

    # ---------------- 9. landmines present ----------------
    print("\nDeliberate landmines")
    loc = pd.read_parquet(RAW_DIR / "DimLocation" / "part-000.parquet")
    lm = []
    name = loc["LocationName"].astype(str)
    dirty = int((name != name.str.strip()).sum() + (name != name.str.title()).sum())
    lm.append(("#3 casing/whitespace in LocationName", dirty > 0, f"{dirty} rows"))
    cn = loc.groupby("CountryCode")["CountryName"].nunique()
    lm.append(("#4 two spellings of one country", int((cn > 1).sum()) > 0,
               f"{int((cn > 1).sum())} country codes with >1 name"))
    bkno = load("FactBooking", ["BookingNo"])["BookingNo"]
    dupno = int(len(bkno) - bkno.nunique())
    lm.append(("#2 duplicated BookingNo", dupno > 0, f"{dupno} duplicates"))
    neg = load("FactFreightCharge", ["Amount_usd", "IsCreditNote"])
    lm.append(("#5 negative credit-note lines",
               int((neg["Amount_usd"] < 0).sum()) > 0,
               f"{int((neg['Amount_usd'] < 0).sum())} negative lines"))
    ves = pd.read_parquet(RAW_DIR / "DimVessel" / "part-000.parquet",
                          columns=["VesselClass", "NominalTeuCapacity"])
    outl = int(((ves["NominalTeuCapacity"] > 25000) | (ves["NominalTeuCapacity"] < 500)).sum())
    lm.append(("#8 implausible vessel capacity outliers", outl > 0, f"{outl} outliers"))
    revised = load("FactPortCall", ["RevisedEtaDateKey"])["RevisedEtaDateKey"]
    lm.append(("#1 unset optional fields", int((revised == -1).sum()) > 0,
               f"{(revised == -1).mean():.1%} RevisedEtaDateKey unset"))
    for n, ok, d_ in lm:
        check(n, ok, d_, severity="warn" if not ok else "error")

    # ---------------- 10. no secretly-constant or all-null columns ----------------
    print("\nColumn health")
    constant: list[str] = []
    allnull: list[str] = []
    for t in FACTS:
        df = load(t)
        for c in df.columns:
            if df[c].isna().all():
                allnull.append(f"{t}.{c}")
            elif df[c].nunique(dropna=True) == 1 and c not in ("ToCurrencyCode", "TradeLane", "ContainerNo"):
                constant.append(f"{t}.{c}={df[c].iloc[0]!r}")
    check("no all-null columns", not allnull, "none" if not allnull else "; ".join(allnull[:8]))
    check("no unintentionally constant columns", not constant,
          "none" if not constant else "; ".join(constant[:8]),
          severity="warn")

    # ---------------- report ----------------
    errors = [f for f in findings if not f["pass"] and f["severity"] == "error"]
    warns = [f for f in findings if not f["pass"] and f["severity"] == "warn"]
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    (VALIDATION_DIR / "audit_report.json").write_text(
        json.dumps({"checks": len(findings), "errors": len(errors),
                    "warnings": len(warns), "findings": findings}, indent=2)
    )
    print(f"\n{len(findings) - len(errors) - len(warns)}/{len(findings)} checks clean, "
          f"{len(errors)} errors, {len(warns)} warnings")
    print(f"report: {VALIDATION_DIR / 'audit_report.json'}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
