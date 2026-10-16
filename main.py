#!/usr/bin/env python3
"""RouteClerk CLI — Route Commitment -> Fill -> Autopsy -> Act or Blocked.

Commands:
  python main.py demo                              full two-scenario walkthrough
  python main.py run    [--slippage-bps N] ...     one commitment cycle
  python main.py status                            gate state for an agent
  python main.py ack    [--cover]                  acknowledge a failed autopsy

No dependencies — Python 3.10+ stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from agents import clerk, console as c, gate, market, scout, skeptic

DATA_DIR = Path(__file__).parent / "data"


def _load_intent(args) -> dict:
    if args.intent:
        return json.loads(Path(args.intent).read_text())
    return json.loads((DATA_DIR / "intent.json").read_text())


def _print_proposal(p: scout.Proposal) -> None:
    print(c.section("SCOUT"))
    print(c.kv("intent", f"{p.side.upper()} ${p.size_usd:,.0f}  budget {p.max_cost_bps:.1f} bps"))
    print(c.kv("proposed route", c.bold(p.chosen.venue)))
    print(c.kv("expected cost", c.green(f"{p.expected_cost_bps:.2f} bps") + "  (vs mid)"))
    print(c.kv("  breakdown", f"impact {p.chosen.impact_bps:.2f} + fee {p.chosen.fee_bps:.2f}"))
    for alt in p.alternatives:
        print(c.kv("alternative", alt.as_row()))
    for rej in p.rejected:
        print(c.kv("rejected", c.dim(rej)))


def _print_verdict(v: skeptic.Verdict) -> None:
    print(c.section("SKEPTIC"))
    color = {"APPROVE": c.green, "IMPROVE": c.yellow, "KILL": c.red}[v.action]
    print(c.kv("verdict", color(c.bold(v.action))))
    for r in v.reasons:
        print(c.kv("reason", c.dim(r)))


def _print_commitment(cm: clerk.Commitment) -> None:
    print(c.section("CLERK * ROUTE COMMITMENT"))
    print(c.kv("commitment id", c.bold(cm.commitment_id)))
    print(c.kv("digest (sha256)", c.dim(cm.digest)))
    print(c.kv("agent", cm.agent))
    print(c.kv("route locked", f"{cm.venue} @ expected {cm.expected_cost_bps:.2f} bps"))
    print(c.kv("deadline", f"{cm.deadline_ms - cm.created_ms} ms after commit"))
    print(c.dim("  -> on-chain: digest stored in RouteClerkGate; canAct required before CoreWriter send"))


def _print_fill(f: clerk.Fill) -> None:
    print(c.section("FILL (ElysiumCoreWriter path, simulated)"))
    print(c.kv("venue", f.venue))
    print(c.kv("avg price", f"{f.avg_price:.4f}   mid {f.mid_price:.4f}"))
    print(c.kv("all-in cost", f"{f.realized_cost_bps:.2f} bps  (impact {f.impact_bps:.2f} + fee {f.fee_bps:.2f})"))
    print(c.kv("writer latency", f"{f.latency_ms} ms"))


def _print_autopsy(a: clerk.Autopsy) -> None:
    print(c.section("AUTOPSY"))
    print(c.kv("autopsy id", a.autopsy_id))
    print(c.kv("committed cost", f"{a.committed_cost_bps:.2f} bps"))
    print(c.kv("realized cost", f"{a.realized_cost_bps:.2f} bps"))
    print(c.kv("entry vs mid", f"{a.entry_vs_mid_bps:.2f} bps"))
    print(c.kv("fees", f"{a.fee_bps:.2f} bps"))
    print(c.kv("funding drift", f"{a.funding_drift_bps:.2f} bps"))
    print(c.kv("deviation", f"{a.deviation_bps:+.2f} bps   (threshold +/-{a.threshold_bps:.1f})"))
    verdict = c.green(c.bold("PASS")) if a.passed else c.red(c.bold("FAIL"))
    print(c.kv("verdict", verdict))


def _print_gate(rec: dict) -> None:
    print(c.section("GATE"))
    if rec["status"] == "clear":
        print(c.kv("agent state", c.green(c.bold("CLEAR — may open new risk"))))
    else:
        oa = rec.get("open_autopsy") or {}
        print(c.kv("agent state", c.red(c.bold("BLOCKED — next intent refused"))))
        print(c.kv("open autopsy", f"{oa.get('autopsy_id')}  deviation {oa.get('deviation_bps'):+.2f} bps"))
        print(c.dim("  -> unblock: `python main.py ack` (optionally --cover to bond the deviation)"))


def cmd_run(args) -> None:
    intent = _load_intent(args)
    agent = args.agent or intent["agent"]
    intent["agent"] = agent

    st = gate.status(agent)
    if st["status"] == "blocked":
        print(c.red(c.bold("GATE: agent is BLOCKED — refusing to open a new commitment.")))
        _print_gate(st)
        print(c.dim("  run `python main.py status` then `python main.py ack`"))
        raise SystemExit(2)

    print(c.bold(f"\nRouteClerk * one cycle for agent {agent[:18]}…\n"))
    p = scout.propose(intent["side"], float(intent["size_usd"]), float(intent["max_cost_bps"]))
    _print_proposal(p)

    v = skeptic.review(p)
    _print_verdict(v)
    if v.action == "KILL":
        print(c.red(c.bold("\nRoute killed before commitment — no fill, no risk opened.\n")))
        raise SystemExit(0)

    cm = clerk.make_commitment(agent, p, intent.get("symbol", "HYPE-PERP"))
    _print_commitment(cm)

    fill = clerk.simulate_fill(cm, slippage_bps=args.slippage_bps)
    _print_fill(fill)

    autopsy = clerk.make_autopsy(cm, fill)
    _print_autopsy(autopsy)

    rec = gate.apply_autopsy(agent, autopsy)
    _print_gate(rec)
    print()


def cmd_demo(_args) -> None:
    print(c.bold(c.header("\n== ROUTECLERK DEMO ==  Commitment -> Fill -> Autopsy -> Act or Blocked\n")))
    demo_agent = "0xDemoAgent000000000000000000000000000001"
    gate.STATE_PATH.write_text(json.dumps({"agents": {}}))  # fresh demo state

    print(c.bold("Scenario 1 — fill lands near expectation -> autopsy PASSES -> gate stays CLEAR\n"))
    ns = argparse.Namespace(intent=None, agent=demo_agent, slippage_bps=clerk.ADVERSE_SLIP_BPS)
    cmd_run(ns)

    print(c.bold("Scenario 2 — book runs 6 bps against us between commit and fill -> FAIL -> BLOCKED\n"))
    ns2 = argparse.Namespace(intent=None, agent=demo_agent, slippage_bps=6.0)
    try:
        cmd_run(ns2)
    except SystemExit:
        pass

    print(c.bold("Scenario 3 — agent tries to act again while blocked -> intent refused\n"))
    try:
        cmd_run(argparse.Namespace(intent=None, agent=demo_agent, slippage_bps=0.5))
    except SystemExit:
        pass

    print(c.bold("Scenario 4 — operator acknowledges the failed autopsy -> gate reopens\n"))
    rec = gate.acknowledge(demo_agent, cover=False)
    _print_gate(rec)
    print(c.dim("  (on-chain: RouteClerkGate.acknowledgeAutopsy, or coverDeviation to post a bond)"))
    print(c.green(c.bold("\nDemo complete. One line to remember: commitment -> fill -> autopsy -> act or blocked.\n")))


def cmd_status(args) -> None:
    agent = args.agent or json.loads((DATA_DIR / "intent.json").read_text())["agent"]
    _print_gate(gate.status(agent))


def cmd_ack(args) -> None:
    agent = args.agent or json.loads((DATA_DIR / "intent.json").read_text())["agent"]
    rec = gate.acknowledge(agent, cover=args.cover)
    if rec is None or rec.get("status") == "clear" and not rec.get("acknowledged"):
        print(c.yellow("Nothing to acknowledge — agent was already clear."))
        return
    print(c.section("GATE * ACKNOWLEDGED"))
    _print_gate(rec)
    if args.cover:
        print(c.kv("bond", c.yellow("deviation covered — specialist challenge can claim it")))


def main() -> None:
    ap = argparse.ArgumentParser(prog="routeclerk", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("demo", help="run all four scenarios").set_defaults(fn=cmd_demo)

    run = sub.add_parser("run", help="one commitment cycle")
    run.add_argument("--intent", help="path to intent JSON (default: data/intent.json)")
    run.add_argument("--agent", help="override agent address")
    run.add_argument("--slippage-bps", type=float, default=clerk.ADVERSE_SLIP_BPS,
                     help=f"adverse fill-time move in bps (default {clerk.ADVERSE_SLIP_BPS})")
    run.set_defaults(fn=cmd_run)

    st = sub.add_parser("status", help="show gate state")
    st.add_argument("--agent")
    st.set_defaults(fn=cmd_status)

    ack = sub.add_parser("ack", help="acknowledge a failed autopsy")
    ack.add_argument("--agent")
    ack.add_argument("--cover", action="store_true", help="post a bond covering the deviation")
    ack.set_defaults(fn=cmd_ack)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
