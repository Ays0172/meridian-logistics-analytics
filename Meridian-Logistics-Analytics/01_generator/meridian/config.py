"""meridian.config -- global constants and per-run configuration.

Implements SCHEMA_CONTRACT.md SS0 (Conventions) and the "Scale dial" table:
the master seed, the transactional/DimDate calendar bounds, the fiscal-year
start month, the unknown-member sentinel values, filesystem paths, and the
loader for config/scale.yaml.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# --------------------------------------------------------------------------- #
# SS0 Conventions
# --------------------------------------------------------------------------- #

SEED: int = 20260824

# Calendar: 2023-01-01 -> 2026-08-31 inclusive for all transactional facts.
FACT_START_DATE: _dt.date = _dt.date(2021, 8, 21)
FACT_END_DATE: _dt.date = _dt.date(2026, 8, 20)

# DimDate extends to 2026-12-31.
DIMDATE_START_DATE: _dt.date = _dt.date(2021, 1, 1)
DIMDATE_END_DATE: _dt.date = _dt.date(2026, 12, 31)

# "Current" anchor used for YearOffset / MonthOffset / WeekOffset / DayOffset
# and IsCurrentYear / IsCurrentMonth (SS1.1).
CURRENT_ANCHOR_DATE: _dt.date = _dt.date(2026, 8, 20)

# Fiscal year starts 1 October (SS1.1).
FISCAL_YEAR_START_MONTH: int = 10

# Unknown-member sentinel (SS0 "Unknown member").
UNKNOWN_KEY: int = -1
UNKNOWN_CODE: str = "#NA"
UNKNOWN_NAME: str = "Unknown"

# Lunar New Year windows (SS3.1): the week containing each date, falls to
# 0.55x for 2 weeks then rebounds to 1.18x for 2 weeks. DimDate flags the
# combined 4-week window per date via IsLunarNewYearWindow.
LUNAR_NEW_YEAR_DATES: tuple[_dt.date, ...] = (
    _dt.date(2021, 2, 12),
    _dt.date(2022, 2, 1),
    _dt.date(2023, 1, 22),
    _dt.date(2024, 2, 10),
    _dt.date(2025, 1, 29),
    _dt.date(2026, 2, 17),
)

# Peak season (SS3.1): Aug-Oct.
PEAK_SEASON_MONTHS: tuple[int, ...] = (8, 9, 10)

# The congestion event (SS3.3).
CONGESTION_START_DATE: _dt.date = _dt.date(2025, 7, 14)
CONGESTION_END_DATE: _dt.date = _dt.date(2025, 9, 14)
CONGESTION_LOCATIONS: tuple[str, ...] = ("NLRTM", "USLAX")

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

GENERATOR_ROOT: Path = Path(__file__).resolve().parent.parent  # .../01_generator
PROJECT_ROOT: Path = GENERATOR_ROOT.parent                     # .../work
CONFIG_DIR: Path = GENERATOR_ROOT / "config"
DATA_ROOT: Path = PROJECT_ROOT / "02_data"
RAW_DIR: Path = DATA_ROOT / "raw"
REFERENCE_DIR: Path = DATA_ROOT / "reference"
VALIDATION_DIR: Path = DATA_ROOT / "_validation"
DOCS_DIR: Path = PROJECT_ROOT / "00_docs"

SCALE_YAML_PATH: Path = CONFIG_DIR / "scale.yaml"


@dataclass(frozen=True)
class Config:
    """Resolved configuration for one generator run.

    Carries the chosen `scale` name plus everything derived from it (fact row
    counts) and everything that never varies with scale (dimension row
    counts, seed, calendar bounds, paths).
    """

    scale: str
    fact_row_counts: dict[str, int]
    dimension_row_counts: dict[str, int]
    seed: int = SEED
    fact_start_date: _dt.date = FACT_START_DATE
    fact_end_date: _dt.date = FACT_END_DATE
    dimdate_start_date: _dt.date = DIMDATE_START_DATE
    dimdate_end_date: _dt.date = DIMDATE_END_DATE
    current_anchor_date: _dt.date = CURRENT_ANCHOR_DATE
    fiscal_year_start_month: int = FISCAL_YEAR_START_MONTH
    raw_dir: Path = RAW_DIR
    reference_dir: Path = REFERENCE_DIR
    validation_dir: Path = VALIDATION_DIR

    def dim_rows(self, dim_name: str) -> int:
        """Return the frozen row count for a dimension, e.g. 'DimCustomer'."""
        try:
            return self.dimension_row_counts[dim_name]
        except KeyError as exc:
            raise KeyError(f"No row count configured for dimension '{dim_name}'") from exc

    def fact_rows(self, fact_name: str) -> int:
        """Return this run's scaled row count for a fact table."""
        try:
            return self.fact_row_counts[fact_name]
        except KeyError as exc:
            raise KeyError(f"No row count configured for fact '{fact_name}'") from exc


def load_scale_yaml(path: Path = SCALE_YAML_PATH) -> dict[str, Any]:
    """Read config/scale.yaml and return its parsed contents."""
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_config(scale: str = "prod") -> Config:
    """Build a `Config` for the named scale ('dev' | 'prod' | 'stress')."""
    doc = load_scale_yaml()
    scales = doc.get("scales", {})
    if scale not in scales:
        raise ValueError(f"Unknown scale '{scale}'; expected one of {sorted(scales)}")
    return Config(
        scale=scale,
        fact_row_counts=dict(scales[scale]["facts"]),
        dimension_row_counts=dict(doc["dimensions"]),
    )
