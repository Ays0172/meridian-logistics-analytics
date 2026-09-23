"""Every live-feed day must draw from its own RNG stream.

Run with: python -m pytest 01_generator/tests/test_live_feed_seeding.py -v
Needs the dimensions on disk (python 01_generator/build_dims.py).

Seven fact builders used to seed from a fixed ``child_rng("<Table>")``. The
history build calls each one once, so that was fine there, but the live feed
calls them once per day: every day drew the same random stream. Port calls were
the first ``n`` rows of an identical draw, so any two days with the same volume
(the same weekday, given weekly seasonality) came out identical apart from keys
and dates.
"""
from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

import pandas as pd

GEN_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GEN_DIR))

from meridian import factio  # noqa: E402
from meridian.facts_core import (  # noqa: E402
    build_fact_booking,
    build_fact_exchange_rate,
    build_fact_shipment,
    build_fact_shipment_milestone,
)
from meridian.facts_land import (  # noqa: E402
    build_fact_inventory_snapshot,
    build_fact_transport_leg,
    build_fact_warehouse_task,
)
from meridian.facts_ops import (  # noqa: E402
    build_fact_container_move,
    build_fact_freight_charge,
    build_fact_port_call,
)

DAY = pd.Timestamp("2026-09-01")
DAY_A, DAY_B = "live:{t}:2026-09-01", "live:{t}:2026-09-08"
KEY_COLUMNS = {"PortCallKey", "ContainerMoveKey", "ChargeLineKey", "TransportLegKey",
               "WarehouseTaskKey", "InventorySnapshotKey"}

# Builders whose draws must follow a seed_label, and the table name that is
# their history default.
SEEDED_BUILDERS = {
    "build_fact_booking": "FactBooking",
    "build_fact_shipment": "FactShipment",
    "build_fact_shipment_milestone": "FactShipmentMilestone",
    "build_fact_port_call": "FactPortCall",
    "build_fact_container_move": "FactContainerMove",
    "build_fact_freight_charge": "FactFreightCharge",
    "build_fact_transport_leg": "FactTransportLeg",
    "build_fact_warehouse_task": "FactWarehouseTask",
    "build_fact_inventory_snapshot": "FactInventorySnapshot",
}


def _content(df: pd.DataFrame) -> pd.DataFrame:
    """Rows without surrogate keys, which the feed assigns itself."""
    return df.drop(columns=[c for c in df.columns if c in KEY_COLUMNS]).reset_index(drop=True)


class TestLiveFeedCallsPassSeedLabels(unittest.TestCase):
    """Static guard: _append_day must pass seed_label to every fact builder."""

    def test_every_builder_call_in_append_day_has_seed_label(self):
        tree = ast.parse((GEN_DIR / "live_feed.py").read_text(encoding="utf-8"))
        append_day = next(n for n in ast.walk(tree)
                          if isinstance(n, ast.FunctionDef) and n.name == "_append_day")
        calls = [n for n in ast.walk(append_day) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id in SEEDED_BUILDERS]
        self.assertEqual(len(calls), len(SEEDED_BUILDERS))
        missing = [c.func.id for c in calls
                   if "seed_label" not in {k.arg for k in c.keywords}]
        self.assertEqual(missing, [])


class TestBuildersFollowSeedLabel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dims = factio.load_dims()
        cls.fx = build_fact_exchange_rate(cls.dims)
        cls.bk = build_fact_booking(cls.dims, cls.fx, 400, window=(DAY, DAY),
                                    seed_label="live:FactBooking:2026-09-01")
        cls.sh = build_fact_shipment(cls.dims, cls.bk, cls.fx, 300,
                                     seed_label="live:FactShipment:2026-09-01")
        cls.cm = build_fact_container_move(cls.dims, cls.sh, 600)

    def _builders(self):
        d, sh, bk, cm, fx = self.dims, self.sh, self.bk, self.cm, self.fx
        return {
            "FactShipmentMilestone": lambda s: build_fact_shipment_milestone(d, sh, bk, as_of=DAY, seed_label=s),
            "FactPortCall": lambda s: build_fact_port_call(d, 90, seed_label=s),
            "FactContainerMove": lambda s: build_fact_container_move(d, sh, 600, seed_label=s),
            "FactFreightCharge": lambda s: build_fact_freight_charge(d, sh, cm, fx, 600, seed_label=s),
            "FactTransportLeg": lambda s: build_fact_transport_leg(d, sh, 200, seed_label=s),
            "FactWarehouseTask": lambda s: build_fact_warehouse_task(d, sh, 400, seed_label=s),
            "FactInventorySnapshot": lambda s: build_fact_inventory_snapshot(d, 300, seed_label=s),
        }

    def test_two_days_with_same_inputs_differ(self):
        for table, build in self._builders().items():
            with self.subTest(table=table):
                a = _content(build(DAY_A.format(t=table)))
                b = _content(build(DAY_B.format(t=table)))
                self.assertFalse(a.equals(b), f"{table}: two live days produced identical rows")

    def test_same_label_is_reproducible(self):
        for table, build in self._builders().items():
            with self.subTest(table=table):
                label = DAY_A.format(t=table)
                pd.testing.assert_frame_equal(build(label), build(label))

    def test_default_label_is_the_history_stream(self):
        """History must stay byte-identical: the default label is the table name."""
        d = self.dims
        pd.testing.assert_frame_equal(build_fact_port_call(d, 90),
                                      build_fact_port_call(d, 90, seed_label="FactPortCall"))
        pd.testing.assert_frame_equal(build_fact_inventory_snapshot(d, 300),
                                      build_fact_inventory_snapshot(d, 300, seed_label="FactInventorySnapshot"))


if __name__ == "__main__":
    unittest.main()
