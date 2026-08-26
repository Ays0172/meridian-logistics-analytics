"""Unit tests for meridian.util.

Run with: python -m pytest 01_generator/tests/test_util.py -v
(or: python 01_generator/tests/test_util.py, it self-runs via unittest too)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from meridian import util  # noqa: E402


class TestRng(unittest.TestCase):
    def test_master_rng_reproducible(self) -> None:
        a = util.master_rng().random(5)
        b = util.master_rng().random(5)
        np.testing.assert_array_equal(a, b)

    def test_child_rng_independent_of_call_order(self) -> None:
        # Draw from "DimCustomer" then "DimVessel"...
        c1 = util.child_rng("DimCustomer").random(5)
        v1 = util.child_rng("DimVessel").random(5)
        # ...vs "DimVessel" then "DimCustomer" -- order must not matter.
        v2 = util.child_rng("DimVessel").random(5)
        c2 = util.child_rng("DimCustomer").random(5)
        np.testing.assert_array_equal(c1, c2)
        np.testing.assert_array_equal(v1, v2)

    def test_child_rng_differs_by_name(self) -> None:
        a = util.child_rng("TableA").random(5)
        b = util.child_rng("TableB").random(5)
        self.assertFalse(np.allclose(a, b))

    def test_stable_hash_deterministic(self) -> None:
        self.assertEqual(util.stable_hash("DimCustomer"), util.stable_hash("DimCustomer"))


class TestIso6346(unittest.TestCase):
    """Verified against the published worked example and two hand-derived cases.

    Hand derivation for CSQU305438 -> 3:
      C=13 S=30 Q=28 U=32 | 3 0 5 4 3 8
      weighted by 2**pos (pos 0..9):
        13*1 + 30*2 + 28*4 + 32*8 + 3*16 + 0*32 + 5*64 + 4*128 + 3*256 + 8*512
        = 13+60+112+256+48+0+320+512+768+4096 = 6185
      6185 mod 11 = 3 (11*562=6182, remainder 3) -> check digit 3. Matches.
    """

    def test_published_worked_example(self) -> None:
        self.assertEqual(util.iso6346_check_digit("CSQU", "305438"), 3)
        self.assertEqual(util.make_container_no("CSQU", "305438"), "CSQU3054383")

    def test_msku_style_example(self) -> None:
        # M=24 S=30 K=21 U=32 | 1 2 3 4 5 6
        # 24*1+30*2+21*4+32*8+1*16+2*32+3*64+4*128+5*256+6*512
        # = 24+60+84+256+16+64+192+512+1280+3072 = 5560
        # 5560 mod 11 = 5 (11*505=5555, remainder 5)
        self.assertEqual(util.iso6346_check_digit("MSKU", "123456"), 5)
        self.assertEqual(util.make_container_no("MSKU", "123456"), "MSKU1234565")

    def test_hand_derived_case_tclu(self) -> None:
        # T=31 C=13 L=23 U=32 | 1 9 2 8 3 7
        # 31*1+13*2+23*4+32*8+1*16+9*32+2*64+8*128+3*256+7*512
        # = 31+26+92+256+16+288+128+1024+768+3584 = 6213
        # 6213 mod 11 = 9 (11*564=6204, remainder 9)
        self.assertEqual(util.iso6346_check_digit("TCLU", "192837"), 9)
        self.assertEqual(util.make_container_no("TCLU", "192837"), "TCLU1928379")

    def test_hand_derived_case_hlxu(self) -> None:
        # H=18 L=23 X=36 U=32 | 5 0 0 1 2 3
        # 18*1+23*2+36*4+32*8+5*16+0*32+0*64+1*128+2*256+3*512
        # = 18+46+144+256+80+0+0+128+512+1536 = 2720
        # 2720 mod 11 = 3 (11*247=2717, remainder 3)
        self.assertEqual(util.iso6346_check_digit("HLXU", "500123"), 3)
        self.assertEqual(util.make_container_no("HLXU", "500123"), "HLXU5001233")

    def test_letter_values_skip_multiples_of_eleven(self) -> None:
        letters = util._ISO6346_LETTER_VALUES
        for letter, value in letters.items():
            self.assertNotEqual(value % 11, 0, f"{letter} maps to {value}, a multiple of 11")
        self.assertEqual(letters["A"], 10)
        self.assertEqual(letters["B"], 12)
        self.assertEqual(letters["C"], 13)

    def test_remainder_ten_maps_to_zero(self) -> None:
        # Construct a payload whose weighted sum mod 11 == 10, and confirm 0.
        # AAAA000000: A=10 four times, zeros elsewhere.
        # 10*1+10*2+10*4+10*8 = 10+20+40+80 = 150; 150 mod 11 = 7 (not useful)
        # Search programmatically instead of hand-picking, since we just need
        # *some* payload with remainder 10 to prove the 10->0 mapping.
        found = False
        for serial_n in range(0, 1000):
            serial = f"{serial_n:06d}"
            total = sum(
                util._iso6346_char_value(ch) * (2**pos)
                for pos, ch in enumerate("CSQU" + serial)
            )
            if total % 11 == 10:
                found = True
                self.assertEqual(util.iso6346_check_digit("CSQU", serial), 0)
                break
        self.assertTrue(found, "could not find a remainder-10 case to test")


class TestImo(unittest.TestCase):
    """Verified against 9074729 (check digit 9) and 9319466 (check digit 6)."""

    def test_9074729(self) -> None:
        # digits 9 0 7 4 7 2, weights 7 6 5 4 3 2
        # 9*7+0*6+7*5+4*4+7*3+2*2 = 63+0+35+16+21+4 = 139 -> last digit 9
        self.assertEqual(util.imo_check_digit("907472"), 9)
        self.assertEqual(util.make_imo("907472"), "9074729")

    def test_9319466(self) -> None:
        # digits 9 3 1 9 4 6, weights 7 6 5 4 3 2
        # 9*7+3*6+1*5+9*4+4*3+6*2 = 63+18+5+36+12+12 = 146 -> last digit 6
        self.assertEqual(util.imo_check_digit("931946"), 6)
        self.assertEqual(util.make_imo("931946"), "9319466")

    def test_invalid_length_raises(self) -> None:
        with self.assertRaises(ValueError):
            util.imo_check_digit("12345")


class TestDateKey(unittest.TestCase):
    def test_scalar_roundtrip(self) -> None:
        key = util.to_date_key("2026-08-31")
        self.assertEqual(int(key), 20260831)
        back = util.from_date_key(20260831)
        self.assertEqual(back.year, 2026)
        self.assertEqual(back.month, 8)
        self.assertEqual(back.day, 31)

    def test_series_roundtrip(self) -> None:
        dates = pd.Series(pd.date_range("2023-01-01", periods=5, freq="D"))
        keys = util.to_date_key(dates)
        self.assertEqual(keys.dtype, np.dtype("int32"))
        self.assertEqual(list(keys), [20230101, 20230102, 20230103, 20230104, 20230105])
        back = util.from_date_key(keys)
        pd.testing.assert_series_equal(
            back.reset_index(drop=True), dates.reset_index(drop=True), check_names=False
        )


class TestEnforceDtypes(unittest.TestCase):
    def test_casts_successfully(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["1.5", "2.5", "3.5"]})
        out = util.enforce_dtypes(df, {"a": "int32", "b": "float32"})
        self.assertEqual(str(out["a"].dtype), "int32")
        self.assertEqual(str(out["b"].dtype), "float32")

    def test_raises_with_all_problems_listed(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        with self.assertRaises(ValueError) as ctx:
            util.enforce_dtypes(df, {"a": "not_a_real_dtype", "missing_col": "int32"})
        message = str(ctx.exception)
        self.assertIn("a", message)
        self.assertIn("missing_col", message)


class TestAddUnknownMember(unittest.TestCase):
    def test_prepends_sentinel_row(self) -> None:
        df = pd.DataFrame(
            {
                "ThingKey": np.array([1, 2], dtype="int32"),
                "ThingCode": ["ABC", "DEF"],
                "ThingName": ["Alpha", "Beta"],
                "IsActive": np.array([1, 0], dtype="int8"),
                "SomeFloat": np.array([1.5, 2.5], dtype="float32"),
            }
        )
        out = util.add_unknown_member(df, "ThingKey")
        self.assertEqual(len(out), 3)
        self.assertEqual(out.loc[0, "ThingKey"], -1)
        self.assertEqual(out.loc[0, "ThingCode"], "#NA")
        self.assertEqual(out.loc[0, "ThingName"], "Unknown")
        self.assertEqual(out.loc[0, "IsActive"], 0)
        self.assertEqual(out.loc[0, "SomeFloat"], 0.0)
        # Original rows preserved unchanged.
        self.assertEqual(out.loc[1, "ThingKey"], 1)
        self.assertEqual(str(out["ThingKey"].dtype), "int32")
        self.assertEqual(str(out["IsActive"].dtype), "int8")

    def test_overrides_applied(self) -> None:
        df = pd.DataFrame({"ThingKey": np.array([1], dtype="int32"), "ValidTo": ["2026-01-01"]})
        out = util.add_unknown_member(df, "ThingKey", overrides={"ValidTo": "9999-12-31"})
        self.assertEqual(out.loc[0, "ValidTo"], "9999-12-31")


if __name__ == "__main__":
    unittest.main()
