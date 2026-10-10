import unittest
from utils.set_tick import get_set_tick, round_to_set_tick


class TestSETTick(unittest.TestCase):
    def test_tick_thresholds(self):
        self.assertEqual(get_set_tick(1.5), 0.01)
        self.assertEqual(get_set_tick(2.0), 0.02)
        self.assertEqual(get_set_tick(4.99), 0.02)
        self.assertEqual(get_set_tick(5.0), 0.05)
        self.assertEqual(get_set_tick(10.0), 0.10)
        self.assertEqual(get_set_tick(25.0), 0.25)
        self.assertEqual(get_set_tick(100.0), 0.50)
        self.assertEqual(get_set_tick(200.0), 1.00)
        self.assertEqual(get_set_tick(400.0), 2.00)

    def test_half_up_rounding(self):
        # SET tick for 44.079 is 0.25 (since 25 <= 44.079 < 100)
        # 44.079 / 0.25 = 176.316 -> rounds to 176 * 0.25 = 44.00
        self.assertEqual(round_to_set_tick(44.079), 44.00)
        # Price 1.50 -> tick 0.01 -> 1.50
        self.assertEqual(round_to_set_tick(1.50), 1.50)
        # Price 2.03 -> tick 0.02 -> 2.04
        self.assertEqual(round_to_set_tick(2.03), 2.04)

    def test_positive_price_never_rounds_to_zero(self):
        # A price below half the minimum tick must still quote at 0.01.
        self.assertEqual(round_to_set_tick(0.004), 0.01)
        self.assertEqual(round_to_set_tick(0.0001), 0.01)


if __name__ == "__main__":
    unittest.main()
