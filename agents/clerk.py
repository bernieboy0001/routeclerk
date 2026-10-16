"""Clerk — the accountability core.

1. Route Commitment: canonical hash of (agent, intent, route, expected cost,
   deadline). On-chain this digest is what RouteClerkGate stores before the
   agent is allowed to fire the order through ElysiumCoreWriter.
2. Fill simulation: re-walks the venue at fill time with an adverse-selection
   offset (slippage_bps) standing in for the 100–200 ms between commitment
   and CoreWriter confirmation.
3. Autopsy: realized all-in cost vs committed cost. deviation > threshold
   => FAIL, and the Gate blocks the agent's next intent until acknowledged.

Digest note: production uses keccak256 (EVM-native, matches the on-chain
commitment id). Python's stdlib has no keccak, so the prototype uses sha256
over the same canonical JSON — the structure is identical, only the hash
function differs.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field

from .market import load_book, load_pool, route_elysium, route_hypercore
from .scout import Proposal

DEVIATION_THRESHOLD_BPS = 2.0
ADVERSE_SLIP_BPS = 0.5  # default fill-time adverse move; raise it to see the gate bite


@dataclass
class Commitment:
    commitment_id: str
    agent: str
    side: str
    symbol: str
    size_usd: float
    venue: str
    expected_cost_bps: float
    max_cost_bps: float
    deadline_ms: int
    route_snapshot: dict
    created_ms: int
    digest: str

    def summary(self) -> str:
        return (f"id={self.commitment_id}  venue={self.venue}  "
                f"expected={self.expected_cost_bps:.2f} bps  budget={self.max_cost_bps:.2f} bps")


@dataclass
class Fill:
    venue: str
    avg_price: float
    mid_price: float
    fee_bps: float
    impact_bps: float
    realized_cost_bps: float
    filled_size: float
    latency_ms: int


@dataclass
class Autopsy:
    autopsy_id: str
    commitment_id: str
    agent: str
    committed_cost_bps: float
    realized_cost_bps: float
    entry_vs_mid_bps: float
    fee_bps: float
    funding_drift_bps: float
    deviation_bps: float
    threshold_bps: float
    passed: bool
    verdict: str
    fill: Fill = field(repr=False, default=None)


def make_commitment(agent: str, proposal: Proposal, symbol: str) -> Commitment:
    now = int(time.time() * 1000)
    body = {
        "agent": agent,
        "side": proposal.side,
        "symbol": symbol,
        "size_usd": round(proposal.size_usd, 2),
        "venue": proposal.chosen.venue,
        "expected_cost_bps": round(proposal.expected_cost_bps, 4),
        "max_cost_bps": proposal.max_cost_bps,
        "deadline_ms": now + 5_000,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return Commitment(
        commitment_id=digest[:16],
        route_snapshot=body,
        created_ms=now,
        digest=digest,
        **body,
    )


def simulate_fill(commitment: Commitment, slippage_bps: float) -> Fill:
    """Fill-time re-walk of the committed venue with adverse selection.

    slippage_bps models the book moving between commitment and the
    ElysiumCoreWriter write landing (~100–200 ms). Default is small; the CLI
    exposes it so a reviewer can force a breach.
    """
    if commitment.venue == "HyperCore":
        r = route_hypercore(load_book(), commitment.side, commitment.size_usd, stress_bps=slippage_bps)
    else:
        r = route_elysium(load_pool(), commitment.side, commitment.size_usd, stress_bps=slippage_bps)
    return Fill(
        venue=r.venue,
        avg_price=r.avg_price,
        mid_price=r.mid_price,
        fee_bps=r.fee_bps,
        impact_bps=r.impact_bps,
        realized_cost_bps=r.cost_bps,
        filled_size=r.filled_size,
        latency_ms=140,
    )


def make_autopsy(commitment: Commitment, fill: Fill, threshold_bps: float = DEVIATION_THRESHOLD_BPS) -> Autopsy:
    # Funding drift is a placeholder for the post-launch position/funding
    # tracking across HyperCore; zero in the MVP fill-grade autopsy.
    funding_drift_bps = 0.0
    deviation = fill.realized_cost_bps - commitment.expected_cost_bps
    passed = deviation <= threshold_bps
    return Autopsy(
        autopsy_id=uuid.uuid4().hex[:12],
        commitment_id=commitment.commitment_id,
        agent=commitment.agent,
        committed_cost_bps=commitment.expected_cost_bps,
        realized_cost_bps=fill.realized_cost_bps,
        entry_vs_mid_bps=fill.impact_bps,
        fee_bps=fill.fee_bps,
        funding_drift_bps=funding_drift_bps,
        deviation_bps=deviation,
        threshold_bps=threshold_bps,
        passed=passed,
        verdict="PASS" if passed else "FAIL",
        fill=fill,
    )
