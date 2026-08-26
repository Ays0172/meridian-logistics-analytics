"""Commercial core fact builders — SCHEMA_CONTRACT.md sections 2.1, 2.2, 2.3, 2.10.

Build order matters and is enforced by build_facts.py:

    FactExchangeRate  ->  FactBooking  ->  FactShipment  ->  FactShipmentMilestone

FactExchangeRate must exist first because every money column in the downstream
facts is converted at the rate in force on the transaction date.

All generation is vectorised: no Python-level loop ever iterates over rows of a
fact table. Loops over dimension members (44 services, 22 currencies) are fine.
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
    LUNAR_NEW_YEAR_DATES as LNY_DATES,
)
from .util import child_rng, to_date_key

# --------------------------------------------------------------------------- #
# Named constants — no magic numbers in the body of the builders.
# --------------------------------------------------------------------------- #

REPORTING_CURRENCY = "USD"

# §3.1 seasonality
LNY_TROUGH_FACTOR = 0.55
LNY_REBOUND_FACTOR = 1.18
LNY_TROUGH_WEEKS = 2
LNY_REBOUND_WEEKS = 2
PEAK_SEASON_MONTHS = (8, 9, 10)
PEAK_SEASON_VOLUME_FACTOR = 1.22
PEAK_SEASON_RATE_FACTOR = 1.35
Q4_SPOT_RATE_FACTOR = 1.40
SATURDAY_FACTOR = 0.70
SUNDAY_FACTOR = 0.35
ANNUAL_GROWTH = 0.06

# §2.1 booking status mix
BOOKING_STATUS_MIX = {
    "Confirmed": 0.78,
    "Rolled": 0.09,
    "Cancelled": 0.08,
    "No-Show": 0.03,
    "Pending": 0.02,
}
CONGESTION_ROLLOVER_MULTIPLIER = 2.1

# §3.2 trade imbalance
HEADHAUL_LOAD_FACTOR_RANGE = (0.88, 0.96)
BACKHAUL_LOAD_FACTOR_RANGE = (0.55, 0.70)
BACKHAUL_YIELD_RATIO = 0.52

# §3.4 distributions
TRANSIT_LOGNORM_MU = 0.9
TRANSIT_LOGNORM_SIGMA = 0.65
RATE_LOGNORM_SIGMA = 0.28
CONGESTION_TRANSIT_ADD_MEAN = 6.4

# §2.2 quality flags. §3.4 fixes the OTIF component rates:
#   DIF 0.962 x DOQ 0.987 x DOT 0.913 -> headline ~0.867.
IN_FULL_RATE = 0.962
DOC_CLEAN_RATE = 0.987
ON_TIME_DELIVERY_TARGET = 0.913
DAMAGE_RATE = 0.011

# Two different on-time measures, and conflating them is the mistake this
# generator has to avoid making on the learner's behalf:
#
#   Schedule reliability  — vessel ATA against the originally published ETA.
#                           Runs ~65% industry-wide and lives on FactPortCall.
#   Delivery OTIF         — cargo delivered against the promised delivery date.
#                           Runs ~91% because the door promise carries slack.
#
# FactShipment.IsOnTime is the second one. The first is a port-call measure.
#
# Published transit times contain deliberate slack: a carrier quoting the median
# achievable transit would miss its own schedule half the time. The buffer below
# is that slack, and it is what puts on-time arrival in the 62-70% band rather
# than the 22% a zero-buffer schedule would produce.
SCHEDULE_BUFFER_DAYS = 2.2

# Delivery lateness is not independent of vessel lateness — a ship arriving six
# days late rarely delivers on time. IsOnTime is therefore drawn from a logistic
# function of transit variance, with the intercept solved at runtime so the mean
# lands on ON_TIME_DELIVERY_TARGET. That gives both the right headline rate and a
# real, discoverable relationship for the learner to find.
ON_TIME_VARIANCE_SENSITIVITY = 0.16

# Air consignments are not containers. Typical air density runs 100-200 kg/cbm,
# which is why chargeable weight exceeds gross weight on most air shipments.
AIR_WEIGHT_KG_RANGE = (45.0, 3200.0)
AIR_DENSITY_KG_PER_CBM = (70.0, 210.0)

# Base freight rate per FFE by trade lane, USD. Directional, chosen to put
# revenue per FFE in a believable band once mix and seasonality are applied.
LANE_BASE_RATE_FFE = {
    "Asia–N Europe": 2650.0,
    "Asia–Mediterranean": 2480.0,
    "Transpacific East": 2950.0,
    "Transpacific West": 1180.0,
    "Asia–ISC": 1420.0,
    "ISC–Europe": 1980.0,
    "Intra-Asia": 620.0,
    "Asia–MEA": 1350.0,
    "Europe–LatAm": 2240.0,
    "Asia–LatAm": 3100.0,
    "Transatlantic": 1760.0,
}
DEFAULT_LANE_RATE_FFE = 1800.0

# Direct cost as a share of revenue, before the margin tail is applied.
COST_RATIO_MEAN = 0.82
COST_RATIO_SIGMA = 0.09

# Account concentration. Higher = more volume sits with the longest-standing
# accounts. Tuned so the top 10 customers carry roughly a fifth of TEU, which is
# the usual shape for a carrier with a few thousand named accounts.
CUSTOMER_CONCENTRATION_EXPONENT = 4.5

# Share of ocean cargo moving on Meridian's own tonnage rather than on partner
# services or chartered slots.
OWN_TONNAGE_SHARE = 0.72

# Relative weight applied to dangerous-goods commodities when drawing a booking.
# Brings the booked DG share from ~20% down to the ~6% seen in real liner cargo.
DG_COMMODITY_WEIGHT = 0.22

# Mode mix at booking. Air is a small share of volume but a large share of
# revenue per kg, which is what makes the modal-shift comparison worth building.
BOOKING_MODE_MIX = {"FCL": 0.800, "LCL": 0.120, "AIR": 0.080}

# Air volumetric divisors — the IATA 1:6000 convention and the 1:5000 variant
# some carriers and lanes apply. Ocean LCL uses 1 CBM = 1000 kg instead. These
# three being different is the classic freight-forwarding arithmetic trap.
AIR_DIVISOR_STANDARD = 6000.0
AIR_DIVISOR_ALTERNATE = 5000.0
AIR_ALTERNATE_SHARE = 0.28
LCL_KG_PER_CBM = 1000.0

# Equipment mix by type code. Real fleets are dominated by 40HC and 20DV; tanks,
# open-tops and flat-racks are rounding errors. Left uniform, a 60-row equipment
# dimension would hand special types ~23% of all bookings, which would make every
# reefer and project-cargo KPI meaningless.
EQUIPMENT_TYPE_WEIGHTS = {
    "40HC": 0.380,
    "20DV": 0.275,
    "40DV": 0.170,
    "40RH": 0.055,
    "20RF": 0.028,
    "45HC": 0.042,
    "40OT": 0.018,
    "20TK": 0.014,
    "40FR": 0.012,
    "20FR": 0.006,
}

CO2_GRAMS_PER_TONNE_KM_OCEAN = 12.5


# --------------------------------------------------------------------------- #
# Shared date / seasonality machinery
# --------------------------------------------------------------------------- #


def _lny_windows() -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
    """Return (trough_start, trough_end, rebound_end) per Lunar New Year."""
    out = []
    for d in LNY_DATES:
        ts = pd.Timestamp(d)
        trough_start = ts - pd.Timedelta(days=3)
        trough_end = trough_start + pd.Timedelta(weeks=LNY_TROUGH_WEEKS)
        rebound_end = trough_end + pd.Timedelta(weeks=LNY_REBOUND_WEEKS)
        out.append((trough_start, trough_end, rebound_end))
    return out


def volume_index(dates: pd.DatetimeIndex) -> np.ndarray:
    """Relative volume weight per calendar day — §3.1.

    Combines underlying growth, Lunar New Year collapse and rebound, peak
    season, and the weekday effect. Returned values are unnormalised weights.
    """
    dates = pd.DatetimeIndex(dates)
    idx = np.ones(len(dates), dtype=np.float64)

    # Underlying growth, compounded from the calendar start.
    years_elapsed = (dates - pd.Timestamp(CALENDAR_START)).days / 365.25
    idx *= (1.0 + ANNUAL_GROWTH) ** years_elapsed

    # Lunar New Year: collapse then rebound.
    for trough_start, trough_end, rebound_end in _lny_windows():
        in_trough = (dates >= trough_start) & (dates < trough_end)
        in_rebound = (dates >= trough_end) & (dates < rebound_end)
        idx[in_trough] *= LNY_TROUGH_FACTOR
        idx[in_rebound] *= LNY_REBOUND_FACTOR

    # Peak season.
    idx[np.isin(dates.month, PEAK_SEASON_MONTHS)] *= PEAK_SEASON_VOLUME_FACTOR

    # Weekday effect.
    idx[dates.dayofweek == 5] *= SATURDAY_FACTOR
    idx[dates.dayofweek == 6] *= SUNDAY_FACTOR

    return idx


def rate_index(dates: pd.DatetimeIndex) -> np.ndarray:
    """Relative freight-rate multiplier per calendar day — §3.1."""
    dates = pd.DatetimeIndex(dates)
    idx = np.ones(len(dates), dtype=np.float64)
    idx[np.isin(dates.month, PEAK_SEASON_MONTHS)] *= PEAK_SEASON_RATE_FACTOR
    idx[np.isin(dates.month, (11, 12))] *= Q4_SPOT_RATE_FACTOR
    return idx


def in_congestion_window(dates: pd.DatetimeIndex) -> np.ndarray:
    """Boolean mask for the §3.3 congestion event window."""
    dates = pd.DatetimeIndex(dates)
    return (dates >= pd.Timestamp(CONGESTION_START)) & (
        dates <= pd.Timestamp(CONGESTION_END)
    )


def _sample_dates(
    rng: np.random.Generator,
    n: int,
    window: tuple[object, object] | None = None,
) -> pd.DatetimeIndex:
    """Draw n dates, weighted by the volume index.

    ``window`` restricts the draw to a date range. That is what lets the live
    feed reuse these builders unchanged for a single day: the seasonality,
    weekday and growth structure all still apply, they are just evaluated over
    one day instead of five years.
    """
    start, end = window if window else (CALENDAR_START, CALENDAR_END)
    all_days = pd.date_range(start, end, freq="D")
    if len(all_days) == 0:
        return pd.DatetimeIndex([])
    weights = volume_index(all_days)
    total = weights.sum()
    weights = weights / total if total > 0 else np.full(len(all_days), 1 / len(all_days))
    picks = rng.choice(len(all_days), size=n, replace=True, p=weights)
    return all_days[np.sort(picks)]


# --------------------------------------------------------------------------- #
# 2.10  FactExchangeRate
# --------------------------------------------------------------------------- #


def build_fact_exchange_rate(dims: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per currency per day — §2.10. Periodic snapshot.

    Rates follow a random walk with mild mean reversion so that year-on-year
    currency effects are visible but not absurd.
    """
    rng = child_rng("FactExchangeRate")
    cur = dims["DimCurrency"]
    cur = cur[cur["CurrencyKey"] > 0]

    days = pd.date_range(CALENDAR_START, CALENDAR_END, freq="D")
    n_days = len(days)

    # Plausible starting rates to USD. Anything not listed gets a drawn anchor.
    anchors = {
        "USD": 1.0, "EUR": 1.09, "GBP": 1.27, "INR": 0.0120, "CNY": 0.1385,
        "JPY": 0.00655, "SGD": 0.745, "AED": 0.2723, "SAR": 0.2666,
        "HKD": 0.1280, "KRW": 0.000735, "TWD": 0.0311, "MYR": 0.2230,
        "THB": 0.0281, "IDR": 0.0000625, "VND": 0.0000394, "BRL": 0.184,
        "MXN": 0.0555, "ZAR": 0.0535, "AUD": 0.655, "NZD": 0.603,
        "CAD": 0.735, "TRY": 0.0295, "EGP": 0.0205,
    }

    frames = []
    for _, row in cur.iterrows():
        code = row["CurrencyCode"]
        is_reporting = code == REPORTING_CURRENCY
        if is_reporting:
            rate = np.ones(n_days, dtype=np.float64)
        else:
            anchor = anchors.get(code, float(rng.uniform(0.02, 1.4)))
            # Ornstein-Uhlenbeck style walk: daily shocks pulled back to anchor.
            shocks = rng.normal(0.0, 0.0045, size=n_days)
            level = np.empty(n_days, dtype=np.float64)
            level[0] = 0.0
            for i in range(1, n_days):  # over 1,340 days, not over fact rows
                level[i] = level[i - 1] * 0.997 + shocks[i]
            rate = anchor * np.exp(level)

        df = pd.DataFrame(
            {
                "RateDateKey": to_date_key(days),
                "CurrencyKey": np.int32(row["CurrencyKey"]),
                "FromCurrencyCode": code,
                "ToCurrencyCode": REPORTING_CURRENCY,
                "RateToUsd": rate.astype(np.float32),
                "RateFromUsd": (1.0 / rate).astype(np.float32),
            }
        )
        df["_month"] = days.to_period("M").astype(str)
        df["MonthAvgRateToUsd"] = (
            df.groupby("_month")["RateToUsd"].transform("mean").astype(np.float32)
        )
        df["IsMonthEndRate"] = days.is_month_end.astype(np.int8)
        frames.append(df.drop(columns="_month"))

    out = pd.concat(frames, ignore_index=True)
    out = out.sort_values(["RateDateKey", "CurrencyKey"], kind="stable").reset_index(
        drop=True
    )
    out.insert(0, "ExchangeRateKey", np.arange(1, len(out) + 1, dtype=np.int64))
    return out


