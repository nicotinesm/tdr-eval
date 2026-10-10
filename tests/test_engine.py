import unittest
from engine import CalculationEngine
from utils.set_tick import round_to_set_tick


class TestCalculationEngine(unittest.TestCase):
    def setUp(self):
        self.engine = CalculationEngine()

    def test_21_levels_generated(self):
        levels = self.engine.generate_price_table(
            underlying_price=144.30,
            fx_rate=33.05,
            ratio=1600.0,
        )
        self.assertEqual(len(levels), 21)
        self.assertEqual(levels[0].level, -10)
        self.assertEqual(levels[10].level, 0)
        self.assertEqual(levels[20].level, 10)

    def test_inav_calculation(self):
        levels = self.engine.generate_price_table(
            underlying_price=100.0,
            fx_rate=35.0,
            ratio=10.0,
        )
        center = levels[10]
        self.assertAlmostEqual(center.dr_price, 350.0)
        self.assertAlmostEqual(center.underlying_price, 100.0, places=1)

    def test_high_ratio_produces_distinct_rows(self):
        levels = self.engine.generate_price_table(
            underlying_price=144.30,
            fx_rate=33.05,
            ratio=1600.0,
        )
        prices = [lvl.dr_price for lvl in levels]
        self.assertEqual(len(set(prices)), 21)

    def test_center_row_uses_half_up_rounding(self):
        # iNAV = 100 * 0.01 / 40 = 0.025 -> SET tick 0.01 -> half-up rounds to 0.03
        # (Python's built-in round() would give 0.02 via banker's rounding)
        levels = self.engine.generate_price_table(100.0, 0.01, 40.0)
        self.assertEqual(levels[10].dr_price, 0.03)

    def test_grid_crossing_tick_band_stays_on_valid_set_prices(self):
        # iNAV = 1.99 sits in the <2.00 band (tick 0.01), but the grid extends
        # into the >=2.00 band (tick 0.02). Every quoted price must still be a
        # valid SET price (a multiple of its own band's tick) and monotonic.
        levels = self.engine.generate_price_table(100.0, 0.0199, 1.0)
        prices = [lvl.dr_price for lvl in levels]
        self.assertEqual(len(levels), 21)
        self.assertEqual(prices, sorted(prices))
        for price in prices:
            self.assertEqual(round_to_set_tick(price), price)

    def test_invalid_inputs_raise_value_error(self):
        with self.assertRaises(ValueError):
            self.engine.generate_price_table(0, 36.0, 10)
        with self.assertRaises(ValueError):
            self.engine.generate_price_table(100, -1, 10)


if __name__ == "__main__":
    unittest.main()
