"""meridian.dims -- the 19 dimension builders.

Every `build_dim_*` function implements one section of
`00_docs/SCHEMA_CONTRACT.md` SS1 and returns a pandas DataFrame whose column
names, dtypes and row count match that section exactly. Each function's
docstring names the section it implements.

Unknown-member convention: per SCHEMA_CONTRACT.md SS0 and the generator brief,
every dimension carries a `-1` / `#NA` / `Unknown` row except `DimDate` and
`DimTime`. Two dimensions are deliberate exceptions to that default because
the contract pins their row count to a *closed, real-world-grounded code
list* with no `#NA` slot in the enumeration itself (unlike e.g. `DimMode`,
whose listed codes already include a literal `#NA`, or `DimIncoterm`, whose
header says "11 + Unknown" outright):

- `DimScenario` (SS1.19): exactly 4 rows -- ACT/BUD/FCT/PLN, no unknown row.
- `DimMilestone` (SS1.13): exactly 42 DCSA event codes, no unknown row.

This is documented again in the final build report.
"""
from __future__ import annotations

import datetime as dt
import string
from typing import Any

import numpy as np
import pandas as pd

from . import config as _cfg
from . import util

# =========================================================================== #
# Small shared constants (named, not magic numbers scattered through logic)
# =========================================================================== #

_TITLE_CASE_UNKNOWN = _cfg.UNKNOWN_NAME
_CODE_UNKNOWN = _cfg.UNKNOWN_CODE

_DAYS_PER_WEEK = 7
_HOURS_PER_DAY = 24
_MINUTES_PER_HOUR = 60
_MINUTES_PER_DAY = _HOURS_PER_DAY * _MINUTES_PER_HOUR  # 1440 -> DimTime row count

# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _real_rows_target(total_rows: int, has_unknown: bool = True) -> int:
    """Given the contract's stated total row count, return how many *real*
    (non-unknown) rows to synthesize, per the module-level convention above.
    """
    return total_rows - 1 if has_unknown else total_rows