def _fx_lookup(fx: pd.DataFrame) -> pd.Series:
    """Series indexed by (RateDateKey, CurrencyKey) -> RateToUsd, for fast joins."""
    return fx.set_index(["RateDateKey", "CurrencyKey"])["RateToUsd"]


# --------------------------------------------------------------------------- #
# Lane / routing helpers
# --------------------------------------------------------------------------- #


def _region_port_pool(locations: pd.DataFrame) -> dict[str, np.ndarray]:
    """Map each TradeRegion to the LocationKeys of its seaports."""
    ports = locations[
        (locations["LocationKey"] > 0)
        & (locations["LocationType"].isin(["Seaport", "Inland Depot", "CFS"]))
    ]
    return {
        region: grp["LocationKey"].to_numpy(dtype=np.int32)
        for region, grp in ports.groupby("TradeRegion")
    }


def _draw_carrier_mix(
    rng: np.random.Generator, carriers: pd.DataFrame, n: int
) -> np.ndarray:
    """Draw ocean carriers: mostly Meridian's own tonnage, some partners.

    A carrier dimension that only ever takes one value is worse than useless —
    it looks like a working dimension and answers every question with a single
    bar. The split below keeps Meridian dominant while leaving enough partner
    volume for a carrier scorecard to mean something.
    """
    ocean = carriers[
        (carriers["CarrierKey"] > 0) & (carriers["CarrierType"] == "Ocean Carrier")
    ]
    if ocean.empty:
        ocean = carriers[carriers["CarrierKey"] > 0]

    own = ocean[ocean["IsOwnFleet"] == 1]["CarrierKey"].to_numpy(np.int32)
    partner = ocean[ocean["IsOwnFleet"] != 1]["CarrierKey"].to_numpy(np.int32)
    if len(own) == 0 or len(partner) == 0:
        return rng.choice(ocean["CarrierKey"].to_numpy(np.int32), size=n, replace=True)

    use_own = rng.random(n) < OWN_TONNAGE_SHARE
    out = np.empty(n, dtype=np.int32)
    out[use_own] = rng.choice(own, size=int(use_own.sum()), replace=True)
    # Partner volume is itself concentrated: a handful of alliance partners carry
    # most of the chartered slots, rather than 100 carriers taking 1% each.
    w = rng.pareto(1.1, size=len(partner)) + 1.0
    w /= w.sum()
    out[~use_own] = rng.choice(
        partner, size=int((~use_own).sum()), replace=True, p=w
    )
    return out


