# RouteClerk — Elysium / Ascend Builder Submission

_Locked: 2026-10-16. This is the canonical submission text._

## 🔗 1. Project + Links

- **Project name:** RouteClerk
- **X account:** @RouteClerk
- **Website:** routeclerk.xyz
- **GitHub / Docs:** Available privately on request (core contracts + agent loop in progress)

## 🧭 2. Project Overview

**What we're building.**
RouteClerk is an on-chain accountability layer for agents that trade on Elysium
and HyperCore. Before any order intent is accepted, the agent must commit to a
specific route and expected cost. After the fill, the system generates a signed
**Autopsy** that compares what was promised versus what actually happened. The
next action is blocked until the Autopsy is acknowledged or the agent covers the
deviation.

**Who it's for.**
Traders, market makers, and agent operators who will use Elysium's upcoming
HyperCore market-data precompile and `ElysiumCoreWriter` to place real orders at
100–200 ms latency.

**Problem it solves.**
Once agents can read full HyperCore books and drive orders on a user's own
HyperCore account from Elysium contracts, speed stops being the main constraint.
The new expensive failure is **hidden cost**: worse fills, unnecessary hops,
funding, or position drift that is only visible after the fact. Most agent
frameworks optimize for generating the next signal. None of them make the
previous fill's true cost **enforceable before the next action is allowed**.

**Why people would use it.**
- Agents cannot open new risk until the last fill has a verified Autopsy.
- Route commitments and Autopsies are on-chain and comparable across Elysium AMM and HyperCore.
- Specialists can sell challenges or research against a commitment and get paid if they are right.
- Users keep custody. RouteClerk only constrains the agent's ability to act; it does not control funds.
- Native to the token lifecycle and co-located HyperCore data that only Elysium will have.

## 🚦 3. Current Status + Launch Plan

**Working today**
- Agent loop with Route Commitment and Autopsy generation logic.
- Mandate checks and basic on-chain payment between agents (testnet).
- Integration points mapped to Elysium RPC, upcoming market-data precompile, and `ElysiumCoreWriter` intent flow.
- Architecture for non-custodial constraint (agent cannot withdraw; only order intents are gated).

**In development**
- Coordination contracts that gate order intents on Autopsy status.
- Callback handling for `ElysiumCoreWriter` outcomes.
- Deviation bonding and specialist challenge market.
- Dashboard for commitments, Autopsies, and agent economics.

**Before launch**
- Security review of the gating and bonding contracts.
- Testnet deployment that uses simulated HyperCore data, then switches to the real precompile once available (~4 weeks after mainnet).
- Design partner integration with at least one trading or market-making agent.
- Documentation and a simple SDK for other builders to attach their agents.

**Timeline**
- Testnet MVP with simulated data: late October – November 2026.
- Mainnet-ready (post `ElysiumCoreWriter` upgrade): aligned with early Elysium + Ascend activity.
- **Token plans:** None required for the core product. Prefer to launch the infrastructure first. Open to Ascend's view on whether a coordination token or fee-sharing model adds value later.

**Support needed from Ascend**
- Feedback on positioning relative to other agent and trading infrastructure.
- Introductions to early Elysium traders and market makers as design partners.
- Launch sequencing so RouteClerk can be available when the first agents start using `ElysiumCoreWriter`.
- Audit or tooling support if selected.

## 🚀 4. After Launch

- Expand Autopsy coverage to full position and funding drift across Elysium and HyperCore.
- Specialist marketplace where agents can sell route challenges or research and get paid on-chain if the challenge is correct.
- Sleep-mode and hard kill-switch mandates that only allow reduce-only actions while the user is offline.
- SDK so other projects (launchpads, vaults, market-making systems) can require RouteClerk Autopsies before their agents are allowed to act.

The long-term goal is shared infrastructure: other builders pay for verified cost
attribution and constrained agent execution rather than rebuilding it.

## 👥 5. Team

- Small pseudonymous team (2–3 people).
- Relevant experience building agent systems, on-chain trading infrastructure, and Hyperliquid ecosystem tools.
- Best contact: Discord / X DM.

## ✅ 6. Why this is stronger

- Tightly coupled to Elysium's actual differentiator (HyperCore data precompile + ~100–200 ms write path via trade-only agents) instead of generic "agents on a chain".
- The core mechanic is simple and enforceable: **commitment → fill → Autopsy → next action allowed or blocked**.
- It does not try to be a trading bot. It is the layer that makes other agents accountable on a high-frequency chain.
- Custody stays with the user. RouteClerk only gates intents.
- Clear path from testnet MVP (simulated data) to production once the ArbOS upgrade lands.
- Fits Ascend's criteria: product clarity, Elysium/Hyperliquid fit, realistic roadmap, and potential to become shared infrastructure rather than a single application.
