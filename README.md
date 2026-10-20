# RouteClerk

**On-chain accountability for agents that trade on Elysium and HyperCore.**

> Route Commitment → Fill → Autopsy → **Act or Blocked**

An agent must commit to a route and its expected all-in cost **before** it may
act. After the fill, RouteClerk generates a signed **Autopsy** comparing what was
promised against what actually happened. The agent's next action is blocked until
the Autopsy is acknowledged or the deviation is covered.

Custody stays with the user. RouteClerk never holds funds — it only gates the
agent's ability to open new risk.

**Repository:** https://github.com/bernieboy0001/routeclerk · **Live site:** https://routeclerk.vercel.app · **Landing page source:** [`site/index.html`](site/index.html)

---

## The problem

Once agents can read full HyperCore books through Elysium's upcoming
**HyperCore market-data precompile** and drive orders on a user's own HyperCore
account via **ElysiumCoreWriter** at **~100–200 ms** latency, speed stops being
the main constraint. The new expensive failure is **hidden cost**: worse fills,
unnecessary hops, funding, and position drift that are only visible after the
fact.

Most agent frameworks optimize for generating the *next* signal. None of them
make the *previous* fill's true cost **enforceable before the next action is
allowed**.

## The mechanic

```
        ┌──────────────┐   ┌────────┐   ┌───────────┐   ┌────────────────┐
intent  │ Route        │   │ Fill   │   │ Autopsy   │   │ Gate           │
──────▶ │ Commitment   │──▶│ (via   │──▶│ realized  │──▶│ deviation ≤ th │──▶ next intent
        │ route + cost │   │ Writer)│   │ vs commit │   │ ? CLEAR : BLOCK│     allowed
        └──────────────┘   └────────┘   └───────────┘   └────────────────┘
                                                              │ blocked
                                                              ▼
                                                    ack / cover deviation
```

1. **Route Commitment** — the agent locks a route and its expected all-in cost (bps vs mid). Hashed and (optionally) stored on-chain.
2. **Fill** — the order lands through the `ElysiumCoreWriter` path.
3. **Autopsy** — realized cost vs committed cost: entry-vs-mid, fees, funding drift, total deviation, PASS/FAIL.
4. **Gate** — on FAIL the agent is **blocked**; its next intent is refused until acknowledged or covered with a bond.

## Why Elysium-native

- Tightly coupled to Elysium's differentiators — the **HyperCore precompile** and the **~100–200 ms write path** through `ElysiumCoreWriter` — not generic "agents on a chain".
- Commitments and Autopsies are on-chain and comparable across **Elysium AMM** and **HyperCore**.
- The core mechanic is simple and enforceable: commit → fill → autopsy → act or block.

## Repo layout

```
routeclerk/
  main.py                 CLI: demo | run | status | ack
  agents/
    market.py             mock HyperCore book + Elysium AMM repricers
    scout.py              proposes a route + expected cost
    skeptic.py            adversarially re-prices; APPROVE / IMPROVE / KILL
    clerk.py              commitment -> fill sim -> autopsy
    gate.py               block/ack state machine (the enforceable half)
    console.py            tiny ANSI helper
  data/                   mock HyperCore orderbook, Elysium pool, sample intent
  contracts/
    RouteClerkGate.sol    commitment store + canAct gate + autopsy grading
    README.md
  scripts/deploy.md       deploy to Elysium testnet (chain id 99801)
```

## Run the prototype

No dependencies — Python 3.10+ stdlib only.

```bash
cd routeclerk
python main.py demo      # full walkthrough: PASS -> FAIL -> BLOCKED -> ack
```

Single cycle and gate control:

```bash
python main.py run                       # one commitment cycle
python main.py run --slippage-bps 6      # force a breach -> autopsy FAILs
python main.py status                    # show gate state for the agent
python main.py ack --cover               # acknowledge / bond and reopen the gate
```