def _pick_eligible_customers(
    rng: np.random.Generator,
    customers: pd.DataFrame,
    event_dates: pd.DatetimeIndex,
) -> np.ndarray:
    """Draw a CustomerCode per event, restricted to customers already onboarded.

    A customer cannot place a booking before the day they were onboarded, so
    naively sampling the whole book and then resolving SCD2 sends ~12% of rows
    to the unknown member. Instead: sort customers by onboarding date, use
    ``searchsorted`` to find how many were live on each event date, and draw
    within that prefix. Account concentration is preserved by drawing a
    power-law position inside the eligible prefix rather than a uniform one, so
    a minority of long-standing accounts still carry most of the volume.
    """
    cur = customers[(customers["IsCurrent"] == 1) & (customers["CustomerKey"] > 0)]
    cur = cur.assign(_onb=pd.to_datetime(cur["OnboardedDate"])).sort_values(
        "_onb", kind="stable"
    )
    codes = cur["CustomerCode"].to_numpy()
    onboarded = cur["_onb"].to_numpy()

    dates = pd.DatetimeIndex(event_dates).to_numpy()
    eligible = np.searchsorted(onboarded, dates, side="right")
    # Guard the earliest dates: always allow at least the first cohort.
    eligible = np.maximum(eligible, 1)

    # Power-law position within the eligible prefix, biased towards the
    # earliest-onboarded (largest) accounts.
    u = rng.random(len(dates))
    pos = (u ** CUSTOMER_CONCENTRATION_EXPONENT * eligible).astype(np.int64)
    pos = np.clip(pos, 0, eligible - 1)
    return codes[pos]


def _resolve_scd_customer(
    customers: pd.DataFrame,
    customer_codes: np.ndarray,
    event_dates: pd.DatetimeIndex,
) -> np.ndarray:
    """Return the CustomerKey of the version valid on each event date.

    This is the point of having SCD Type 2 at all: a fact must point at the
    version of the customer that was true when the fact happened, not at
    whoever owns the account today.
    """
    hist = customers[customers["CustomerKey"] > 0][
        ["CustomerCode", "CustomerKey", "ScdValidFrom", "ScdValidTo"]
    ].copy()
    hist["ScdValidFrom"] = pd.to_datetime(hist["ScdValidFrom"])
    hist["ScdValidTo"] = pd.to_datetime(hist["ScdValidTo"])

    probe = pd.DataFrame(
        {
            "CustomerCode": customer_codes,
            "_d": pd.DatetimeIndex(event_dates),
            "_row": np.arange(len(customer_codes)),
        }
    )
    merged = probe.merge(hist, on="CustomerCode", how="left")
    ok = (merged["_d"] >= merged["ScdValidFrom"]) & (merged["_d"] <= merged["ScdValidTo"])
    merged = merged[ok]
    # One version can match; keep the first deterministically.
    merged = merged.drop_duplicates(subset="_row", keep="first")

    out = np.full(len(customer_codes), -1, dtype=np.int32)
    out[merged["_row"].to_numpy()] = merged["CustomerKey"].to_numpy(dtype=np.int32)
    return out


# --------------------------------------------------------------------------- #
# 2.1  FactBooking
# --------------------------------------------------------------------------- #


