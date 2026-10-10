"""Calculation engine: 21-level indicative DR price table (web copy).

iNAV (THB) = (Underlying_Price x FX_Rate) / Ratio
"""

from dataclasses import dataclass
from typing import List

from set_tick import get_set_tick, round_to_set_tick

HALF_STEPS = 10


@dataclass(frozen=True)
class PriceLevel:
    level: int
    dr_price: float
    underlying_price: float
    fx_rate: float
    raw_dr: float


class CalculationEngine:
    @staticmethod
    def _step_up(current: float) -> float:
        return round_to_set_tick(current + get_set_tick(current))

    @staticmethod
    def _step_down(current: float) -> float:
        return round_to_set_tick(current - get_set_tick(current))

    def generate_price_table(
        self,
        underlying_price: float,
        fx_rate: float,
        ratio: float,
    ) -> List[PriceLevel]:
        if not (underlying_price > 0 and fx_rate > 0 and ratio > 0):
            raise ValueError("Price, FX rate and ratio must be positive.")

        current_inav = (underlying_price * fx_rate) / ratio
        center = round_to_set_tick(current_inav)
        if center == 0:
            center = 0.01

        above: List[float] = []
        price = center
        for _ in range(HALF_STEPS):
            price = self._step_up(price)
            if price <= center:
                break
            above.append(price)

        below: List[float] = []
        price = center
        for _ in range(HALF_STEPS):
            price = self._step_down(price)
            if price <= 0 or price >= center:
                break
            below.append(price)

        ordered = list(reversed(below)) + [center] + above

        table: List[PriceLevel] = []
        for level, dr_price in zip(range(-HALF_STEPS, HALF_STEPS + 1), ordered):
            implied_underlying = (dr_price * ratio) / fx_rate
            raw_dr = (implied_underlying * fx_rate) / ratio
            table.append(
                PriceLevel(
                    level=level,
                    dr_price=dr_price,
                    underlying_price=round(implied_underlying, 6),
                    fx_rate=fx_rate,
                    raw_dr=raw_dr,
                )
            )
        return table
