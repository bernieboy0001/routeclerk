"""Gate — the enforceable half of RouteClerk.

State machine per agent:
    CLEAR  --failed autopsy-->  BLOCKED  --ack (or cover deviation)-->  CLEAR

While BLOCKED the agent may not open new risk: any new route commitment is
refused. This is exactly what the on-chain RouteClerkGate.canAct flag encodes;
here it is a local JSON file so the CLI persists across invocations.
"""

from __future__ import annotations

import json
from pathlib import Path

from .clerk import Autopsy

STATE_PATH = Path(__file__).resolve().parent.parent / ".routeclerk_state.json"


def _load() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"agents": {}}


def _save(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))


def status(agent: str) -> dict:
    state = _load()
    return state["agents"].get(agent, {"status": "clear", "open_autopsy": None, "blocked_count": 0})


def check_clear(agent: str) -> bool:
    return status(agent)["status"] == "clear"


def apply_autopsy(agent: str, autopsy: Autopsy) -> dict:
    """Record the autopsy; block the agent on FAIL until acknowledged."""
    state = _load()
    rec = state["agents"].setdefault(agent, {"status": "clear", "open_autopsy": None, "blocked_count": 0})
    rec["last_autopsy"] = {
        "autopsy_id": autopsy.autopsy_id,
        "commitment_id": autopsy.commitment_id,
        "verdict": autopsy.verdict,
        "deviation_bps": round(autopsy.deviation_bps, 4),
    }
    if not autopsy.passed:
        rec["status"] = "blocked"
        rec["blocked_count"] += 1
        rec["open_autopsy"] = {
            "autopsy_id": autopsy.autopsy_id,
            "commitment_id": autopsy.commitment_id,
            "deviation_bps": round(autopsy.deviation_bps, 4),
            "threshold_bps": autopsy.threshold_bps,
        }
    _save(state)
    return rec


def acknowledge(agent: str, cover: bool = False) -> dict:
    state = _load()
    rec = state["agents"].get(agent)
    if not rec or rec["status"] != "blocked":
        return rec or {"status": "clear"}
    if cover:
        rec["covered_deviation_bps"] = rec["open_autopsy"]["deviation_bps"]
    rec["status"] = "clear"
    rec["open_autopsy"] = None
    rec["acknowledged"] = True
    _save(state)
    return rec