The demo prints, in order: the **Route Commitment**, the **simulated fill**, the
**Autopsy** (entry vs mid, fees, deviation, pass/fail) and whether the agent is
**allowed to act again**.

## The contract

`contracts/RouteClerkGate.sol` holds the commitment, exposes a single
`canAct(agent)` check the order path calls before `ElysiumCoreWriter` dispatches,
grades the Autopsy, and unblocks on `acknowledgeAutopsy` / `coverDeviation`.

```powershell
npx --yes solc@0.8.24 --base-path . --optimize --bin --abi contracts/RouteClerkGate.sol -o build
```

See `contracts/README.md` and `scripts/deploy.md`. **Testnet address:** _to be
filled after deploy (chain id 99801)._

## Status

**Working today**
- Agent loop with Route Commitment and Autopsy generation logic (Scout → Skeptic → Clerk → Autopsy), stdlib only.
- Gate state machine that refuses a blocked agent's next commitment until `ack`/`--cover`.
- `RouteClerkGate.sol` compiles clean to `build/…{bin,abi}`; deploy runbook for testnet (chain id 99801).
- Integration points mapped to Elysium RPC, the upcoming market-data precompile, and the `ElysiumCoreWriter` intent flow.
- Architecture for non-custodial constraint (agent cannot withdraw; only order intents are gated).

**In development**
- Coordination contracts that gate order intents on Autopsy status.
- Callback handling for `ElysiumCoreWriter` outcomes.
- Deviation bonding and specialist challenge market.
- Dashboard for commitments, Autopsies, and agent economics.

**Before launch**
- Security review of the gating and bonding contracts.
- Testnet deploy using simulated HyperCore data, then switch to the real precompile once available.
- Design-partner integration with at least one trading / market-making agent.
- Documentation and a simple SDK for other builders to attach their agents.

## Roadmap

- Testnet MVP with simulated data: late October – November 2026.
- Mainnet-ready post-`ElysiumCoreWriter` upgrade: aligned with early Elysium + Ascend activity.
- Expand Autopsy coverage to full position and funding drift across Elysium and HyperCore.
- Specialist marketplace: agents sell route challenges / research, paid on-chain when correct.
- Sleep-mode and hard kill-switch mandates (reduce-only while the user is offline).
- SDK so launchpads, vaults, and market-making systems can require RouteClerk Autopsies before their agents act.

The long-term goal is shared infrastructure: other builders pay for verified cost
attribution and constrained agent execution rather than rebuilding it.

## Team

Small pseudonymous team (2–3 people) with experience building agent systems,
on-chain trading infrastructure, and Hyperliquid-ecosystem tools. Contact: X DM.

## Support needed from Ascend

- Feedback on positioning relative to other agent and trading infrastructure.
- Introductions to early Elysium traders and market makers as design partners.
- Launch sequencing so RouteClerk is available when the first agents start using `ElysiumCoreWriter`.
- Audit or tooling support if selected.

## Submission text

The full, locked builder-submission write-up is in [`SUBMISSION.md`](SUBMISSION.md).

## Landing page

![RouteClerk landing page](site/preview.png)

[`site/index.html`](site/index.html) is a single self-contained page that walks
the mechanic and replays the prototype's own figures as an interactive
commitment → fill → autopsy → gate receipt. Open it directly in a browser — no
build step, no server.

It was styled with the [`frontend-design`](https://skills.sh/anthropics/skills)
skill from [skills.sh](https://skills.sh), then reworked with
[`high-end-visual-design`](https://skills.sh/leonxlnx/taste-skill) and
[`web-design-guidelines`](https://skills.sh/vercel-labs/agent-skills) — see
[`skills-lock.json`](skills-lock.json) and `.agents/skills/`. The palette is
semantic: gold for the commitment, teal when a fill is clear, coral when the gate
blocks.

## License

MIT — see [`LICENSE`](LICENSE).
