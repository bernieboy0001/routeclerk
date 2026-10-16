"""Skeptic agent — adversarially re-prices the Scout's route before commitment.

Two jobs:
1. Stress test: re-walk the venue with the book/pool shifted a few bps against
   the trader. If the stressed all-in cost still fits the budget, approve.
2. Cross-venue check: if another venue beats the Scout's pick by more than
   IMPROVE_MARGIN_BPS under stress, propose it as an improvement.

A KILLED route never becomes a commitment — the agent does not act.
"""

from __future__ import annotations

from dataclasses import dataclass

from .market import all_routes
from .scout import Proposal

STRESS_BPS = 3.0
IMPROVE_MARGIN_BPS = 1.5


@dataclass
class Verdict:
    action: str  # APPROVE | IMPROVE | KILL
    reasons: list[str]
    improved: Proposal | None = None


def review(proposal: Proposal) -> Verdict:
    stressed = all_routes(proposal.side, proposal.size_usd, stress_bps=STRESS_BPS)
    by_venue = {r.venue: r for r in stressed}
    chosen_stressed = by_venue[proposal.chosen.venue]
    reasons: list[str] = [f"stress re-price @ {STRESS_BPS:.0f} bps adverse: {chosen_stressed.as_row()}"]

    if chosen_stressed.cost_bps != chosen_stressed.cost_bps:
        return Verdict("KILL", reasons + ["stressed venue has no depth — route is a mirage"])

    if chosen_stressed.cost_bps > proposal.max_cost_bps:
        return Verdict("KILL", reasons + [
            f"stressed cost {chosen_stressed.cost_bps:.2f} bps breaches budget "
            f"{proposal.max_cost_bps:.2f} bps — refusing to commit"
        ])

    best_alt = None
    for r in stressed:
        if r.venue == proposal.chosen.venue or r.cost_bps != r.cost_bps:
            continue
        if proposal.chosen.cost_bps - r.cost_bps > IMPROVE_MARGIN_BPS:
            best_alt = r
    if best_alt is not None:
        reasons.append(f"{best_alt.venue} beats pick by "
                       f"{proposal.chosen.cost_bps - best_alt.cost_bps:.2f} bps under stress")
        return Verdict("IMPROVE", reasons)

    reasons.append("no cheaper venue under stress; route survives")
    return Verdict("APPROVE", reasons)
