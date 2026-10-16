"""Scout agent — proposes a route and expected all-in cost for an order intent.

Reads live venue prices (mock HyperCore book + Elysium AMM) and returns the
cheapest viable route. The expected cost travels with the commitment; the
Autopsy later grades the fill against exactly this number.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .market import RoutePrice, all_routes


@dataclass
class Proposal:
    side: str
    size_usd: float
    max_cost_bps: float
    chosen: RoutePrice
    alternatives: list[RoutePrice] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)

    @property
    def expected_cost_bps(self) -> float:
        return self.chosen.cost_bps


def propose(side: str, size_usd: float, max_cost_bps: float) -> Proposal:
    routes = all_routes(side, size_usd)
    viable, rejected = [], []
    for r in routes:
        if r.cost_bps != r.cost_bps:  # NaN = insufficient depth
            rejected.append(f"{r.venue}: {r.note}")
        elif r.cost_bps > max_cost_bps:
            rejected.append(f"{r.venue}: cost {r.cost_bps:.2f} bps exceeds budget {max_cost_bps:.2f} bps")
        else:
            viable.append(r)
    if not viable:
        raise SystemExit(
            "Scout: no viable route — every venue is over budget or dry.\n  " + "\n  ".join(rejected)
        )
    viable.sort(key=lambda r: r.cost_bps)
    return Proposal(side=side, size_usd=size_usd, max_cost_bps=max_cost_bps,
                    chosen=viable[0], alternatives=viable[1:], rejected=rejected)