def build_fact_booking(
    dims: dict[str, pd.DataFrame],
    fx: pd.DataFrame,
    n_rows: int,
    *,
    window: tuple[object, object] | None = None,
    seed_label: str = "FactBooking",
    key_offset: int = 0,
) -> pd.DataFrame:
    """One row per booking line at confirmation — §2.1. Transaction grain.

    ``window``, ``seed_label`` and ``key_offset`` exist for the live feed: one
    day at a time, seeded per day so the day is reproducible on its own, and
    with surrogate keys continuing from wherever the frozen history stopped.
    """
    rng = child_rng(seed_label)

    voyages = dims["DimVoyage"][dims["DimVoyage"]["VoyageKey"] > 0]
    services = dims["DimService"][dims["DimService"]["ServiceKey"] > 0]
    customers = dims["DimCustomer"]
    equipment = dims["DimEquipment"][dims["DimEquipment"]["EquipmentKey"] > 0]
    commodities = dims["DimCommodity"][dims["DimCommodity"]["CommodityKey"] > 0]
    incoterms = dims["DimIncoterm"][dims["DimIncoterm"]["IncotermKey"] > 0]
    carriers = dims["DimCarrier"]
    modes = dims["DimMode"][dims["DimMode"]["ModeKey"] > 0]
    currencies = dims["DimCurrency"][dims["DimCurrency"]["CurrencyKey"] > 0]
    locations = dims["DimLocation"]

    booking_dates = _sample_dates(rng, n_rows, window)

    # --- voyage assignment: bias towards voyages departing after the booking
    voy = voyages.sample(n=n_rows, replace=True, random_state=int(rng.integers(1 << 31)))
    voyage_key = voy["VoyageKey"].to_numpy(dtype=np.int32)
    service_key = voy["ServiceKey"].to_numpy(dtype=np.int32)
    direction = voy["Direction"].to_numpy()
    is_headhaul = direction == "Headhaul"

    svc = services.set_index("ServiceKey")
    lane = svc["TradeLane"].reindex(service_key).to_numpy()
    origin_region = svc["OriginRegion"].reindex(service_key).to_numpy()
    dest_region = svc["DestinationRegion"].reindex(service_key).to_numpy()
    nominal_transit = (
        svc["NominalTransitDays"].reindex(service_key).to_numpy(dtype=np.float64)
    )

    # On a backhaul the trade lane runs the other way round.
    o_region = np.where(is_headhaul, origin_region, dest_region)
    d_region = np.where(is_headhaul, dest_region, origin_region)

    pool = _region_port_pool(locations)
    fallback = locations[locations["LocationKey"] > 0]["LocationKey"].to_numpy(np.int32)

    def pick_ports(regions: np.ndarray) -> np.ndarray:
        out = np.empty(len(regions), dtype=np.int32)
        for region in np.unique(regions):
            mask = regions == region
            candidates = pool.get(region, fallback)
            out[mask] = rng.choice(candidates, size=int(mask.sum()), replace=True)
        return out

    loc_origin = pick_ports(o_region)
    loc_dest = pick_ports(d_region)

    # --- customers, drawn only from those already onboarded, then SCD2-resolved
    picked_codes = _pick_eligible_customers(rng, customers, booking_dates)
    customer_key = _resolve_scd_customer(customers, picked_codes, booking_dates)

    # --- equipment, weighted to the workhorse boxes (see EQUIPMENT_TYPE_WEIGHTS)
    type_codes = equipment["EquipmentTypeCode"].to_numpy()
    default_w = min(EQUIPMENT_TYPE_WEIGHTS.values()) / 4.0
    per_type = np.array(
        [EQUIPMENT_TYPE_WEIGHTS.get(t, default_w) for t in type_codes], dtype=np.float64
    )
    # Share the type's weight across however many rows carry that type code, so
    # the mix is driven by the type, not by how many variants of it exist.
    rows_per_type = pd.Series(type_codes).groupby(type_codes).transform("size").to_numpy()
    eq_weights = per_type / rows_per_type
    eq_weights = eq_weights / eq_weights.sum()
    eq_idx = rng.choice(len(equipment), size=n_rows, replace=True, p=eq_weights)
    eq = equipment.iloc[eq_idx]
    equipment_key = eq["EquipmentKey"].to_numpy(dtype=np.int32)
    teu_factor = eq["TeuFactor"].to_numpy(dtype=np.float64)
    ffe_factor = eq["FfeFactor"].to_numpy(dtype=np.float64)
    is_reefer_eq = eq["IsReefer"].to_numpy(dtype=np.int8)

    # --- commodity, incoterm, mode, carrier, currency
    # Dangerous goods are a real but small share of containerised cargo. The
    # commodity dimension deliberately over-represents DG so that the DG
    # attributes are well populated; the booking mix has to correct for that or
    # every hazmat KPI comes out three times too large.
    dg_flag = commodities["IsDangerousGoods"].to_numpy(dtype=np.int8)
    com_weights = np.where(dg_flag == 1, DG_COMMODITY_WEIGHT, 1.0)
    com_weights = com_weights / com_weights.sum()
    commodity_key = rng.choice(
        commodities["CommodityKey"].to_numpy(np.int32),
        size=n_rows,
        replace=True,
        p=com_weights,
    )
    com = commodities.set_index("CommodityKey")
    is_dg = com["IsDangerousGoods"].reindex(commodity_key).to_numpy(dtype=np.int8)

    incoterm_key = rng.choice(
        incoterms["IncotermKey"].to_numpy(np.int32), size=n_rows, replace=True
    )

    # Mode mix. Air is booked through the same funnel as ocean — the forwarding
    # desk is part of the same business — but an air booking has no vessel
    # voyage, so its voyage and service keys resolve to the unknown member and
    # its ports are airports.
    mode_lookup = modes.set_index("ModeCode")["ModeKey"]
    mode_key = np.empty(n_rows, dtype=np.int32)
    mode_draw = rng.choice(
        list(BOOKING_MODE_MIX.keys()),
        size=n_rows,
        replace=True,
        p=np.array(list(BOOKING_MODE_MIX.values())) / sum(BOOKING_MODE_MIX.values()),
    )
    for code, key in mode_lookup.items():
        mode_key[mode_draw == code] = np.int32(key)

    is_air = mode_draw == "AIR"
    if is_air.any():
        airports = locations[
            (locations["LocationType"] == "Airport") & (locations["LocationKey"] > 0)
        ]["LocationKey"].to_numpy(np.int32)
        if len(airports) >= 2:
            n_air = int(is_air.sum())
            loc_origin[is_air] = rng.choice(airports, size=n_air, replace=True)
            loc_dest[is_air] = rng.choice(airports, size=n_air, replace=True)
        voyage_key = voyage_key.copy()
        service_key = service_key.copy()
        voyage_key[is_air] = np.int32(-1)
        service_key[is_air] = np.int32(-1)
        # Air transit is days, not weeks.
        nominal_transit = nominal_transit.copy()
        nominal_transit[is_air] = rng.uniform(2.0, 5.0, size=int(is_air.sum()))

    # Carrier mix. Meridian carries most of its own cargo on its own tonnage, but
    # slot charters and partner services are a real and large part of liner
    # operations. Restricting this to own-fleet ocean carriers collapsed
    # CarrierKey to a single value across four fact tables, which silently killed
    # every carrier-comparison measure in the model.
    carrier_key = _draw_carrier_mix(rng, carriers, n_rows)

    # Currency correlates with origin region; most ocean freight bills in USD.
    usd_key = int(currencies[currencies["CurrencyCode"] == "USD"]["CurrencyKey"].iloc[0])
    currency_key = np.full(n_rows, usd_key, dtype=np.int32)
    non_usd = currencies[currencies["CurrencyCode"] != "USD"]["CurrencyKey"].to_numpy(np.int32)
    swap = rng.random(n_rows) < 0.22
    currency_key[swap] = rng.choice(non_usd, size=int(swap.sum()), replace=True)

    # --- volumes
    container_count = (1 + rng.poisson(1.6, size=n_rows)).astype(np.int16)
    teu_booked = (container_count * teu_factor).astype(np.float32)
    ffe_booked = (container_count * ffe_factor).astype(np.float32)

    density = com["AvgDensityKgPerCbm"].reindex(commodity_key).to_numpy(dtype=np.float64)
    internal_cbm = eq["InternalCbm"].to_numpy(dtype=np.float64)
    fill = rng.uniform(0.55, 0.92, size=n_rows)
    volume_cbm = (container_count * internal_cbm * fill).astype(np.float32)
    weight_kg = (volume_cbm * density).astype(np.float32)
    max_payload = eq["MaxPayloadKg"].to_numpy(dtype=np.float64) * container_count
    weight_kg = np.minimum(weight_kg, max_payload * 0.95).astype(np.float32)

    # --- rates
    base = np.array([LANE_BASE_RATE_FFE.get(l, DEFAULT_LANE_RATE_FFE) for l in lane])
    seasonal = rate_index(booking_dates)
    noise = rng.lognormal(0.0, RATE_LOGNORM_SIGMA, size=n_rows)
    direction_factor = np.where(is_headhaul, 1.0, BACKHAUL_YIELD_RATIO)
    reefer_premium = np.where(is_reefer_eq == 1, 1.45, 1.0)
    dg_premium = np.where(is_dg == 1, 1.18, 1.0)

    rate_per_ffe = base * seasonal * noise * direction_factor * reefer_premium * dg_premium
    rate_per_container = rate_per_ffe * ffe_factor
    quoted_total_usd = rate_per_container * container_count

    fx_map = _fx_lookup(fx)
    booking_date_key = to_date_key(booking_dates)
    rates = fx_map.reindex(
        pd.MultiIndex.from_arrays([booking_date_key, currency_key])
    ).to_numpy(dtype=np.float64)
    rates = np.where(np.isnan(rates) | (rates <= 0), 1.0, rates)

    quoted_rate_doc = rate_per_container / rates
    quoted_total_doc = quoted_total_usd / rates

    # --- status
    statuses = np.array(list(BOOKING_STATUS_MIX.keys()))
    probs = np.array(list(BOOKING_STATUS_MIX.values()))
    probs = probs / probs.sum()
    status = rng.choice(statuses, size=n_rows, replace=True, p=probs)

    # Inside the congestion window rollovers multiply — §3.3.
    # Congestion is a property of the *service*, not just the two ports. A
    # vessel stuck at Rotterdam delays every port on its rotation, so any
    # booking on a voyage whose rotation touches an affected port is exposed.
    # Scoping this to bookings whose own origin or destination is one of the two
    # ports would touch 2 locations in 420 and leave no signal to find.
    rotation = voy["RotationString"].fillna("").to_numpy().astype(str)
    touches_congested_port = np.zeros(n_rows, dtype=bool)
    for code in CONGESTION_PORTS:
        touches_congested_port |= np.char.find(rotation, code) >= 0
    congested = in_congestion_window(booking_dates) & touches_congested_port
    extra_roll = congested & (status == "Confirmed") & (
        rng.random(n_rows) < (BOOKING_STATUS_MIX["Rolled"] * (CONGESTION_ROLLOVER_MULTIPLIER - 1.0))
    )
    status = np.where(extra_roll, "Rolled", status)

    is_rolled = (status == "Rolled").astype(np.int8)
    rollover_count = np.zeros(n_rows, dtype=np.int8)
    rollover_count[is_rolled == 1] = rng.integers(
        1, 4, size=int(is_rolled.sum()), dtype=np.int8
    )

    lead_time = np.clip(rng.gamma(4.0, 3.2, size=n_rows), 1, 90).astype(np.int16)
    requested_dep = booking_dates + pd.to_timedelta(lead_time, unit="D")
    roll_delay = rollover_count.astype(np.int64) * 7
    confirmed_dep = requested_dep + pd.to_timedelta(roll_delay, unit="D")
    confirmed_key = to_date_key(confirmed_dep)
    confirmed_key = np.where(
        np.isin(status, ["Confirmed", "Rolled"]), confirmed_key, np.int32(-1)
    ).astype(np.int32)
    cutoff = requested_dep - pd.Timedelta(days=3)

    out = pd.DataFrame(
        {
            "BookingKey": np.arange(key_offset + 1, key_offset + n_rows + 1, dtype=np.int64),
            "BookingNo": [f"BKG{y % 100:02d}{i:07d}" for i, y in
                          zip(range(1, n_rows + 1), booking_dates.year)],
            "BookingDateKey": booking_date_key,
            "RequestedDepartureDateKey": to_date_key(requested_dep),
            "ConfirmedDepartureDateKey": confirmed_key,
            "CutoffDateKey": to_date_key(cutoff),
            "CustomerKey": customer_key,
            "LocationKeyOrigin": loc_origin,
            "LocationKeyDestination": loc_dest,
            "CarrierKey": carrier_key,
            "VoyageKey": np.where(
                np.isin(status, ["Confirmed", "Rolled"]), voyage_key, np.int32(-1)
            ).astype(np.int32),
            "ServiceKey": service_key,
            "EquipmentKey": equipment_key,
            "ModeKey": mode_key,
            "CommodityKey": commodity_key,
            "IncotermKey": incoterm_key,
            "CurrencyKey": currency_key,
            "QuoteKey": np.arange(500001 + key_offset, 500001 + key_offset + n_rows, dtype=np.int64),
            "ContainerCount": container_count,
            "TeuBooked": teu_booked,
            "FfeBooked": ffe_booked,
            "WeightKgBooked": weight_kg,
            "VolumeCbmBooked": volume_cbm,
            "QuotedRatePerContainer_doc": quoted_rate_doc.astype(np.float32),
            "QuotedRatePerContainer_usd": rate_per_container.astype(np.float32),
            "QuotedTotal_doc": quoted_total_doc.astype(np.float32),
            "QuotedTotal_usd": quoted_total_usd.astype(np.float32),
            "RolloverCount": rollover_count,
            "LeadTimeDays": lead_time,
            "IsConfirmed": (status == "Confirmed").astype(np.int8),
            "IsRolled": is_rolled,
            "IsCancelled": (status == "Cancelled").astype(np.int8),
            "IsNoShow": (status == "No-Show").astype(np.int8),
            "IsSpotBooking": (rng.random(n_rows) < 0.31).astype(np.int8),
            "IsReeferBooking": is_reefer_eq,
            "IsDangerousGoods": is_dg,
            "IsShipperOwnedEquipment": (
                eq["OwnershipType"].to_numpy() == "Shipper-Owned"
            ).astype(np.int8),
            "BookingStatus": status,
            # carried forward internally, dropped before write
            "_nominal_transit": nominal_transit,
            "_is_headhaul": is_headhaul,
            "_lane": lane,
            "_is_air": is_air,
            "_mode_code": mode_draw,
        }
    )
    out = out.sort_values("BookingDateKey", kind="stable").reset_index(drop=True)

    # Landmine #2: DUPLICATE_BOOKING_REFS booking references are made
    # non-unique, with genuinely different detail on each row. A booking
    # reference is the natural key an analyst will reach for, and discovering it
    # is not unique — then choosing a defensible dedupe rule — is the exercise.
    if len(out) > 2 * DUPLICATE_BOOKING_REFS:
        victims = rng.choice(len(out), size=DUPLICATE_BOOKING_REFS, replace=False)
        donors = rng.choice(len(out), size=DUPLICATE_BOOKING_REFS, replace=False)
        nos = out["BookingNo"].to_numpy().copy()
        nos[victims] = nos[donors]
        out["BookingNo"] = nos

    return out


