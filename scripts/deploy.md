# Deploying RouteClerkGate to Elysium testnet

Elysium testnet chain id: **99801** (mainnet-ready once the `ElysiumCoreWriter`
upgrade lands). You need an RPC endpoint and a funded testnet key — take the RPC
URL and explorer from the official Elysium docs (it is not hardcoded here).

## 1. Compile

```powershell
npx --yes solc@0.8.24 --base-path . --optimize --bin --abi contracts/RouteClerkGate.sol -o build
```

## 2. Deploy with Foundry (`forge`)

```bash
export RPC_URL="$ELYSIUM_TESTNET_RPC"
export PRIVATE_KEY=0x...            # funded testnet key
export CLERK=0x...                  # RouteClerk Clerk signer (files Autopsies)

forge create contracts/RouteClerkGate.sol:RouteClerkGate \
  --rpc-url "$RPC_URL" \
  --private-key "$PRIVATE_KEY" \
  --constructor-args "$CLERK" \
  --chain 99801
```

## 3. Or deploy raw bytecode with `cast`

```bash
BYTECODE=$(cat build/contracts_RouteClerkGate_sol_RouteClerkGate.bin)
CLERK=0x...
# constructor arg: address padded to 32 bytes
ARGS=$(cast abi-encode "constructor(address)" "$CLERK" | sed 's/^0x//')

cast send --rpc-url "$RPC_URL" --private-key "$PRIVATE_KEY" \
  --create "0x${BYTECODE}${ARGS}"
```

## 4. Smoke test

```bash
GATE=0x<deployed address>

# agent is clear
cast call "$GATE" "canAct(address)(bool)" 0xAgent...

# clerk files a failing autopsy -> agent blocked
cast send "$GATE" "submitAutopsy(bytes32,bytes32,int256,int256,int256)" \
  0xAA.. 0xBB.. 12 0 2 --rpc-url "$RPC_URL" --private-key "$CLERK_KEY"

cast call "$GATE" "canAct(address)(bool)" 0xAgent...   # -> false

# acknowledge -> clear again
cast send "$GATE" "acknowledgeAutopsy(bytes32)" 0xAA.. \
  --rpc-url "$RPC_URL" --private-key "$CLERK_KEY"
```

Paste the deployed address + explorer link into the top-level `README.md` when
done.
