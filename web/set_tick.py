"""SET (Stock Exchange of Thailand) tick size rounding logic (web copy)."""

from decimal import ROUND_HALF_UP, Decimal
from typing import List, Tuple

TICK_RULES: List[Tuple[float, float]] = [
    (2.0, 0.01),
    (5.0, 0.02),
    (10.0, 0.05),
    (25.0, 0.10),
    (100.0, 0.25),
    (200.0, 0.50),
    (400.0, 1.00),
]

MAX_TICK = 2.00


def get_set_tick(price: float) -> float:
    if price is None or price <= 0:
        return TICK_RULES[0][1]
    for threshold, tick in TICK_RULES:
        if price < threshold:
            return tick
    return MAX_TICK


def round_to_set_tick(price: float) -> float:
    if price <= 0:
        return 0.01
    tick = get_set_tick(price)
    d_price = Decimal(str(price))
    d_tick = Decimal(str(tick))
    units = d_price / d_tick
    rounded_units = int(units.to_integral_value(rounding=ROUND_HALF_UP))
    if rounded_units == 0:
        rounded_units = 1
    return float((rounded_units * d_tick).quantize(d_tick))