_CONGESTION_KEY_CACHE: dict[int, np.ndarray] = {}


def CONGESTION_PORT_KEYS(locations: pd.DataFrame) -> np.ndarray:
    """LocationKeys of the §3.3 congestion ports, cached per dataframe identity."""
    ident = id(locations)
    if ident not in _CONGESTION_KEY_CACHE:
        _CONGESTION_KEY_CACHE[ident] = locations[
            locations["LocationCode"].isin(CONGESTION_PORTS)
        ]["LocationKey"].to_numpy(dtype=np.int32)
    return _CONGESTION_KEY_CACHE[ident]


# --------------------------------------------------------------------------- #
# 2.2  FactShipment
# --------------------------------------------------------------------------- #

EARTH_RADIUS_KM = 6371.0
# Sea and air routes are not great circles. Ocean routing has to go round
# landmasses and through canals, so realised distance runs well above the
# straight-line figure; air is much closer to direct.
OCEAN_ROUTE_FACTOR = 1.34
AIR_ROUTE_FACTOR = 1.06
LANDSIDE_DELIVERY_DAYS = (1.0, 9.0)
TRANSHIPMENT_RATE = 0.31
LATE_ARRIVING_CUSTOMER_ROWS = 47
DUPLICATE_BOOKING_REFS = 312


