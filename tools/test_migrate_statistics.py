"""Synthetic boundary tests. No Home Assistant connection or personal data."""

import unittest

from migrate_statistics import HOUR_MS, make_plan


def row(hour, state, total):
    return {"start": hour * HOUR_MS, "state": state, "sum": total}


class MigrationPlanTests(unittest.TestCase):
    def setUp(self):
        self.source = [row(0, 100, 10), row(1, 102, 12), row(2, 105, 15)]
        self.target = [row(3, 106, 0), row(4, 108, 2)]

    def test_bridge_preserves_production_without_changing_target(self):
        plan = make_plan(self.source, self.target, HOUR_MS, 3 * HOUR_MS)
        sums = [item["sum"] for item in plan["stats"]]
        self.assertEqual(sums, [0, 2, 5])
        self.assertEqual(plan["legacy_production_kwh"], 5)
        self.assertEqual(self.target[0]["sum"] + plan["target_sum_adjustment"] - sums[-1], 1)
        self.assertEqual(self.target[-1], row(4, 108, 2))

    def test_existing_prefix_aborts_including_second_run(self):
        with self.assertRaises(ValueError):
            make_plan(self.source, [row(1, 102, -4), *self.target], HOUR_MS, 3 * HOUR_MS)

    def test_missing_hour_aborts(self):
        with self.assertRaises(ValueError):
            make_plan(self.source[:1] + self.source[2:], self.target, HOUR_MS, 3 * HOUR_MS)

    def test_counter_reset_aborts(self):
        with self.assertRaises(ValueError):
            make_plan([*self.source[:2], row(2, 1, 15)], self.target, HOUR_MS, 3 * HOUR_MS)

    def test_missing_baseline_aborts(self):
        with self.assertRaises(ValueError):
            make_plan(self.source[1:], self.target, HOUR_MS, 3 * HOUR_MS)


if __name__ == "__main__":
    unittest.main()
