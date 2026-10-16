"""Mock market layer.

In production these two repricers are fed by Elysium's HyperCore market-data
precompile (full book depth from an Elysium contract) and the Elysium AMM
router. For the hackathon prototype they read local JSON snapshots so the
whole loop runs offline and deterministically.

`stress_bps` degrades the executable price — the Skeptic uses it to re-price
a route under adverse conditions before the Clerk is allowed to commit.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class RoutePrice:
    venue: str
    avg_price: float
    mid_price: float
    fee_bps: float
    impact_bps: float
    cost_bps: float
    filled_size: float
    note: str

    def as_row(self) -> str:
        return (
            f"{self.venue:<12} avg={self.avg_price:.4f}  fee={self.fee_bps:5.2f}  "
            f"impact={self.impact_bps:5.2f}  cost={self.cost_bps:5.2f} bps"
        )


def load_book() -> dict:
    return json.loads((DATA_DIR / "hypercore_book.json").read_text())


def load_pool() -> dict:
    return json.loads((DATA_DIR / "elysium_pool.json").read_text())


def book_mid(book: dict) -> float:
    best_bid = book["bids"][0][0]
    best_ask = book["asks"][0][0]
    return (best_bid + best_ask) / 2.0


def pool_mid(pool: dict) -> float:
    return pool["usdc_reserve"] / pool["token_reserve"]


def _stress_price(price: float, side: str, stress_bps: float) -> float:
    """Move the executable price against the trader by stress_bps."""
    factor = stress_bps / 10_000.0
    return price * (1 + factor) if side == "buy" else price * (1 - factor)


def route_hypercore(book: dict, side: str, size_usd: float, stress_bps: float = 0.0) -> RoutePrice:
    """Walk the HyperCore book and compute the all-in cost vs mid."""
    mid = book_mid(book)
    levels = book["asks"] if side == "buy" else book["bids"]
    remaining = size_usd
    notional = 0.0
    filled = 0.0
    for px, sz in levels:
        exec_px = _stress_price(px, side, stress_bps)
        level_usd = exec_px * sz
        take = min(remaining, level_usd)
        notional += take
        filled += take / exec_px
        remaining -= take
        if remaining <= 1e-9:
            break
    if remaining > 1e-9:
        avg = notional / filled if filled else float("inf")
        return RoutePrice("HyperCore", avg, mid, book["taker_fee_bps"], float("nan"), float("nan"),
                          filled, "INSUFFICIENT DEPTH — order exceeds visible book")
    avg = notional / filled
    slip = (avg - mid) / mid if side == "buy" else (mid - avg) / mid
    impact_bps = slip * 10_000.0
    fee_bps = book["taker_fee_bps"]
    return RoutePrice("HyperCore", avg, mid, fee_bps, impact_bps, impact_bps + fee_bps,
                      filled, "taker fill, full depth walk")


def route_elysium(pool: dict, side: str, size_usd: float, stress_bps: float = 0.0) -> RoutePrice:
    """Constant-product swap against the Elysium AMM pool."""
    mid = pool_mid(pool)
    x = pool["token_reserve"]
    y = pool["usdc_reserve"]
    fee = pool["fee_bps"] / 10_000.0
    if side == "buy":
        dx_in = size_usd * (1 - 0)  # USDC in
        dx_eff = dx_in * (1 - fee)
        dy_out = (x * dx_eff) / (y + dx_eff)
        exec_avg = dx_in / dy_out if dy_out else float("inf")
        slip = (exec_avg - mid) / mid
    else:
        dx_in = size_usd / mid  # token in, valued at mid notional
        dx_eff = dx_in * (1 - fee)
        dy_out = (y * dx_eff) / (x + dx_eff)
        exec_avg = dx_in / dy_out if dy_out else float("inf")  # token per USDC, invert for compare
        exec_avg = 1.0 / exec_avg if exec_avg else float("inf")
        slip = (mid - exec_avg) / mid
    impact_bps = slip * 10_000.0
    impact_bps += stress_bps  # AMM stress = extra adverse impact
    impact_bps = max(impact_bps, 0.0)
    fee_bps = pool["fee_bps"]
    avg = mid * (1 + impact_bps / 10_000.0) if side == "buy" else mid * (1 - impact_bps / 10_000.0)
    filled = dy_out if side == "buy" else size_usd / avg
    return RoutePrice("ElysiumAMM", avg, mid, fee_bps, impact_bps, impact_bps + fee_bps,
                      filled, "constant-product, fee-on-input")


def all_routes(side: str, size_usd: float, stress_bps: float = 0.0) -> list[RoutePrice]:
    return [
        route_hypercore(load_book(), side, size_usd, stress_bps),
        route_elysium(load_pool(), side, size_usd, stress_bps),
    ]