def _finalize(
    df: pd.DataFrame,
    key_col: str,
    dtype_spec: dict[str, str],
    add_unknown: bool = True,
    overrides: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Assign surrogate keys 1..N, enforce dtypes, and (usually) prepend the
    unknown member. Shared tail-end of every builder.
    """
    df = df.reset_index(drop=True).copy()
    df[key_col] = np.arange(1, len(df) + 1, dtype="int32")
    df = util.enforce_dtypes(df, dtype_spec)
    if add_unknown:
        df = util.add_unknown_member(df, key_col, overrides=overrides)
        df = util.enforce_dtypes(df, dtype_spec)
    return df


def _clean_title_whitespace_landmine(
    rng: np.random.Generator, values: pd.Series, rate: float
) -> pd.Series:
    """Landmine #3: mixed casing + trailing whitespace on `rate` of rows.

    Applied directly to the column values (both parquet and CSV mirror carry
    it -- SCHEMA_CONTRACT.md SS3.5 does not scope it to "mirror CSV" the way
    it does landmines #7 and #10).
    """
    values = values.astype(str).copy()
    n = len(values)
    n_dirty = int(round(n * rate))
    if n_dirty == 0:
        return values
    dirty_idx = rng.choice(n, size=n_dirty, replace=False)
    manglers = rng.integers(0, 3, size=n_dirty)  # 0=upper, 1=lower, 2=mixed-pad
    out = values.to_numpy(copy=True)
    for pos, mangler in zip(dirty_idx, manglers):
        original = out[pos]
        if mangler == 0:
            mangled = original.upper()
        elif mangler == 1:
            mangled = original.lower()
        else:
            mangled = original.swapcase()
        out[pos] = f"  {mangled}  \t"
    return pd.Series(out, index=values.index)


# =========================================================================== #
# 1.1 DimDate
# =========================================================================== #

_FISCAL_QUARTER_LENGTH_MONTHS = 3
_LNY_DOWN_WEEKS = 2
_LNY_UP_WEEKS = 2
_LNY_WINDOW_WEEKS = _LNY_DOWN_WEEKS + _LNY_UP_WEEKS


def build_dim_date(cfg: _cfg.Config) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.1 DimDate -- 1,461 rows, 2023-01-01..2026-12-31.

    No unknown member (per the generator brief, DimDate/DimTime are exempt).
    """
    dates = pd.date_range(cfg.dimdate_start_date, cfg.dimdate_end_date, freq="D")
    anchor = pd.Timestamp(cfg.current_anchor_date)
    iso = dates.isocalendar()
    iso_year = iso["year"].to_numpy()
    iso_week = iso["week"].to_numpy()

    fiscal_year = np.where(
        dates.month.to_numpy() >= cfg.fiscal_year_start_month, dates.year.to_numpy() + 1, dates.year.to_numpy()
    )
    fiscal_month = (dates.month.to_numpy() - cfg.fiscal_year_start_month) % 12 + 1
    fiscal_quarter = (fiscal_month - 1) // _FISCAL_QUARTER_LENGTH_MONTHS + 1

    monday_of_date = dates - pd.to_timedelta(dates.dayofweek.to_numpy(), unit="D")
    monday_of_anchor = anchor - pd.Timedelta(days=int(anchor.dayofweek))

    lny_flags = np.zeros(len(dates), dtype=bool)
    for lny in _cfg.LUNAR_NEW_YEAR_DATES:
        lny_ts = pd.Timestamp(lny)
        week_start = lny_ts - pd.Timedelta(days=int(lny_ts.dayofweek))
        window_start = week_start
        window_end = week_start + pd.Timedelta(weeks=_LNY_WINDOW_WEEKS) - pd.Timedelta(days=1)
        lny_flags |= (dates >= window_start) & (dates <= window_end)

    df = pd.DataFrame(
        {
            "DateKey": util.to_date_key(pd.Series(dates)),
            "Date": dates.date,
            "Year": dates.year.astype("int16"),
            "Quarter": dates.quarter.astype("int8"),
            "QuarterName": "Q" + dates.quarter.astype(str),
            "Month": dates.month.astype("int8"),
            "MonthName": dates.month_name(),
            "MonthShort": dates.strftime("%b"),
            "MonthYear": dates.strftime("%b %Y"),
            "MonthYearSort": (dates.year.astype("int32") * 100 + dates.month.astype("int32")).astype("int32"),
            "Day": dates.day.astype("int8"),
            "DayName": dates.day_name(),
            "DayShort": dates.strftime("%a"),
            "DayOfWeek": (dates.dayofweek + 1).astype("int8"),
            "DayOfYear": dates.dayofyear.astype("int16"),
            "ISOWeek": iso_week.astype("int8"),
            "ISOYear": iso_year.astype("int16"),
            "ISOWeekLabel": pd.Series(iso_year).astype(str) + "-W" + pd.Series(iso_week).astype(str).str.zfill(2),
            "ISOWeekSort": (iso_year.astype("int32") * 100 + iso_week.astype("int32")).astype("int32"),
            "FiscalYear": fiscal_year.astype("int16"),
            "FiscalQuarter": fiscal_quarter.astype("int8"),
            "FiscalMonth": fiscal_month.astype("int8"),
            "FiscalYearLabel": "FY" + pd.Series(fiscal_year % 100).astype(str).str.zfill(2),
            "IsWeekend": dates.dayofweek.isin([5, 6]).astype("int8"),
            "IsMonthEnd": dates.is_month_end.astype("int8"),
            "IsQuarterEnd": dates.is_quarter_end.astype("int8"),
            "YearOffset": (dates.year.to_numpy() - anchor.year).astype("int16"),
            "MonthOffset": (
                (dates.year.to_numpy() - anchor.year) * 12 + (dates.month.to_numpy() - anchor.month)
            ).astype("int16"),
            "WeekOffset": (((monday_of_date - monday_of_anchor).days) // _DAYS_PER_WEEK).astype("int16"),
            "DayOffset": (dates - anchor).days.astype("int32"),
            "IsCurrentYear": (dates.year.to_numpy() == anchor.year).astype("int8"),
            "IsCurrentMonth": (
                (dates.year.to_numpy() == anchor.year) & (dates.month.to_numpy() == anchor.month)
            ).astype("int8"),
            "IsLunarNewYearWindow": lny_flags.astype("int8"),
            "IsPeakSeason": dates.month.isin(_cfg.PEAK_SEASON_MONTHS).astype("int8"),
        }
    )
    return df


# =========================================================================== #
# 1.2 DimTime
# =========================================================================== #

_SHIFT_A_START_MIN = 6 * _MINUTES_PER_HOUR    # 06:00
_SHIFT_B_START_MIN = 14 * _MINUTES_PER_HOUR   # 14:00
_SHIFT_C_START_MIN = 22 * _MINUTES_PER_HOUR   # 22:00
_PORT_WINDOW_START_MIN = 6 * _MINUTES_PER_HOUR   # 06:00
_PORT_WINDOW_END_MIN = 22 * _MINUTES_PER_HOUR    # 22:00 inclusive
_SHIFT_KEY_BY_NAME = {"A": 1, "B": 2, "C": 3}


def build_dim_time(cfg: _cfg.Config) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.2 DimTime -- 1,440 rows, minute grain.

    No unknown member (per the generator brief, DimDate/DimTime are exempt).
    """
    hours = np.repeat(np.arange(_HOURS_PER_DAY), _MINUTES_PER_HOUR)
    minutes = np.tile(np.arange(_MINUTES_PER_HOUR), _HOURS_PER_DAY)
    total_min = hours * _MINUTES_PER_HOUR + minutes

    hour12 = hours % 12
    hour12 = np.where(hour12 == 0, 12, hour12)
    ampm = np.where(hours < 12, "AM", "PM")
    hour12_label = [f"{h} {m}" for h, m in zip(hour12, ampm)]

    shift_name = np.where(
        (total_min >= _SHIFT_A_START_MIN) & (total_min < _SHIFT_B_START_MIN),
        "A",
        np.where((total_min >= _SHIFT_B_START_MIN) & (total_min < _SHIFT_C_START_MIN), "B", "C"),
    )
    shift_key = np.array([_SHIFT_KEY_BY_NAME[s] for s in shift_name], dtype="int8")
    half_hour_bucket = [f"{h:02d}:{'00' if m < 30 else '30'}" for h, m in zip(hours, minutes)]

    df = pd.DataFrame(
        {
            "TimeKey": (hours * 100 + minutes).astype("int32"),
            "Time": [dt.time(int(h), int(m)) for h, m in zip(hours, minutes)],
            "Hour": hours.astype("int8"),
            "Minute": minutes.astype("int8"),
            "Hour12Label": hour12_label,
            "ShiftName": shift_name,
            "ShiftKey": shift_key,
            "IsNightShift": (shift_name == "C").astype("int8"),
            "HalfHourBucket": half_hour_bucket,
            "PortWorkingWindow": (
                (total_min >= _PORT_WINDOW_START_MIN) & (total_min <= _PORT_WINDOW_END_MIN)
            ).astype("int8"),
        }
    )
    return df


# =========================================================================== #
# 1.18 DimCurrency -- 22 rows (21 real + Unknown)
# =========================================================================== #

# (code, name, symbol, decimal_places, region_used)
_CURRENCIES: tuple[tuple[str, str, str, int, str], ...] = (
    ("USD", "US Dollar", "$", 2, "North America"),
    ("EUR", "Euro", "€", 2, "Europe"),
    ("GBP", "British Pound", "£", 2, "Europe"),
    ("CNY", "Chinese Yuan", "¥", 2, "East Asia"),
    ("JPY", "Japanese Yen", "¥", 0, "East Asia"),
    ("KRW", "South Korean Won", "₩", 0, "East Asia"),
    ("INR", "Indian Rupee", "₹", 2, "South Asia"),
    ("SGD", "Singapore Dollar", "S$", 2, "SE Asia"),
    ("HKD", "Hong Kong Dollar", "HK$", 2, "East Asia"),
    ("MYR", "Malaysian Ringgit", "RM", 2, "SE Asia"),
    ("THB", "Thai Baht", "฿", 2, "SE Asia"),
    ("VND", "Vietnamese Dong", "₫", 0, "SE Asia"),
    ("IDR", "Indonesian Rupiah", "Rp", 0, "SE Asia"),
    ("AED", "UAE Dirham", "AED", 2, "Middle East"),
    ("SAR", "Saudi Riyal", "SAR", 2, "Middle East"),
    ("AUD", "Australian Dollar", "A$", 2, "Oceania"),
    ("NZD", "New Zealand Dollar", "NZ$", 2, "Oceania"),
    ("BRL", "Brazilian Real", "R$", 2, "LatAm East"),
    ("MXN", "Mexican Peso", "MX$", 2, "LatAm West"),
    ("ZAR", "South African Rand", "R", 2, "Africa"),
    ("TRY", "Turkish Lira", "₺", 2, "Mediterranean"),
)

_DIMCURRENCY_DTYPES = {
    "CurrencyKey": "int32",
    "CurrencyCode": "str",
    "CurrencyName": "str",
    "CurrencySymbol": "str",
    "DecimalPlaces": "int8",
    "IsReportingCurrency": "int8",
    "RegionUsed": "str",
}


def build_dim_currency(cfg: _cfg.Config) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.18 DimCurrency -- 22 rows (21 real + Unknown)."""
    codes, names, symbols, decimals, regions = zip(*_CURRENCIES)
    df = pd.DataFrame(
        {
            "CurrencyCode": codes,
            "CurrencyName": names,
            "CurrencySymbol": symbols,
            "DecimalPlaces": np.array(decimals, dtype="int8"),
            "IsReportingCurrency": (np.array(codes) == "USD").astype("int8"),
            "RegionUsed": regions,
        }
    )
    return _finalize(df, "CurrencyKey", _DIMCURRENCY_DTYPES)


# =========================================================================== #
# 1.11 DimIncoterm -- 12 rows (11 + Unknown)
# =========================================================================== #

# (code, name, group, mode_applicability, seller_risk_ends_at, who_pays_main_carriage,
#  who_insures, is_sea_only)
_INCOTERMS: tuple[tuple[str, str, str, str, str, str, str, int], ...] = (
    ("EXW", "Ex Works", "E", "Any Mode", "Seller's Premises", "Buyer", "Not Required", 0),
    ("FCA", "Free Carrier", "F", "Any Mode", "Named Place (Carrier)", "Buyer", "Not Required", 0),
    ("FAS", "Free Alongside Ship", "F", "Sea and Inland Waterway", "Alongside Vessel", "Buyer", "Not Required", 1),
    ("FOB", "Free on Board", "F", "Sea and Inland Waterway", "On Board Vessel", "Buyer", "Not Required", 1),
    ("CFR", "Cost and Freight", "C", "Sea and Inland Waterway", "On Board Vessel", "Seller", "Not Required", 1),
    ("CIF", "Cost, Insurance and Freight", "C", "Sea and Inland Waterway", "On Board Vessel", "Seller", "Seller", 1),
    ("CPT", "Carriage Paid To", "C", "Any Mode", "First Carrier", "Seller", "Not Required", 0),
    ("CIP", "Carriage and Insurance Paid To", "C", "Any Mode", "First Carrier", "Seller", "Seller", 0),
    ("DAP", "Delivered at Place", "D", "Any Mode", "Named Destination", "Seller", "Not Required", 0),
    ("DPU", "Delivered at Place Unloaded", "D", "Any Mode", "Named Destination, Unloaded", "Seller", "Not Required", 0),
    ("DDP", "Delivered Duty Paid", "D", "Any Mode", "Named Destination, Duty Paid", "Seller", "Not Required", 0),
)

_DIMINCOTERM_DTYPES = {
    "IncotermKey": "int32",
    "IncotermCode": "str",
    "IncotermName": "str",
    "IncotermGroup": "str",
    "ModeApplicability": "str",
    "SellerRiskEndsAt": "str",
    "WhoPaysMainCarriage": "str",
    "WhoInsures": "str",
    "IsSeaOnly": "int8",
    "SortOrder": "int8",
}


def build_dim_incoterm(cfg: _cfg.Config) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.11 DimIncoterm -- 12 rows (11 + Unknown)."""
    cols = list(zip(*_INCOTERMS))
    df = pd.DataFrame(
        {
            "IncotermCode": cols[0],
            "IncotermName": cols[1],
            "IncotermGroup": cols[2],
            "ModeApplicability": cols[3],
            "SellerRiskEndsAt": cols[4],
            "WhoPaysMainCarriage": cols[5],
            "WhoInsures": cols[6],
            "IsSeaOnly": np.array(cols[7], dtype="int8"),
            "SortOrder": np.arange(1, len(_INCOTERMS) + 1, dtype="int8"),
        }
    )
    return _finalize(df, "IncotermKey", _DIMINCOTERM_DTYPES, overrides={"SortOrder": 99})


# =========================================================================== #
# 1.12 DimChargeType -- 48 rows (47 real + Unknown)
# =========================================================================== #

# (code, name, category, revenue_or_cost, is_accessorial, is_pass_through, is_surcharge,
#  is_dd, charge_basis, applies_to_mode, is_credit_note_eligible)
_CHARGE_TYPES: tuple[tuple[str, str, str, str, int, int, int, int, str, str, int], ...] = (
    ("OFR", "Ocean Freight", "Base Freight", "Revenue", 0, 0, 0, 0, "Per Container", "Ocean", 1),
    ("BAF", "Bunker Adjustment Factor", "Fuel Surcharge", "Revenue", 1, 0, 1, 0, "Per Container", "Ocean", 1),
    ("THC", "Terminal Handling Charge", "Terminal", "Both", 1, 1, 0, 0, "Per Container", "Ocean", 1),
    ("DEM", "Demurrage", "Detention & Demurrage", "Revenue", 1, 0, 0, 1, "Per Day", "Ocean", 1),
    ("DET", "Detention", "Detention & Demurrage", "Revenue", 1, 0, 0, 1, "Per Day", "Ocean", 1),
    ("CGS", "Container Guarantee Surcharge", "Terminal", "Cost", 1, 1, 0, 0, "Per Container", "Ocean", 0),
    ("DOC", "Documentation Fee", "Documentation", "Revenue", 1, 0, 0, 0, "Per B/L", "All", 1),
    ("ISPS", "ISPS Security Fee", "Security", "Both", 1, 1, 0, 0, "Per Container", "Ocean", 1),
    ("VGM", "VGM Declaration Fee", "Documentation", "Revenue", 1, 0, 0, 0, "Per Container", "Ocean", 1),
    ("LSS", "Low Sulphur Surcharge", "Fuel Surcharge", "Revenue", 1, 0, 1, 0, "Per Container", "Ocean", 1),
    ("PSS", "Peak Season Surcharge", "Other", "Revenue", 1, 0, 1, 0, "Per Container", "Ocean", 1),
    ("CAF", "Currency Adjustment Factor", "Other", "Revenue", 1, 0, 1, 0, "Per Container", "Ocean", 1),
    ("EBS", "Emergency Bunker Surcharge", "Fuel Surcharge", "Revenue", 1, 0, 1, 0, "Per Container", "Ocean", 1),
    ("WRS", "War Risk Surcharge", "Security", "Revenue", 1, 0, 1, 0, "Per Container", "Ocean", 1),
    ("AMS", "AMS Filing Fee", "Customs", "Both", 1, 1, 0, 0, "Per B/L", "Ocean", 0),
    ("ENS", "ENS Filing Fee", "Customs", "Both", 1, 1, 0, 0, "Per B/L", "Ocean", 0),
    ("CFS", "CFS Handling Fee", "Warehousing", "Both", 1, 1, 0, 0, "Per CBM", "Warehouse", 1),
    ("DRY", "Dry Container Usage Fee", "Equipment", "Cost", 1, 0, 0, 0, "Per Container", "Ocean", 0),
    ("RAI", "Rail Haulage Charge", "Inland", "Both", 0, 0, 0, 0, "Per Container", "Rail", 1),
    ("WHS", "Warehousing Storage Fee", "Warehousing", "Revenue", 1, 0, 0, 0, "Per Day", "Warehouse", 1),
    ("PIC", "Container Pickup Charge", "Inland", "Both", 1, 0, 0, 0, "Per Container", "Road", 1),
    ("AIR", "Air Freight", "Base Freight", "Revenue", 0, 0, 0, 0, "Per KG", "Air", 1),
    ("FSC", "Air Fuel Surcharge", "Fuel Surcharge", "Revenue", 1, 0, 1, 0, "Per KG", "Air", 1),
    ("SSC", "Security Surcharge", "Security", "Revenue", 1, 0, 1, 0, "Per KG", "Air", 1),
    ("CUS", "Customs Clearance Fee", "Customs", "Both", 1, 1, 0, 0, "Per Shipment", "All", 1),
    ("INS", "Insurance Premium", "Insurance", "Revenue", 1, 0, 0, 0, "Per Shipment", "All", 0),
    ("ERS", "Empty Repositioning Surcharge", "Equipment", "Cost", 1, 0, 1, 0, "Per Container", "Ocean", 0),
    ("GRI", "General Rate Increase", "Base Freight", "Revenue", 0, 0, 1, 0, "Per Container", "Ocean", 1),
    ("CCF", "Container Cleaning Fee", "Equipment", "Cost", 1, 0, 0, 0, "Per Container", "Ocean", 0),
    ("CDF", "Chassis Usage Fee", "Equipment", "Both", 1, 0, 0, 0, "Per Day", "Road", 1),
    ("REP", "Container Repair Fee", "Equipment", "Cost", 1, 0, 0, 0, "Per Container", "Ocean", 0),
    ("PLF", "Port Lift Fee", "Terminal", "Cost", 1, 1, 0, 0, "Per Container", "Ocean", 0),
    ("WFG", "Wharfage Fee", "Terminal", "Both", 1, 1, 0, 0, "Per TEU", "Ocean", 1),
    ("PCS", "Panama Canal Surcharge", "Other", "Revenue", 1, 0, 1, 0, "Per Container", "Ocean", 1),
    ("SCS", "Suez Canal Surcharge", "Other", "Revenue", 1, 0, 1, 0, "Per Container", "Ocean", 1),
    ("GOH", "Genset Monitoring Fee", "Equipment", "Cost", 1, 0, 0, 0, "Per Day", "Ocean", 0),
    ("REE", "Reefer Plug-in Fee", "Equipment", "Both", 1, 0, 0, 0, "Per Day", "Ocean", 1),
    ("HAZ", "Hazmat Handling Fee", "Other", "Both", 1, 1, 0, 0, "Per Container", "All", 1),
    ("OWS", "Overweight Surcharge", "Other", "Revenue", 1, 0, 1, 0, "Per Container", "Ocean", 1),
    ("LOLO", "Lift On/Lift Off Charge", "Terminal", "Cost", 1, 1, 0, 0, "Per Container", "Ocean", 0),
    ("TRK", "Drayage/Trucking Charge", "Inland", "Both", 0, 0, 0, 0, "Per Container", "Road", 1),
    ("FUM", "Fumigation Fee", "Other", "Both", 1, 1, 0, 0, "Per Container", "All", 0),
    ("SEA", "Seal Fee", "Documentation", "Cost", 1, 1, 0, 0, "Per Container", "Ocean", 0),
    ("BLF", "Bill of Lading Fee", "Documentation", "Revenue", 1, 0, 0, 0, "Per B/L", "All", 1),
    ("AMF", "Advance Manifest Fee", "Customs", "Cost", 1, 1, 0, 0, "Per Shipment", "All", 0),
    ("EXA", "Export Customs Declaration", "Customs", "Both", 1, 1, 0, 0, "Per Shipment", "All", 1),
    ("CRN", "Credit Note Adjustment", "Other", "Revenue", 0, 0, 0, 0, "Flat", "All", 1),
)

_DIMCHARGETYPE_DTYPES = {
    "ChargeTypeKey": "int32",
    "ChargeCode": "str",
    "ChargeName": "str",
    "ChargeCategory": "str",
    "RevenueOrCost": "str",
    "IsAccessorial": "int8",
    "IsPassThrough": "int8",
    "IsSurcharge": "int8",
    "IsDemurrageOrDetention": "int8",
    "ChargeBasis": "str",
    "AppliesToMode": "str",
    "IsCreditNoteEligible": "int8",
    "SortOrder": "int16",
}


def build_dim_charge_type(cfg: _cfg.Config) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.12 DimChargeType -- 48 rows (47 real + Unknown)."""
    cols = list(zip(*_CHARGE_TYPES))
    df = pd.DataFrame(
        {
            "ChargeCode": cols[0],
            "ChargeName": cols[1],
            "ChargeCategory": cols[2],
            "RevenueOrCost": cols[3],
            "IsAccessorial": np.array(cols[4], dtype="int8"),
            "IsPassThrough": np.array(cols[5], dtype="int8"),
            "IsSurcharge": np.array(cols[6], dtype="int8"),
            "IsDemurrageOrDetention": np.array(cols[7], dtype="int8"),
            "ChargeBasis": cols[8],
            "AppliesToMode": cols[9],
            "IsCreditNoteEligible": np.array(cols[10], dtype="int8"),
            "SortOrder": np.arange(1, len(_CHARGE_TYPES) + 1, dtype="int16"),
        }
    )
    return _finalize(df, "ChargeTypeKey", _DIMCHARGETYPE_DTYPES, overrides={"SortOrder": 999})


# =========================================================================== #
# 1.14 DimMode -- 8 rows (7 real + explicit "#NA" -- already the 8th ModeCode)
# =========================================================================== #

# (code, name, group, is_consolidated, chargeable_weight_rule, transit_band, co2_g_per_tonne_km)
_MODES: tuple[tuple[str, str, str, int, str, str, float], ...] = (
    ("FCL", "Full Container Load", "Ocean", 0, "Ocean 1:1000", "15-35 days", 11.0),
    ("LCL", "Less than Container Load", "Ocean", 1, "Ocean 1:1000", "18-40 days", 16.0),
    ("AIR", "Air Freight", "Air", 0, "Air 1:6000", "1-5 days", 500.0),
    ("ROA", "Road Freight", "Land", 0, "Actual Weight", "1-7 days", 62.0),
    ("RAI", "Rail Freight", "Land", 0, "Actual Weight", "3-10 days", 22.0),
    ("BAR", "Barge / Inland Waterway", "Land", 0, "Actual Weight", "2-6 days", 31.0),
    ("MMD", "Multimodal", "Multimodal", 1, "Actual Weight", "5-20 days", 80.0),
)

_DIMMODE_DTYPES = {
    "ModeKey": "int32",
    "ModeCode": "str",
    "ModeName": "str",
    "ModeGroup": "str",
    "IsConsolidated": "int8",
    "ChargeableWeightRule": "str",
    "TypicalTransitDaysBand": "str",
    "Co2GramsPerTonneKm": "float32",
    "SortOrder": "int8",
}


def build_dim_mode(cfg: _cfg.Config) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.14 DimMode -- 8 rows; `#NA` is explicitly listed
    as the 8th ModeCode value, so the unknown member fills that slot exactly.
    """
    cols = list(zip(*_MODES))
    df = pd.DataFrame(
        {
            "ModeCode": cols[0],
            "ModeName": cols[1],
            "ModeGroup": cols[2],
            "IsConsolidated": np.array(cols[3], dtype="int8"),
            "ChargeableWeightRule": cols[4],
            "TypicalTransitDaysBand": cols[5],
            "Co2GramsPerTonneKm": np.array(cols[6], dtype="float32"),
            "SortOrder": np.arange(1, len(_MODES) + 1, dtype="int8"),
        }
    )
    return _finalize(df, "ModeKey", _DIMMODE_DTYPES, overrides={"SortOrder": 8})


# =========================================================================== #
# 1.19 DimScenario -- exactly 4 rows, no unknown member (see module docstring)
# =========================================================================== #

_SCENARIOS: tuple[tuple[str, str], ...] = (
    ("ACT", "Actual"),
    ("BUD", "Budget"),
    ("FCT", "Forecast"),
    ("PLN", "Plan"),
)

_DIMSCENARIO_DTYPES = {
    "ScenarioKey": "int32",
    "ScenarioCode": "str",
    "ScenarioName": "str",
    "SortOrder": "int8",
}


def build_dim_scenario(cfg: _cfg.Config) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.19 DimScenario -- exactly 4 rows (ACT/BUD/FCT/PLN).

    Deliberate exception to the generic unknown-member rule: see the module
    docstring for why.
    """
    codes, names = zip(*_SCENARIOS)
    df = pd.DataFrame(
        {
            "ScenarioCode": codes,
            "ScenarioName": names,
            "SortOrder": np.arange(1, len(_SCENARIOS) + 1, dtype="int8"),
        }
    )
    return _finalize(df, "ScenarioKey", _DIMSCENARIO_DTYPES, add_unknown=False)


# =========================================================================== #
# 1.13 DimMilestone -- exactly 42 DCSA-aligned event codes, no unknown member
# =========================================================================== #

_MILESTONE_SEQUENCE_BY_GROUP: dict[str, tuple[int, int]] = {
    "Documentation": (1, 4),
    "Origin": (5, 9),
    "Main Carriage": (10, 14),
    "Transhipment": (15, 16),
    "Destination": (17, 20),
}

_PLANNED_CLASSIFIER_CODES = frozenset({"DRFT", "PEND", "SUBM", "HOLD", "NOTF"})
_ESTIMATED_CLASSIFIER_CODES = frozenset({"WAYP"})

_CODECO_CODES = frozenset(
    {"GTIN", "GTOT", "PICK", "DROP", "STUF", "STRP", "INSP", "RSEA", "AVPU", "AVDO", "EMTY", "FULL"}
)
_BAPLIE_CODES = frozenset({"LOAD", "DISC"})
_IFTSTA_CODES = frozenset({"ARRI", "DEPA", "BERT", "UNBR", "WAYP", "XFER", "TRAN", "RAIO", "RAII", "NOTF", "DLVR"})
_IFTMIN_CODES = frozenset({"SUBM", "COMP", "AMND", "CANC", "HOLD"})
_IFTMBF_CODES = frozenset({"ISSU", "SURR", "APPR", "REJE", "RELS"})
_COPARN_CODES = frozenset({"RECE", "DRFT", "PEND", "CONF"})

# (code, name, journey, group, customer_visible, is_sla)
_MILESTONES: tuple[tuple[str, str, str, str, int, int], ...] = (
    ("GTIN", "Gate In", "Equipment", "Origin", 1, 1),
    ("GTOT", "Gate Out", "Equipment", "Origin", 1, 1),
    ("LOAD", "Vessel Load", "Equipment", "Main Carriage", 0, 1),
    ("DISC", "Vessel Discharge", "Equipment", "Destination", 0, 1),
    ("STUF", "Container Stuffing", "Equipment", "Origin", 0, 0),
    ("STRP", "Container Stripping", "Equipment", "Destination", 0, 0),
    ("PICK", "Empty Container Pickup", "Equipment", "Origin", 1, 1),
    ("DROP", "Empty Container Drop-off", "Equipment", "Destination", 1, 1),
    ("INSP", "Equipment Inspection", "Equipment", "Origin", 1, 0),
    ("CUSR", "Customs Release", "Equipment", "Destination", 1, 1),
    ("RSEA", "Seal Affixed", "Equipment", "Origin", 0, 0),
    ("AVPU", "Available for Pickup", "Equipment", "Destination", 1, 0),
    ("AVDO", "Available for Drop-off", "Equipment", "Origin", 1, 0),
    ("RAIO", "Rail Loaded", "Equipment", "Main Carriage", 0, 0),
    ("RAII", "Rail Discharged", "Equipment", "Main Carriage", 0, 0),
    ("EXPT", "Export Customs Cleared", "Equipment", "Origin", 1, 0),
    ("IMPT", "Import Customs Cleared", "Equipment", "Destination", 1, 0),
    ("EMTY", "Empty Container Returned", "Equipment", "Destination", 1, 0),
    ("FULL", "Full Container Gated In", "Equipment", "Origin", 0, 0),
    ("ARRI", "Vessel Arrival", "Transport", "Main Carriage", 1, 1),
    ("DEPA", "Vessel Departure", "Transport", "Main Carriage", 1, 1),
    ("BERT", "Vessel Berthed", "Transport", "Main Carriage", 0, 0),
    ("UNBR", "Vessel Unberthed", "Transport", "Main Carriage", 0, 0),
    ("WAYP", "Waypoint Passed", "Transport", "Transhipment", 0, 0),
    ("XFER", "Transhipment Transfer", "Transport", "Transhipment", 0, 0),
    ("TRAN", "In Transit at Transhipment Port", "Transport", "Transhipment", 0, 0),
    ("CONF", "Booking Confirmed", "Shipment", "Documentation", 1, 0),
    ("ISSU", "Bill of Lading Issued", "Shipment", "Documentation", 1, 0),
    ("SURR", "Bill of Lading Surrendered", "Shipment", "Documentation", 1, 0),
    ("APPR", "Booking Approved", "Shipment", "Documentation", 1, 0),
    ("REJE", "Booking Rejected", "Shipment", "Documentation", 1, 0),
    ("RECE", "Cargo Received", "Shipment", "Origin", 1, 0),
    ("DRFT", "Draft Bill of Lading Issued", "Shipment", "Documentation", 0, 0),
    ("PEND", "Booking Pending", "Shipment", "Documentation", 0, 0),
    ("SUBM", "Booking Submitted", "Shipment", "Documentation", 1, 0),
    ("COMP", "Shipment Completed", "Shipment", "Destination", 1, 1),
    ("AMND", "Booking Amended", "Shipment", "Documentation", 1, 0),
    ("CANC", "Booking Cancelled", "Shipment", "Documentation", 1, 0),
    ("HOLD", "Shipment On Hold", "Shipment", "Documentation", 1, 0),
    ("RELS", "Cargo Released", "Shipment", "Documentation", 1, 1),
    ("NOTF", "Arrival Notice Sent", "Shipment", "Destination", 1, 0),
    ("DLVR", "Cargo Delivered", "Shipment", "Destination", 1, 1),
)

_DIMMILESTONE_DTYPES = {
    "MilestoneKey": "int32",
    "EventCode": "str",
    "EventName": "str",
    "EventJourney": "str",
    "EventClassifier": "str",
    "MilestoneSequence": "int8",
    "MilestoneGroup": "str",
    "IsCustomerVisible": "int8",
    "IsSlaMilestone": "int8",
    "EdifactMessageType": "str",
}


def _milestone_classifier(code: str) -> str:
    if code in _PLANNED_CLASSIFIER_CODES:
        return "Planned"
    if code in _ESTIMATED_CLASSIFIER_CODES:
        return "Estimated"
    return "Actual"


def _milestone_edifact(code: str) -> str:
    if code in _CODECO_CODES:
        return "CODECO"
    if code in _BAPLIE_CODES:
        return "BAPLIE"
    if code in _COPARN_CODES:
        return "COPARN"
    if code in _IFTMIN_CODES:
        return "IFTMIN"
    if code in _IFTMBF_CODES:
        return "IFTMBF"
    if code in _IFTSTA_CODES:
        return "IFTSTA"
    return _CODE_UNKNOWN


def build_dim_milestone(cfg: _cfg.Config) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.13 DimMilestone -- exactly 42 DCSA-aligned event
    codes. Deliberate exception to the generic unknown-member rule: see the
    module docstring for why.
    """
    group_counters: dict[str, int] = {g: 0 for g in _MILESTONE_SEQUENCE_BY_GROUP}
    sequences: list[int] = []
    for _, _, _, group, _, _ in _MILESTONES:
        lo, hi = _MILESTONE_SEQUENCE_BY_GROUP[group]
        span = hi - lo + 1
        seq = lo + (group_counters[group] % span)
        group_counters[group] += 1
        sequences.append(seq)

    codes = [m[0] for m in _MILESTONES]
    df = pd.DataFrame(
        {
            "EventCode": codes,
            "EventName": [m[1] for m in _MILESTONES],
            "EventJourney": [m[2] for m in _MILESTONES],
            "EventClassifier": [_milestone_classifier(c) for c in codes],
            "MilestoneSequence": np.array(sequences, dtype="int8"),
            "MilestoneGroup": [m[3] for m in _MILESTONES],
            "IsCustomerVisible": np.array([m[4] for m in _MILESTONES], dtype="int8"),
            "IsSlaMilestone": np.array([m[5] for m in _MILESTONES], dtype="int8"),
            "EdifactMessageType": [_milestone_edifact(c) for c in codes],
        }
    )
    return _finalize(df, "MilestoneKey", _DIMMILESTONE_DTYPES, add_unknown=False)


# =========================================================================== #
# 1.9 DimEquipment -- 60 rows (59 real + Unknown)
# =========================================================================== #

# (type_code, iso_code, name, length_ft, height_ft, family, max_payload_kg,
#  tare_kg, internal_cbm)
_EQUIPMENT_TYPES: tuple[tuple[str, str, str, int, str, str, int, int, float], ...] = (
    ("20DV", "22G1", "20ft Dry Van", 20, "8'6\"", "dry", 21750, 2230, 33.2),
    ("40DV", "42G1", "40ft Dry Van", 40, "8'6\"", "dry", 26680, 3800, 67.5),
    ("40HC", "45G1", "40ft High Cube Dry Van", 40, "9'6\"", "dry", 26580, 3900, 76.0),
    ("45HC", "L5G1", "45ft High Cube Dry Van", 45, "9'6\"", "dry", 29500, 4800, 86.0),
    ("20RF", "22R1", "20ft Reefer", 20, "8'6\"", "reefer", 27400, 3080, 28.3),
    ("40RH", "45R1", "40ft High Cube Reefer", 40, "9'6\"", "reefer", 29000, 4800, 59.3),
    ("20TK", "22T1", "20ft Tank Container", 20, "8'6\"", "special", 26000, 3900, 24.0),
    ("40OT", "42U1", "40ft Open Top", 40, "8'6\"", "special", 26500, 3900, 67.0),
    ("40FR", "42P1", "40ft Flat Rack", 40, "8'6\"", "special", 40000, 5600, 0.0),
    ("20FR", "22P1", "20ft Flat Rack", 20, "8'6\"", "special", 28000, 2700, 0.0),
)

_EQUIPMENT_ROWS_PER_TYPE = 6
_EQUIPMENT_FEWER_ROWS_TYPE = "20FR"  # the one type that gets 5 instead of 6 (59 real total)
_EQUIPMENT_OWNERSHIP_CYCLE = (
    "Owned",
    "Owned",
    "Leased Long-Term",
    "Leased Long-Term",
    "Leased Short-Term",
    "Shipper-Owned",
)

_FREE_DAYS_BY_FAMILY = {"dry": 5, "reefer": 3, "special": 4}
_DEMURRAGE_TIER1_BASE_BY_FAMILY = {"dry": 75.0, "reefer": 150.0, "special": 100.0}
_DETENTION_TIER1_BASE_BY_FAMILY = {"dry": 60.0, "reefer": 120.0, "special": 80.0}
_TIER2_MULTIPLIER = 2.0
_TIER3_MULTIPLIER = 4.0
_LENGTH_RATE_MULTIPLIER = {20: 1.0, 40: 1.3, 45: 1.5}
_EQUIPMENT_JITTER_FRACTION = 0.02  # +/-2% unit-to-unit variance on weight/volume

_DIMEQUIPMENT_DTYPES = {
    "EquipmentKey": "int32",
    "IsoSizeTypeCode": "str",
    "EquipmentTypeCode": "str",
    "EquipmentTypeName": "str",
    "LengthFt": "int8",
    "HeightFt": "str",
    "TeuFactor": "float32",
    "FfeFactor": "float32",
    "MaxPayloadKg": "int32",
    "TareWeightKg": "int32",
    "InternalCbm": "float32",
    "IsReefer": "int8",
    "IsTank": "int8",
    "IsOpenTop": "int8",
    "IsFlatRack": "int8",
    "IsSpecialEquipment": "int8",
    "OwnershipType": "str",
    "FreeDaysDemurrage": "int8",
    "FreeDaysDetention": "int8",
    "DailyDemurrageTier1Usd": "float32",
    "DailyDemurrageTier2Usd": "float32",
    "DailyDemurrageTier3Usd": "float32",
    "DailyDetentionTier1Usd": "float32",
    "DailyDetentionTier2Usd": "float32",
    "DailyDetentionTier3Usd": "float32",
}


def _teu_factor_for_length(length_ft: int) -> float:
    return {20: 1.0, 40: 2.0, 45: 2.25}[length_ft]


def _ffe_factor_for_length(length_ft: int) -> float:
    return {20: 0.5, 40: 1.0, 45: 1.125}[length_ft]


def build_dim_equipment(cfg: _cfg.Config) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.9 DimEquipment -- 60 rows (59 real + Unknown).

    One row per (EquipmentTypeCode, ownership pool): 6 rows for 9 of the 10
    type codes and 5 for `20FR`, giving 59 real fleet-master rows. Tier bands
    per SS1.9: dry 1-5/6-10/11+ days past free time, reefer 1-3/4-8/9+.
    """
    rng = util.child_rng("DimEquipment")
    rows: list[dict[str, Any]] = []
    for type_code, iso_code, name, length_ft, height_ft, family, payload, tare, cbm in _EQUIPMENT_TYPES:
        n_rows = _EQUIPMENT_ROWS_PER_TYPE - 1 if type_code == _EQUIPMENT_FEWER_ROWS_TYPE else _EQUIPMENT_ROWS_PER_TYPE
        demurrage_t1 = _DEMURRAGE_TIER1_BASE_BY_FAMILY[family] * _LENGTH_RATE_MULTIPLIER[length_ft]
        detention_t1 = _DETENTION_TIER1_BASE_BY_FAMILY[family] * _LENGTH_RATE_MULTIPLIER[length_ft]
        for i in range(n_rows):
            jitter = 1.0 + rng.uniform(-_EQUIPMENT_JITTER_FRACTION, _EQUIPMENT_JITTER_FRACTION)
            rows.append(
                {
                    "IsoSizeTypeCode": iso_code,
                    "EquipmentTypeCode": type_code,
                    "EquipmentTypeName": name,
                    "LengthFt": length_ft,
                    "HeightFt": height_ft,
                    "TeuFactor": _teu_factor_for_length(length_ft),
                    "FfeFactor": _ffe_factor_for_length(length_ft),
                    "MaxPayloadKg": int(round(payload * jitter)),
                    "TareWeightKg": int(round(tare * jitter)),
                    "InternalCbm": round(cbm * jitter, 1),
                    "IsReefer": int(family == "reefer"),
                    "IsTank": int(type_code == "20TK"),
                    "IsOpenTop": int(type_code == "40OT"),
                    "IsFlatRack": int(type_code in ("40FR", "20FR")),
                    "IsSpecialEquipment": int(family == "special"),
                    "OwnershipType": _EQUIPMENT_OWNERSHIP_CYCLE[i % len(_EQUIPMENT_OWNERSHIP_CYCLE)],
                    "FreeDaysDemurrage": _FREE_DAYS_BY_FAMILY[family],
                    "FreeDaysDetention": _FREE_DAYS_BY_FAMILY[family],
                    "DailyDemurrageTier1Usd": round(demurrage_t1, 2),
                    "DailyDemurrageTier2Usd": round(demurrage_t1 * _TIER2_MULTIPLIER, 2),
                    "DailyDemurrageTier3Usd": round(demurrage_t1 * _TIER3_MULTIPLIER, 2),
                    "DailyDetentionTier1Usd": round(detention_t1, 2),
                    "DailyDetentionTier2Usd": round(detention_t1 * _TIER2_MULTIPLIER, 2),
                    "DailyDetentionTier3Usd": round(detention_t1 * _TIER3_MULTIPLIER, 2),
                }
            )
    df = pd.DataFrame(rows)
    return _finalize(df, "EquipmentKey", _DIMEQUIPMENT_DTYPES)


# =========================================================================== #
# 1.10 DimCommodity -- 900 rows (899 real + Unknown), real HS structure
# =========================================================================== #

# (chapter2, chapter_name, heading4, heading_name, group, dangerous, imdg_class,
#  un_number, temp_controlled, required_temp_c, high_value, density_lo, density_hi)
# Chapter names and IMDG class / UN number pairs are real (e.g. 85 = Electrical
# machinery and equipment, 87 = Vehicles other than railway; UN1170 ethanol
# class 3, UN3480 lithium-ion batteries class 9, etc).
_COMMODITY_HEADINGS: tuple[tuple, ...] = (
    ("02", "Meat and Edible Meat Offal", "0202", "Frozen Bovine Meat", "Perishable", 0, None, None, 1, -18.0, 0, 250, 350),
    ("03", "Fish and Crustaceans, Molluscs", "0303", "Frozen Fish", "Perishable", 0, None, None, 1, -20.0, 0, 300, 450),
    ("04", "Dairy Produce; Birds' Eggs; Natural Honey", "0402", "Milk and Cream, Concentrated or Sweetened", "Perishable", 0, None, None, 0, None, 0, 500, 600),
    ("08", "Edible Fruit and Nuts", "0803", "Bananas, Fresh or Dried", "Perishable", 0, None, None, 1, 13.0, 0, 300, 400),
    ("08", "Edible Fruit and Nuts", "0805", "Citrus Fruit, Fresh or Dried", "Perishable", 0, None, None, 1, 7.0, 0, 350, 450),
    ("10", "Cereals", "1006", "Rice", "Raw Materials", 0, None, None, 0, None, 0, 750, 850),
    ("15", "Animal or Vegetable Fats and Oils", "1511", "Palm Oil and Its Fractions", "Chemical", 0, None, None, 0, None, 0, 900, 920),
    ("17", "Sugars and Sugar Confectionery", "1701", "Cane or Beet Sugar", "Consumer Goods", 0, None, None, 0, None, 0, 800, 850),
    ("18", "Cocoa and Cocoa Preparations", "1801", "Cocoa Beans, Whole or Broken", "Raw Materials", 0, None, None, 0, None, 0, 500, 600),
    ("22", "Beverages, Spirits and Vinegar", "2204", "Wine of Fresh Grapes", "Consumer Goods", 0, None, None, 0, None, 0, 950, 980),
    ("22", "Beverages, Spirits and Vinegar", "2203", "Beer Made from Malt", "Consumer Goods", 0, None, None, 0, None, 0, 980, 1000),
    ("27", "Mineral Fuels, Mineral Oils and Products of Their Distillation", "2710", "Petroleum Oils, Refined", "Chemical", 1, 3, "UN1268", 0, None, 0, 800, 900),
    ("28", "Inorganic Chemicals", "2811", "Other Inorganic Acids", "Chemical", 1, 8, "UN3264", 0, None, 0, 1100, 1400),
    ("28", "Inorganic Chemicals", "2804", "Hydrogen, Rare Gases and Other Non-Metals", "Chemical", 1, 2, "UN1049", 0, None, 0, 50, 100),
    ("29", "Organic Chemicals", "2909", "Ethers, Alcohols, Peroxides", "Chemical", 1, 3, "UN1170", 0, None, 0, 750, 900),
    ("30", "Pharmaceutical Products", "3004", "Medicaments, Mixed or Unmixed", "Chemical", 0, None, None, 1, 5.0, 1, 400, 600),
    ("31", "Fertilisers", "3105", "Mineral or Chemical Fertilisers", "Chemical", 1, 5, "UN2067", 0, None, 0, 900, 1100),
    ("33", "Essential Oils and Resinoids; Perfumery", "3303", "Perfumes and Toilet Waters", "Consumer Goods", 1, 3, "UN1266", 0, None, 1, 600, 750),
    ("34", "Soap, Organic Surface-Active Agents", "3401", "Soap and Organic Surface-Active Products", "Consumer Goods", 0, None, None, 0, None, 0, 500, 650),
    ("36", "Explosives; Pyrotechnic Products", "3604", "Fireworks, Signalling Flares", "Industrial", 1, 1, "UN0335", 0, None, 0, 600, 900),
    ("38", "Miscellaneous Chemical Products", "3808", "Insecticides, Pesticides, Disinfectants", "Chemical", 1, 6, "UN2902", 0, None, 0, 700, 950),
    ("39", "Plastics and Articles Thereof", "3901", "Polymers of Ethylene, in Primary Forms", "Industrial", 0, None, None, 0, None, 0, 400, 550),
    ("39", "Plastics and Articles Thereof", "3926", "Other Articles of Plastics", "Industrial", 0, None, None, 0, None, 0, 200, 350),
    ("40", "Rubber and Articles Thereof", "4011", "New Pneumatic Tyres, of Rubber", "Industrial", 0, None, None, 0, None, 0, 150, 250),
    ("44", "Wood and Articles of Wood", "4407", "Wood Sawn or Chipped Lengthwise", "Raw Materials", 0, None, None, 0, None, 0, 400, 600),
    ("48", "Paper and Paperboard", "4802", "Uncoated Paper and Paperboard", "Industrial", 0, None, None, 0, None, 0, 300, 450),
    ("61", "Articles of Apparel, Knitted or Crocheted", "6109", "T-Shirts, Singlets, Knitted", "Consumer Goods", 0, None, None, 0, None, 0, 100, 180),
    ("62", "Articles of Apparel, Not Knitted", "6203", "Men's Suits, Trousers, Not Knitted", "Consumer Goods", 0, None, None, 0, None, 0, 120, 200),
    ("64", "Footwear, Gaiters and the Like", "6403", "Footwear with Leather Uppers", "Consumer Goods", 0, None, None, 0, None, 0, 150, 250),
    ("72", "Iron and Steel", "7208", "Flat-Rolled Iron or Steel Products", "Raw Materials", 0, None, None, 0, None, 0, 2000, 3500),
    ("73", "Articles of Iron or Steel", "7308", "Structures and Parts of Iron/Steel", "Industrial", 0, None, None, 0, None, 0, 600, 1200),
    ("74", "Copper and Articles Thereof", "7409", "Copper Plates, Sheets and Strip", "Raw Materials", 0, None, None, 0, None, 0, 3000, 4500),
    ("76", "Aluminium and Articles Thereof", "7604", "Aluminium Bars, Rods and Profiles", "Raw Materials", 0, None, None, 0, None, 0, 900, 1500),
    ("84", "Nuclear Reactors, Boilers, Machinery and Mechanical Appliances", "8471", "Automatic Data Processing Machines", "Industrial", 0, None, None, 0, None, 1, 150, 300),
    ("84", "Nuclear Reactors, Boilers, Machinery and Mechanical Appliances", "8481", "Taps, Cocks, Valves and Similar Appliances", "Industrial", 0, None, None, 0, None, 0, 300, 500),
    ("85", "Electrical Machinery and Equipment", "8517", "Telephone Sets, Smartphones", "Consumer Goods", 0, None, None, 0, None, 1, 150, 250),
    ("85", "Electrical Machinery and Equipment", "8528", "Monitors and Projectors", "Consumer Goods", 0, None, None, 0, None, 1, 120, 220),
    ("85", "Electrical Machinery and Equipment", "8507", "Electric Accumulators (Batteries)", "Industrial", 1, 9, "UN3480", 0, None, 1, 300, 500),
    ("87", "Vehicles Other Than Railway or Tramway Rolling Stock", "8703", "Motor Cars and Other Motor Vehicles", "Automotive", 0, None, None, 0, None, 1, 250, 400),
    ("87", "Vehicles Other Than Railway or Tramway Rolling Stock", "8708", "Parts and Accessories of Motor Vehicles", "Automotive", 0, None, None, 0, None, 0, 200, 350),
    ("88", "Aircraft, Spacecraft, and Parts Thereof", "8803", "Parts of Balloons, Aircraft or Spacecraft", "Project Cargo", 0, None, None, 0, None, 1, 150, 300),
    ("89", "Ships, Boats and Floating Structures", "8907", "Other Floating Structures", "Project Cargo", 0, None, None, 0, None, 0, 400, 800),
    ("90", "Optical, Photographic, Medical Instruments", "9018", "Medical Instruments and Appliances", "Industrial", 0, None, None, 0, None, 1, 200, 350),
    ("94", "Furniture; Bedding, Mattresses", "9403", "Other Furniture and Parts Thereof", "Consumer Goods", 0, None, None, 0, None, 0, 150, 300),
    ("95", "Toys, Games and Sports Requisites", "9503", "Tricycles, Toys, Reduced-Size Models", "Consumer Goods", 0, None, None, 0, None, 0, 100, 200),
)

_COMMODITY_REAL_ROWS = 899
_COMMODITY_MODIFIERS: tuple[str, ...] = (
    "Grade A", "Grade B", "Bulk", "Retail Pack", "Industrial Grade", "Premium",
    "Standard", "Economy", "Type I", "Type II", "Type III", "Class 1",
    "Class 2", "Export Grade", "Domestic Grade", "Carton Pack", "Palletized",
    "Loose", "Refined", "Processed",
)
_MAX_20FT_PAYLOAD_KG = 21750.0    # SS1.9 20DV MaxPayloadKg, used as the weight-out constraint
_USABLE_20FT_CBM = 30.0           # usable (post-packing-loss) cube of a 20DV
_MIN_STUFF_FACTOR_TEU = 2.0

_DIMCOMMODITY_DTYPES = {
    "CommodityKey": "int32",
    "HsCode6": "str",
    "HsCode4": "str",
    "HsCode2": "str",
    "HsChapterName": "str",
    "HsHeadingName": "str",
    "CommodityName": "str",
    "CommodityGroup": "str",
    "IsDangerousGoods": "int8",
    "ImdgClass": "str",
    "UnNumber": "str",
    "IsTemperatureControlled": "int8",
    "RequiredTempC": "float32",
    "IsHighValue": "int8",
    "AvgDensityKgPerCbm": "float32",
    "TypicalStuffFactorTeu": "float32",
}


def build_dim_commodity(cfg: _cfg.Config) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.10 DimCommodity -- 900 rows (899 real + Unknown).

    899 six-digit codes are spread across `_COMMODITY_HEADINGS` (real HS
    chapter/heading names and numbers, e.g. 85 -> Electrical machinery and
    equipment, 87 -> Vehicles other than railway). Dangerous-goods headings
    carry a real IMDG class and UN number (e.g. UN3480 lithium-ion batteries,
    class 9). `TypicalStuffFactorTeu` models the classic "cubes out vs.
    weighs out" tradeoff: dense commodities hit the 20DV weight limit before
    filling its volume.
    """
    rng = util.child_rng("DimCommodity")
    n_headings = len(_COMMODITY_HEADINGS)
    base_count, remainder = divmod(_COMMODITY_REAL_ROWS, n_headings)

    rows: list[dict[str, Any]] = []
    for h_idx, heading in enumerate(_COMMODITY_HEADINGS):
        (chapter2, chapter_name, heading4, heading_name, group, dangerous, imdg_class,
         un_number, temp_controlled, required_temp_c, high_value, density_lo, density_hi) = heading
        n_sub = base_count + (1 if h_idx < remainder else 0)
        densities = rng.uniform(density_lo, density_hi, size=n_sub)
        for sub_idx in range(n_sub):
            density = float(densities[sub_idx])
            stuff_factor = max(_MIN_STUFF_FACTOR_TEU, min(_USABLE_20FT_CBM, _MAX_20FT_PAYLOAD_KG / density))
            modifier = _COMMODITY_MODIFIERS[sub_idx % len(_COMMODITY_MODIFIERS)]
            hs6 = f"{heading4}{sub_idx + 1:02d}"
            rows.append(
                {
                    "HsCode6": hs6,
                    "HsCode4": heading4,
                    "HsCode2": chapter2,
                    "HsChapterName": chapter_name,
                    "HsHeadingName": heading_name,
                    "CommodityName": f"{heading_name} - {modifier}",
                    "CommodityGroup": group,
                    "IsDangerousGoods": int(dangerous),
                    "ImdgClass": str(imdg_class) if imdg_class is not None else _CODE_UNKNOWN,
                    "UnNumber": un_number if un_number is not None else _CODE_UNKNOWN,
                    "IsTemperatureControlled": int(temp_controlled),
                    "RequiredTempC": float(required_temp_c) if required_temp_c is not None else np.nan,
                    "IsHighValue": int(high_value),
                    "AvgDensityKgPerCbm": round(density, 1),
                    "TypicalStuffFactorTeu": round(stuff_factor, 2),
                }
            )
    df = pd.DataFrame(rows)
    return _finalize(
        df,
        "CommodityKey",
        _DIMCOMMODITY_DTYPES,
        overrides={"RequiredTempC": np.nan, "ImdgClass": _CODE_UNKNOWN, "UnNumber": _CODE_UNKNOWN},
    )


# =========================================================================== #
# 1.3 DimLocation -- 420 rows (419 real + Unknown)
# =========================================================================== #

# The 58 real UN/LOCODEs enumerated in SCHEMA_CONTRACT.md SS1.3, all seaports.
# (locode, name, country_code, country_name, region, traderegion, subregion,
#  lat, lon, tz_offset, is_gateway, is_transhipment_hub, teu_capacity_m,
#  berth_count, crane_count)
_SEED_SEAPORTS: tuple[tuple, ...] = (
    ("INNSA", "Nhava Sheva (JNPT)", "IN", "India", "South Asia", "Asia", "Indian Subcontinent", 18.95, 72.95, 5.5, 1, 0, 5.6, 20, 40),
    ("INMAA", "Chennai Port", "IN", "India", "South Asia", "Asia", "Indian Subcontinent", 13.10, 80.29, 5.5, 1, 0, 1.6, 24, 20),
    ("INMUN", "Mundra Port", "IN", "India", "South Asia", "Asia", "Indian Subcontinent", 22.84, 69.72, 5.5, 1, 0, 7.5, 30, 45),
    ("INCOK", "Cochin Port", "IN", "India", "South Asia", "Asia", "Indian Subcontinent", 9.97, 76.27, 5.5, 0, 0, 1.0, 12, 10),
    ("INPAV", "Pipavav Port", "IN", "India", "South Asia", "Asia", "Indian Subcontinent", 20.92, 71.55, 5.5, 0, 0, 1.35, 8, 8),
    ("CNSHA", "Port of Shanghai", "CN", "China", "East Asia", "Asia", "Greater China", 31.23, 121.47, 8.0, 1, 1, 47.0, 90, 180),
    ("CNNGB", "Port of Ningbo-Zhoushan", "CN", "China", "East Asia", "Asia", "Greater China", 29.87, 121.55, 8.0, 1, 0, 33.5, 70, 140),
    ("CNYTN", "Yantian Port (Shenzhen)", "CN", "China", "East Asia", "Asia", "Greater China", 22.58, 114.27, 8.0, 1, 0, 14.5, 26, 60),
    ("CNTAO", "Port of Qingdao", "CN", "China", "East Asia", "Asia", "Greater China", 36.07, 120.38, 8.0, 1, 0, 24.0, 45, 90),
    ("HKHKG", "Port of Hong Kong", "HK", "Hong Kong", "East Asia", "Asia", "Greater China", 22.30, 114.17, 8.0, 1, 1, 17.0, 24, 60),
    ("SGSIN", "Port of Singapore", "SG", "Singapore", "SE Asia", "Asia", "Maritime SE Asia", 1.29, 103.85, 8.0, 1, 1, 37.0, 67, 150),
    ("MYPKG", "Port Klang", "MY", "Malaysia", "SE Asia", "Asia", "Maritime SE Asia", 3.00, 101.39, 8.0, 1, 1, 13.7, 32, 60),
    ("MYTPP", "Port of Tanjung Pelepas", "MY", "Malaysia", "SE Asia", "Asia", "Maritime SE Asia", 1.36, 103.55, 8.0, 1, 1, 10.5, 20, 50),
    ("VNSGN", "Port of Ho Chi Minh City", "VN", "Vietnam", "SE Asia", "Asia", "Mainland SE Asia", 10.78, 106.70, 7.0, 1, 0, 6.8, 22, 30),
    ("THLCH", "Laem Chabang Port", "TH", "Thailand", "SE Asia", "Asia", "Mainland SE Asia", 13.08, 100.88, 7.0, 1, 0, 8.4, 18, 35),
    ("IDJKT", "Tanjung Priok Port", "ID", "Indonesia", "SE Asia", "Asia", "Maritime SE Asia", -6.10, 106.88, 7.0, 1, 0, 7.6, 20, 35),
    ("KRPUS", "Port of Busan", "KR", "South Korea", "East Asia", "Asia", "Korean Peninsula", 35.10, 129.04, 9.0, 1, 1, 22.0, 40, 80),
    ("JPYOK", "Port of Yokohama", "JP", "Japan", "East Asia", "Asia", "Japan", 35.44, 139.64, 9.0, 1, 0, 3.0, 16, 25),
    ("JPUKB", "Port of Kobe", "JP", "Japan", "East Asia", "Asia", "Japan", 34.68, 135.20, 9.0, 0, 0, 2.9, 14, 22),
    ("TWKHH", "Port of Kaohsiung", "TW", "Taiwan", "East Asia", "Asia", "Greater China", 22.61, 120.28, 8.0, 1, 0, 10.3, 24, 40),
    ("NLRTM", "Port of Rotterdam", "NL", "Netherlands", "N Europe", "Europe", "Benelux", 51.95, 4.14, 1.0, 1, 1, 15.3, 40, 70),
    ("DEHAM", "Port of Hamburg", "DE", "Germany", "N Europe", "Europe", "Central Europe", 53.54, 9.97, 1.0, 1, 0, 8.7, 30, 55),
    ("BEANR", "Port of Antwerp-Bruges", "BE", "Belgium", "N Europe", "Europe", "Benelux", 51.26, 4.40, 1.0, 1, 1, 12.0, 28, 50),
    ("GBFXT", "Port of Felixstowe", "GB", "United Kingdom", "N Europe", "Europe", "British Isles", 51.96, 1.35, 0.0, 1, 0, 4.0, 9, 20),
    ("GBLGP", "London Gateway", "GB", "United Kingdom", "N Europe", "Europe", "British Isles", 51.51, 0.45, 0.0, 0, 0, 3.5, 6, 14),
    ("FRLEH", "Port of Le Havre", "FR", "France", "N Europe", "Europe", "Western Europe", 49.49, 0.11, 1.0, 1, 0, 2.9, 14, 24),
    ("ESVLC", "Port of Valencia", "ES", "Spain", "Mediterranean", "Europe", "Iberia", 39.44, -0.32, 1.0, 1, 1, 5.4, 20, 34),
    ("ESALG", "Port of Algeciras", "ES", "Spain", "Mediterranean", "Europe", "Iberia", 36.13, -5.44, 1.0, 1, 1, 5.1, 16, 26),
    ("ITGOA", "Port of Genoa", "IT", "Italy", "Mediterranean", "Europe", "Southern Europe", 44.41, 8.93, 1.0, 1, 0, 2.6, 14, 20),
    ("GRPIR", "Port of Piraeus", "GR", "Greece", "Mediterranean", "Europe", "Southern Europe", 37.94, 23.65, 2.0, 1, 1, 5.6, 16, 24),
    ("TRAMB", "Port of Ambarli", "TR", "Turkey", "Mediterranean", "Europe", "Southern Europe", 40.96, 28.68, 3.0, 1, 0, 3.4, 12, 18),
    ("EGPSD", "Port Said", "EG", "Egypt", "Middle East", "MEA", "North Africa", 31.26, 32.28, 2.0, 1, 1, 5.0, 14, 20),
    ("EGSUZ", "Port of Suez", "EG", "Egypt", "Middle East", "MEA", "North Africa", 29.97, 32.55, 2.0, 0, 0, 1.2, 8, 10),
    ("AEJEA", "Jebel Ali Port", "AE", "United Arab Emirates", "Middle East", "MEA", "Gulf", 25.02, 55.06, 4.0, 1, 1, 15.0, 26, 60),
    ("AEKLF", "Khalifa Port", "AE", "United Arab Emirates", "Middle East", "MEA", "Gulf", 24.81, 54.65, 4.0, 0, 0, 2.5, 8, 14),
    ("SAJED", "Jeddah Islamic Port", "SA", "Saudi Arabia", "Middle East", "MEA", "Gulf", 21.48, 39.17, 3.0, 1, 0, 7.2, 20, 32),
    ("OMSLL", "Port of Salalah", "OM", "Oman", "Middle East", "MEA", "Gulf", 16.94, 54.01, 4.0, 1, 1, 4.5, 14, 20),
    ("USLAX", "Port of Los Angeles", "US", "United States", "N America West", "Americas", "Pacific Coast", 33.74, -118.26, -8.0, 1, 0, 10.7, 27, 40),
    ("USLGB", "Port of Long Beach", "US", "United States", "N America West", "Americas", "Pacific Coast", 33.75, -118.19, -8.0, 1, 0, 9.4, 22, 36),
    ("USOAK", "Port of Oakland", "US", "United States", "N America West", "Americas", "Pacific Coast", 37.80, -122.28, -8.0, 0, 0, 2.4, 12, 18),
    ("USSEA", "Port of Seattle", "US", "United States", "N America West", "Americas", "Pacific Coast", 47.58, -122.35, -8.0, 0, 0, 2.0, 10, 14),
    ("USNYC", "Port of New York/New Jersey", "US", "United States", "N America East", "Americas", "Atlantic Coast", 40.67, -74.13, -5.0, 1, 0, 8.4, 24, 35),
    ("USSAV", "Port of Savannah", "US", "United States", "N America East", "Americas", "Atlantic Coast", 32.08, -81.10, -5.0, 1, 0, 5.6, 18, 28),
    ("USHOU", "Port of Houston", "US", "United States", "N America East", "Americas", "Gulf Coast", 29.73, -95.27, -6.0, 0, 0, 3.4, 16, 20),
    ("USCHS", "Port of Charleston", "US", "United States", "N America East", "Americas", "Atlantic Coast", 32.79, -79.92, -5.0, 0, 0, 2.7, 10, 16),
    ("CAVAN", "Port of Vancouver", "CA", "Canada", "N America West", "Americas", "Pacific Coast", 49.29, -123.11, -8.0, 1, 0, 3.5, 14, 20),
    ("CAMTR", "Port of Montreal", "CA", "Canada", "N America East", "Americas", "Atlantic Coast", 45.55, -73.55, -5.0, 0, 0, 1.7, 10, 14),
    ("MXZLO", "Port of Manzanillo", "MX", "Mexico", "LatAm West", "Americas", "North America", 19.06, -104.32, -6.0, 1, 0, 3.5, 12, 18),
    ("PABLB", "Port of Balboa", "PA", "Panama", "LatAm West", "Americas", "Central America", 8.95, -79.57, -5.0, 1, 1, 5.0, 10, 20),
    ("BRSSZ", "Port of Santos", "BR", "Brazil", "LatAm East", "Americas", "South America", -23.96, -46.33, -3.0, 1, 0, 4.5, 20, 24),
    ("BRRIG", "Port of Rio Grande", "BR", "Brazil", "LatAm East", "Americas", "South America", -32.03, -52.10, -3.0, 0, 0, 1.1, 8, 10),
    ("CLSAI", "Port of San Antonio", "CL", "Chile", "LatAm West", "Americas", "South America", -33.60, -71.62, -4.0, 1, 0, 1.8, 10, 14),
    ("PECLL", "Port of Callao", "PE", "Peru", "LatAm West", "Americas", "South America", -12.05, -77.15, -5.0, 1, 0, 2.2, 12, 16),
    ("ZADUR", "Port of Durban", "ZA", "South Africa", "Africa", "MEA", "Southern Africa", -29.87, 31.03, 2.0, 1, 0, 2.9, 16, 20),
    ("MAPTM", "Tanger Med Port", "MA", "Morocco", "Africa", "MEA", "North Africa", 35.88, -5.51, 0.0, 1, 1, 9.0, 18, 30),
    ("AUSYD", "Port Botany (Sydney)", "AU", "Australia", "Oceania", "Oceania", "Australia", -33.97, 151.23, 10.0, 1, 0, 2.8, 10, 16),
    ("AUMEL", "Port of Melbourne", "AU", "Australia", "Oceania", "Oceania", "Australia", -37.83, 144.93, 10.0, 1, 0, 3.1, 12, 18),
    ("NZAKL", "Port of Auckland", "NZ", "New Zealand", "Oceania", "Oceania", "New Zealand", -36.84, 174.77, 12.0, 0, 0, 1.0, 6, 8),
)

# Secondary/tertiary cities used to pad DimLocation up to 419 real rows,
# spread across LocationType and reusing the same country set as the seed
# seaports. (city_name, region, traderegion, subregion) -- region is given
# per-city (not per-country) so multi-coast countries (US, CA) split
# correctly between e.g. "N America West" and "N America East".
_EXTRA_CITY_POOL: dict[str, tuple[tuple[str, str, str, str], ...]] = {
    "IN": (("Delhi", "South Asia", "Asia", "Indian Subcontinent"), ("Bengaluru", "South Asia", "Asia", "Indian Subcontinent"),
           ("Kolkata", "South Asia", "Asia", "Indian Subcontinent"), ("Ahmedabad", "South Asia", "Asia", "Indian Subcontinent"),
           ("Pune", "South Asia", "Asia", "Indian Subcontinent"), ("Hyderabad", "South Asia", "Asia", "Indian Subcontinent")),
    "CN": (("Beijing", "East Asia", "Asia", "Greater China"), ("Shenzhen", "East Asia", "Asia", "Greater China"),
           ("Guangzhou", "East Asia", "Asia", "Greater China"), ("Xiamen", "East Asia", "Asia", "Greater China"),
           ("Dalian", "East Asia", "Asia", "Greater China"), ("Tianjin", "East Asia", "Asia", "Greater China")),
    "HK": (("Kwai Chung", "East Asia", "Asia", "Greater China"), ("Tsing Yi", "East Asia", "Asia", "Greater China"),
           ("Yau Tong", "East Asia", "Asia", "Greater China")),
    "SG": (("Jurong", "SE Asia", "Asia", "Maritime SE Asia"), ("Tuas", "SE Asia", "Asia", "Maritime SE Asia"),
           ("Changi", "SE Asia", "Asia", "Maritime SE Asia")),
    "MY": (("Johor Bahru", "SE Asia", "Asia", "Maritime SE Asia"), ("Penang", "SE Asia", "Asia", "Maritime SE Asia"),
           ("Kuantan", "SE Asia", "Asia", "Maritime SE Asia")),
    "VN": (("Hai Phong", "SE Asia", "Asia", "Mainland SE Asia"), ("Da Nang", "SE Asia", "Asia", "Mainland SE Asia"),
           ("Vung Tau", "SE Asia", "Asia", "Mainland SE Asia")),
    "TH": (("Bangkok", "SE Asia", "Asia", "Mainland SE Asia"), ("Songkhla", "SE Asia", "Asia", "Mainland SE Asia")),
    "ID": (("Surabaya", "SE Asia", "Asia", "Maritime SE Asia"), ("Semarang", "SE Asia", "Asia", "Maritime SE Asia"),
           ("Medan", "SE Asia", "Asia", "Maritime SE Asia")),
    "KR": (("Incheon", "East Asia", "Asia", "Korean Peninsula"), ("Gwangyang", "East Asia", "Asia", "Korean Peninsula"),
           ("Ulsan", "East Asia", "Asia", "Korean Peninsula")),
    "JP": (("Tokyo", "East Asia", "Asia", "Japan"), ("Nagoya", "East Asia", "Asia", "Japan"), ("Osaka", "East Asia", "Asia", "Japan")),
    "TW": (("Taipei", "East Asia", "Asia", "Greater China"), ("Taichung", "East Asia", "Asia", "Greater China")),
    "NL": (("Amsterdam", "N Europe", "Europe", "Benelux"), ("Vlissingen", "N Europe", "Europe", "Benelux")),
    "DE": (("Bremerhaven", "N Europe", "Europe", "Central Europe"), ("Duisburg", "N Europe", "Europe", "Central Europe")),
    "BE": (("Ghent", "N Europe", "Europe", "Benelux"), ("Zeebrugge", "N Europe", "Europe", "Benelux")),
    "GB": (("Southampton", "N Europe", "Europe", "British Isles"), ("Liverpool", "N Europe", "Europe", "British Isles"),
           ("Tilbury", "N Europe", "Europe", "British Isles")),
    "FR": (("Marseille", "N Europe", "Europe", "Western Europe"), ("Dunkirk", "N Europe", "Europe", "Western Europe")),
    "ES": (("Barcelona", "Mediterranean", "Europe", "Iberia"), ("Bilbao", "Mediterranean", "Europe", "Iberia")),
    "IT": (("La Spezia", "Mediterranean", "Europe", "Southern Europe"), ("Livorno", "Mediterranean", "Europe", "Southern Europe")),
    "GR": (("Thessaloniki", "Mediterranean", "Europe", "Southern Europe"),),
    "TR": (("Izmir", "Mediterranean", "Europe", "Southern Europe"), ("Mersin", "Mediterranean", "Europe", "Southern Europe")),
    "EG": (("Alexandria", "Middle East", "MEA", "North Africa"), ("Damietta", "Middle East", "MEA", "North Africa")),
    "AE": (("Dubai", "Middle East", "MEA", "Gulf"), ("Abu Dhabi", "Middle East", "MEA", "Gulf"), ("Sharjah", "Middle East", "MEA", "Gulf")),
    "SA": (("Dammam", "Middle East", "MEA", "Gulf"), ("Riyadh", "Middle East", "MEA", "Gulf")),
    "OM": (("Muscat", "Middle East", "MEA", "Gulf"), ("Sohar", "Middle East", "MEA", "Gulf")),
    "US": (("Miami", "N America East", "Americas", "Atlantic Coast"), ("Norfolk", "N America East", "Americas", "Atlantic Coast"),
           ("New Orleans", "N America East", "Americas", "Gulf Coast"), ("Portland", "N America West", "Americas", "Pacific Coast"),
           ("San Diego", "N America West", "Americas", "Pacific Coast"), ("Chicago", "N America East", "Americas", "Inland"),
           ("Dallas", "N America East", "Americas", "Inland"), ("Atlanta", "N America East", "Americas", "Inland")),
    "CA": (("Toronto", "N America East", "Americas", "Inland"), ("Halifax", "N America East", "Americas", "Atlantic Coast"),
           ("Calgary", "N America West", "Americas", "Inland")),
    "MX": (("Veracruz", "LatAm West", "Americas", "North America"), ("Lazaro Cardenas", "LatAm West", "Americas", "North America"),
           ("Tijuana", "LatAm West", "Americas", "North America")),
    "PA": (("Colon", "LatAm West", "Americas", "Central America"), ("Panama City", "LatAm West", "Americas", "Central America")),
    "BR": (("Rio de Janeiro", "LatAm East", "Americas", "South America"), ("Sao Paulo", "LatAm East", "Americas", "South America"),
           ("Itajai", "LatAm East", "Americas", "South America")),
    "CL": (("Valparaiso", "LatAm West", "Americas", "South America"), ("Santiago", "LatAm West", "Americas", "South America")),
    "PE": (("Lima", "LatAm West", "Americas", "South America"), ("Paita", "LatAm West", "Americas", "South America")),
    "ZA": (("Cape Town", "Africa", "MEA", "Southern Africa"), ("Port Elizabeth", "Africa", "MEA", "Southern Africa")),
    "MA": (("Casablanca", "Africa", "MEA", "North Africa"), ("Agadir", "Africa", "MEA", "North Africa")),
    "AU": (("Brisbane", "Oceania", "Oceania", "Australia"), ("Fremantle", "Oceania", "Oceania", "Australia"),
           ("Adelaide", "Oceania", "Oceania", "Australia")),
    "NZ": (("Tauranga", "Oceania", "Oceania", "New Zealand"), ("Wellington", "Oceania", "Oceania", "New Zealand")),
}

# Approximate country centroid (lat, lon) used to jitter coordinates for the
# synthetic extra locations (the seed seaports above carry real coordinates).
_COUNTRY_CENTROID: dict[str, tuple[float, float]] = {
    "IN": (21.0, 78.0), "CN": (34.0, 108.0), "HK": (22.3, 114.2), "SG": (1.35, 103.8),
    "MY": (3.1, 101.7), "VN": (14.0, 108.0), "TH": (13.7, 100.5), "ID": (-2.5, 118.0),
    "KR": (36.5, 127.8), "JP": (36.2, 138.2), "TW": (23.7, 121.0), "NL": (52.1, 5.3),
    "DE": (51.2, 10.4), "BE": (50.8, 4.5), "GB": (52.3, -1.2), "FR": (46.6, 2.2),
    "ES": (40.0, -3.7), "IT": (42.8, 12.5), "GR": (39.0, 22.0), "TR": (39.0, 35.0),
    "EG": (26.8, 30.8), "AE": (24.0, 54.0), "SA": (24.0, 45.0), "OM": (21.0, 57.0),
    "US": (39.0, -98.0), "CA": (56.0, -106.0), "MX": (23.6, -102.5), "PA": (8.5, -80.0),
    "BR": (-14.2, -51.9), "CL": (-35.7, -71.5), "PE": (-9.2, -75.0), "ZA": (-30.6, 22.9),
    "MA": (31.8, -7.1), "AU": (-25.0, 135.0), "NZ": (-41.0, 174.0),
}

_COUNTRY_TZ: dict[str, float] = {
    "IN": 5.5, "CN": 8.0, "HK": 8.0, "SG": 8.0, "MY": 8.0, "VN": 7.0, "TH": 7.0, "ID": 7.0,
    "KR": 9.0, "JP": 9.0, "TW": 8.0, "NL": 1.0, "DE": 1.0, "BE": 1.0, "GB": 0.0, "FR": 1.0,
    "ES": 1.0, "IT": 1.0, "GR": 2.0, "TR": 3.0, "EG": 2.0, "AE": 4.0, "SA": 3.0, "OM": 4.0,
    "MX": -6.0, "PA": -5.0, "BR": -3.0, "CL": -4.0, "PE": -5.0, "ZA": 2.0, "MA": 0.0,
    "AU": 10.0, "NZ": 12.0,
}
# US/CA timezone depends on coast; keyed by (country, region) instead.
_COUNTRY_REGION_TZ: dict[tuple[str, str], float] = {
    ("US", "N America West"): -8.0, ("US", "N America East"): -5.0,
    ("CA", "N America West"): -8.0, ("CA", "N America East"): -5.0,
}

# Two-spellings-of-the-same-country landmine (#4): alternate spellings used
# for a subset of rows sharing that CountryCode.
_COUNTRY_NAME_ALT: dict[str, tuple[str, str, float]] = {
    "VN": ("Vietnam", "Viet Nam", 0.5),
    "KR": ("South Korea", "Korea, Republic of", 0.5),
}

_LOCATION_TYPES: tuple[str, ...] = ("Seaport", "Inland Depot", "CFS", "Airport", "Warehouse", "Rail Terminal")
# How many *extra* (non-seed) rows of each type to generate; seed seaports
# (58) plus these sum to 419 real rows (420 - 1 unknown).
_EXTRA_LOCATION_COUNTS: dict[str, int] = {
    "Seaport": 39, "Airport": 70, "Inland Depot": 90, "CFS": 50, "Warehouse": 60, "Rail Terminal": 52,
}
_LOCATION_NAME_TEMPLATE: dict[str, str] = {
    "Seaport": "Port of {city}",
    "Inland Depot": "{city} Inland Container Depot",
    "CFS": "{city} Container Freight Station",
    "Airport": "{city} International Airport",
    "Warehouse": "{city} Logistics Park",
    "Rail Terminal": "{city} Rail Terminal",
}
_TRADE_REGION_BY_REGION: dict[str, str] = {
    "South Asia": "Asia", "East Asia": "Asia", "SE Asia": "Asia",
    "N Europe": "Europe", "Mediterranean": "Europe",
    "N America West": "Americas", "N America East": "Americas", "LatAm East": "Americas", "LatAm West": "Americas",
    "Middle East": "MEA", "Africa": "MEA", "Oceania": "Oceania",
}

_LOCATION_NAME_WHITESPACE_RATE = 0.08  # landmine #3

_DIMLOCATION_DTYPES = {
    "LocationKey": "int32",
    "LocationCode": "str",
    "LocationName": "str",
    "LocationType": "str",
    "CountryCode": "str",
    "CountryName": "str",
    "Region": "str",
    "TradeRegion": "str",
    "SubRegion": "str",
    "Latitude": "float32",
    "Longitude": "float32",
    "TimezoneOffset": "float32",
    "IsGateway": "int8",
    "IsTranshipmentHub": "int8",
    "AnnualTeuCapacityM": "float32",
    "BerthCount": "int16",
    "CraneCount": "int16",
    "IataCode": "str",
    "IsBondedFacility": "int8",
    "CustomsRegime": "str",
}


def _unique_location_code(country_code: str, city: str, used: set[str], rng: np.random.Generator) -> str:
    """Build a plausible 5-char UN/LOCODE-style code: country + 3 letters."""
    base = "".join(ch for ch in city.upper() if ch.isalpha())
    candidates = []
    if len(base) >= 3:
        candidates.append(base[:3])
        candidates.append((base[0] + base[len(base) // 2] + base[-1]))
        candidates.append(base[::2][:3].ljust(3, "X"))
    else:
        candidates.append(base.ljust(3, "X"))
    for cand in candidates:
        code = f"{country_code}{cand}"
        if code not in used:
            used.add(code)
            return code
    while True:
        letters = "".join(rng.choice(list(string.ascii_uppercase), size=3))
        code = f"{country_code}{letters}"
        if code not in used:
            used.add(code)
            return code


def _unique_iata_code(city: str, used: set[str], rng: np.random.Generator) -> str:
    base = "".join(ch for ch in city.upper() if ch.isalpha())
    candidates = [base[:3]] if len(base) >= 3 else [base.ljust(3, "X")]
    candidates.append((base[0] + base[-2] + base[-1]) if len(base) >= 3 else base.ljust(3, "X"))
    for cand in candidates:
        if cand not in used:
            used.add(cand)
            return cand
    while True:
        letters = "".join(rng.choice(list(string.ascii_uppercase), size=3))
        if letters not in used:
            used.add(letters)
            return letters


def build_dim_location(cfg: _cfg.Config) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.3 DimLocation -- 420 rows (419 real + Unknown).

    Seeds with the 58 real UN/LOCODEs enumerated in SS1.3, then pads to 419
    real rows across the other five LocationTypes using a curated pool of
    real secondary cities per country. Carries landmine #3 (mixed casing +
    trailing whitespace on 8% of `LocationName`) and landmine #4 (two
    spellings of Vietnam / South Korea's CountryName).
    """
    rng = util.child_rng("DimLocation")
    used_codes: set[str] = set()
    used_iata: set[str] = set()
    rows: list[dict[str, Any]] = []

    for locode, name, cc, cname, region, traderegion, subregion, lat, lon, tz, gw, hub, teu, berths, cranes in _SEED_SEAPORTS:
        used_codes.add(locode)
        rows.append(
            {
                "LocationCode": locode, "LocationName": name, "LocationType": "Seaport",
                "CountryCode": cc, "CountryName": cname, "Region": region, "TradeRegion": traderegion,
                "SubRegion": subregion, "Latitude": lat, "Longitude": lon, "TimezoneOffset": tz,
                "IsGateway": gw, "IsTranshipmentHub": hub, "AnnualTeuCapacityM": teu,
                "BerthCount": berths, "CraneCount": cranes, "IataCode": _CODE_UNKNOWN,
                "IsBondedFacility": 0, "CustomsRegime": "Domestic",
            }
        )

    country_codes = list(_EXTRA_CITY_POOL.keys())
    for loc_type in _LOCATION_TYPES:
        n_extra = _EXTRA_LOCATION_COUNTS[loc_type]
        countries_for_rows = rng.choice(country_codes, size=n_extra, replace=True)
        for cc in countries_for_rows:
            city, region, traderegion, subregion = _EXTRA_CITY_POOL[cc][
                rng.integers(0, len(_EXTRA_CITY_POOL[cc]))
            ]
            code = _unique_location_code(cc, city, used_codes, rng)
            centroid_lat, centroid_lon = _COUNTRY_CENTROID[cc]
            lat = float(np.clip(centroid_lat + rng.normal(0, 3.0), -85, 85))
            lon = float(((centroid_lon + rng.normal(0, 5.0)) + 180) % 360 - 180)
            tz = _COUNTRY_REGION_TZ.get((cc, region), _COUNTRY_TZ.get(cc, 0.0))

            is_seaport = loc_type == "Seaport"
            is_airport = loc_type == "Airport"
            is_gateway = int(is_seaport and rng.random() < 0.25)
            is_hub = int(is_seaport and is_gateway and rng.random() < 0.15)
            teu_cap = round(float(rng.uniform(0.3, 3.5)), 2) if is_seaport else 0.0
            berths = int(rng.integers(4, 16)) if is_seaport else 0
            cranes = int(rng.integers(6, 24)) if is_seaport else 0
            iata = _unique_iata_code(city, used_iata, rng) if is_airport else _CODE_UNKNOWN

            bonded_rate = {"Inland Depot": 0.40, "CFS": 0.45, "Warehouse": 0.30, "Airport": 0.20, "Seaport": 0.10, "Rail Terminal": 0.15}[loc_type]
            is_bonded = int(rng.random() < bonded_rate)
            if is_bonded:
                customs_regime = rng.choice(["Free Trade Zone", "Bonded"], p=[0.4, 0.6])
            else:
                customs_regime = "Domestic"

            country_name = _COUNTRY_NAME_LOOKUP[cc]
            if cc in _COUNTRY_NAME_ALT:
                primary, alt, alt_rate = _COUNTRY_NAME_ALT[cc]
                country_name = alt if rng.random() < alt_rate else primary

            rows.append(
                {
                    "LocationCode": code,
                    "LocationName": _LOCATION_NAME_TEMPLATE[loc_type].format(city=city),
                    "LocationType": loc_type,
                    "CountryCode": cc,
                    "CountryName": country_name,
                    "Region": region,
                    "TradeRegion": traderegion,
                    "SubRegion": subregion,
                    "Latitude": round(lat, 4),
                    "Longitude": round(lon, 4),
                    "TimezoneOffset": tz,
                    "IsGateway": is_gateway,
                    "IsTranshipmentHub": is_hub,
                    "AnnualTeuCapacityM": teu_cap,
                    "BerthCount": berths,
                    "CraneCount": cranes,
                    "IataCode": iata,
                    "IsBondedFacility": is_bonded,
                    "CustomsRegime": customs_regime,
                }
            )

    df = pd.DataFrame(rows)
    df["LocationName"] = _clean_title_whitespace_landmine(rng, df["LocationName"], _LOCATION_NAME_WHITESPACE_RATE)
    return _finalize(
        df,
        "LocationKey",
        _DIMLOCATION_DTYPES,
        overrides={"CustomsRegime": _CODE_UNKNOWN, "IataCode": _CODE_UNKNOWN},
    )


_COUNTRY_NAME_LOOKUP: dict[str, str] = {
    locode_row[2]: locode_row[3] for locode_row in _SEED_SEAPORTS
}


# =========================================================================== #
# 1.5 DimCarrier -- 180 rows (179 real + Unknown)
# =========================================================================== #

# Real-named carriers, for flavour and realism.
# (code, name, carrier_type, home_country_code, home_country_name, is_own_fleet)
_REAL_CARRIERS: tuple[tuple[str, str, str, str, str, int], ...] = (
    ("MGLU", "Meridian Global Logistics", "Ocean Carrier", "SG", "Singapore", 1),
    ("MAEU", "Maersk Line", "Ocean Carrier", "DK", "Denmark", 0),
    ("MSCU", "Mediterranean Shipping Company", "Ocean Carrier", "CH", "Switzerland", 0),
    ("CMDU", "CMA CGM", "Ocean Carrier", "FR", "France", 0),
    ("HLCU", "Hapag-Lloyd", "Ocean Carrier", "DE", "Germany", 0),
    ("ONEY", "Ocean Network Express", "Ocean Carrier", "JP", "Japan", 0),
    ("EGLV", "Evergreen Line", "Ocean Carrier", "TW", "Taiwan", 0),
    ("COSU", "COSCO Shipping Lines", "Ocean Carrier", "CN", "China", 0),
    ("YMLU", "Yang Ming Marine Transport", "Ocean Carrier", "TW", "Taiwan", 0),
    ("HDMU", "HMM", "Ocean Carrier", "KR", "South Korea", 0),
    ("OOLU", "OOCL", "Ocean Carrier", "HK", "Hong Kong", 0),
    ("ZIMU", "ZIM Integrated Shipping Lines", "Ocean Carrier", "IL", "Israel", 0),
    ("WHLC", "Wan Hai Lines", "Ocean Carrier", "TW", "Taiwan", 0),
    ("PILU", "Pacific International Lines", "Ocean Carrier", "SG", "Singapore", 0),
    ("ECAR", "Emirates SkyCargo", "Airline", "AE", "United Arab Emirates", 0),
    ("CPAC", "Cathay Pacific Cargo", "Airline", "HK", "Hong Kong", 0),
    ("LHCA", "Lufthansa Cargo", "Airline", "DE", "Germany", 0),
    ("SIAC", "Singapore Airlines Cargo", "Airline", "SG", "Singapore", 0),
    ("QRCA", "Qatar Airways Cargo", "Airline", "QA", "Qatar", 0),
    ("KLMC", "KLM Cargo", "Airline", "NL", "Netherlands", 0),
    ("ANAC", "ANA Cargo", "Airline", "JP", "Japan", 0),
    ("FEDX", "FedEx Express", "Airline", "US", "United States", 0),
    ("BNSF", "BNSF Railway", "Rail Operator", "US", "United States", 0),
    ("UPRR", "Union Pacific Railroad", "Rail Operator", "US", "United States", 0),
    ("DBSR", "DB Cargo", "Rail Operator", "DE", "Germany", 0),
    ("CRCT", "China Railway Container Transport", "Rail Operator", "CN", "China", 0),
)

_CARRIER_TYPE_TARGETS: dict[str, int] = {
    "Ocean Carrier": 45, "Road Haulier": 40, "Rail Operator": 20,
    "Airline": 25, "Barge Operator": 15, "Drayage": 34,
}
_CARRIER_SYNTH_PREFIXES: tuple[str, ...] = (
    "Atlas", "Orion", "Pacific Rim", "Northstar", "Continental", "Horizon", "Summit", "Apex",
    "Vantage", "Blue Wave", "Golden Gate", "Silver Line", "Crown", "Titan", "Pioneer", "Trans",
    "Delta", "Falcon", "Anchor", "Harbor", "Coastal", "Union", "Liberty", "Prime", "Cascade",
    "Ridgeline", "Ironclad", "Compass", "Beacon", "Sentinel", "Voyager", "Frontier", "Meridian Star",
    "Nova", "Zenith", "Equator", "Monsoon", "Longitude", "Latitude", "Skyline", "Redwood",
    "Amber", "Cobalt", "Granite", "Onyx", "Vertex", "Odyssey", "Solstice", "Mosaic",
)
_CARRIER_SYNTH_SUFFIX_BY_TYPE: dict[str, tuple[str, ...]] = {
    "Ocean Carrier": ("Container Lines", "Shipping Line", "Ocean Carriers", "Marine Transport"),
    "Airline": ("Air Cargo", "Airlines Cargo", "Air Freight"),
    "Rail Operator": ("Rail Freight", "Railway", "Rail Logistics"),
    "Road Haulier": ("Road Transport", "Trucking", "Freight Lines", "Haulage"),
    "Barge Operator": ("Barge Lines", "Inland Waterways", "River Transport"),
    "Drayage": ("Drayage Services", "Container Trucking", "Intermodal Services"),
}
_CARRIER_HOME_COUNTRY_POOL: tuple[tuple[str, str], ...] = (
    ("US", "United States"), ("GB", "United Kingdom"), ("DE", "Germany"), ("NL", "Netherlands"),
    ("SG", "Singapore"), ("CN", "China"), ("HK", "Hong Kong"), ("JP", "Japan"), ("KR", "South Korea"),
    ("IN", "India"), ("FR", "France"), ("ES", "Spain"), ("IT", "Italy"), ("AE", "United Arab Emirates"),
    ("AU", "Australia"), ("BR", "Brazil"), ("MX", "Mexico"), ("ZA", "South Africa"), ("CA", "Canada"),
    ("TW", "Taiwan"), ("TH", "Thailand"), ("MY", "Malaysia"), ("VN", "Vietnam"),
)
_ALLIANCE_CHOICES_FOR_OCEAN: tuple[str, ...] = ("Alliance North", "Alliance Pacific", "Independent")
_ALLIANCE_WEIGHTS_FOR_OCEAN: tuple[float, ...] = (0.35, 0.35, 0.30)
_RATE_BASIS_CHOICES: tuple[str, ...] = ("Fixed", "Index-Linked", "Spot")
_RATE_BASIS_WEIGHTS_BY_TYPE: dict[str, tuple[float, float, float]] = {
    "Ocean Carrier": (0.25, 0.55, 0.20), "Airline": (0.30, 0.30, 0.40),
    "Rail Operator": (0.55, 0.30, 0.15), "Road Haulier": (0.55, 0.15, 0.30),
    "Barge Operator": (0.60, 0.20, 0.20), "Drayage": (0.50, 0.10, 0.40),
}
_TIER_CHOICES: tuple[str, ...] = ("Tier 1", "Tier 2", "Tier 3")
_TIER_WEIGHTS: tuple[float, ...] = (0.20, 0.45, 0.35)
_INACTIVE_CARRIER_RATE = 0.05

_DIMCARRIER_DTYPES = {
    "CarrierKey": "int32",
    "CarrierCode": "str",
    "CarrierName": "str",
    "CarrierType": "str",
    "IsOwnFleet": "int8",
    "HomeCountryCode": "str",
    "HomeCountryName": "str",
    "AllianceName": "str",
    "ContractRateBasis": "str",
    "PreferredTier": "str",
    "OnTimeTargetPct": "float32",
    "IsActive": "int8",
}


def _unique_carrier_code(rng: np.random.Generator, used: set[str]) -> str:
    while True:
        code = "".join(rng.choice(list(string.ascii_uppercase), size=4))
        if code not in used:
            used.add(code)
            return code


def build_dim_carrier(cfg: _cfg.Config) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.5 DimCarrier -- 180 rows (179 real + Unknown).

    Seeds with real, recognisable carrier names (Meridian's own MGLU plus
    well-known ocean/air/rail operators) and fills the remainder with
    synthetically combined but plausible names, split across CarrierType per
    `_CARRIER_TYPE_TARGETS` (sums to 179).
    """
    rng = util.child_rng("DimCarrier")
    used_codes: set[str] = {c[0] for c in _REAL_CARRIERS}
    used_names: set[str] = {c[1] for c in _REAL_CARRIERS}

    rows: list[dict[str, Any]] = []
    for code, name, ctype, hcc, hcn, own in _REAL_CARRIERS:
        rows.append({"CarrierCode": code, "CarrierName": name, "CarrierType": ctype,
                      "IsOwnFleet": own, "HomeCountryCode": hcc, "HomeCountryName": hcn})

    real_counts_by_type = {ctype: 0 for ctype in _CARRIER_TYPE_TARGETS}
    for _, _, ctype, _, _, _ in _REAL_CARRIERS:
        real_counts_by_type[ctype] += 1

    for ctype, target in _CARRIER_TYPE_TARGETS.items():
        n_synth = target - real_counts_by_type[ctype]
        suffixes = _CARRIER_SYNTH_SUFFIX_BY_TYPE[ctype]
        for _ in range(n_synth):
            for _attempt in range(1000):
                prefix = rng.choice(_CARRIER_SYNTH_PREFIXES)
                suffix = rng.choice(suffixes)
                name = f"{prefix} {suffix}"
                if name not in used_names:
                    used_names.add(name)
                    break
            code = _unique_carrier_code(rng, used_codes)
            hcc, hcn = _CARRIER_HOME_COUNTRY_POOL[rng.integers(0, len(_CARRIER_HOME_COUNTRY_POOL))]
            rows.append({"CarrierCode": code, "CarrierName": name, "CarrierType": ctype,
                         "IsOwnFleet": 0, "HomeCountryCode": hcc, "HomeCountryName": hcn})

    df = pd.DataFrame(rows)
    n = len(df)
    is_ocean = (df["CarrierType"] == "Ocean Carrier").to_numpy()
    is_own = (df["IsOwnFleet"] == 1).to_numpy()

    alliance = np.full(n, _CODE_UNKNOWN, dtype=object)
    alliance[is_own] = "Meridian Own"
    ocean_not_own = is_ocean & ~is_own
    alliance[ocean_not_own] = rng.choice(
        _ALLIANCE_CHOICES_FOR_OCEAN, size=int(ocean_not_own.sum()), p=_ALLIANCE_WEIGHTS_FOR_OCEAN
    )

    rate_basis = np.empty(n, dtype=object)
    for ctype, weights in _RATE_BASIS_WEIGHTS_BY_TYPE.items():
        mask = (df["CarrierType"] == ctype).to_numpy()
        rate_basis[mask] = rng.choice(_RATE_BASIS_CHOICES, size=int(mask.sum()), p=weights)

    preferred_tier = rng.choice(_TIER_CHOICES, size=n, p=_TIER_WEIGHTS)
    tier_target_bonus = np.select(
        [preferred_tier == "Tier 1", preferred_tier == "Tier 2", preferred_tier == "Tier 3"],
        [6.0, 2.0, -3.0],
        default=0.0,
    )
    on_time_target = np.clip(88.0 + tier_target_bonus + rng.normal(0, 2.5, size=n), 70.0, 99.0)
    is_active = (rng.random(n) >= _INACTIVE_CARRIER_RATE).astype("int8")
    is_active[is_own] = 1

    df["AllianceName"] = alliance
    df["ContractRateBasis"] = rate_basis
    df["PreferredTier"] = preferred_tier
    df["OnTimeTargetPct"] = np.round(on_time_target, 1)
    df["IsActive"] = is_active

    return _finalize(df, "CarrierKey", _DIMCARRIER_DTYPES, overrides={"AllianceName": _CODE_UNKNOWN})


# =========================================================================== #
# 1.6 DimVessel -- 240 rows (239 real + Unknown)
# =========================================================================== #

# (class_name, teu_lo, teu_hi, loa_lo, loa_hi, beam_lo, beam_hi, draught_lo,
#  draught_hi, speed_lo, speed_hi, count)
_VESSEL_CLASS_SPECS: tuple[tuple[str, int, int, float, float, float, float, float, float, float, float, int], ...] = (
    ("Feeder", 1100, 2999, 100.0, 160.0, 20.0, 25.0, 7.0, 9.0, 16.0, 19.0, 40),
    ("Feedermax", 3000, 4499, 160.0, 210.0, 27.0, 30.0, 10.0, 11.0, 19.0, 21.0, 40),
    ("Handysize", 4500, 5999, 210.0, 230.0, 30.0, 32.0, 11.0, 12.0, 20.0, 22.0, 35),
    ("Panamax", 6000, 8499, 230.0, 290.0, 32.0, 36.0, 12.0, 13.0, 22.0, 23.0, 35),
    ("Post-Panamax", 8500, 11999, 290.0, 320.0, 40.0, 45.0, 13.0, 14.0, 23.0, 24.0, 35),
    ("Neo-Panamax", 12000, 15999, 320.0, 366.0, 48.0, 51.0, 14.0, 15.0, 23.0, 24.0, 30),
    ("ULCV", 16000, 23900, 366.0, 400.0, 51.0, 61.0, 15.0, 17.0, 22.0, 23.0, 24),
)

_VESSEL_FLAG_STATES: tuple[tuple[str, str], ...] = (
    ("PA", "Panama"), ("LR", "Liberia"), ("MH", "Marshall Islands"), ("SG", "Singapore"),
    ("HK", "Hong Kong"), ("MT", "Malta"), ("BS", "Bahamas"), ("CY", "Cyprus"),
)
_VESSEL_FUEL_TYPES: tuple[str, ...] = ("VLSFO", "LNG Dual-Fuel", "Methanol Dual-Fuel", "MGO")
_VESSEL_FUEL_WEIGHTS: tuple[float, ...] = (0.70, 0.14, 0.08, 0.08)
_VESSEL_EEXI_RATINGS: tuple[str, ...] = ("A", "B", "C", "D", "E")
_VESSEL_NAME_ADJECTIVES: tuple[str, ...] = (
    "Pacific", "Atlantic", "Northern", "Southern", "Golden", "Silver", "Grand", "Royal",
    "Eastern", "Western", "Rising", "Morning", "Evening", "Majestic", "Noble", "Bold",
    "Bright", "Steady", "Endless", "Radiant", "Amber", "Crystal", "Emerald", "Sapphire",
)
_VESSEL_NAME_NOUNS: tuple[str, ...] = (
    "Voyager", "Star", "Pioneer", "Horizon", "Explorer", "Trader", "Mariner", "Navigator",
    "Odyssey", "Endeavour", "Discovery", "Legacy", "Spirit", "Wave", "Current", "Harbour",
    "Compass", "Zenith", "Summit", "Bridge", "Frontier", "Passage", "Crossing", "Dawn",
)

_VESSEL_YEAR_MIN = 1998
_VESSEL_YEAR_MAX = 2025
_MGLU_VESSEL_SHARE = 0.18   # ~18% of the fleet is Meridian's own-brand (MGLU) tonnage
_MGLU_OWNED_RATE = 0.75     # of MGLU-operated vessels, share actually owned (rest chartered-in)
_VESSEL_TEU_OUTLIER_COUNT = 3  # landmine #8

_DIMVESSEL_DTYPES = {
    "VesselKey": "int32",
    "ImoNumber": "str",
    "VesselName": "str",
    "CallSign": "str",
    "VesselClass": "str",
    "NominalTeuCapacity": "int32",
    "ReeferPlugCount": "int16",
    "FlagCountryCode": "str",
    "FlagCountryName": "str",
    "YearBuilt": "int16",
    "DeadweightTonnes": "int32",
    "LoaMetres": "float32",
    "BeamMetres": "float32",
    "MaxDraughtMetres": "float32",
    "ServiceSpeedKnots": "float32",
    "FuelType": "str",
    "HasScrubber": "int8",
    "EexiRating": "str",
    "IsOwnedTonnage": "int8",
    "OperatorCarrierCode": "str",
}


def build_dim_vessel(cfg: _cfg.Config, dim_carrier: pd.DataFrame) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.6 DimVessel -- 240 rows (239 real + Unknown).

    Physical specs (TEU, LOA, beam, draught, speed) are drawn class-
    consistently from `_VESSEL_CLASS_SPECS` (a Feeder never gets a Panamax's
    dimensions). `OperatorCarrierCode` is drawn from `DimCarrier`'s Ocean
    Carrier rows. Landmine #8: 3 rows get an implausible NominalTeuCapacity
    that contradicts their VesselClass, injected *after* the coherent
    generation below.
    """
    rng = util.child_rng("DimVessel")
    ocean_carriers = dim_carrier[(dim_carrier["CarrierType"] == "Ocean Carrier") & (dim_carrier["CarrierKey"] > 0)]
    mglu_code = "MGLU"
    other_codes = ocean_carriers.loc[ocean_carriers["CarrierCode"] != mglu_code, "CarrierCode"].to_numpy()

    used_imo: set[str] = set()
    used_names: set[str] = set()
    used_callsigns: set[str] = set()
    rows: list[dict[str, Any]] = []

    for class_name, teu_lo, teu_hi, loa_lo, loa_hi, beam_lo, beam_hi, draught_lo, draught_hi, speed_lo, speed_hi, n in _VESSEL_CLASS_SPECS:
        teu = rng.integers(teu_lo, teu_hi + 1, size=n)
        loa = rng.uniform(loa_lo, loa_hi, size=n)
        beam = rng.uniform(beam_lo, beam_hi, size=n)
        draught = rng.uniform(draught_lo, draught_hi, size=n)
        speed = rng.uniform(speed_lo, speed_hi, size=n)
        dwt_per_teu = rng.uniform(10.0, 14.0, size=n)
        reefer_frac = rng.uniform(0.05, 0.15, size=n)
        year_built = rng.integers(_VESSEL_YEAR_MIN, _VESSEL_YEAR_MAX + 1, size=n)

        is_mglu = rng.random(n) < _MGLU_VESSEL_SHARE
        operator = np.where(is_mglu, mglu_code, rng.choice(other_codes, size=n))

        for i in range(n):
            for _attempt in range(1000):
                six_digits = f"{rng.integers(100_000, 1_000_000):06d}"  # real IMO numbers never lead with 0
                imo = util.make_imo(six_digits)
                if imo not in used_imo:
                    used_imo.add(imo)
                    break
            for _attempt in range(1000):
                name = f"{rng.choice(_VESSEL_NAME_ADJECTIVES)} {rng.choice(_VESSEL_NAME_NOUNS)}"
                if name not in used_names:
                    used_names.add(name)
                    break
            for _attempt in range(1000):
                callsign = "".join(rng.choice(list(string.ascii_uppercase + string.digits), size=6))
                if callsign not in used_callsigns:
                    used_callsigns.add(callsign)
                    break
            flag_code, flag_name = _VESSEL_FLAG_STATES[rng.integers(0, len(_VESSEL_FLAG_STATES))]
            fuel = rng.choice(_VESSEL_FUEL_TYPES, p=_VESSEL_FUEL_WEIGHTS)
            has_scrubber = int(fuel == "VLSFO" and rng.random() < 0.30)
            eexi_bias = 1 if year_built[i] >= 2018 else (-1 if year_built[i] < 2008 else 0)
            eexi_idx = int(np.clip(rng.integers(1, 4) - eexi_bias, 0, len(_VESSEL_EEXI_RATINGS) - 1))
            is_own = 1 if (operator[i] == mglu_code and rng.random() < _MGLU_OWNED_RATE) else 0

            rows.append(
                {
                    "ImoNumber": imo,
                    "VesselName": name,
                    "CallSign": callsign,
                    "VesselClass": class_name,
                    "NominalTeuCapacity": int(teu[i]),
                    "ReeferPlugCount": int(round(teu[i] * reefer_frac[i])),
                    "FlagCountryCode": flag_code,
                    "FlagCountryName": flag_name,
                    "YearBuilt": int(year_built[i]),
                    "DeadweightTonnes": int(round(teu[i] * dwt_per_teu[i])),
                    "LoaMetres": round(float(loa[i]), 1),
                    "BeamMetres": round(float(beam[i]), 1),
                    "MaxDraughtMetres": round(float(draught[i]), 2),
                    "ServiceSpeedKnots": round(float(speed[i]), 1),
                    "FuelType": fuel,
                    "HasScrubber": has_scrubber,
                    "EexiRating": _VESSEL_EEXI_RATINGS[eexi_idx],
                    "IsOwnedTonnage": is_own,
                    "OperatorCarrierCode": operator[i],
                }
            )

    df = pd.DataFrame(rows)

    # Landmine #8: 3 implausible NominalTeuCapacity outliers, injected after
    # the class-consistent generation above so they read as data-entry
    # errors rather than a legitimate part of the distribution.
    outlier_idx = rng.choice(len(df), size=_VESSEL_TEU_OUTLIER_COUNT, replace=False)
    df.loc[outlier_idx[0], "NominalTeuCapacity"] = 21000    # a Feeder-band vessel shown as ULCV-sized
    df.loc[outlier_idx[1], "NominalTeuCapacity"] = 350       # a large-class vessel shown near-empty
    df.loc[outlier_idx[2], "NominalTeuCapacity"] = 99999     # out of the contract's entire 1,100-23,900 range

    return _finalize(df, "VesselKey", _DIMVESSEL_DTYPES)


# =========================================================================== #
# 1.8 DimService -- 44 rows (43 real + Unknown)
# =========================================================================== #

# (trade_lane, code_prefix, n_services, origin_region, dest_region,
#  loop_days_lo, loop_days_hi, transit_days_lo, transit_days_hi)
_SERVICE_LANE_SPECS: tuple[tuple[str, str, int, str, str, int, int, int, int], ...] = (
    ("Asia–N Europe", "AE", 5, "East Asia", "N Europe", 77, 84, 30, 35),
    ("Asia–Mediterranean", "AM", 4, "East Asia", "Mediterranean", 63, 70, 25, 28),
    ("Transpacific East", "TP", 6, "East Asia", "N America West", 35, 42, 14, 18),
    ("Transpacific West", "TW", 3, "N America West", "East Asia", 35, 42, 14, 18),
    ("Asia–ISC", "AI", 5, "SE Asia", "South Asia", 28, 35, 10, 14),
    ("ISC–Europe", "IE", 4, "South Asia", "N Europe", 42, 49, 18, 22),
    ("Intra-Asia", "IA", 6, "SE Asia", "East Asia", 14, 21, 4, 8),
    ("Asia–MEA", "AG", 4, "East Asia", "Middle East", 28, 35, 12, 16),
    ("Europe–LatAm", "EL", 3, "N Europe", "LatAm East", 42, 49, 18, 22),
    ("Asia–LatAm", "AL", 2, "East Asia", "LatAm West", 56, 63, 30, 35),
    ("Transatlantic", "TA", 1, "N Europe", "N America East", 28, 35, 10, 14),
)

_SERVICE_FREQUENCY_CHOICES: tuple[str, ...] = ("Weekly", "Fortnightly")
_SERVICE_FREQUENCY_WEIGHTS: tuple[float, ...] = (0.75, 0.25)
_SERVICE_DAYS_PER_WEEKLY_SLOT = 7
_SERVICE_DAYS_PER_FORTNIGHTLY_SLOT = 14
_SERVICE_ALLIANCE_RATE = 0.40
_SERVICE_INACTIVE_RATE = 0.08

_DIMSERVICE_DTYPES = {
    "ServiceKey": "int32",
    "ServiceCode": "str",
    "ServiceName": "str",
    "TradeLane": "str",
    "OriginRegion": "str",
    "DestinationRegion": "str",
    "LoopDurationDays": "int16",
    "VesselsDeployed": "int8",
    "ServiceFrequency": "str",
    "NominalTransitDays": "int16",
    "IsAllianceService": "int8",
    "IsActive": "int8",
}


def build_dim_service(cfg: _cfg.Config) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.8 DimService -- 44 rows (43 real + Unknown).

    `VesselsDeployed` is derived from `LoopDurationDays` / sailing slot so the
    two roughly reconcile (weekly service on an 84-day loop needs ~12
    vessels), matching the reconciliation DimVoyage later relies on.
    """
    rng = util.child_rng("DimService")
    rows: list[dict[str, Any]] = []
    for lane, prefix, n_services, origin_region, dest_region, loop_lo, loop_hi, transit_lo, transit_hi in _SERVICE_LANE_SPECS:
        for seq in range(1, n_services + 1):
            loop_days = int(rng.integers(loop_lo, loop_hi + 1))
            transit_days = int(rng.integers(transit_lo, transit_hi + 1))
            frequency = rng.choice(_SERVICE_FREQUENCY_CHOICES, p=_SERVICE_FREQUENCY_WEIGHTS)
            slot_days = _SERVICE_DAYS_PER_WEEKLY_SLOT if frequency == "Weekly" else _SERVICE_DAYS_PER_FORTNIGHTLY_SLOT
            vessels_deployed = max(3, int(round(loop_days / slot_days)))
            rows.append(
                {
                    "ServiceCode": f"{prefix}{seq}",
                    "ServiceName": f"{lane} Loop {seq}",
                    "TradeLane": lane,
                    "OriginRegion": origin_region,
                    "DestinationRegion": dest_region,
                    "LoopDurationDays": loop_days,
                    "VesselsDeployed": vessels_deployed,
                    "ServiceFrequency": frequency,
                    "NominalTransitDays": transit_days,
                    "IsAllianceService": int(rng.random() < _SERVICE_ALLIANCE_RATE),
                    "IsActive": int(rng.random() >= _SERVICE_INACTIVE_RATE),
                }
            )
    df = pd.DataFrame(rows)
    return _finalize(df, "ServiceKey", _DIMSERVICE_DTYPES)


# =========================================================================== #
# 1.7 DimVoyage -- 6,800 rows (6,799 real + Unknown)
# =========================================================================== #

# Representative port rotation per trade lane, built entirely from real
# UN/LOCODEs seeded in DimLocation (SS1.3), in headhaul order.
_VOYAGE_ROTATION_BY_LANE: dict[str, tuple[str, ...]] = {
    "Asia–N Europe": ("CNSHA", "CNNGB", "SGSIN", "NLRTM", "DEHAM", "GBFXT"),
    "Asia–Mediterranean": ("CNSHA", "HKHKG", "SGSIN", "ESALG", "ITGOA", "GRPIR"),
    "Transpacific East": ("CNSHA", "CNNGB", "USLAX", "USLGB"),
    "Transpacific West": ("USLAX", "USOAK", "CNNGB", "CNSHA"),
    "Asia–ISC": ("SGSIN", "MYPKG", "INNSA", "INMUN"),
    "ISC–Europe": ("INNSA", "INMUN", "AEJEA", "NLRTM"),
    "Intra-Asia": ("SGSIN", "MYTPP", "THLCH", "VNSGN", "HKHKG"),
    "Asia–MEA": ("CNSHA", "SGSIN", "AEJEA", "SAJED"),
    "Europe–LatAm": ("NLRTM", "ESALG", "BRSSZ", "BRRIG"),
    "Asia–LatAm": ("CNSHA", "SGSIN", "PABLB", "CLSAI"),
    "Transatlantic": ("GBFXT", "NLRTM", "USNYC", "USSAV"),
}
# (headhaul_leg, backhaul_leg)
_VOYAGE_LEG_BY_LANE: dict[str, tuple[str, str]] = {
    "Asia–N Europe": ("Westbound", "Eastbound"),
    "Asia–Mediterranean": ("Westbound", "Eastbound"),
    "Transpacific East": ("Eastbound", "Westbound"),
    "Transpacific West": ("Westbound", "Eastbound"),
    "Asia–ISC": ("Westbound", "Eastbound"),
    "ISC–Europe": ("Westbound", "Eastbound"),
    "Intra-Asia": ("Southbound", "Northbound"),
    "Asia–MEA": ("Westbound", "Eastbound"),
    "Europe–LatAm": ("Westbound", "Eastbound"),
    "Asia–LatAm": ("Eastbound", "Westbound"),
    "Transatlantic": ("Westbound", "Eastbound"),
}
_VOYAGE_ASIA_ORIGIN_REGIONS = frozenset({"South Asia", "East Asia", "SE Asia"})
_VOYAGE_BLANK_BASE_RATE = 0.003
_VOYAGE_BLANK_LNY_RATE = 0.14
_VOYAGE_TEU_UTILIZATION_LO = 0.85
_VOYAGE_TEU_UTILIZATION_HI = 0.98
_VOYAGE_DATE_JITTER_DAYS = 2

_DIMVOYAGE_DTYPES = {
    "VoyageKey": "int32",
    "VoyageNo": "str",
    "VesselKey": "int32",
    "ServiceKey": "int32",
    "Direction": "str",
    "Leg": "str",
    "VoyageStartDateKey": "int32",
    "VoyageEndDateKey": "int32",
    "PortCallCount": "int8",
    "RotationString": "str",
    "AllocatedTeuCapacity": "int32",
    "IsBlankSailing": "int8",
    "VoyageStatus": "str",
}


def _voyage_in_lny_window(ts: pd.Timestamp) -> bool:
    """Same 4-week (2 down + 2 up) window as DimDate.IsLunarNewYearWindow."""
    for lny in _cfg.LUNAR_NEW_YEAR_DATES:
        lny_ts = pd.Timestamp(lny)
        week_start = lny_ts - pd.Timedelta(days=int(lny_ts.dayofweek))
        window_end = week_start + pd.Timedelta(weeks=_LNY_WINDOW_WEEKS) - pd.Timedelta(days=1)
        if week_start <= ts <= window_end:
            return True
    return False


def _reconcile_voyage_counts_per_service(natural_counts: list[int], target_total: int) -> list[int]:
    """Scale each service's natural voyage count so the grand total hits
    `target_total` exactly, while keeping counts roughly proportional to
    each service's frequency x loop duration (the SS1.7 reconciliation
    requirement) -- rounding remainders are absorbed by the largest
    services rather than distorting the smallest ones.
    """
    total_natural = sum(natural_counts)
    scaled = [max(1, round(c * target_total / total_natural)) for c in natural_counts]
    order = sorted(range(len(scaled)), key=lambda i: -scaled[i])
    diff = target_total - sum(scaled)
    i = 0
    while diff != 0:
        idx = order[i % len(order)]
        if diff > 0:
            scaled[idx] += 1
            diff -= 1
        elif scaled[idx] > 1:
            scaled[idx] -= 1
            diff += 1
        i += 1
    return scaled


def build_dim_voyage(
    cfg: _cfg.Config, dim_vessel: pd.DataFrame, dim_service: pd.DataFrame, dim_location: pd.DataFrame
) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.7 DimVoyage -- 6,800 rows (6,799 real + Unknown).

    Voyage counts per service reconcile with `DimService.ServiceFrequency` x
    `LoopDurationDays` (a weekly 84-day-loop service sails roughly 52x/year);
    `RotationString` is built entirely from real `DimLocation.LocationCode`
    values on that service's trade lane. ~1.5% blank sailings overall,
    concentrated in the Lunar New Year windows for Asia-origin services
    (SS3.1).
    """
    rng = util.child_rng("DimVoyage")
    real_services = dim_service[dim_service["ServiceKey"] > 0].reset_index(drop=True)
    real_vessels = dim_vessel[dim_vessel["VesselKey"] > 0]
    vessel_teu_by_key = dict(zip(real_vessels["VesselKey"], real_vessels["NominalTeuCapacity"]))
    vessel_keys = real_vessels["VesselKey"].to_numpy()

    known_codes = set(dim_location["LocationCode"])
    for ports in _VOYAGE_ROTATION_BY_LANE.values():
        missing = [p for p in ports if p not in known_codes]
        if missing:
            raise ValueError(f"DimVoyage rotation references unknown LocationCode(s): {missing}")

    total_days = (cfg.fact_end_date - cfg.fact_start_date).days + 1
    natural_counts = []
    for _, svc in real_services.iterrows():
        slot_days = _SERVICE_DAYS_PER_WEEKLY_SLOT if svc["ServiceFrequency"] == "Weekly" else _SERVICE_DAYS_PER_FORTNIGHTLY_SLOT
        natural_counts.append(max(1, round(total_days / slot_days)))
    target_total = cfg.dim_rows("DimVoyage") - 1  # 6,799 real rows
    voyages_per_service = _reconcile_voyage_counts_per_service(natural_counts, target_total)

    anchor = pd.Timestamp(cfg.current_anchor_date)
    rows: list[dict[str, Any]] = []
    for svc_idx, (_, svc) in enumerate(real_services.iterrows()):
        n_voyages = voyages_per_service[svc_idx]
        lane = svc["TradeLane"]
        rotation_ports = _VOYAGE_ROTATION_BY_LANE[lane]
        headhaul_leg, backhaul_leg = _VOYAGE_LEG_BY_LANE[lane]
        is_asia_origin = svc["OriginRegion"] in _VOYAGE_ASIA_ORIGIN_REGIONS
        loop_days = int(svc["LoopDurationDays"])
        n_pool = max(1, min(int(svc["VesselsDeployed"]), len(vessel_keys)))
        vessel_pool = rng.choice(vessel_keys, size=n_pool, replace=False)

        start_offsets = np.linspace(0, total_days - 1, n_voyages)
        for seq, offset in enumerate(start_offsets, start=1):
            start_ts = pd.Timestamp(cfg.fact_start_date) + pd.Timedelta(days=float(offset))
            direction = "Headhaul" if seq % 2 == 1 else "Backhaul"
            leg = headhaul_leg if direction == "Headhaul" else backhaul_leg
            rotation = rotation_ports if direction == "Headhaul" else tuple(reversed(rotation_ports))
            vessel_key = int(vessel_pool[(seq - 1) % len(vessel_pool)])

            jitter = int(rng.integers(-_VOYAGE_DATE_JITTER_DAYS, _VOYAGE_DATE_JITTER_DAYS + 1))
            end_ts = start_ts + pd.Timedelta(days=max(1, loop_days + jitter))

            iso = start_ts.isocalendar()
            voyage_no = f"{iso.year}W{iso.week:02d}{leg[0]}-{svc['ServiceCode']}{seq:03d}"

            blank_rate = _VOYAGE_BLANK_LNY_RATE if (is_asia_origin and _voyage_in_lny_window(start_ts)) else _VOYAGE_BLANK_BASE_RATE
            is_blank = rng.random() < blank_rate

            nominal_teu = vessel_teu_by_key.get(vessel_key, 0)
            utilization = rng.uniform(_VOYAGE_TEU_UTILIZATION_LO, _VOYAGE_TEU_UTILIZATION_HI)
            allocated_teu = 0 if is_blank else int(round(nominal_teu * utilization))

            if is_blank:
                status = "Cancelled"
            elif end_ts < anchor:
                status = "Completed"
            elif start_ts <= anchor <= end_ts:
                status = "In Progress"
            else:
                status = "Planned"

            rows.append(
                {
                    "VoyageNo": voyage_no,
                    "VesselKey": vessel_key,
                    "ServiceKey": int(svc["ServiceKey"]),
                    "Direction": direction,
                    "Leg": leg,
                    "VoyageStartDateKey": int(util.to_date_key(start_ts)),
                    "VoyageEndDateKey": int(util.to_date_key(end_ts)),
                    "PortCallCount": len(rotation),
                    "RotationString": "-".join(rotation),
                    "AllocatedTeuCapacity": allocated_teu,
                    "IsBlankSailing": int(is_blank),
                    "VoyageStatus": status,
                }
            )

    df = pd.DataFrame(rows)
    return _finalize(df, "VoyageKey", _DIMVOYAGE_DTYPES)


# =========================================================================== #
# 1.15 DimWarehouse -- 26 rows (25 real + Unknown)
# =========================================================================== #

_WAREHOUSE_TYPES: tuple[str, ...] = (
    "Distribution Centre", "Bonded Warehouse", "CFS", "Cross-Dock", "Cold Store", "Hazmat Store",
)
_WAREHOUSE_TYPE_WEIGHTS: tuple[float, ...] = (0.40, 0.20, 0.12, 0.12, 0.10, 0.06)
_WAREHOUSE_RACKING_TYPES: tuple[str, ...] = ("Selective", "Drive-In", "Push-Back", "Cantilever", "Bulk Floor Stack")
_WAREHOUSE_SHIFT_PATTERNS: tuple[str, ...] = ("2-Shift", "3-Shift", "Day Only")
_WAREHOUSE_WMS_SYSTEMS: tuple[str, ...] = ("MERIDIAN-WMS", "Client WMS", "Legacy")
_WAREHOUSE_WMS_WEIGHTS: tuple[float, ...] = (0.60, 0.25, 0.15)
_WAREHOUSE_OPERATING_MODELS: tuple[str, ...] = ("Dedicated", "Multi-User")
_WAREHOUSE_GROSS_AREA_LO, _WAREHOUSE_GROSS_AREA_HI = 5_000, 60_000
_WAREHOUSE_STORAGE_FRACTION_LO, _WAREHOUSE_STORAGE_FRACTION_HI = 0.65, 0.85
_WAREHOUSE_SQM_PER_PALLET_POSITION = 2.5
_WAREHOUSE_AUTOMATION_RATE = 0.15
_WAREHOUSE_COMMISSIONED_YEAR_LO, _WAREHOUSE_COMMISSIONED_YEAR_HI = 1995, 2024

_DIMWAREHOUSE_DTYPES = {
    "WarehouseKey": "int32",
    "WarehouseCode": "str",
    "WarehouseName": "str",
    "LocationKey": "int32",
    "WarehouseType": "str",
    "GrossAreaSqm": "int32",
    "StorageAreaSqm": "int32",
    "PalletPositions": "int32",
    "RackingType": "str",
    "DockDoorCount": "int16",
    "HasTemperatureZones": "int8",
    "TempZoneCount": "int8",
    "ShiftPattern": "str",
    "WmsSystem": "str",
    "IsAutomated": "int8",
    "CommissionedYear": "int16",
    "OperatingModel": "str",
}


def build_dim_warehouse(cfg: _cfg.Config, dim_location: pd.DataFrame) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.15 DimWarehouse -- 26 rows (25 real + Unknown).

    `LocationKey` is drawn from `DimLocation` rows whose `LocationType` is
    "Warehouse" (SS1.3 seeds enough of those to cover this comfortably).
    """
    rng = util.child_rng("DimWarehouse")
    candidate_locations = dim_location[dim_location["LocationType"] == "Warehouse"]
    n_real = cfg.dim_rows("DimWarehouse") - 1
    chosen = candidate_locations.sample(n=n_real, random_state=int(rng.integers(0, 2**31 - 1)))

    rows: list[dict[str, Any]] = []
    for _, loc in chosen.iterrows():
        wtype = rng.choice(_WAREHOUSE_TYPES, p=_WAREHOUSE_TYPE_WEIGHTS)
        city = str(loc["LocationName"]).replace(" Logistics Park", "").strip()
        gross_area = int(rng.integers(_WAREHOUSE_GROSS_AREA_LO, _WAREHOUSE_GROSS_AREA_HI))
        storage_area = int(round(gross_area * rng.uniform(_WAREHOUSE_STORAGE_FRACTION_LO, _WAREHOUSE_STORAGE_FRACTION_HI)))
        pallet_positions = int(round(storage_area / _WAREHOUSE_SQM_PER_PALLET_POSITION))
        has_temp_zones = int(wtype == "Cold Store" or rng.random() < 0.15)
        temp_zone_count = int(rng.integers(1, 4)) if has_temp_zones else 0

        rows.append(
            {
                "WarehouseCode": f"WH-{loc['LocationCode']}-01",
                "WarehouseName": f"{city} {wtype}",
                "LocationKey": int(loc["LocationKey"]),
                "WarehouseType": wtype,
                "GrossAreaSqm": gross_area,
                "StorageAreaSqm": storage_area,
                "PalletPositions": pallet_positions,
                "RackingType": rng.choice(_WAREHOUSE_RACKING_TYPES),
                "DockDoorCount": int(rng.integers(6, 41)),
                "HasTemperatureZones": has_temp_zones,
                "TempZoneCount": temp_zone_count,
                "ShiftPattern": rng.choice(_WAREHOUSE_SHIFT_PATTERNS),
                "WmsSystem": rng.choice(_WAREHOUSE_WMS_SYSTEMS, p=_WAREHOUSE_WMS_WEIGHTS),
                "IsAutomated": int(rng.random() < _WAREHOUSE_AUTOMATION_RATE),
                "CommissionedYear": int(rng.integers(_WAREHOUSE_COMMISSIONED_YEAR_LO, _WAREHOUSE_COMMISSIONED_YEAR_HI + 1)),
                "OperatingModel": rng.choice(_WAREHOUSE_OPERATING_MODELS),
            }
        )
    df = pd.DataFrame(rows)
    return _finalize(df, "WarehouseKey", _DIMWAREHOUSE_DTYPES, overrides={"LocationKey": -1})


# =========================================================================== #
# 1.4 DimCustomer -- 3,200 durable customers, ~4,180 rows via SCD2
# =========================================================================== #

_CUSTOMER_DURABLE_COUNT = 3200
_CUSTOMER_SEGMENTS: tuple[str, ...] = ("BCO", "NVOCC", "Freight Forwarder", "3PL", "SME Direct")
_CUSTOMER_SEGMENT_WEIGHTS: tuple[float, ...] = (0.35, 0.15, 0.20, 0.15, 0.15)
_INDUSTRY_VERTICALS: tuple[str, ...] = (
    "Retail", "Automotive", "Chemicals", "Electronics", "FMCG", "Pharma",
    "Agriculture", "Machinery", "Textiles", "Metals", "Energy",
)
_INDUSTRY_CORE_WORDS: dict[str, tuple[str, ...]] = {
    "Retail": ("Retail", "Mercantile", "Stores", "Trading"),
    "Automotive": ("Motors", "Automotive", "Auto Parts"),
    "Chemicals": ("Chemicals", "Chemical Industries"),
    "Electronics": ("Electronics", "Semiconductor", "Technologies"),
    "FMCG": ("Consumer Goods", "FMCG", "Foods"),
    "Pharma": ("Pharmaceuticals", "Life Sciences", "Pharma"),
    "Agriculture": ("Agro", "Agri-Foods", "Farms"),
    "Machinery": ("Machinery", "Engineering", "Industrial"),
    "Textiles": ("Textiles", "Apparel", "Garments"),
    "Metals": ("Metals", "Steel", "Alloys"),
    "Energy": ("Energy", "Petrochemicals", "Power"),
}
_COMPANY_NAME_PREFIXES: tuple[str, ...] = (
    "Sterling", "Everest", "Aurora", "Vantage", "Redwood", "Cobalt", "Granite", "Onyx", "Vertex",
    "Solstice", "Mosaic", "Beacon", "Sentinel", "Voyager", "Zenith", "Equator", "Monsoon", "Skyline",
    "Nova", "Ironbridge", "Wellspring", "Ashgrove", "Brightwater", "Cedarline", "Dockside", "Elmfield",
    "Foxrun", "Greystone", "Harborview", "Ivyhill", "Junction", "Kingswell", "Lakemoor", "Marlowe",
    "Northgate", "Oakford", "Palisade", "Quarrystone", "Ridgemont", "Southwick", "Thornwell", "Underhill",
    "Valleyforge", "Westbrook", "Ashford", "Brookline", "Clearwater", "Deerfield", "Eastridge", "Fairhaven",
    "Glenmoor", "Hillcrest", "Ironwood", "Juniper", "Kestrel", "Lonestar", "Millbrook", "Nightingale",
)
_COMPANY_NAME_SUFFIXES: tuple[str, ...] = (
    "Ltd", "Inc", "Corp", "GmbH", "Pte Ltd", "S.A.", "Group", "Holdings", "LLC", "PLC", "B.V.", "Co.",
)
_SIZE_TIERS: tuple[str, ...] = ("Global Key Account", "National", "Mid-Market", "SME")
_SIZE_TIER_NON_GKA_CHOICES: tuple[str, ...] = ("National", "Mid-Market", "SME")
_SIZE_TIER_WEIGHTS_GENERAL: tuple[float, ...] = (0.20, 0.45, 0.35)
_SIZE_TIER_WEIGHTS_CHILD: tuple[float, ...] = (0.10, 0.35, 0.55)
_GKA_RATE = 0.05
_CHILD_RATE = 0.18
_CREDIT_TIERS: tuple[str, ...] = ("A", "B", "C", "D")
_CREDIT_TIER_WEIGHTS_BY_SIZE: dict[str, tuple[float, float, float, float]] = {
    "Global Key Account": (0.55, 0.35, 0.08, 0.02),
    "National": (0.25, 0.40, 0.25, 0.10),
    "Mid-Market": (0.10, 0.30, 0.40, 0.20),
    "SME": (0.05, 0.20, 0.40, 0.35),
}
_PAYMENT_TERMS_CHOICES: tuple[int, ...] = (0, 15, 30, 45, 60)
_PAYMENT_TERMS_WEIGHTS_BY_CREDIT: dict[str, tuple[float, float, float, float, float]] = {
    "A": (0.02, 0.08, 0.30, 0.35, 0.25),
    "B": (0.05, 0.15, 0.40, 0.25, 0.15),
    "C": (0.15, 0.30, 0.40, 0.10, 0.05),
    "D": (0.35, 0.35, 0.25, 0.04, 0.01),
}
_CONTRACT_TYPES: tuple[str, ...] = ("Long-Term Contract", "Named Account Tariff", "Spot")
_CONTRACT_TYPE_WEIGHTS_BY_SIZE: dict[str, tuple[float, float, float]] = {
    "Global Key Account": (0.75, 0.20, 0.05),
    "National": (0.45, 0.35, 0.20),
    "Mid-Market": (0.25, 0.35, 0.40),
    "SME": (0.10, 0.25, 0.65),
}
_ACCOUNT_MANAGER_FIRST_NAMES: tuple[str, ...] = (
    "James", "Maria", "Wei", "Priya", "Ahmed", "Sofia", "Liam", "Yuki", "Fatima", "Carlos",
    "Anna", "Kenji", "Olivia", "Raj", "Elena", "Marco", "Grace", "Hassan", "Ingrid", "Diego",
)
_ACCOUNT_MANAGER_LAST_NAMES: tuple[str, ...] = (
    "Nguyen", "Silva", "Chen", "Sharma", "Al-Farsi", "Rossi", "O'Brien", "Tanaka", "Haddad", "Ramirez",
    "Kowalski", "Yamamoto", "Novak", "Patel", "Larsson", "Ferreira", "Kim", "Osei", "Berg", "Torres",
)
_N_ACCOUNT_MANAGERS = 50
_CUSTOMER_HQ_POOL: tuple[tuple[str, str, str, str], ...] = (
    ("IN", "India", "South Asia", "APAC"), ("CN", "China", "East Asia", "APAC"),
    ("HK", "Hong Kong", "East Asia", "APAC"), ("SG", "Singapore", "SE Asia", "APAC"),
    ("MY", "Malaysia", "SE Asia", "APAC"), ("VN", "Vietnam", "SE Asia", "APAC"),
    ("TH", "Thailand", "SE Asia", "APAC"), ("ID", "Indonesia", "SE Asia", "APAC"),
    ("KR", "South Korea", "East Asia", "APAC"), ("JP", "Japan", "East Asia", "APAC"),
    ("TW", "Taiwan", "East Asia", "APAC"), ("NL", "Netherlands", "N Europe", "EMEA"),
    ("DE", "Germany", "N Europe", "EMEA"), ("BE", "Belgium", "N Europe", "EMEA"),
    ("GB", "United Kingdom", "N Europe", "EMEA"), ("FR", "France", "N Europe", "EMEA"),
    ("ES", "Spain", "Mediterranean", "EMEA"), ("IT", "Italy", "Mediterranean", "EMEA"),
    ("TR", "Turkey", "Mediterranean", "EMEA"), ("AE", "United Arab Emirates", "Middle East", "EMEA"),
    ("SA", "Saudi Arabia", "Middle East", "EMEA"), ("ZA", "South Africa", "Africa", "EMEA"),
    ("US", "United States", "N America East", "Americas"), ("CA", "Canada", "N America East", "Americas"),
    ("MX", "Mexico", "LatAm West", "Americas"), ("BR", "Brazil", "LatAm East", "Americas"),
    ("CL", "Chile", "LatAm West", "Americas"), ("AU", "Australia", "Oceania", "ANZ"),
    ("NZ", "New Zealand", "Oceania", "ANZ"),
)
_CUSTOMER_ONBOARD_EARLIEST = dt.date(2015, 1, 1)
_CUSTOMER_ONBOARD_WITHIN_WINDOW_RATE = 0.30  # rest onboarded before the fact window (long-standing)
_CUSTOMER_SCD_EXTRA_VERSIONS_CHOICES: tuple[int, ...] = (0, 1, 2)
_CUSTOMER_SCD_EXTRA_VERSIONS_WEIGHTS: tuple[float, ...] = (0.70, 0.29375, 0.00625)
_SCD2_TRIGGER_COLUMNS: tuple[str, ...] = ("AccountManager", "CreditTier", "SizeTier", "ContractType")
_SENTINEL_END_DATE = dt.date(9999, 12, 31)

_DIMCUSTOMER_DTYPES = {
    "CustomerKey": "int32",
    "CustomerCode": "str",
    "CustomerName": "str",
    "CustomerSegment": "str",
    "IndustryVertical": "str",
    "SizeTier": "str",
    "ParentCustomerCode": "str",
    "ParentCustomerName": "str",
    "HqCountryCode": "str",
    "HqCountryName": "str",
    "HqRegion": "str",
    "SalesRegion": "str",
    "AccountManager": "str",
    "AccountManagerEmail": "str",
    "CreditTier": "str",
    "PaymentTermsDays": "int16",
    "ContractType": "str",
    "OnboardedDate": "object",
    "ScdValidFrom": "object",
    "ScdValidTo": "object",
    "IsCurrent": "int8",
    "ScdVersion": "int8",
}


def _weighted_pick(rng: np.random.Generator, choices: tuple, weights: tuple) -> Any:
    return choices[int(rng.choice(len(choices), p=weights))]


def build_dim_customer(cfg: _cfg.Config) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.4 DimCustomer -- 3,200 durable customers, ~4,180
    rows via SCD2 on AccountManager/CreditTier/SizeTier/ContractType.

    ~18% of customers are children of a ~5%-of-population pool of "Global
    Key Account" parents (parent linkage is a durable attribute, not an
    SCD2 trigger, so it never changes across a customer's versions).
    """
    rng = util.child_rng("DimCustomer")
    n = _CUSTOMER_DURABLE_COUNT

    manager_first = rng.choice(_ACCOUNT_MANAGER_FIRST_NAMES, size=_N_ACCOUNT_MANAGERS)
    manager_last = rng.choice(_ACCOUNT_MANAGER_LAST_NAMES, size=_N_ACCOUNT_MANAGERS)
    manager_names = [f"{f} {l}" for f, l in zip(manager_first, manager_last)]
    manager_emails = [f"{f.lower().replace(chr(39), '')}.{l.lower().replace(chr(39), '')}@meridiangl.com" for f, l in zip(manager_first, manager_last)]

    codes = [f"CUS{i:04d}" for i in range(1, n + 1)]
    segments = rng.choice(_CUSTOMER_SEGMENTS, size=n, p=_CUSTOMER_SEGMENT_WEIGHTS)
    verticals = rng.choice(_INDUSTRY_VERTICALS, size=n)

    used_names: set[str] = set()
    names = []
    for i in range(n):
        vertical = verticals[i]
        for _attempt in range(1000):
            prefix = rng.choice(_COMPANY_NAME_PREFIXES)
            core = rng.choice(_INDUSTRY_CORE_WORDS[vertical])
            suffix = rng.choice(_COMPANY_NAME_SUFFIXES)
            candidate = f"{prefix} {core} {suffix}"
            if candidate not in used_names:
                used_names.add(candidate)
                names.append(candidate)
                break

    hq_idx = rng.integers(0, len(_CUSTOMER_HQ_POOL), size=n)
    hq_cc = np.array([_CUSTOMER_HQ_POOL[j][0] for j in hq_idx])
    hq_cn = np.array([_CUSTOMER_HQ_POOL[j][1] for j in hq_idx])
    hq_region = np.array([_CUSTOMER_HQ_POOL[j][2] for j in hq_idx])
    sales_region = np.array([_CUSTOMER_HQ_POOL[j][3] for j in hq_idx])

    is_gka = rng.random(n) < _GKA_RATE
    non_gka_idx = np.flatnonzero(~is_gka)
    n_children = int(round(_CHILD_RATE * n))
    child_idx = rng.choice(non_gka_idx, size=min(n_children, len(non_gka_idx)), replace=False)
    is_child = np.zeros(n, dtype=bool)
    is_child[child_idx] = True
    gka_idx = np.flatnonzero(is_gka)
    parent_choice_for_child = rng.choice(gka_idx, size=len(child_idx), replace=True)
    parent_code = np.full(n, None, dtype=object)
    parent_name = np.full(n, None, dtype=object)
    for pos, ci in enumerate(child_idx):
        pi = parent_choice_for_child[pos]
        parent_code[ci] = codes[pi]
        parent_name[ci] = names[pi]

    base_size_tier = np.empty(n, dtype=object)
    base_size_tier[is_gka] = "Global Key Account"
    for i in range(n):
        if is_gka[i]:
            continue
        weights = _SIZE_TIER_WEIGHTS_CHILD if is_child[i] else _SIZE_TIER_WEIGHTS_GENERAL
        base_size_tier[i] = _weighted_pick(rng, _SIZE_TIER_NON_GKA_CHOICES, weights)

    base_credit_tier = np.array([_weighted_pick(rng, _CREDIT_TIERS, _CREDIT_TIER_WEIGHTS_BY_SIZE[t]) for t in base_size_tier])
    base_contract_type = np.array([_weighted_pick(rng, _CONTRACT_TYPES, _CONTRACT_TYPE_WEIGHTS_BY_SIZE[t]) for t in base_size_tier])
    base_payment_terms = np.array([_weighted_pick(rng, _PAYMENT_TERMS_CHOICES, _PAYMENT_TERMS_WEIGHTS_BY_CREDIT[t]) for t in base_credit_tier])
    base_manager_idx = rng.integers(0, _N_ACCOUNT_MANAGERS, size=n)

    window_days = (cfg.fact_end_date - _CUSTOMER_ONBOARD_EARLIEST).days
    fact_window_days = (cfg.fact_end_date - cfg.fact_start_date).days
    onboarded_dates = []
    for i in range(n):
        if rng.random() < _CUSTOMER_ONBOARD_WITHIN_WINDOW_RATE:
            offset = int(rng.integers(0, fact_window_days + 1))
            onboarded_dates.append(cfg.fact_start_date + dt.timedelta(days=offset))
        else:
            offset = int(rng.integers(0, window_days - fact_window_days + 1))
            onboarded_dates.append(_CUSTOMER_ONBOARD_EARLIEST + dt.timedelta(days=offset))

    n_extra_versions = rng.choice(
        _CUSTOMER_SCD_EXTRA_VERSIONS_CHOICES, size=n, p=_CUSTOMER_SCD_EXTRA_VERSIONS_WEIGHTS
    )

    rows: list[dict[str, Any]] = []
    for i in range(n):
        onboarded = onboarded_dates[i]
        n_versions = 1 + int(n_extra_versions[i])
        available_days = (cfg.fact_end_date - onboarded).days
        n_versions = min(n_versions, max(1, available_days))

        change_dates: list[dt.date] = []
        if n_versions > 1:
            change_offsets = sorted(rng.choice(np.arange(1, available_days + 1), size=n_versions - 1, replace=False))
            change_dates = [onboarded + dt.timedelta(days=int(off)) for off in change_offsets]
        boundaries = [onboarded, *change_dates]

        cur_manager_idx = int(base_manager_idx[i])
        cur_credit_tier = base_credit_tier[i]
        cur_size_tier = base_size_tier[i]
        cur_contract_type = base_contract_type[i]

        eligible_trigger_cols = [c for c in _SCD2_TRIGGER_COLUMNS if not (is_gka[i] and c == "SizeTier")]

        for v in range(n_versions):
            valid_from = boundaries[v]
            valid_to = boundaries[v + 1] - dt.timedelta(days=1) if v + 1 < n_versions else _SENTINEL_END_DATE
            is_current = 1 if v == n_versions - 1 else 0

            if v > 0:
                n_changing = int(rng.integers(1, len(eligible_trigger_cols) + 1))
                changing_cols = rng.choice(eligible_trigger_cols, size=n_changing, replace=False)
                if "AccountManager" in changing_cols:
                    cur_manager_idx = int(rng.integers(0, _N_ACCOUNT_MANAGERS))
                if "CreditTier" in changing_cols:
                    choices = [c for c in _CREDIT_TIERS if c != cur_credit_tier]
                    cur_credit_tier = choices[int(rng.integers(0, len(choices)))]
                if "SizeTier" in changing_cols:
                    choices = [c for c in _SIZE_TIER_NON_GKA_CHOICES if c != cur_size_tier]
                    cur_size_tier = choices[int(rng.integers(0, len(choices)))]
                if "ContractType" in changing_cols:
                    choices = [c for c in _CONTRACT_TYPES if c != cur_contract_type]
                    cur_contract_type = choices[int(rng.integers(0, len(choices)))]

            rows.append(
                {
                    "CustomerCode": codes[i],
                    "CustomerName": names[i],
                    "CustomerSegment": segments[i],
                    "IndustryVertical": verticals[i],
                    "SizeTier": cur_size_tier,
                    "ParentCustomerCode": parent_code[i],
                    "ParentCustomerName": parent_name[i],
                    "HqCountryCode": hq_cc[i],
                    "HqCountryName": hq_cn[i],
                    "HqRegion": hq_region[i],
                    "SalesRegion": sales_region[i],
                    "AccountManager": manager_names[cur_manager_idx],
                    "AccountManagerEmail": manager_emails[cur_manager_idx],
                    "CreditTier": cur_credit_tier,
                    "PaymentTermsDays": int(base_payment_terms[i]),
                    "ContractType": cur_contract_type,
                    "OnboardedDate": onboarded,
                    "ScdValidFrom": valid_from,
                    "ScdValidTo": valid_to,
                    "IsCurrent": is_current,
                    "ScdVersion": v + 1,
                }
            )

    df = pd.DataFrame(rows)
    return _finalize(
        df,
        "CustomerKey",
        _DIMCUSTOMER_DTYPES,
        overrides={
            "OnboardedDate": _SENTINEL_END_DATE,
            "ScdValidFrom": _SENTINEL_END_DATE,
            "ScdValidTo": _SENTINEL_END_DATE,
            "ParentCustomerCode": _CODE_UNKNOWN,
            "ParentCustomerName": _CODE_UNKNOWN,
        },
    )


# =========================================================================== #
# 1.16 DimSku -- 12,000 rows (11,999 real + Unknown)
# =========================================================================== #

_SKU_WAREHOUSE_USER_RATE = 0.40  # fraction of current customers treated as warehouse-using owners
_SKU_WAREHOUSE_USER_SEGMENT_WEIGHTS: dict[str, float] = {
    "BCO": 1.4, "3PL": 1.6, "SME Direct": 1.2, "Freight Forwarder": 0.5, "NVOCC": 0.3,
}
_SKU_EXCLUDED_COMMODITY_GROUPS = frozenset({"Raw Materials"})
_SKU_UOM_CHOICES: tuple[str, ...] = ("EA", "CTN", "PAL", "KG", "LTR")
_SKU_UOM_WEIGHTS: tuple[float, ...] = (0.45, 0.25, 0.10, 0.12, 0.08)
_SKU_VOLUME_CBM_LO, _SKU_VOLUME_CBM_HI = 0.0005, 0.05
_SKU_WEIGHT_NOISE_LO, _SKU_WEIGHT_NOISE_HI = 0.85, 1.15
_SKU_COST_PER_KG_LO, _SKU_COST_PER_KG_HI = 2.0, 40.0
_SKU_HIGH_VALUE_COST_MULTIPLIER = 6.0
_SKU_MARKUP_LO, _SKU_MARKUP_HI = 1.15, 2.5
_SKU_ABC_CHOICES: tuple[str, ...] = ("A", "B", "C")
_SKU_ABC_WEIGHTS: tuple[float, ...] = (0.10, 0.30, 0.60)
_SKU_STORAGE_TYPE_CHOICES: tuple[str, ...] = ("Ambient", "Chilled", "Frozen", "Hazmat", "Bulk")
_SKU_SHELF_LIFE_LO, _SKU_SHELF_LIFE_HI = 30, 720
_SKU_INACTIVE_RATE = 0.05
_SKU_EXTRA_NULL_RATE = 0.041  # landmine #1's "4.1% nulls in optional fields" applied to ShelfLifeDays/RequiredTempC
_SKU_LEADING_ZERO_DIGITS = 6  # landmine #10: CSV mirror drops the "SKU-" prefix, leaving bare zero-padded digits

_DIMSKU_DTYPES = {
    "SkuKey": "int32",
    "SkuCode": "str",
    "SkuDescription": "str",
    "CustomerCode": "str",
    "CommodityKey": "int32",
    "ProductCategory": "str",
    "ProductSubCategory": "str",
    "UnitOfMeasure": "str",
    "UnitsPerCarton": "int16",
    "CartonsPerPallet": "int16",
    "UnitWeightKg": "float32",
    "UnitVolumeCbm": "float32",
    "UnitCostUsd": "float32",
    "UnitPriceUsd": "float32",
    "AbcClassStatic": "str",
    "IsHazardous": "int8",
    "RequiresColdChain": "int8",
    "ShelfLifeDays": "Int16",
    "StorageType": "str",
    "IsActive": "int8",
}


def build_dim_sku(cfg: _cfg.Config, dim_commodity: pd.DataFrame, dim_customer: pd.DataFrame) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.16 DimSku -- 12,000 rows (11,999 real + Unknown).

    Owned by a subset of current customers treated as warehouse users.
    `UnitWeightKg` is derived from the linked commodity's
    `AvgDensityKgPerCbm` so weight/volume stay physically coherent, and
    `UnitPriceUsd` is always `UnitCostUsd` x a markup > 1, so price > cost
    by construction.
    """
    rng = util.child_rng("DimSku")
    n = cfg.dim_rows("DimSku") - 1

    current_customers = dim_customer[dim_customer["IsCurrent"] == 1]
    owner_weights = current_customers["CustomerSegment"].map(_SKU_WAREHOUSE_USER_SEGMENT_WEIGHTS).to_numpy()
    owner_weights = owner_weights / owner_weights.sum()
    n_owners = max(1, int(round(_SKU_WAREHOUSE_USER_RATE * len(current_customers))))
    owner_pool_idx = rng.choice(len(current_customers), size=n_owners, replace=False, p=owner_weights)
    owner_codes = current_customers["CustomerCode"].to_numpy()[owner_pool_idx]

    eligible_commodities = dim_commodity[
        (dim_commodity["CommodityKey"] > 0) & (~dim_commodity["CommodityGroup"].isin(_SKU_EXCLUDED_COMMODITY_GROUPS))
    ].reset_index(drop=True)

    sku_owner = rng.choice(owner_codes, size=n)
    commodity_row_idx = rng.integers(0, len(eligible_commodities), size=n)
    commodity_keys = eligible_commodities["CommodityKey"].to_numpy()[commodity_row_idx]
    commodity_groups = eligible_commodities["CommodityGroup"].to_numpy()[commodity_row_idx]
    commodity_headings = eligible_commodities["HsHeadingName"].to_numpy()[commodity_row_idx]
    commodity_density = eligible_commodities["AvgDensityKgPerCbm"].to_numpy()[commodity_row_idx]
    commodity_is_dg = eligible_commodities["IsDangerousGoods"].to_numpy()[commodity_row_idx]
    commodity_is_temp = eligible_commodities["IsTemperatureControlled"].to_numpy()[commodity_row_idx]
    commodity_is_high_value = eligible_commodities["IsHighValue"].to_numpy()[commodity_row_idx]
    commodity_name = eligible_commodities["CommodityName"].to_numpy()[commodity_row_idx]

    unit_volume = rng.uniform(_SKU_VOLUME_CBM_LO, _SKU_VOLUME_CBM_HI, size=n)
    weight_noise = rng.uniform(_SKU_WEIGHT_NOISE_LO, _SKU_WEIGHT_NOISE_HI, size=n)
    unit_weight = unit_volume * commodity_density * weight_noise

    cost_per_kg = rng.uniform(_SKU_COST_PER_KG_LO, _SKU_COST_PER_KG_HI, size=n)
    cost_per_kg = np.where(commodity_is_high_value == 1, cost_per_kg * _SKU_HIGH_VALUE_COST_MULTIPLIER, cost_per_kg)
    unit_cost = np.maximum(0.05, unit_weight * cost_per_kg)
    markup = rng.uniform(_SKU_MARKUP_LO, _SKU_MARKUP_HI, size=n)
    unit_price = unit_cost * markup

    is_hazardous = (commodity_is_dg == 1) & (rng.random(n) < 0.9)
    requires_cold_chain = (commodity_is_temp == 1) & (rng.random(n) < 0.9)

    storage_type = np.where(
        requires_cold_chain, np.where(rng.random(n) < 0.5, "Chilled", "Frozen"),
        np.where(is_hazardous, "Hazmat", np.where(rng.random(n) < 0.15, "Bulk", "Ambient")),
    )
    shelf_life = np.where(requires_cold_chain, rng.integers(_SKU_SHELF_LIFE_LO, _SKU_SHELF_LIFE_HI + 1, size=n), -1)

    units_per_carton = rng.integers(1, 49, size=n)
    cartons_per_pallet = rng.integers(20, 81, size=n)
    abc_class = rng.choice(_SKU_ABC_CHOICES, size=n, p=_SKU_ABC_WEIGHTS)
    uom = rng.choice(_SKU_UOM_CHOICES, size=n, p=_SKU_UOM_WEIGHTS)
    is_active = (rng.random(n) >= _SKU_INACTIVE_RATE).astype("int8")

    df = pd.DataFrame(
        {
            "SkuCode": [f"SKU-{i:06d}" for i in range(1, n + 1)],
            "SkuDescription": [f"{name} - Retail Unit" for name in commodity_name],
            "CustomerCode": sku_owner,
            "CommodityKey": commodity_keys.astype("int32"),
            "ProductCategory": commodity_groups,
            "ProductSubCategory": commodity_headings,
            "UnitOfMeasure": uom,
            "UnitsPerCarton": units_per_carton.astype("int16"),
            "CartonsPerPallet": cartons_per_pallet.astype("int16"),
            "UnitWeightKg": np.round(unit_weight, 4).astype("float32"),
            "UnitVolumeCbm": np.round(unit_volume, 5).astype("float32"),
            "UnitCostUsd": np.round(unit_cost, 2).astype("float32"),
            "UnitPriceUsd": np.round(unit_price, 2).astype("float32"),
            "AbcClassStatic": abc_class,
            "IsHazardous": is_hazardous.astype("int8"),
            "RequiresColdChain": requires_cold_chain.astype("int8"),
            "ShelfLifeDays": pd.Series(np.where(shelf_life >= 0, shelf_life, np.nan)).astype("Int16"),
            "StorageType": storage_type,
            "IsActive": is_active,
        }
    )

    # Landmine #1 (partial; dimension-side only -- see build report): an
    # additional 4.1% random null rate on top of the business-logic nulls
    # already present in ShelfLifeDays.
    extra_null_idx = rng.random(n) < _SKU_EXTRA_NULL_RATE
    df.loc[extra_null_idx, "ShelfLifeDays"] = pd.NA

    df = _finalize(
        df,
        "SkuKey",
        _DIMSKU_DTYPES,
        overrides={"CommodityKey": -1, "ShelfLifeDays": pd.NA},
    )

    # Landmine #10: the CSV mirror represents SkuCode as the bare zero-padded
    # serial (no "SKU-" prefix), which a naive importer will read as a
    # number and silently strip the leading zeros from.
    csv_df = df.copy()
    is_real = csv_df["SkuKey"] > 0
    csv_df.loc[is_real, "SkuCode"] = csv_df.loc[is_real, "SkuCode"].str.replace("SKU-", "", regex=False)

    return df, csv_df


# =========================================================================== #
# 1.17 DimEmployee -- 1,800 rows (1,799 real + Unknown)
# =========================================================================== #

_EMPLOYEE_ROLES: tuple[str, ...] = ("Picker", "Packer", "Forklift Operator", "Receiver", "Checker", "Team Lead", "Supervisor")
_EMPLOYEE_ROLE_WEIGHTS: tuple[float, ...] = (0.30, 0.20, 0.14, 0.12, 0.12, 0.07, 0.05)
_EMPLOYEE_SHIFT_KEYS: tuple[int, ...] = (1, 2, 3)
_EMPLOYEE_SHIFT_NAMES: dict[int, str] = {1: "A", 2: "B", 3: "C"}
_EMPLOYMENT_TYPES: tuple[str, ...] = ("Permanent", "Agency", "Seasonal")
_EMPLOYMENT_TYPE_WEIGHTS: tuple[float, ...] = (0.65, 0.25, 0.10)
_EMPLOYEE_HIRE_EARLIEST = dt.date(2016, 1, 1)
_EMPLOYEE_FORKLIFT_CERT_RATE_OPERATOR = 0.98
_EMPLOYEE_FORKLIFT_CERT_RATE_OTHER = 0.10
_EMPLOYEE_INACTIVE_RATE = 0.06
_EMPLOYEE_FIRST_NAMES: tuple[str, ...] = (
    "Ravi", "Wei", "Siti", "John", "Maria", "Ahmed", "Li", "Anita", "Carlos", "Fatima",
    "Kenji", "Grace", "Hassan", "Ingrid", "Diego", "Priya", "Marco", "Elena", "Sofia", "Liam",
)
_EMPLOYEE_LAST_NAMES: tuple[str, ...] = (
    "Kumar", "Zhang", "Rahman", "Smith", "Silva", "Al-Amin", "Wang", "Fernandes", "Gomez", "Haddad",
    "Sato", "Mensah", "Khalid", "Berg", "Torres", "Sharma", "Rossi", "Novak", "Costa", "Nguyen",
)
_TENURE_BANDS: tuple[tuple[int, str], ...] = (
    (6, "<6m"), (12, "6-12m"), (24, "1-2y"), (60, "2-5y"), (10**6, "5y+"),
)

_DIMEMPLOYEE_DTYPES = {
    "EmployeeKey": "int32",
    "EmployeeCode": "str",
    "EmployeeName": "str",
    "WarehouseKey": "int32",
    "RoleName": "str",
    "ShiftKey": "int8",
    "ShiftName": "str",
    "EmploymentType": "str",
    "HireDate": "object",
    "TenureBand": "str",
    "IsCertifiedForklift": "int8",
    "IsActive": "int8",
}


def _tenure_band(months: float) -> str:
    for threshold, label in _TENURE_BANDS:
        if months < threshold:
            return label
    return _TENURE_BANDS[-1][1]


def build_dim_employee(cfg: _cfg.Config, dim_warehouse: pd.DataFrame) -> pd.DataFrame:
    """SCHEMA_CONTRACT.md SS1.17 DimEmployee -- 1,800 rows (1,799 real + Unknown)."""
    rng = util.child_rng("DimEmployee")
    n = cfg.dim_rows("DimEmployee") - 1

    real_warehouses = dim_warehouse[dim_warehouse["WarehouseKey"] > 0]
    warehouse_keys = rng.choice(real_warehouses["WarehouseKey"].to_numpy(), size=n)
    roles = rng.choice(_EMPLOYEE_ROLES, size=n, p=_EMPLOYEE_ROLE_WEIGHTS)
    shift_keys = rng.choice(_EMPLOYEE_SHIFT_KEYS, size=n)
    employment_types = rng.choice(_EMPLOYMENT_TYPES, size=n, p=_EMPLOYMENT_TYPE_WEIGHTS)

    hire_window_days = (cfg.fact_end_date - _EMPLOYEE_HIRE_EARLIEST).days
    hire_offsets = rng.integers(0, hire_window_days + 1, size=n)
    hire_dates = [_EMPLOYEE_HIRE_EARLIEST + dt.timedelta(days=int(off)) for off in hire_offsets]
    anchor = cfg.current_anchor_date
    tenure_months = [(anchor - hd).days / 30.44 for hd in hire_dates]
    tenure_bands = [_tenure_band(m) for m in tenure_months]

    is_forklift_cert = np.where(
        roles == "Forklift Operator",
        rng.random(n) < _EMPLOYEE_FORKLIFT_CERT_RATE_OPERATOR,
        rng.random(n) < _EMPLOYEE_FORKLIFT_CERT_RATE_OTHER,
    ).astype("int8")
    is_active = (rng.random(n) >= _EMPLOYEE_INACTIVE_RATE).astype("int8")

    first_names = rng.choice(_EMPLOYEE_FIRST_NAMES, size=n)
    last_names = rng.choice(_EMPLOYEE_LAST_NAMES, size=n)

    df = pd.DataFrame(
        {
            "EmployeeCode": [f"EMP{i:05d}" for i in range(1, n + 1)],
            "EmployeeName": [f"{f} {l}" for f, l in zip(first_names, last_names)],
            "WarehouseKey": warehouse_keys.astype("int32"),
            "RoleName": roles,
            "ShiftKey": shift_keys.astype("int8"),
            "ShiftName": [_EMPLOYEE_SHIFT_NAMES[k] for k in shift_keys],
            "EmploymentType": employment_types,
            "HireDate": hire_dates,
            "TenureBand": tenure_bands,
            "IsCertifiedForklift": is_forklift_cert,
            "IsActive": is_active,
        }
    )
    return _finalize(df, "EmployeeKey", _DIMEMPLOYEE_DTYPES, overrides={"HireDate": _SENTINEL_END_DATE, "ShiftKey": -1})
