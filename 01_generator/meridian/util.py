"""meridian.util -- shared helpers used by every dimension (and later, fact)
builder.

Implements the seeded-RNG discipline, business-key check-digit algorithms,
and I/O conventions from SCHEMA_CONTRACT.md SS0.
"""
from __future__ import annotations

import hashlib
import string
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from . import config as _cfg

# --------------------------------------------------------------------------- #
# RNG management
# --------------------------------------------------------------------------- #
# One master seed (SS0). Each table gets its own independent, reproducible
# stream derived from a stable hash of its name, so the order in which
# tables are built never changes any table's random sequence.

_HASH_DIGEST_BYTES: int = 8  # take the first 8 bytes of the sha256 digest
_HASH_MODULUS: int = 2**31 - 1  # keep spawn_key within a comfortable int range


def stable_hash(name: str) -> int:
    """Deterministic, platform-independent integer hash of `name`.

    Uses sha256 rather than Python's built-in `hash()`, which is randomised
    per-process (PYTHONHASHSEED) and would break reproducibility.
    """
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    return int.from_bytes(digest[:_HASH_DIGEST_BYTES], byteorder="big") % _HASH_MODULUS


def master_rng() -> np.random.Generator:
    """The single master generator, seeded per SS0."""
    return np.random.default_rng(_cfg.SEED)


def child_rng(name: str) -> np.random.Generator:
    """An independent, reproducible generator for one named table/stream.

    Derived from `np.random.SeedSequence(SEED, spawn_key=(stable_hash(name),))`.
    Because the spawn key depends only on `name` (not on call order or on
    what other tables have already drawn), calling `child_rng("DimVessel")`
    can never shift the stream returned for `child_rng("DimCustomer")`.
    """
    seed_sequence = np.random.SeedSequence(_cfg.SEED, spawn_key=(stable_hash(name),))
    return np.random.default_rng(seed_sequence)


# --------------------------------------------------------------------------- #
# ISO 6346 container-number check digit
# --------------------------------------------------------------------------- #
# Letters map to values 10..38, skipping every multiple of 11 (so no letter
# ever maps to 11, 22, or 33). Each of the 10 characters (4 alpha + 6 digit)
# is weighted by 2**position (position 0 = leftmost), summed, and reduced
# mod 11; a remainder of 10 becomes check digit 0.

_ISO6346_POSITION_COUNT: int = 10
_ISO6346_MODULUS: int = 11
_ISO6346_REMAINDER_TEN_MAPS_TO: int = 0


def _build_iso6346_letter_values() -> dict[str, int]:
    values: dict[str, int] = {}
    candidate = 10
    for letter in string.ascii_uppercase:
        while candidate % _ISO6346_MODULUS == 0:
            candidate += 1
        values[letter] = candidate
        candidate += 1
    return values


_ISO6346_LETTER_VALUES: dict[str, int] = _build_iso6346_letter_values()


def _iso6346_char_value(ch: str) -> int:
    if ch.isdigit():
        return int(ch)
    upper = ch.upper()
    if upper in _ISO6346_LETTER_VALUES:
        return _ISO6346_LETTER_VALUES[upper]
    raise ValueError(f"Invalid ISO 6346 character: {ch!r}")


def iso6346_check_digit(owner_prefix: str, serial: str) -> int:
    """Compute the ISO 6346 check digit for a container number.

    `owner_prefix` is the 4-character owner code + equipment category
    identifier (e.g. "CSQU"); `serial` is the 6-digit serial number (e.g.
    "305438"). Together they form the 10 characters the check digit is
    computed over. Verified against the published worked example
    CSQU305438 -> 3.
    """
    payload = f"{owner_prefix}{serial}"
    if len(payload) != _ISO6346_POSITION_COUNT:
        raise ValueError(
            f"ISO 6346 payload must be {_ISO6346_POSITION_COUNT} characters "
            f"(4 owner + 6 serial), got {len(payload)}: {payload!r}"
        )
    total = sum(_iso6346_char_value(ch) * (2**pos) for pos, ch in enumerate(payload))
    remainder = total % _ISO6346_MODULUS
    return _ISO6346_REMAINDER_TEN_MAPS_TO if remainder == 10 else remainder


