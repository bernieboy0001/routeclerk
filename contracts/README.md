# RouteClerkGate

On-chain accountability gate for agents trading on **Elysium** and **HyperCore**.

```
Route Commitment  ->  Fill  ->  Autopsy  ->  Act or Blocked
```

An agent must commit to a route and its expected all-in cost **before** it may
act. After the fill lands (via `ElysiumCoreWriter`), the **Clerk** files an
**Autopsy** grading realized cost against the commitment. A deviation beyond the
threshold sets `openAutopsy[agent]`, and the agent's next action reverts until it
is acknowledged or the deviation is covered with a bond.

Custody is untouched — the contract only gates the agent's ability to open new
risk; it never holds or moves trading funds.

## Files

| File | Purpose |
| --- | --- |
| `RouteClerkGate.sol` | Commitment store, `canAct` gate, Autopsy grading, unblock (ack / cover) |
| `../scripts/deploy.md` | Deploy to Elysium testnet (chain id `99801`) |

## API at a glance

- `submitCommitment(id, routeHash, expectedCostBps, sizeUsd, deadline)` — agent commits before acting.
- `canAct(agent) -> bool` / `act(agent)` — the single check the order path makes before dispatching via `ElysiumCoreWriter`.
- `submitAutopsy(id, commitmentId, realizedCostBps, fundingDriftBps, thresholdBps)` — Clerk grades the fill; blocks on breach.
- `acknowledgeAutopsy(id)` / `coverDeviation(id)` (payable) — reopen the gate.
- Views: `commitments(id)`, `autopsies(id)`, `openAutopsy(agent)`.

## Compile (no toolchain needed)

```powershell
npx --yes solc@0.8.24 --base-path . --optimize --bin --abi contracts/RouteClerkGate.sol -o build
```

Produces `build/contracts_RouteClerkGate_sol_RouteClerkGate.{bin,abi}`.

## Design notes

- Commitments are keyed by a `keccak256` digest computed off-chain by the Clerk: `(agent, intent, route, expected cost, deadline)`. The Python prototype uses `sha256` over the same canonical JSON (stdlib has no keccak) — structure identical, only the hash function differs.
- `act()` is a `view` in the MVP so an integrating contract can call it inline before the `ElysiumCoreWriter` send. In production it gates the send itself.
- Autopsy inputs (realized cost, funding/position drift) come from a `RouteClerkAdapter` that reads Elysium's **HyperCore market-data precompile** once live (~4 weeks after mainnet). Until then the Clerk operator files them; the gate logic is unchanged.
- `coverDeviation` accepts a bond that a specialist challenge market can later claim — post-launch roadmap, not in the MVP.
