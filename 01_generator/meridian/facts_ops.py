"""Operational fact builders — SCHEMA_CONTRACT.md sections 2.4, 2.5, 2.6.

    FactPortCall  ->  FactContainerMove  ->  FactFreightCharge

These three carry the congestion set-piece of §3.3. The event degrades berth
productivity, lengthens dwell, and *raises* demurrage revenue at the same time —
so the analyst who reports "D&D revenue up 30%" as good news gets caught out.
That contradiction is the point, and it has to be present in the numbers rather
than described in a README.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import (
    CONGESTION_END_DATE as CONGESTION_END,
    CONGESTION_LOCATIONS as CONGESTION_PORTS,
    CONGESTION_START_DATE as CONGESTION_START,
    FACT_END_DATE as CALENDAR_END,
)
from .facts_core import _draw_carrier_mix
from .util import child_rng, make_container_no, to_date_key

# --------------------------------------------------------------------------- #
# Port call constants — §2.5, §3.3
# --------------------------------------------------------------------------- #

ON_TIME_ARRIVAL_WINDOW_HOURS = 24.0   # the +/- 1 calendar day industry rule
BASE_ON_TIME_ARRIVAL_RATE = 0.66      # §4 gate 5: 0.62-0.70 outside the window
CONGESTED_ON_TIME_ARRIVAL_RATE = 0.31 # §4 gate 5: 0.28-0.34 inside it

ARRIVAL_DELAY_HOURS_SCALE = 26.0
WAIT_FOR_BERTH_HOURS_MEAN = 7.5
BERTH_HOURS_PER_1000_MOVES = 13.0
MOVES_PER_CRANE_HOUR_NET = (26.0, 34.0)
GROSS_TO_NET_CRANE_RATIO = (0.72, 0.88)
CRANES_PER_CALL = (2, 8)
RESTOW_SHARE = (0.002, 0.02)
PORT_COST_PER_MOVE_USD = (78.0, 165.0)
BUNKER_TONNES_PER_CALL = (55.0, 420.0)

# §3.3 multipliers
CONGESTION_WAIT_MULTIPLIER = 3.4
CONGESTION_PRODUCTIVITY_MULTIPLIER = 0.72
# The NET congestion effect on turnaround must be x1.9. It cannot be applied as
# x1.9 directly, because berth occupancy is derived from crane hours, and crane
# hours already rise by 1/0.72 = x1.39 when productivity drops. Applying 1.9 on
# top of that compounded to x2.59. The explicit multiplier is therefore
# 1.9 / (1/0.72) = 1.368, so the two effects together land on 1.9.
CONGESTION_TURNAROUND_MULTIPLIER = 1.368
# Contract 3.3 wants OBSERVED dwell at congested ports x2.6. Two event classes
# carry different multipliers: the charged events (gate-out, empty return) take
# their dwell from the storage/hold interval and so move by
# CONGESTION_STORAGE_MULTIPLIER, while every other event uses the gamma draw
# below. So the input constant is not the observed effect, and the observed
# effect is the one the contract specifies.
#
# Calibrated empirically on the reproducible build (ADR-002), because the
# closed-form "(5m + 2s)/7" approximation used before the determinism fix does
# not hold: the gate figure is a ratio of MEANS over rows with DwellHours > 0,
# which weights by magnitude rather than by count. Measured pairs at
# CONGESTION_STORAGE_MULTIPLIER = 2.045:
#     m_dwell 2.99 -> observed 2.29     m_dwell 3.25 -> observed 2.43
# Target 2.6, gate tolerance +/-15% i.e. [2.21, 2.99].
CONGESTION_DWELL_MULTIPLIER = 3.25

# Contract 3.3 specifies two congestion effects that look like one number but are
# not: dwell hours x2.6, and demurrage charge lines x3.1 *in volume*. Because
# demurrage is the tail of the storage distribution above a fixed free-time
# threshold, a multiplier on the interval multiplies the charged COUNT by much
# more than itself -- the threshold amplifies it. So the storage interval carries
# its own multiplier, separate from the dwell one.
#
# Solving for it needs one more correction. Congestion is applied on the basis of
# the box ARRIVING during the window, but the demurrage line is dated when the
# box GATES OUT, several days later. A container arriving in the final week of
# congestion is billed after the window closes, so measured at event-date grain
# the effect is smeared and reads smaller than its true size. That smearing is
# real, not an artefact -- demurrage invoices always lag the congestion that
# caused them -- so the multiplier is solved against the OBSERVED ratio.
#
# The closed form gets the SHAPE right and the level wrong. Charged population is
# the GTOT and DROP rows (FreeTimeDaysUsed > 0); demurrage lands only on GTOT.
# With interval ~ gamma(1.7, 1.30) and free time of 5 days for 84.4% of boxes, 3
# for reefers and 4 for specials, P(m*G > free) / P(G > free) is 2.56 at m=1.5,
# 3.95 at m=1.97 and 5.19 at m=2.5 — steeply amplified, exactly as the threshold
# argument predicts. But the smearing factor is not a constant, so dividing by a
# single fitted smearing (the 0.78 this was tuned to before ADR-002, against a
# build that could not be reproduced) gives the wrong answer.
#
# So it is solved by measurement on the reproducible build instead:
#     m 1.97 -> 2.39     m 2.045 -> 3.20     m 2.10 -> 3.63     m 2.45 -> 4.84
# Target is 3.1 with a +/-15% gate, i.e. [2.635, 3.565]. Note how sharp the
# response is: 0.13 on the input moves the observed count ratio by 1.2. That
# sensitivity is inherent to a threshold effect and is the reason this constant is
# measured rather than reasoned about.
#
# This also lifts observed dwell, because DwellHours on the two charged events IS
# the interval (see the `dwell = interval * 24` line below) rather than an
# independent draw. That coupling is deliberate — a container cannot dwell for one
# length of time and be billed for another — so the two gate figures move together
# and both are checked.
CONGESTION_STORAGE_MULTIPLIER = 2.045

OMITTED_CALL_RATE = 0.014
EXTRA_CALL_RATE = 0.008

# --------------------------------------------------------------------------- #
# Container move constants — §2.4
# --------------------------------------------------------------------------- #

# One instrumented container journey is seven equipment events. Two of the seven
# are empty (collect the box, return the box), which is what fixes the empty
# share inside journeys; standalone repositioning moves top it up to the §3.4
# target of 32% empty overall.
JOURNEY_EVENTS: tuple[tuple[str, float, int], ...] = (
    #  DCSA code, day offset from gate-in, is_laden
    ("PICK", -6.0, 0),
    ("STUF", -4.5, 1),
    ("GTIN",  0.0, 1),
    ("LOAD",  1.5, 1),
    ("DISC",  0.0, 1),   # anchored to arrival, not gate-in
    ("GTOT",  3.0, 1),   # anchored to arrival
    ("DROP",  8.0, 0),   # anchored to arrival
)

# IsRailEvent, IsInspection and IsTranshipmentMove were zero on every single row
# of 1.4M — three columns that looked like working flags and could never filter
# anything. Rather than add extra event rows (which would break the fixed
# seven-event journey budget and the 32% empty share derived from it), the
# existing events are classified:
#
#   * a share of gate-outs leave the terminal by rail rather than by truck, so
#     the gate-out event IS the rail-out. The demurrage clock stops either way,
#     which is why reclassifying it does not disturb the D&D calculation.
#   * a small share of gate-ins are held for customs or scanning inspection.
#   * discharge and load events on a transhipped shipment are transhipment moves.
RAIL_OUT_SHARE = 0.24
INSPECTION_SHARE = 0.031
ARRIVAL_ANCHORED_EVENTS = frozenset({"DISC", "GTOT", "DROP"})
TARGET_EMPTY_SHARE = 0.32

DWELL_GAMMA_SHAPE = 2.2
DWELL_GAMMA_SCALE = 18.0

# Port storage (DISC -> GTOT) and customer hold (GTOT -> DROP), in days.
# Right-skewed on purpose: free time is 3-5 days depending on equipment, so the
# tail of these distributions is exactly the population that incurs demurrage
# and detention.
# Solved numerically against the equipment mix rather than guessed. Free time is
# 5 days for dry (86.7% of boxes), 3 for reefer (8.3%) and 4 for specials (5.0%),
# so the blended exceedance is
#     0.867*P(X>5) + 0.083*P(X>3) + 0.050*P(X>4)
# which these parameters put at ~9% for demurrage and ~15% for detention — the
# order of magnitude a carrier actually bills. Reefers are over-represented in
# the charged tail by construction, because their free time is shorter.
PORT_STORAGE_GAMMA_SHAPE = 1.7
PORT_STORAGE_GAMMA_SCALE = 1.30
DETENTION_GAMMA_SHAPE = 1.8
DETENTION_GAMMA_SCALE = 1.55
MOVE_COST_USD = (32.0, 210.0)
CONTAINER_OWNER_PREFIXES = ("MGLU", "MGRU", "MGTU", "TCLU", "HLXU", "SEGU")

# --------------------------------------------------------------------------- #
# Freight charge constants — §2.6
# --------------------------------------------------------------------------- #

# Revenue charge lines must sum to FactShipment.Revenue_usd (gate 13), so the
# shares below are an allocation of that revenue, not an addition to it.
REVENUE_ALLOCATION = {
    "OFR": 0.640,   # base ocean/air freight
    "BAF": 0.135,   # bunker adjustment
    "THC": 0.105,   # terminal handling
    "DOC": 0.030,   # documentation
    "ISPS": 0.014,  # security
    "LSS": 0.026,   # low-sulphur surcharge
    "CGS": 0.010,   # congestion surcharge
    # Applied only to shipments that actually incurred them (see DD_CODES), so
    # these weights are per-affected-invoice, not per-invoice. Sized so combined
    # D&D lands near 2% of total revenue, which is the order carriers report.
    "DEM": 0.150,   # demurrage
    "DET": 0.110,   # detention
}
COST_ALLOCATION = {
    "OFR": 0.520,
    "THC": 0.170,
    "DRY": 0.140,   # inland drayage
    "CFS": 0.060,
    "CUS": 0.045,
    "INS": 0.030,
    "RAI": 0.035,
}
CREDIT_NOTE_RATE = 0.003
DISPUTED_RATE = 0.021
WAIVED_RATE = 0.008
TAX_RATE_RANGE = (0.0, 0.18)
CONGESTION_DEMURRAGE_MULTIPLIER = 3.1


def _congested(dates, location_keys, congested_keys) -> np.ndarray:
    """Rows inside the congestion window at one of the affected ports."""
    d = pd.DatetimeIndex(dates)
    in_window = (d >= pd.Timestamp(CONGESTION_START)) & (d <= pd.Timestamp(CONGESTION_END))
    return in_window & np.isin(location_keys, congested_keys)


def _congested_port_keys(locations: pd.DataFrame) -> np.ndarray:
    return locations[locations["LocationCode"].isin(CONGESTION_PORTS)][
        "LocationKey"
    ].to_numpy(dtype=np.int32)


# --------------------------------------------------------------------------- #
# 2.5  FactPortCall
# --------------------------------------------------------------------------- #


def build_fact_port_call(dims: dict[str, pd.DataFrame], n_rows: int) -> pd.DataFrame:
    """One row per vessel call at one terminal — §2.5.

    Built by exploding each voyage's rotation string, so a call's port is always
    a port the vessel actually visits on that service. PromisedEtaDateKey is the
    originally published ETA and is never revised: schedule reliability measured
    against a revised ETA is the number carriers can flatter, and the model has
    to make that distinction available.
    """
    rng = child_rng("FactPortCall")
    voyages = dims["DimVoyage"][dims["DimVoyage"]["VoyageKey"] > 0]
    locations = dims["DimLocation"]
    services = dims["DimService"].set_index("ServiceKey")
    vessels = dims["DimVessel"].set_index("VesselKey")
    carriers = dims["DimCarrier"]
    code_to_key = locations.set_index("LocationCode")["LocationKey"]

    # --- explode rotations
    rot = voyages["RotationString"].fillna("").astype(str)
    parts = rot.str.split("-")
    lengths = parts.map(len).to_numpy()
    voyage_key = np.repeat(voyages["VoyageKey"].to_numpy(np.int32), lengths)
    vessel_key = np.repeat(voyages["VesselKey"].to_numpy(np.int32), lengths)
    service_key = np.repeat(voyages["ServiceKey"].to_numpy(np.int32), lengths)
    start_key = np.repeat(voyages["VoyageStartDateKey"].to_numpy(np.int64), lengths)
    flat_codes = np.concatenate(parts.to_numpy())
    call_seq = np.concatenate([np.arange(1, n + 1) for n in lengths]).astype(np.int8)

    location_key = code_to_key.reindex(flat_codes).fillna(-1).to_numpy(np.int32)

    df = pd.DataFrame(
        {
            "VoyageKey": voyage_key,
            "VesselKey": vessel_key,
            "ServiceKey": service_key,
            "LocationKey": location_key,
            "CallSequence": call_seq,
            "_start_key": start_key,
        }
    )
    df = df[df["LocationKey"] > 0]

    # Trim or grow to the contracted row count.
    if len(df) > n_rows:
        df = df.sample(n=n_rows, replace=False, random_state=int(rng.integers(1 << 31)))
    df = df.sort_values(["_start_key", "VoyageKey", "CallSequence"], kind="stable")
    df = df.reset_index(drop=True)
    n = len(df)

    # --- promised ETA: voyage start plus cumulative steaming time per call
    loop_days = (
        services["LoopDurationDays"].reindex(df["ServiceKey"]).fillna(42.0).to_numpy(float)
    )
    calls_on_voyage = df.groupby("VoyageKey")["CallSequence"].transform("max").to_numpy()
    frac = df["CallSequence"].to_numpy() / np.maximum(calls_on_voyage, 1)
    start = pd.to_datetime(df["_start_key"].to_numpy().astype(str), format="%Y%m%d")
    promised = start + pd.to_timedelta(np.round(frac * loop_days), unit="D")
    promised_ts = promised + pd.to_timedelta(rng.integers(0, 24, size=n), unit="h")

    cong = _congested(promised_ts, df["LocationKey"].to_numpy(), _congested_port_keys(locations))

    # --- arrival. On-time is drawn to the target rate, then the delay magnitude
    # is made consistent with the flag rather than the other way round.
    target = np.where(cong, CONGESTED_ON_TIME_ARRIVAL_RATE, BASE_ON_TIME_ARRIVAL_RATE)
    is_on_time = (rng.random(n) < target).astype(np.int8)

    within = rng.uniform(-ON_TIME_ARRIVAL_WINDOW_HOURS, ON_TIME_ARRIVAL_WINDOW_HOURS, size=n)
    beyond = ON_TIME_ARRIVAL_WINDOW_HOURS + rng.exponential(
        ARRIVAL_DELAY_HOURS_SCALE * np.where(cong, CONGESTION_TURNAROUND_MULTIPLIER, 1.0),
        size=n,
    )
    # A late vessel is far more common than an early one.
    beyond = beyond * np.where(rng.random(n) < 0.88, 1.0, -1.0)
    arrival_delay_hours = np.where(is_on_time == 1, within, beyond)
    ata_ts = promised_ts + pd.to_timedelta(arrival_delay_hours, unit="h")

    wait_hours = rng.exponential(WAIT_FOR_BERTH_HOURS_MEAN, size=n) * np.where(
        cong, CONGESTION_WAIT_MULTIPLIER, 1.0
    )
    berth_ts = ata_ts + pd.to_timedelta(wait_hours, unit="h")

    # --- moves and productivity
    capacity = (
        vessels["NominalTeuCapacity"].reindex(df["VesselKey"]).fillna(6000).to_numpy(float)
    )
    capacity = np.clip(capacity, 800, 24000)
    exchange_ratio = rng.uniform(0.12, 0.42, size=n)
    total_moves = np.maximum(np.round(capacity * exchange_ratio), 40).astype(np.int32)
    discharge_share = rng.uniform(0.35, 0.65, size=n)
    discharge_moves = np.round(total_moves * discharge_share).astype(np.int32)
    load_moves = (total_moves - discharge_moves).astype(np.int32)
    restow = np.round(total_moves * rng.uniform(*RESTOW_SHARE, size=n)).astype(np.int16)

    cranes = rng.integers(CRANES_PER_CALL[0], CRANES_PER_CALL[1] + 1, size=n).astype(np.int8)
    mpch_net = rng.uniform(*MOVES_PER_CRANE_HOUR_NET, size=n) * np.where(
        cong, CONGESTION_PRODUCTIVITY_MULTIPLIER, 1.0
    )
    crane_hours_net = total_moves / np.maximum(mpch_net, 1.0)
    gross_ratio = rng.uniform(*GROSS_TO_NET_CRANE_RATIO, size=n)
    crane_hours_gross = crane_hours_net / gross_ratio
    mpch_gross = total_moves / np.maximum(crane_hours_gross, 0.1)

    berth_occupancy_hours = crane_hours_gross / np.maximum(cranes, 1) + rng.uniform(
        1.5, 6.0, size=n
    )
    berth_occupancy_hours *= np.where(cong, CONGESTION_TURNAROUND_MULTIPLIER, 1.0)
    unberth_ts = berth_ts + pd.to_timedelta(berth_occupancy_hours, unit="h")
    atd_ts = unberth_ts + pd.to_timedelta(rng.uniform(0.5, 4.0, size=n), unit="h")
    turnaround_hours = (atd_ts - ata_ts).total_seconds().to_numpy() / 3600.0
    moves_per_hour_berth = total_moves / np.maximum(berth_occupancy_hours, 0.1)

    # Revised ETA exists only where the carrier re-published one — and §3.5
    # landmine #1 leaves 4.1% of them unset even where they should exist.
    has_revision = rng.random(n) < 0.46
    revised = np.where(
        has_revision & (rng.random(n) > 0.041),
        to_date_key(promised_ts + pd.to_timedelta(arrival_delay_hours * 0.7, unit="h")),
        np.int32(-1),
    ).astype(np.int32)

    status = np.where(
        rng.random(n) < OMITTED_CALL_RATE,
        "Omitted",
        np.where(ata_ts > pd.Timestamp(CALENDAR_END), "Planned", "Completed"),
    )
    is_omitted = (status == "Omitted").astype(np.int8)

    # Same carrier-mix problem as the bookings: filtering to own-fleet ocean
    # carriers left one distinct value, so CarrierKey could not discriminate
    # anything on the port-call fact either.
    call_carriers = _draw_carrier_mix(rng, carriers, n)

    teu_discharged = discharge_moves * rng.uniform(1.5, 1.9, size=n)
    teu_loaded = load_moves * rng.uniform(1.5, 1.9, size=n)
    slot_capacity = capacity.astype(np.int32)
    slots_used = np.minimum(teu_loaded * rng.uniform(2.0, 5.5, size=n), capacity * 0.98)

    out = pd.DataFrame(
        {
            "PortCallKey": np.arange(1, n + 1, dtype=np.int64),
            "VoyageKey": df["VoyageKey"].to_numpy(np.int32),
            "VesselKey": df["VesselKey"].to_numpy(np.int32),
            "LocationKey": df["LocationKey"].to_numpy(np.int32),
            "ServiceKey": df["ServiceKey"].to_numpy(np.int32),
            "CarrierKey": call_carriers,
            "PromisedEtaDateKey": to_date_key(promised_ts),
            "RevisedEtaDateKey": revised,
            "AtaDateKey": to_date_key(ata_ts),
            "AtdDateKey": to_date_key(atd_ts),
            "BerthDateKey": to_date_key(berth_ts),
            "CallSequence": df["CallSequence"].to_numpy(np.int8),
            "PromisedEtaTs": promised_ts,
            "AtaTs": ata_ts,
            "AtdTs": atd_ts,
            "BerthTs": berth_ts,
            "UnberthTs": unberth_ts,
            "ArrivalDelayHours": arrival_delay_hours.astype(np.float32),
            "DepartureDelayHours": (
                arrival_delay_hours + berth_occupancy_hours - berth_occupancy_hours.mean()
            ).astype(np.float32),
            "WaitingForBerthHours": wait_hours.astype(np.float32),
            "BerthOccupancyHours": berth_occupancy_hours.astype(np.float32),
            "TurnaroundHours": turnaround_hours.astype(np.float32),
            "TotalMoves": total_moves,
            "DischargeMoves": discharge_moves,
            "LoadMoves": load_moves,
            "RestowMoves": restow,
            "CranesDeployed": cranes,
            "CraneHoursGross": crane_hours_gross.astype(np.float32),
            "CraneHoursNet": crane_hours_net.astype(np.float32),
            "MovesPerCraneHourGross": mpch_gross.astype(np.float32),
            "MovesPerCraneHourNet": mpch_net.astype(np.float32),
            "MovesPerHourBerth": moves_per_hour_berth.astype(np.float32),
            "TeuDischarged": teu_discharged.astype(np.float32),
            "TeuLoaded": teu_loaded.astype(np.float32),
            "SlotCapacityTeu": slot_capacity,
            "SlotsUsedTeu": slots_used.astype(np.float32),
            "BunkerConsumedTonnes": rng.uniform(*BUNKER_TONNES_PER_CALL, size=n).astype(np.float32),
            "PortCostUsd": (
                total_moves * rng.uniform(*PORT_COST_PER_MOVE_USD, size=n)
            ).astype(np.float32),
            "IsOnTimeArrival": is_on_time,
            "IsOmitted": is_omitted,
            "IsExtraCall": (rng.random(n) < EXTRA_CALL_RATE).astype(np.int8),
            "CallStatus": status,
        }
    )
    return out.sort_values("AtaDateKey", kind="stable").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 2.4  FactContainerMove
# --------------------------------------------------------------------------- #


def _solve_journey_split(n_rows: int) -> tuple[int, int]:
    """Split the row budget between full journeys and repositioning moves.

    Let J be instrumented container journeys of ``len(JOURNEY_EVENTS)`` events
    each, of which ``n_empty_in_journey`` are empty, and R standalone empty
    repositioning moves. Then:

        events:  E*J + R      = n_rows
        empties: e*J + R      = TARGET_EMPTY_SHARE * n_rows

    Subtracting gives J directly, which is how the 32% empty share of §3.4 is
    hit exactly rather than approximately.
    """
    events_per_journey = len(JOURNEY_EVENTS)
    empties_per_journey = sum(1 for _c, _o, laden in JOURNEY_EVENTS if laden == 0)
    j = int(
        round(
            (1.0 - TARGET_EMPTY_SHARE)
            * n_rows
            / (events_per_journey - empties_per_journey)
        )
    )
    r = int(n_rows - events_per_journey * j)
    if r < 0:
        j = n_rows // events_per_journey
        r = n_rows - events_per_journey * j
    return j, r


def build_fact_container_move(
    dims: dict[str, pd.DataFrame],
    shipments: pd.DataFrame,
    n_rows: int,
) -> pd.DataFrame:
    """One row per equipment event — §2.4. Transaction grain, the largest fact.

    Two kinds of row live here, and telling them apart is the whole reason
    ``IsRepositioning`` exists:

      * events on an instrumented container journey, tied to a shipment;
      * standalone empty repositioning moves with ``ShipmentKey = -1``, which
        carry cost and no revenue and are what makes trade imbalance expensive.
    """
    rng = child_rng("FactContainerMove")
    locations = dims["DimLocation"]
    equipment = dims["DimEquipment"].set_index("EquipmentKey")
    milestones = dims["DimMilestone"]
    congested_keys = _congested_port_keys(locations)

    key_by_code = (
        milestones[milestones["MilestoneKey"] > 0]
        .drop_duplicates(subset="EventCode", keep="first")
        .set_index("EventCode")["MilestoneKey"]
    )

    n_journeys, n_repo = _solve_journey_split(n_rows)

    # ---------------- instrumented journeys ----------------
    ocean = shipments[~shipments["_is_air"].to_numpy(dtype=bool)]
    # Expand shipments into containers, then take the first n_journeys of them.
    counts = ocean["ContainerCount"].to_numpy(dtype=np.int64)
    counts = np.maximum(counts, 1)
    ship_idx = np.repeat(np.arange(len(ocean)), counts)
    if len(ship_idx) > n_journeys:
        ship_idx = rng.choice(ship_idx, size=n_journeys, replace=False)
        ship_idx.sort()
    else:
        extra = rng.choice(ship_idx, size=n_journeys - len(ship_idx), replace=True)
        ship_idx = np.sort(np.concatenate([ship_idx, extra]))
    j = len(ship_idx)

    src = ocean.iloc[ship_idx]
    gate_in_anchor = pd.DatetimeIndex(src["_dep"])
    arrival_anchor = pd.DatetimeIndex(src["_ata"])

    # Container numbers with valid ISO 6346 check digits.
    prefixes = np.array(CONTAINER_OWNER_PREFIXES)
    pfx = rng.choice(prefixes, size=j, replace=True)
    serial = rng.integers(100000, 999999, size=j)
    container_no = np.array(
        [make_container_no(p, f"{s:06d}") for p, s in zip(pfx, serial)]
    )

    n_events = len(JOURNEY_EVENTS)
    rep = np.repeat(np.arange(j), n_events)
    event_codes = np.tile([c for c, _o, _l in JOURNEY_EVENTS], j)
    offsets = np.tile([o for _c, o, _l in JOURNEY_EVENTS], j)
    laden_flags = np.tile([l for _c, _o, l in JOURNEY_EVENTS], j).astype(np.int8)
    move_seq = np.tile(np.arange(1, n_events + 1), j).astype(np.int8)

    arrival_anchored = np.isin(
        event_codes, np.array(sorted(ARRIVAL_ANCHORED_EVENTS))
    )
    base = np.where(
        arrival_anchored,
        arrival_anchor.to_numpy()[rep],
        gate_in_anchor.to_numpy()[rep],
    )

    # Demurrage and detention are defined by real intervals, not by an
    # independent dwell draw:
    #
    #   demurrage = time the laden box sits inside the terminal   (DISC -> GTOT)
    #   detention = time the customer holds the box outside it    (GTOT -> DROP)
    #
    # Drawing those two intervals per container, right-skewed, and then placing
    # the events at them means the charge and the timestamps can never disagree.
    # It is also what lets congestion at the discharge port push demurrage up,
    # which is the contradiction the Week 5 exercise turns on.
    pod_keys = src["LocationKeyPod"].to_numpy(np.int32)
    pod_congested = _congested(arrival_anchor, pod_keys, congested_keys)

    storage_days = rng.gamma(PORT_STORAGE_GAMMA_SHAPE, PORT_STORAGE_GAMMA_SCALE, size=j)
    storage_days *= np.where(pod_congested, CONGESTION_STORAGE_MULTIPLIER, 1.0)
    handover_days = rng.gamma(
        DETENTION_GAMMA_SHAPE, DETENTION_GAMMA_SCALE, size=j
    )
    # Congestion lengthens the customer's hold as well as the port's. When a
    # terminal is gridlocked, empty-return appointments become unobtainable, so
    # the box sits on the customer's yard through no fault of theirs. That is the
    # real reason detention disputes spike during congestion, and it gives the
    # Week 4 exercise a defensible waiver argument to find.
    handover_days *= np.where(pod_congested, CONGESTION_STORAGE_MULTIPLIER, 1.0)

    per_container_offset = {
        "DISC": np.zeros(j),
        "GTOT": storage_days,
        "DROP": storage_days + handover_days,
    }
    offsets = offsets.astype(np.float64)
    for pos, (code_i, _off, _laden) in enumerate(JOURNEY_EVENTS):
        if code_i in per_container_offset:
            offsets[pos::n_events] = per_container_offset[code_i]

    jitter = rng.uniform(-0.4, 0.4, size=len(rep))
    event_ts = pd.DatetimeIndex(base) + pd.to_timedelta(offsets + jitter, unit="D")

    # Carry the two intervals onto the rows that are charged for them.
    interval_days = np.zeros(len(rep), dtype=np.float64)
    for pos, (code_i, _off, _laden) in enumerate(JOURNEY_EVENTS):
        if code_i == "GTOT":
            interval_days[pos::n_events] = storage_days
        elif code_i == "DROP":
            interval_days[pos::n_events] = handover_days

    # Origin-side events happen at the load port, arrival-side at the discharge
    # port. Getting this wrong would make port dwell meaningless.
    loc_pol = src["LocationKeyPol"].to_numpy(np.int32)[rep]
    loc_pod = src["LocationKeyPod"].to_numpy(np.int32)[rep]
    location_key = np.where(arrival_anchored, loc_pod, loc_pol).astype(np.int32)

    jrn = pd.DataFrame(
        {
            "ContainerNo": container_no[rep],
            "ShipmentKey": src["ShipmentKey"].to_numpy(np.int64)[rep],
            "EventTs": event_ts,
            "_code": event_codes,
            "LocationKey": location_key,
            "EquipmentKey": src["EquipmentKey"].to_numpy(np.int32)[rep],
            "CarrierKey": src["CarrierKey"].to_numpy(np.int32)[rep],
            "VoyageKey": src["VoyageKey"].to_numpy(np.int32)[rep],
            "CustomerKey": src["CustomerKey"].to_numpy(np.int32)[rep],
            "ModeKey": src["ModeKey"].to_numpy(np.int32)[rep],
            "MoveSequence": move_seq,
            "IsLaden": laden_flags,
            "IsRepositioning": np.zeros(len(rep), dtype=np.int8),
            "_teu_factor": equipment["TeuFactor"]
            .reindex(src["EquipmentKey"].to_numpy())
            .to_numpy(np.float64)[rep],
            "_ffe_factor": equipment["FfeFactor"]
            .reindex(src["EquipmentKey"].to_numpy())
            .to_numpy(np.float64)[rep],
            "_gross_kg": src["GrossWeightKg"].to_numpy(np.float64)[rep]
            / np.maximum(counts[ship_idx][rep], 1),
            "_interval_days": interval_days,
        }
    )

    # ---------------- standalone empty repositioning ----------------
    depots = locations[
        (locations["LocationKey"] > 0)
        & (locations["LocationType"].isin(["Seaport", "Inland Depot"]))
    ]["LocationKey"].to_numpy(np.int32)
    eq_keys = equipment.index.to_numpy(np.int32)
    eq_keys = eq_keys[eq_keys > 0]

    repo_days = rng.integers(
        0,
        (pd.Timestamp(CALENDAR_END) - pd.Timestamp("2023-01-01")).days,
        size=n_repo,
    )
    repo_ts = pd.Timestamp("2023-01-01") + pd.to_timedelta(repo_days, unit="D")
    repo_eq = rng.choice(eq_keys, size=n_repo, replace=True)
    repo_pfx = rng.choice(prefixes, size=n_repo, replace=True)
    repo_serial = rng.integers(100000, 999999, size=n_repo)

    repo = pd.DataFrame(
        {
            "ContainerNo": [
                make_container_no(p, f"{s:06d}") for p, s in zip(repo_pfx, repo_serial)
            ],
            "ShipmentKey": np.full(n_repo, -1, dtype=np.int64),
            "EventTs": repo_ts,
            "_code": np.where(rng.random(n_repo) < 0.5, "GTOT", "GTIN"),
            "LocationKey": rng.choice(depots, size=n_repo, replace=True),
            "EquipmentKey": repo_eq,
            "CarrierKey": rng.choice(
                dims["DimCarrier"][dims["DimCarrier"]["CarrierKey"] > 0][
                    "CarrierKey"
                ].to_numpy(np.int32),
                size=n_repo,
                replace=True,
            ),
            "VoyageKey": np.full(n_repo, -1, dtype=np.int32),
            "CustomerKey": np.full(n_repo, -1, dtype=np.int32),
            "ModeKey": np.full(n_repo, -1, dtype=np.int32),
            "MoveSequence": np.ones(n_repo, dtype=np.int8),
            "IsLaden": np.zeros(n_repo, dtype=np.int8),
            "IsRepositioning": np.ones(n_repo, dtype=np.int8),
            "_teu_factor": equipment["TeuFactor"].reindex(repo_eq).to_numpy(np.float64),
            "_ffe_factor": equipment["FfeFactor"].reindex(repo_eq).to_numpy(np.float64),
            "_gross_kg": np.zeros(n_repo, dtype=np.float64),
            "_interval_days": np.zeros(n_repo, dtype=np.float64),
        }
    )

    all_moves = pd.concat([jrn, repo], ignore_index=True)
    all_moves = all_moves.sort_values(
        ["ContainerNo", "EventTs"], kind="stable"
    ).reset_index(drop=True)
    n = len(all_moves)

    # ---------------- derived measures ----------------
    event_ts = pd.DatetimeIndex(all_moves["EventTs"])
    loc = all_moves["LocationKey"].to_numpy(np.int32)
    cong = _congested(event_ts, loc, congested_keys)

    dwell = rng.gamma(DWELL_GAMMA_SHAPE, DWELL_GAMMA_SCALE, size=n) * np.where(
        cong, CONGESTION_DWELL_MULTIPLIER, 1.0
    )
    # The first event of a container journey has no prior event to dwell from.
    dwell = np.where(all_moves["MoveSequence"].to_numpy() == 1, -1.0, dwell)

    eq_key_arr = all_moves["EquipmentKey"].to_numpy(np.int32)
    free_dem = equipment["FreeDaysDemurrage"].reindex(eq_key_arr).fillna(5).to_numpy(float)
    free_det = equipment["FreeDaysDetention"].reindex(eq_key_arr).fillna(5).to_numpy(float)

    # Free time runs against the real interval, so charge and timestamps agree.
    code = all_moves["_code"].to_numpy()
    interval = all_moves["_interval_days"].to_numpy(np.float64)
    is_dem_event = code == "GTOT"
    is_det_event = code == "DROP"
    demurrage_days = np.where(
        is_dem_event, np.maximum(interval - free_dem, 0.0), 0.0
    )
    detention_days = np.where(
        is_det_event, np.maximum(interval - free_det, 0.0), 0.0
    )
    free_used = np.where(
        is_dem_event, np.minimum(interval, free_dem),
        np.where(is_det_event, np.minimum(interval, free_det), 0.0),
    )
    past_free = ((demurrage_days > 0) | (detention_days > 0)).astype(np.int8)

    # Dwell on the two charged events is the interval itself, not an independent
    # draw — otherwise DwellHours and DemurrageDays would tell different stories
    # about the same container.
    dwell = np.where(is_dem_event | is_det_event, interval * 24.0, dwell)

    teu = all_moves["_teu_factor"].to_numpy(np.float64)
    ffe = all_moves["_ffe_factor"].to_numpy(np.float64)

    # ---- event classification (see RAIL_OUT_SHARE above)
    is_rail = ((code == "GTOT") & (rng.random(n) < RAIL_OUT_SHARE)).astype(np.int8)
    is_inspection = ((code == "GTIN") & (rng.random(n) < INSPECTION_SHARE)).astype(np.int8)

    tranship_ships = set(
        shipments.loc[shipments["IsTranshipped"] == 1, "ShipmentKey"].tolist()
    )
    on_tranship = all_moves["ShipmentKey"].isin(tranship_ships).to_numpy()
    is_tranship_move = (on_tranship & np.isin(code, ["DISC", "LOAD"])).astype(np.int8)

    milestone_key = key_by_code.reindex(code).fillna(-1).to_numpy(np.int32)
    rail_key = int(key_by_code.get("RAIO", -1))
    if rail_key > 0:
        milestone_key = np.where(is_rail == 1, rail_key, milestone_key).astype(np.int32)
    insp_key = int(key_by_code.get("INSP", -1))
    if insp_key > 0:
        milestone_key = np.where(
            is_inspection == 1, insp_key, milestone_key
        ).astype(np.int32)

    out = pd.DataFrame(
        {
            "ContainerMoveKey": np.arange(1, n + 1, dtype=np.int64),
            "ContainerNo": all_moves["ContainerNo"].to_numpy(),
            "ShipmentKey": all_moves["ShipmentKey"].to_numpy(np.int64),
            "EventDateKey": to_date_key(event_ts),
            "EventTs": event_ts,
            "TimeKey": (event_ts.hour * 100 + event_ts.minute).astype(np.int32),
            "MilestoneKey": milestone_key,
            "LocationKey": loc,
            "EquipmentKey": eq_key_arr,
            "CarrierKey": all_moves["CarrierKey"].to_numpy(np.int32),
            "VoyageKey": all_moves["VoyageKey"].to_numpy(np.int32),
            "CustomerKey": all_moves["CustomerKey"].to_numpy(np.int32),
            "ModeKey": all_moves["ModeKey"].to_numpy(np.int32),
            "MoveSequence": all_moves["MoveSequence"].to_numpy(np.int8),
            "Teu": teu.astype(np.float32),
            "Ffe": ffe.astype(np.float32),
            "GrossWeightKg": all_moves["_gross_kg"].to_numpy(np.float32),
            "DwellHours": dwell.astype(np.float32),
            "MoveCostUsd": rng.uniform(*MOVE_COST_USD, size=n).astype(np.float32),
            "CraneMoves": np.where(np.isin(code, ["LOAD", "DISC"]), 1, 0).astype(np.int8),
            "IsLaden": all_moves["IsLaden"].to_numpy(np.int8),
            "IsEmpty": (1 - all_moves["IsLaden"].to_numpy(np.int8)).astype(np.int8),
            "IsRepositioning": all_moves["IsRepositioning"].to_numpy(np.int8),
            "IsTranshipmentMove": is_tranship_move,
            "IsGateEvent": np.isin(code, ["GTIN", "GTOT"]).astype(np.int8),
            "IsVesselEvent": np.isin(code, ["LOAD", "DISC"]).astype(np.int8),
            "IsRailEvent": is_rail,
            "IsInspection": is_inspection,
            "FreeTimeDaysUsed": free_used.astype(np.float32),
            "IsPastFreeTime": past_free,
            "DemurrageDays": demurrage_days.astype(np.float32),
            "DetentionDays": detention_days.astype(np.float32),
        }
    )
    return out.sort_values("EventDateKey", kind="stable").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 2.6  FactFreightCharge
# --------------------------------------------------------------------------- #

# Lines per invoice.
#
# Minimum two revenue lines, and it is not an arbitrary floor: no ocean invoice
# is base-freight-only, because BAF or THC always applies. It is also what keeps
# the revenue mix honest. Renormalising the allocation shares across whatever
# codes a shipment happens to draw inflates OFR badly — a shipment that draws
# only OFR assigns it 100% of revenue, and the aggregate base-freight share
# lands near 84% against an intended 64%. Fixing OFR at its intended weight and
# letting the *other* picked codes share the remainder removes that bias, and
# needs at least one other code to be present.
#
# Minimum one cost line for the same class of reason: every shipment costs
# somebody something, and letting a shipment carry no cost line left total cost
# under-reconciled by 22%.
# Solved, not guessed. Observed lines/shipment = E[rev] + E[cost] + extras,
# where extras (forced D&D lines plus credit notes) measured 0.130. Target is
# 1,180,000 / 360,000 = 3.2778, so the two draws must sum to 3.1478:
#   E[rev]  = 2*0.930 + 3*0.070 = 2.070
#   E[cost] = 1*0.923 + 2*0.077 = 1.077
REVENUE_LINES_PER_SHIPMENT = ((2, 3), (0.930, 0.070))
COST_LINES_PER_SHIPMENT = ((1, 2), (0.923, 0.077))
OFR_FIXED_REVENUE_WEIGHT = 0.640


def build_fact_freight_charge(
    dims: dict[str, pd.DataFrame],
    shipments: pd.DataFrame,
    container_moves: pd.DataFrame,
    fx: pd.DataFrame,
    n_rows: int,
) -> pd.DataFrame:
    """One row per charge line — §2.6. Transaction grain.

    Revenue lines are an *allocation* of ``FactShipment.Revenue_usd``, not an
    addition to it: the shares of whichever charge codes a shipment draws are
    renormalised to sum to one, so contract gate 13 (charge revenue reconciles
    to shipment revenue within 0.5%) holds by construction rather than by luck.
    Credit notes are the only deliberate divergence, because a credit note is a
    separate document in the real world and belongs on its own negative line.

    Demurrage and detention lines are raised only for shipments whose containers
    actually ran past free time in ``FactContainerMove``, so the charge and the
    equipment event agree. A D&D figure that does not tie back to a container
    event is the single most common piece of nonsense in freight reporting.
    """
    rng = child_rng("FactFreightCharge")
    charge_types = dims["DimChargeType"]
    ct = charge_types[charge_types["ChargeTypeKey"] > 0]
    key_by_code = ct.drop_duplicates("ChargeCode").set_index("ChargeCode")["ChargeTypeKey"]

    # Which shipments genuinely incurred demurrage / detention.
    dd = container_moves[
        (container_moves["DemurrageDays"] > 0) | (container_moves["DetentionDays"] > 0)
    ]
    dem_ships = set(
        container_moves.loc[container_moves["DemurrageDays"] > 0, "ShipmentKey"].tolist()
    )
    det_ships = set(
        container_moves.loc[container_moves["DetentionDays"] > 0, "ShipmentKey"].tolist()
    )

    ship_keys = shipments["ShipmentKey"].to_numpy(np.int64)
    n_ship = len(ship_keys)
    has_dem = np.isin(ship_keys, np.fromiter(dem_ships, dtype=np.int64, count=len(dem_ships)))
    has_det = np.isin(ship_keys, np.fromiter(det_ships, dtype=np.int64, count=len(det_ships)))

    rev_codes = [c for c in REVENUE_ALLOCATION if c in key_by_code.index]
    cost_codes = [c for c in COST_ALLOCATION if c in key_by_code.index]
    if not rev_codes:
        raise ValueError("No revenue charge codes from REVENUE_ALLOCATION exist in DimChargeType")

    rev_share = np.array([REVENUE_ALLOCATION[c] for c in rev_codes])
    cost_share = np.array([COST_ALLOCATION[c] for c in cost_codes])

    n_rev = rng.choice(
        REVENUE_LINES_PER_SHIPMENT[0], size=n_ship, p=REVENUE_LINES_PER_SHIPMENT[1]
    )
    n_cost = rng.choice(
        COST_LINES_PER_SHIPMENT[0], size=n_ship, p=COST_LINES_PER_SHIPMENT[1]
    )

    # ---- build the (shipment, code) pairs
    rows_ship: list[int] = []
    rows_code: list[str] = []
    rows_is_rev: list[int] = []

    # OFR always present on the revenue side: every shipment has base freight.
    #
    # DEM and DET are excluded from the random pool. They are added ONLY by the
    # forced path below, for shipments whose containers actually ran past free
    # time in FactContainerMove. Leaving them in the random draw meant 60% of
    # demurrage lines and 35% of detention lines belonged to shipments with no
    # exposure at all — a D&D figure that does not tie back to an equipment
    # event, which is the single most common piece of nonsense in freight
    # reporting and precisely what this model is supposed to avoid.
    DD_CODES = ("DEM", "DET")
    rev_others = [c for c in rev_codes if c != "OFR" and c not in DD_CODES]
    other_share = np.array([REVENUE_ALLOCATION[c] for c in rev_others])
    other_p = other_share / other_share.sum()

    for i in range(n_ship):  # per-invoice code selection; vectorising this would
        k = int(n_rev[i])    # require ragged fancy indexing for little gain
        picks = ["OFR"]
        if k > 1:
            extra = rng.choice(rev_others, size=k - 1, replace=False, p=other_p)
            picks.extend(extra.tolist())
        # Force D&D lines where the equipment events say they are owed.
        if has_dem[i] and "DEM" not in picks:
            picks.append("DEM")
        if has_det[i] and "DET" not in picks:
            picks.append("DET")
        for c in picks:
            rows_ship.append(i)
            rows_code.append(c)
            rows_is_rev.append(1)

        kc = int(n_cost[i])
        if kc and cost_codes:
            cp = cost_share / cost_share.sum()
            cpicks = rng.choice(
                cost_codes, size=min(kc, len(cost_codes)), replace=False, p=cp
            )
            for c in cpicks.tolist():
                rows_ship.append(i)
                rows_code.append(c)
                rows_is_rev.append(0)

    ship_pos = np.array(rows_ship, dtype=np.int64)
    code_arr = np.array(rows_code)
    is_rev = np.array(rows_is_rev, dtype=np.int8)

    # ---- allocate money so each side sums to the shipment total
    share_lookup = {**REVENUE_ALLOCATION, **{f"C_{k}": v for k, v in COST_ALLOCATION.items()}}
    raw_share = np.where(
        is_rev == 1,
        np.array([REVENUE_ALLOCATION.get(c, 0.01) for c in code_arr]),
        np.array([COST_ALLOCATION.get(c, 0.01) for c in code_arr]),
    )

    # OFR takes a fixed weight; the other revenue codes on the same invoice share
    # what is left. Cost codes renormalise normally.
    is_ofr = (code_arr == "OFR") & (is_rev == 1)
    other_rev = (code_arr != "OFR") & (is_rev == 1)

    frame = pd.DataFrame(
        {
            "pos": ship_pos,
            "grp": np.where(is_ofr, 0, np.where(other_rev, 1, 2)),
            "share": raw_share,
        }
    )
    denom = frame.groupby(["pos", "grp"])["share"].transform("sum").to_numpy()
    normalised = raw_share / np.where(denom > 0, denom, 1.0)

    weight = np.where(
        is_ofr,
        OFR_FIXED_REVENUE_WEIGHT,
        np.where(other_rev, normalised * (1.0 - OFR_FIXED_REVENUE_WEIGHT), normalised),
    )

    revenue_total = shipments["Revenue_usd"].to_numpy(np.float64)[ship_pos]
    cost_total = shipments["DirectCost_usd"].to_numpy(np.float64)[ship_pos]
    amount_usd = np.where(is_rev == 1, revenue_total * weight, cost_total * weight)

    # ---- context columns
    currency_key = shipments["CurrencyKey"].to_numpy(np.int32)[ship_pos]
    charge_ts = pd.DatetimeIndex(shipments["_dep"])[ship_pos]
    charge_date_key = to_date_key(charge_ts)
    invoice_ts = charge_ts + pd.to_timedelta(rng.integers(1, 22, size=len(ship_pos)), unit="D")

    fx_map = fx.set_index(["RateDateKey", "CurrencyKey"])["RateToUsd"]
    rates = fx_map.reindex(
        pd.MultiIndex.from_arrays([charge_date_key, currency_key])
    ).to_numpy(np.float64)
    rates = np.where(np.isnan(rates) | (rates <= 0), 1.0, rates)

    quantity = np.where(
        np.isin(code_arr, ["DEM", "DET"]),
        rng.uniform(1.0, 9.0, size=len(ship_pos)),
        np.maximum(shipments["ContainerCount"].to_numpy(np.float64)[ship_pos], 1.0),
    )
    n = len(ship_pos)

    is_credit = (rng.random(n) < 0.0).astype(np.int8)  # real credits appended below
    tier = np.where(
        np.isin(code_arr, ["DEM", "DET"]), rng.integers(1, 4, size=n), 0
    ).astype(np.int8)

    out = pd.DataFrame(
        {
            "ShipmentKey": shipments["ShipmentKey"].to_numpy(np.int64)[ship_pos],
            "ChargeDateKey": charge_date_key,
            "InvoiceDateKey": to_date_key(invoice_ts),
            "ChargeTypeKey": key_by_code.reindex(code_arr).fillna(-1).to_numpy(np.int32),
            "CustomerKey": shipments["CustomerKey"].to_numpy(np.int32)[ship_pos],
            "CarrierKey": shipments["CarrierKey"].to_numpy(np.int32)[ship_pos],
            "LocationKey": shipments["LocationKeyPod"].to_numpy(np.int32)[ship_pos],
            "ModeKey": shipments["ModeKey"].to_numpy(np.int32)[ship_pos],
            "EquipmentKey": shipments["EquipmentKey"].to_numpy(np.int32)[ship_pos],
            "CurrencyKey": currency_key,
            "Quantity": quantity.astype(np.float32),
            "Amount_usd": amount_usd.astype(np.float32),
            "FxRateUsed": rates.astype(np.float32),
            "IsRevenue": is_rev,
            "IsCost": (1 - is_rev).astype(np.int8),
            "IsCreditNote": is_credit,
            "TierApplied": tier,
            "_code": code_arr,
        }
    )

    # ---- credit notes as their own negative lines (§3.5 landmine #5)
    eligible = out.index.to_numpy()[out["IsRevenue"].to_numpy() == 1]
    n_credit = int(round(CREDIT_NOTE_RATE * len(out)))
    pick = rng.choice(eligible, size=min(n_credit, len(eligible)), replace=False)
    credits = out.loc[pick].copy()
    credits["Amount_usd"] = (
        -credits["Amount_usd"].to_numpy() * rng.uniform(0.05, 0.40, size=len(credits))
    ).astype(np.float32)
    credits["IsCreditNote"] = np.int8(1)
    credits["Quantity"] = -credits["Quantity"].to_numpy()

    out = pd.concat([out, credits], ignore_index=True)
    out = out.sort_values("ChargeDateKey", kind="stable").reset_index(drop=True)
    n = len(out)

    code_arr = out["_code"].to_numpy()
    amount_usd = out["Amount_usd"].to_numpy(np.float64)
    is_rev = out["IsRevenue"].to_numpy(np.int8)
    rates = out["FxRateUsed"].to_numpy(np.float64)

    settle_roll = rng.random(n)
    settlement = np.where(
        out["IsCreditNote"].to_numpy() == 1, "Credited",
        np.where(settle_roll < DISPUTED_RATE, "Disputed",
        np.where(settle_roll < DISPUTED_RATE + WAIVED_RATE, "Written Off",
        np.where(settle_roll < 0.72, "Paid", "Invoiced"))),
    )

    out["ChargeLineKey"] = np.arange(1, n + 1, dtype=np.int64)
    out["InvoiceNo"] = "INV" + pd.Series(out["ShipmentKey"].to_numpy()).astype(str).str.zfill(9)
    out["ChargeLineNo"] = (out.groupby("ShipmentKey").cumcount() + 1).astype(np.int16)
    out["ContainerNo"] = "#NA"
    out["UnitRate_doc"] = (
        amount_usd / rates / np.maximum(np.abs(out["Quantity"].to_numpy(np.float64)), 1e-6)
    ).astype(np.float32)
    out["Amount_doc"] = (amount_usd / rates).astype(np.float32)
    out["RevenueAmount_usd"] = np.where(is_rev == 1, amount_usd, 0.0).astype(np.float32)
    out["CostAmount_usd"] = np.where(is_rev == 0, amount_usd, 0.0).astype(np.float32)
    out["TaxAmount_usd"] = (
        amount_usd * rng.uniform(*TAX_RATE_RANGE, size=n)
    ).astype(np.float32)
    out["ChargeableDays"] = np.where(
        np.isin(code_arr, ["DEM", "DET"]), np.abs(out["Quantity"].to_numpy()), 0.0
    ).astype(np.float32)
    out["IsDisputed"] = (settlement == "Disputed").astype(np.int8)
    out["IsWaived"] = (settlement == "Written Off").astype(np.int8)
    out["IsDemurrage"] = (code_arr == "DEM").astype(np.int8)
    out["IsDetention"] = (code_arr == "DET").astype(np.int8)
    out["IsSurcharge"] = np.isin(
        code_arr, ["BAF", "LSS", "CGS", "PSS", "CAF", "EBS", "WRS"]
    ).astype(np.int8)
    out["SettlementStatus"] = settlement

    ordered = [
        "ChargeLineKey", "ShipmentKey", "InvoiceNo", "ChargeLineNo", "ChargeDateKey",
        "InvoiceDateKey", "ChargeTypeKey", "CustomerKey", "CarrierKey", "LocationKey",
        "ModeKey", "EquipmentKey", "CurrencyKey", "ContainerNo", "Quantity",
        "UnitRate_doc", "Amount_doc", "Amount_usd", "FxRateUsed", "RevenueAmount_usd",
        "CostAmount_usd", "TaxAmount_usd", "ChargeableDays", "TierApplied",
        "IsRevenue", "IsCost", "IsCreditNote", "IsDisputed", "IsWaived",
        "IsDemurrage", "IsDetention", "IsSurcharge", "SettlementStatus",
    ]
    return out[ordered]
