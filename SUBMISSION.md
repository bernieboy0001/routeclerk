# RouteClerk — Ascend × Elysium Builder Competition Submission



## 1. Project + Links

- **Project name:** RouteClerk
- **X account:** @RouteClerk _(confirm handle)_
- **Website:** https://routeclerk.vercel.app — live now. Custom domain `routeclerk.xyz` pending DNS.
- **GitHub / docs:** https://github.com/bernieboy0001/routeclerk (public). In-repo docs:
  [`README.md`](README.md), [`SUBMISSION.md`](SUBMISSION.md), [`scripts/deploy.md`](scripts/deploy.md).
- **Demo video:** [`demo/routeclerk-demo.mp4`](demo/routeclerk-demo.mp4) — 90s, captioned, with voiceover.

## 2. Project Overview

**What we're building.** RouteClerk is an on-chain accountability layer for agents that trade
on Elysium + HyperCore. One mechanic:

```
Route Commitment → Fill → Autopsy → Act or Blocked
```

Before an order intent is accepted, the agent commits to a specific route and its expected
all-in cost. After the fill lands (via `ElysiumCoreWriter`), RouteClerk files a signed
**Autopsy** grading promise against reality. If the deviation breaches the threshold, the
agent's next action is **blocked** until the Autopsy is acknowledged or the gap is covered
with a bond.

**Who it's for.** Traders, market makers, and agent operators driving real orders on their own
HyperCore account from Elysium at ~100–200 ms latency.

**The problem.** Once agents can read full HyperCore books (market-data precompile) and place
orders in ~100–200 ms, speed stops being the constraint. The new expensive failure is **hidden
cost** — worse fills, unnecessary hops, funding and position drift that are only visible after
the fact. Every agent framework optimises for the *next* signal; none make the *previous*
fill's true cost **enforceable before the next action is allowed**.

**Why people would use it.**
- An agent cannot open new risk until the last fill has a verified Autopsy.
- Commitments and Autopsies are on-chain and comparable across Elysium AMM and HyperCore.
- Specialists can sell route challenges/research against a commitment, paid when correct.
- Custody stays with the user — RouteClerk constrains the agent's ability to act, never funds.
- Native to the only chain with co-located HyperCore data.

## 3. Product Demo

**Applicable — yes.** The core mechanic is demonstrable today, end to end, with **zero
dependencies** (Python 3.10+ stdlib only).

**The 90-second demo:** [`demo/routeclerk-demo.mp4`](demo/routeclerk-demo.mp4)
Every figure is a replay of a real
`python main.py demo` run.

**What currently works**
- **Agent loop** — Scout proposes a route and expected cost across a mock HyperCore book +
  Elysium AMM; Skeptic adversarially re-prices and returns APPROVE / IMPROVE / KILL.
- **Commitment** — canonical-hashed, with a 5,000 ms deadline.
- **Fill + Autopsy** — realized cost vs mid, fees, deviation, PASS/FAIL.
- **The gate** — a failed Autopsy blocks the agent; its next intent is refused until `ack`
  (or `--cover`). Persisted across runs.
- **`RouteClerkGate.sol`** — compiles clean (solc 0.8.24) to `build/…{bin,abi}`.
- **Landing page** — single self-contained `site/index.html`, no build step, deployed.



## 4. Current Status + Launch Plan

**Working**
- Agent loop, gate state machine, canonical-hashed commitments, Autopsies (Python, stdlib only).
- `RouteClerkGate.sol` — commitment store, `canAct(agent)` / `act(agent)`, Autopsy grading,
  `acknowledgeAutopsy` / `coverDeviation`. Compiles clean.
- Deploy runbook for Elysium testnet (chain id **99801**) in `scripts/deploy.md`.
- Landing page live at https://routeclerk.vercel.app.

**In development**
- Deploy `RouteClerkGate` to Elysium testnet; wire `canAct()` into the `ElysiumCoreWriter`
  order path.
- `ElysiumCoreWriter` callback handling (fill outcome → Autopsy trigger).
- `RouteClerkAdapter` to source realized cost + funding/position drift from the HyperCore
  market-data precompile once live (until then the Clerk files these; gate logic is identical).
- Deviation bonding + specialist challenge market (`coverDeviation` hook already present).
- Dashboard for commitments, Autopsies and agent economics.

**Before launch**
- Security review of the gating and bonding contracts.
- Testnet deploy on simulated data → switch to the real precompile when available.
- At least one design-partner integration with a trading / market-making agent.
- Docs + a minimal SDK so other builders can attach their agents.

**Timeline & milestones**
- **Now (Oct 2026):** full local prototype + compiled contract + landing page + demo video. ✅
- **Late Oct – Nov 2026:** testnet MVP — `RouteClerkGate` on 99801, `canAct` wired to a
  simulated CoreWriter path, callback → Autopsy loop.
- **Post `ElysiumCoreWriter` / precompile:** swap simulated data for live precompile;
  design-partner agent integrated.
- **Aligned with early Elysium + Ascend activity:** mainnet-ready gate + bonding.

**Token plans.** None required for the core product — we'd rather ship the infrastructure
first. Open to Ascend's view on whether a coordination token or fee-sharing model adds value
later.

**Support needed from Ascend**
- Feedback on positioning vs other agent / trading infrastructure on Elysium.
- Introductions to early Elysium traders and market makers as design partners.
- Launch sequencing so RouteClerk is available when the first agents use `ElysiumCoreWriter`.
- Audit or tooling support if selected.

## 5. After Launch

- Expand Autopsy coverage to **full position and funding drift** across Elysium + HyperCore.
- **Specialist marketplace** — agents sell route challenges/research, paid on-chain when correct.
- **Sleep-mode and hard kill-switch mandates** — reduce-only while the user is offline.
- **SDK** so launchpads, vaults and market-making systems can require a RouteClerk Autopsy
  before their agents act.

The long-term goal is **shared infrastructure**: other builders pay for verified cost
attribution and constrained agent execution instead of rebuilding it.

## 6. Team

- **Team members:**  Delight Bernard (RerunJago)
- **Team size:** 1
-

### Appendix — Why this is stronger

- Tightly coupled to Elysium's actual differentiator (HyperCore data precompile + the
  ~100–200 ms write path via trade-only agents) — not generic "agents on a chain".
- The core mechanic is simple and enforceable: **commitment → fill → autopsy → next action
  allowed or blocked**.
- Not a trading bot — it is the layer that makes other agents accountable on a high-frequency chain.
- Custody stays with the user; RouteClerk only gates intents.
- Clear path from testnet MVP (simulated data) to production once the ArbOS / precompile upgrade lands.
- Fits Ascend's criteria: product clarity, Elysium/Hyperliquid fit, a realistic roadmap, and the
  potential to become shared infrastructure rather than a single application.