def make_container_no(prefix: str, serial: str) -> str:
    """Build the full 11-character ISO 6346 container number."""
    check_digit = iso6346_check_digit(prefix, serial)
    return f"{prefix}{serial}{check_digit}"


# --------------------------------------------------------------------------- #
# IMO number check digit
# --------------------------------------------------------------------------- #
# Multiply the six digits by 7,6,5,4,3,2 respectively; the check digit is the
# last digit of the sum. Verified against 907472->9 (IMO 9074729) and
# 931946->6 (IMO 9319466).

_IMO_WEIGHTS: tuple[int, ...] = (7, 6, 5, 4, 3, 2)
_IMO_DIGIT_COUNT: int = 6


def imo_check_digit(six_digits: str) -> int:
    """Compute the IMO number check digit from its leading six digits."""
    if len(six_digits) != _IMO_DIGIT_COUNT or not six_digits.isdigit():
        raise ValueError(f"IMO check digit needs exactly {_IMO_DIGIT_COUNT} digits, got {six_digits!r}")
    total = sum(int(d) * w for d, w in zip(six_digits, _IMO_WEIGHTS))
    return total % 10


def make_imo(six_digits: str) -> str:
    """Build the full 7-digit IMO number."""
    return f"{six_digits}{imo_check_digit(six_digits)}"


# --------------------------------------------------------------------------- #
# Date keys
# --------------------------------------------------------------------------- #

def to_date_key(series_or_dates: Any) -> Any:
    """Convert dates (Series, array, scalar, list) to int32 yyyymmdd date keys."""
    dt = pd.to_datetime(series_or_dates)
    if isinstance(dt, pd.DatetimeIndex):
        keys = dt.year.astype("int32") * 10000 + dt.month.astype("int32") * 100 + dt.day.astype("int32")
        return keys.astype("int32")
    if isinstance(dt, pd.Series):
        keys = dt.dt.year.astype("int32") * 10000 + dt.dt.month.astype("int32") * 100 + dt.dt.day.astype("int32")
        return keys.astype("int32")
    # scalar Timestamp
    return np.int32(dt.year * 10000 + dt.month * 100 + dt.day)


def from_date_key(date_key: Any) -> Any:
    """Convert int32 yyyymmdd date keys back to dates (Series, array, or scalar)."""
    if isinstance(date_key, pd.Series):
        return pd.to_datetime(date_key.astype("int64").astype(str), format="%Y%m%d")
    if isinstance(date_key, (np.ndarray, list, tuple, pd.Index)):
        arr = pd.Series(np.asarray(date_key).astype("int64").astype(str))
        return pd.to_datetime(arr, format="%Y%m%d").to_numpy()
    return pd.to_datetime(str(int(date_key)), format="%Y%m%d")


# --------------------------------------------------------------------------- #
# dtype enforcement
# --------------------------------------------------------------------------- #

def enforce_dtypes(df: pd.DataFrame, spec: Mapping[str, str]) -> pd.DataFrame:
    """Cast every column named in `spec` to its target dtype.

    Collects every failure (missing column, or a cast pandas/numpy refuses)
    and raises a single `ValueError` listing all of them, rather than
    stopping at the first problem.
    """
    errors: list[str] = []
    out = df.copy()
    for col, dtype in spec.items():
        if col not in out.columns:
            errors.append(f"column '{col}' missing from DataFrame (expected dtype {dtype})")
            continue
        try:
            out[col] = out[col].astype(dtype)
        except (ValueError, TypeError) as exc:
            errors.append(f"column '{col}': cannot cast to {dtype!r}: {exc}")
    if errors:
        raise ValueError("enforce_dtypes found " + str(len(errors)) + " problem(s):\n  " + "\n  ".join(errors))
    return out