def _haversine_km(
    lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray
) -> np.ndarray:
    """Great-circle distance in km between two arrays of coordinates."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlam / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def _draw_on_time(
    rng: np.random.Generator, variance_days: np.ndarray, target_rate: float
) -> np.ndarray:
    """Draw a delivery on-time flag correlated with vessel transit variance.

    ``p_i = sigmoid(alpha - beta * variance_i)`` with ``beta`` fixed by
    ON_TIME_VARIANCE_SENSITIVITY and ``alpha`` solved by bisection so that the
    mean of ``p`` equals ``target_rate``. Self-calibrating, so changing the
    transit distribution does not silently move the headline OTIF number.
    """
    beta = ON_TIME_VARIANCE_SENSITIVITY
    shifted = -beta * np.clip(variance_days, -30.0, 90.0)

    def mean_p(alpha: float) -> float:
        return float(np.mean(1.0 / (1.0 + np.exp(-(alpha + shifted)))))

    lo, hi = -20.0, 20.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if mean_p(mid) < target_rate:
            lo = mid
        else:
            hi = mid
    alpha = (lo + hi) / 2.0
    p = 1.0 / (1.0 + np.exp(-(alpha + shifted)))
    return (rng.random(len(p)) < p).astype(np.int8)


def build_fact_shipment(
    dims: dict[str, pd.DataFrame],
    bookings: pd.DataFrame,
    fx: pd.DataFrame,
    n_rows: int,
    *,
    seed_label: str = "FactShipment",
    key_offset: int = 0,
) -> pd.DataFrame:
    """One row per house bill of lading — §2.2. Transaction grain.

    Only bookings that were confirmed or rolled become shipments; cancelled,
    no-show and pending bookings never sail. That is what makes the booking
    funnel a real funnel rather than two tables with the same row count.
    """
    rng = child_rng(seed_label)

    eligible = bookings[bookings["BookingStatus"].isin(["Confirmed", "Rolled"])]
    if len(eligible) < n_rows:
        n_rows = len(eligible)
    src = eligible.sample(
        n=n_rows, replace=False, random_state=int(rng.integers(1 << 31))
    ).sort_values("BookingDateKey", kind="stable").reset_index(drop=True)

    locations = dims["DimLocation"].set_index("LocationKey")
    modes = dims["DimMode"].set_index("ModeKey")
    warehouses = dims["DimWarehouse"]
    voyages = dims["DimVoyage"].set_index("VoyageKey")

    n = len(src)
    is_air = src["_is_air"].to_numpy(dtype=bool)
    nominal_transit = src["_nominal_transit"].to_numpy(dtype=np.float64)
    is_headhaul = src["_is_headhaul"].to_numpy(dtype=bool)

    # --- departure: confirmed date, plus the slippage that always happens
    confirmed = src["ConfirmedDepartureDateKey"].to_numpy(dtype=np.int64)
    requested = src["RequestedDepartureDateKey"].to_numpy(dtype=np.int64)
    base_key = np.where(confirmed > 0, confirmed, requested)
    dep = pd.to_datetime(base_key.astype(str), format="%Y%m%d")
    dep = dep + pd.to_timedelta(rng.integers(0, 3, size=n), unit="D")

    # --- planned vs actual transit. §3.4: right-skewed, so mean != median.
    planned_transit = np.round(nominal_transit + SCHEDULE_BUFFER_DAYS).astype(np.int16)
    excess = rng.lognormal(TRANSIT_LOGNORM_MU, TRANSIT_LOGNORM_SIGMA, size=n)

    eta = dep + pd.to_timedelta(planned_transit, unit="D")

    # Congestion adds materially to transit on affected rotations — §3.3.
    rot = voyages["RotationString"].reindex(src["VoyageKey"].to_numpy()).fillna("")
    rot = rot.to_numpy().astype(str)
    affected_service = np.zeros(n, dtype=bool)
    for code in CONGESTION_PORTS:
        affected_service |= np.char.find(rot, code) >= 0
    in_window = in_congestion_window(pd.DatetimeIndex(eta))
    congestion_add = np.where(
        affected_service & in_window,
        rng.exponential(CONGESTION_TRANSIT_ADD_MEAN, size=n),
        0.0,
    )

    actual_transit = np.round(
        nominal_transit + excess + congestion_add
    ).astype(np.int16)
    ata = dep + pd.to_timedelta(actual_transit, unit="D")
    delivery = ata + pd.to_timedelta(
        np.round(rng.uniform(*LANDSIDE_DELIVERY_DAYS, size=n)).astype(np.int16), unit="D"
    )

    # --- geography and distance
    o_lat = locations["Latitude"].reindex(src["LocationKeyOrigin"]).to_numpy(np.float64)
    o_lon = locations["Longitude"].reindex(src["LocationKeyOrigin"]).to_numpy(np.float64)
    d_lat = locations["Latitude"].reindex(src["LocationKeyDestination"]).to_numpy(np.float64)
    d_lon = locations["Longitude"].reindex(src["LocationKeyDestination"]).to_numpy(np.float64)
    gc = _haversine_km(o_lat, o_lon, d_lat, d_lon)
    distance_km = gc * np.where(is_air, AIR_ROUTE_FACTOR, OCEAN_ROUTE_FACTOR)
    distance_km = np.nan_to_num(distance_km, nan=0.0)

    # --- POL / POD. For ocean these differ from the door origin/destination.
    pol = src["LocationKeyOrigin"].to_numpy(np.int32)
    pod = src["LocationKeyDestination"].to_numpy(np.int32)

    # --- volumes carried from the booking
    container_count = src["ContainerCount"].to_numpy(dtype=np.int16).copy()
    teu = src["TeuBooked"].to_numpy(dtype=np.float32).copy()
    ffe = src["FfeBooked"].to_numpy(dtype=np.float32).copy()
    gross_kg = src["WeightKgBooked"].to_numpy(dtype=np.float64).copy()
    volume_cbm = src["VolumeCbmBooked"].to_numpy(dtype=np.float64).copy()

    # An air consignment is not a container. Zeroing TEU and FFE here is what
    # keeps revenue per FFE honest — leaving air volume in the denominator would
    # quietly understate ocean yield by about a tenth.
    n_air = int(is_air.sum())
    if n_air:
        container_count[is_air] = 0
        teu[is_air] = 0.0
        ffe[is_air] = 0.0
        air_kg = rng.uniform(*AIR_WEIGHT_KG_RANGE, size=n_air)
        air_density = rng.uniform(*AIR_DENSITY_KG_PER_CBM, size=n_air)
        gross_kg[is_air] = air_kg
        volume_cbm[is_air] = air_kg / air_density

    # --- chargeable weight: the three divisor conventions, applied per mode
    mode_code = src["_mode_code"].to_numpy()
    volumetric_air_std = volume_cbm * 1_000_000.0 / AIR_DIVISOR_STANDARD
    volumetric_air_alt = volume_cbm * 1_000_000.0 / AIR_DIVISOR_ALTERNATE
    use_alt = rng.random(n) < AIR_ALTERNATE_SHARE
    volumetric_air = np.where(use_alt, volumetric_air_alt, volumetric_air_std)

    chargeable = gross_kg.copy()
    air_mask = mode_code == "AIR"
    chargeable[air_mask] = np.maximum(gross_kg[air_mask], volumetric_air[air_mask])
    lcl_mask = mode_code == "LCL"
    chargeable[lcl_mask] = np.maximum(
        gross_kg[lcl_mask], volume_cbm[lcl_mask] * LCL_KG_PER_CBM
    )
    # Revenue tons only mean anything for LCL, where the 1:1000 rule applies.
    revenue_tons = np.where(
        lcl_mask, np.maximum(gross_kg / 1000.0, volume_cbm), 0.0
    )

    # --- money
    revenue_usd = src["QuotedTotal_usd"].to_numpy(dtype=np.float64) * rng.uniform(
        0.94, 1.08, size=n
    )
    cost_ratio = np.clip(
        rng.normal(COST_RATIO_MEAN, COST_RATIO_SIGMA, size=n), 0.45, 1.35
    )
    direct_cost_usd = revenue_usd * cost_ratio
    gross_profit_usd = revenue_usd - direct_cost_usd
    gross_margin_pct = np.divide(
        gross_profit_usd, revenue_usd, out=np.zeros(n), where=revenue_usd > 0
    )

    fx_map = _fx_lookup(fx)
    currency_key = src["CurrencyKey"].to_numpy(np.int32)
    ship_date_key = to_date_key(dep)
    rates = fx_map.reindex(
        pd.MultiIndex.from_arrays([ship_date_key, currency_key])
    ).to_numpy(dtype=np.float64)
    rates = np.where(np.isnan(rates) | (rates <= 0), 1.0, rates)

    # --- quality flags
    variance = (actual_transit - planned_transit).astype(np.float64)
    on_time = _draw_on_time(rng, variance, ON_TIME_DELIVERY_TARGET)
    in_full = (rng.random(n) < IN_FULL_RATE).astype(np.int8)
    doc_clean = (rng.random(n) < DOC_CLEAN_RATE).astype(np.int8)
    damaged = (rng.random(n) < DAMAGE_RATE).astype(np.int8)
    perfect = (
        (on_time == 1) & (in_full == 1) & (doc_clean == 1) & (damaged == 0)
    ).astype(np.int8)

    transhipped = ((rng.random(n) < TRANSHIPMENT_RATE) & ~is_air).astype(np.int8)
    tranship_count = np.where(
        transhipped == 1, rng.integers(1, 3, size=n), 0
    ).astype(np.int8)

    co2_gpk = modes["Co2GramsPerTonneKm"].reindex(src["ModeKey"]).to_numpy(np.float64)
    co2_gpk = np.nan_to_num(co2_gpk, nan=CO2_GRAMS_PER_TONNE_KM_OCEAN)
    co2_tonnes = (gross_kg / 1000.0) * distance_km * co2_gpk / 1_000_000.0

    # --- warehousing attachment
    warehouse_key = np.full(n, -1, dtype=np.int32)
    wh_pool = warehouses[warehouses["WarehouseKey"] > 0]["WarehouseKey"].to_numpy(np.int32)
    has_wh = rng.random(n) < 0.34
    warehouse_key[has_wh] = rng.choice(wh_pool, size=int(has_wh.sum()), replace=True)

    # The booking resolved its customer version as at the *booking* date. By the
    # time the box sails, that version may have expired — a new account manager,
    # a new credit tier. Re-resolving at departure keeps the fact pointing at the
    # version that was true when the shipment happened, so the only temporally
    # invalid references left in the data are the deliberate ones below.
    cust_codes_for_ship = (
        dims["DimCustomer"].set_index("CustomerKey")["CustomerCode"]
        .reindex(src["CustomerKey"].to_numpy())
        .to_numpy()
    )
    customer_key_at_departure = _resolve_scd_customer(
        dims["DimCustomer"], cust_codes_for_ship, pd.DatetimeIndex(dep)
    )
    # Anything that still fails to resolve falls back to the booking-time key,
    # which is a defensible commercial attribution rather than an unknown member.
    unresolved = customer_key_at_departure == -1
    customer_key_at_departure[unresolved] = src["CustomerKey"].to_numpy(np.int32)[unresolved]

    # Landmine #6: exactly LATE_ARRIVING_CUSTOMER_ROWS shipments are pointed at a
    # customer version whose validity begins after the shipment date. The learner
    # has to detect and route these to the unknown member, and report the count.
    late_pool = np.flatnonzero(~unresolved)
    if len(late_pool) > LATE_ARRIVING_CUSTOMER_ROWS:
        late_idx = rng.choice(
            late_pool, size=LATE_ARRIVING_CUSTOMER_ROWS, replace=False
        )
        newest = (
            dims["DimCustomer"].query("IsCurrent == 1")
            .sort_values("OnboardedDate")
            .tail(200)["CustomerKey"].to_numpy(np.int32)
        )
        if len(newest):
            customer_key_at_departure[late_idx] = rng.choice(
                newest, size=len(late_idx), replace=True
            )

    status = np.where(
        delivery <= pd.Timestamp(CALENDAR_END), "Delivered",
        np.where(ata <= pd.Timestamp(CALENDAR_END), "At Destination", "In Transit"),
    )

    year2 = pd.DatetimeIndex(dep).year % 100
    out = pd.DataFrame(
        {
            "ShipmentKey": np.arange(key_offset + 1, key_offset + n + 1, dtype=np.int64),
            "HouseBlNo": [f"MGLH{y:02d}{i:07d}" for i, y in zip(range(1, n + 1), year2)],
            "MasterBlNo": [f"MGLM{y:02d}{i // 3 + 1:07d}" for i, y in zip(range(1, n + 1), year2)],
            "BookingKey": src["BookingKey"].to_numpy(dtype=np.int64),
            "ShipmentDateKey": ship_date_key,
            "EtaDateKey": to_date_key(eta),
            "AtaDateKey": to_date_key(ata),
            "DeliveryDateKey": to_date_key(delivery),
            "CustomerKey": customer_key_at_departure,
            "LocationKeyOrigin": src["LocationKeyOrigin"].to_numpy(np.int32),
            "LocationKeyDestination": src["LocationKeyDestination"].to_numpy(np.int32),
            "LocationKeyPol": pol,
            "LocationKeyPod": pod,
            "CarrierKey": src["CarrierKey"].to_numpy(np.int32),
            "VoyageKey": src["VoyageKey"].to_numpy(np.int32),
            "ServiceKey": src["ServiceKey"].to_numpy(np.int32),
            "ModeKey": src["ModeKey"].to_numpy(np.int32),
            "EquipmentKey": src["EquipmentKey"].to_numpy(np.int32),
            "CommodityKey": src["CommodityKey"].to_numpy(np.int32),
            "IncotermKey": src["IncotermKey"].to_numpy(np.int32),
            "CurrencyKey": currency_key,
            "WarehouseKey": warehouse_key,
            "ContainerCount": container_count,
            "Teu": teu,
            "Ffe": ffe,
            "GrossWeightKg": gross_kg.astype(np.float32),
            "VolumeCbm": volume_cbm.astype(np.float32),
            "ChargeableWeightKg": chargeable.astype(np.float32),
            "RevenueTons": revenue_tons.astype(np.float32),
            "PieceCount": (container_count * rng.integers(40, 900, size=n)).astype(np.int32),
            "Revenue_doc": (revenue_usd / rates).astype(np.float32),
            "Revenue_usd": revenue_usd.astype(np.float32),
            "DirectCost_doc": (direct_cost_usd / rates).astype(np.float32),
            "DirectCost_usd": direct_cost_usd.astype(np.float32),
            "GrossProfit_usd": gross_profit_usd.astype(np.float32),
            "GrossMarginPct": gross_margin_pct.astype(np.float32),
            "PlannedTransitDays": planned_transit,
            "ActualTransitDays": actual_transit,
            "TransitVarianceDays": (actual_transit - planned_transit).astype(np.int16),
            "DistanceKm": distance_km.astype(np.float32),
            "Co2Tonnes": co2_tonnes.astype(np.float32),
            "IsOnTime": on_time,
            "IsInFull": in_full,
            "IsDamaged": damaged,
            "IsDocumentationClean": doc_clean,
            "IsPerfectOrder": perfect,
            "IsTranshipped": transhipped,
            "TranshipmentCount": tranship_count,
            "ShipmentStatus": status,
            "_is_air": is_air,
            "_mode_code": mode_code,
            "_dep": dep,
            "_eta": eta,
            "_ata": ata,
            "_delivery": delivery,
            "_affected_service": affected_service,
        }
    )
    return out.sort_values("ShipmentDateKey", kind="stable").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 2.3  FactShipmentMilestone  —  accumulating snapshot
# --------------------------------------------------------------------------- #

# Offsets in days for each milestone, expressed relative to an anchor. Negative
# values sit before the anchor. The accumulating-snapshot shape means these are
# COLUMNS on one row per shipment, not rows — which is exactly the distinction
# Day 3 asks the learner to state.
MILESTONE_PLAN: tuple[tuple[str, str, float, float, str, str], ...] = (
    #  column                        anchor  lo    hi   applies_to  DCSA code
    ("BookingConfirmedDateKey",      "book",  0.0,  2.0, "all",      "CONF"),
    ("EmptyPickupDateKey",           "dep",  -9.0, -6.0, "ocean",    "PICK"),
    ("StuffingDateKey",              "dep",  -7.0, -4.0, "ocean",    "STUF"),
    ("GateInOriginDateKey",          "dep",  -4.0, -2.0, "all",      "GTIN"),
    ("CustomsExportClearedDateKey",  "dep",  -3.0, -1.0, "all",      "CUSR"),
    ("VesselLoadDateKey",            "dep",  -2.0,  0.0, "ocean",    "LOAD"),
    ("VesselDepartureDateKey",       "dep",   0.0,  0.0, "all",      "DEPA"),
    ("TranshipmentDischargeDateKey", "mid",  -1.0,  1.0, "tranship", "DISC"),
    ("TranshipmentLoadDateKey",      "mid",   1.0,  4.0, "tranship", "LOAD"),
    ("VesselArrivalDateKey",         "ata",   0.0,  0.0, "all",      "ARRI"),
    ("VesselDischargeDateKey",       "ata",   0.0,  2.0, "all",      "DISC"),
    ("CustomsImportClearedDateKey",  "ata",   1.0,  5.0, "all",      "CUSR"),
    ("GateOutDestinationDateKey",    "ata",   2.0,  7.0, "all",      "GTOT"),
    ("EmptyReturnDateKey",           "ata",   4.0, 14.0, "ocean",    "DROP"),
)

LAG_PLAN: tuple[tuple[str, str, str], ...] = (
    ("LagBookingToGateIn", "BookingConfirmedDateKey", "GateInOriginDateKey"),
    ("LagGateInToLoad", "GateInOriginDateKey", "VesselLoadDateKey"),
    ("LagLoadToDeparture", "VesselLoadDateKey", "VesselDepartureDateKey"),
    ("LagDepartureToArrival", "VesselDepartureDateKey", "VesselArrivalDateKey"),
    ("LagArrivalToDischarge", "VesselArrivalDateKey", "VesselDischargeDateKey"),
    ("LagDischargeToGateOut", "VesselDischargeDateKey", "GateOutDestinationDateKey"),
    ("LagGateOutToEmptyReturn", "GateOutDestinationDateKey", "EmptyReturnDateKey"),
    ("LagTotalDoorToDoor", "BookingConfirmedDateKey", "GateOutDestinationDateKey"),
)


def build_fact_shipment_milestone(
    dims: dict[str, pd.DataFrame],
    shipments: pd.DataFrame,
    bookings: pd.DataFrame,
    *,
    as_of: object | None = None,
) -> pd.DataFrame:
    """One row per shipment, 14 milestone date columns — §2.3.

    ``as_of`` is the date the snapshot is taken. It defaults to the frozen
    history's horizon, but the live feed must pass the run date: with the
    horizon hard-coded, every milestone on a live shipment evaluated as "has not
    happened yet", so all 14 columns came back -1, MilestonesCompleted was 0,
    and every live row landed in the unknown date partition.

    A milestone that has not happened yet carries ``-1``, not null: the whole
    point of an accumulating snapshot is that the row exists from the start and
    fills in over the journey's life. Milestones falling after the dataset's
    'today' are therefore unset, which is what gives the model genuine
    in-flight shipments to reason about.
    """
    rng = child_rng("FactShipmentMilestone")
    milestones = dims["DimMilestone"]

    n = len(shipments)
    today = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp(CALENDAR_END)

    dep = pd.DatetimeIndex(shipments["_dep"])
    ata = pd.DatetimeIndex(shipments["_ata"])
    book = pd.to_datetime(
        bookings.set_index("BookingKey")["BookingDateKey"]
        .reindex(shipments["BookingKey"].to_numpy())
        .to_numpy()
        .astype(str),
        format="%Y%m%d",
    )
    mid = dep + (ata - dep) / 2

    anchors = {"book": book, "dep": dep, "ata": ata, "mid": mid}
    is_air = shipments["_is_air"].to_numpy(dtype=bool)
    is_tranship = shipments["IsTranshipped"].to_numpy(dtype=np.int8) == 1

    cols: dict[str, np.ndarray] = {}
    for col, anchor, lo, hi, applies, _code in MILESTONE_PLAN:
        offset = np.round(rng.uniform(lo, hi, size=n))
        ts = pd.DatetimeIndex(anchors[anchor]) + pd.to_timedelta(offset, unit="D")
        keys = to_date_key(ts).astype(np.int32)

        # Not applicable: air has no vessel or empty-equipment leg; the
        # transhipment pair only exists where the cargo was transhipped.
        if applies == "ocean":
            keys = np.where(is_air, np.int32(-1), keys)
        elif applies == "tranship":
            keys = np.where(is_tranship & ~is_air, keys, np.int32(-1))

        # Not yet happened.
        keys = np.where(ts > today, np.int32(-1), keys)
        cols[col] = keys.astype(np.int32)

    out = pd.DataFrame(
        {
            "ShipmentKey": shipments["ShipmentKey"].to_numpy(dtype=np.int64),
            "HouseBlNo": shipments["HouseBlNo"].to_numpy(),
            "CustomerKey": shipments["CustomerKey"].to_numpy(np.int32),
            "ServiceKey": shipments["ServiceKey"].to_numpy(np.int32),
            "ModeKey": shipments["ModeKey"].to_numpy(np.int32),
            "LocationKeyPol": shipments["LocationKeyPol"].to_numpy(np.int32),
            "LocationKeyPod": shipments["LocationKeyPod"].to_numpy(np.int32),
            **cols,
        }
    )

    # --- lag measures. -1 wherever either end is unset.
    for name, start_col, end_col in LAG_PLAN:
        a = out[start_col].to_numpy(dtype=np.int64)
        b = out[end_col].to_numpy(dtype=np.int64)
        both = (a > 0) & (b > 0)
        lag = np.full(n, -1, dtype=np.int64)
        if both.any():
            sa = pd.to_datetime(a[both].astype(str), format="%Y%m%d")
            sb = pd.to_datetime(b[both].astype(str), format="%Y%m%d")
            lag[both] = (sb - sa).days
        out[name] = np.clip(lag, -1, 32767).astype(np.int16)

    milestone_cols = [c for c, *_ in MILESTONE_PLAN]
    date_matrix = out[milestone_cols].to_numpy(dtype=np.int64)
    reached_mask = date_matrix > 0
    out["MilestonesCompleted"] = reached_mask.sum(axis=1).astype(np.int8)

    # CurrentMilestoneKey: the milestone whose date is the latest one reached.
    # Resolved from the actual dates, not from a count — a count cannot tell
    # "not applicable to this mode" apart from "not yet reached", so an air
    # shipment with eight dates set would otherwise be reported as sitting at
    # the eighth milestone of an ocean journey it never takes.
    code_by_col = {c: code for c, *_rest, code in MILESTONE_PLAN}
    key_by_code = (
        milestones[milestones["MilestoneKey"] > 0]
        .drop_duplicates(subset="EventCode", keep="first")
        .set_index("EventCode")["MilestoneKey"]
    )
    col_keys = np.array(
        [int(key_by_code.get(code_by_col[c], -1)) for c in milestone_cols],
        dtype=np.int32,
    )

    # Unreached milestones are pushed to -1 so argmax picks the true latest.
    ranked = np.where(reached_mask, date_matrix, -1)
    latest_idx = ranked.argmax(axis=1)
    any_reached = reached_mask.any(axis=1)
    out["CurrentMilestoneKey"] = np.where(
        any_reached, col_keys[latest_idx], np.int32(-1)
    ).astype(np.int32)
    out["IsJourneyComplete"] = (
        out["GateOutDestinationDateKey"].to_numpy() > 0
    ).astype(np.int8)

    return out.sort_values("BookingConfirmedDateKey", kind="stable").reset_index(drop=True)