# --------------------------------------------------------------------------- #
# Unknown member
# --------------------------------------------------------------------------- #

def add_unknown_member(
    df: pd.DataFrame,
    key_col: str,
    overrides: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Prepend the -1 / #NA / Unknown row required on every dimension (SS0).

    `key_col` gets `-1`. Every other column is filled with a type-appropriate
    sentinel: int columns whose name ends in "Key" get `-1` (FK-shaped
    columns), other ints/bools get `0`, floats get `0.0`, datetimes get
    `NaT`, and text columns get `"#NA"` (or `"Unknown"` for columns whose
    name ends in "Name"). Pass `overrides` to set specific columns to a
    contract-mandated sentinel instead (e.g. `ScdValidTo="9999-12-31"`).
    """
    overrides = dict(overrides or {})
    original_dtypes = df.dtypes.to_dict()
    unknown_row: dict[str, Any] = {}

    for col in df.columns:
        if col == key_col:
            unknown_row[col] = _cfg.UNKNOWN_KEY
            continue
        if col in overrides:
            unknown_row[col] = overrides[col]
            continue

        dtype = df[col].dtype
        if pd.api.types.is_bool_dtype(dtype):
            unknown_row[col] = False
        elif pd.api.types.is_integer_dtype(dtype):
            unknown_row[col] = _cfg.UNKNOWN_KEY if col.endswith("Key") else 0
        elif pd.api.types.is_float_dtype(dtype):
            unknown_row[col] = 0.0
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            unknown_row[col] = pd.NaT
        else:
            if col.endswith("Name"):
                unknown_row[col] = _cfg.UNKNOWN_NAME
            else:
                unknown_row[col] = _cfg.UNKNOWN_CODE

    unknown_df = pd.DataFrame([unknown_row], columns=df.columns)
    out = pd.concat([unknown_df, df], ignore_index=True)
    out = out.astype(original_dtypes)
    return out


# --------------------------------------------------------------------------- #
# Output writers
# --------------------------------------------------------------------------- #

def write_dim(df: pd.DataFrame, name: str, csv_df: pd.DataFrame | None = None) -> dict[str, Any]:
    """Write a dimension to its two canonical locations.

    - `02_data/raw/<name>/part-000.parquet` (snappy), the canonical form.
    - `02_data/reference/<name>.csv`, a CSV mirror -- normally the same data,
      but pass `csv_df` when a landmine is specific to the CSV mirror (e.g.
      DimSku's leading-zero SkuCode, landmine #10) so the parquet stays
      clean while the CSV mirror carries the deliberate quirk.

    Returns a small manifest dict (row/col counts, dtypes) for convenience.
    """
    raw_dir = _cfg.RAW_DIR / name
    raw_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = raw_dir / "part-000.parquet"
    df.to_parquet(parquet_path, engine="pyarrow", compression="snappy", index=False)

    _cfg.REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = _cfg.REFERENCE_DIR / f"{name}.csv"
    (csv_df if csv_df is not None else df).to_csv(csv_path, index=False)

    return {
        "name": name,
        "rows": int(len(df)),
        "cols": int(len(df.columns)),
        "columns": list(df.columns),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "parquet_path": str(parquet_path),
        "csv_path": str(csv_path),
    }


def sample_rows(df: pd.DataFrame, n: int = 3) -> list[dict[str, Any]]:
    """JSON-safe sample of the first `n` rows, for the dims manifest."""
    sample = df.head(n).copy()
    for col in sample.columns:
        if pd.api.types.is_datetime64_any_dtype(sample[col].dtype):
            sample[col] = sample[col].astype(str)
    return sample.astype(object).where(pd.notnull(sample), None).to_dict(orient="records")
