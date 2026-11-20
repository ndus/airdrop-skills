---
name: sepolia-mining
description: Daily Sepolia testnet activity routine for the burner wallet — small varied swaps and transfers under a hard 0.1 ETH/day cap, run by a scheduled script, flat by end of day.
---

# Sepolia Mining

## What this is

A daily activity routine ("mining") on **Ethereum Sepolia testnet only** for the burner identity. It keeps the burner wallet active with a small set of human-paced, varied on-chain actions — Uniswap V3 swaps (ETH ↔ USDC), an occasional WETH wrap/unwrap, an occasional self-transfer — and always ends the day flat. The owner set the budget: **at most 0.1 Sepolia ETH of value moved per day**, enforced in code, not by judgment.

## Identity and hard limits

- Identity: identitas burner kamu di airdrop-agent, EVM wallet `0xALAMAT_BURNER_EVM_KAMU` — the ONLY wallet this routine may ever use. Never the owner's main wallets, never any other identity.
- Chain: Sepolia, chain ID 11155111. Testnet only — no mainnet actions of any kind, ever.
- Hard cap: **0.1 ETH/day cumulative value moved**, tracked in the script's daily ledger (`~/.hermes/scripts/sepolia_mining_ledger.json`, resets daily Asia/Jakarta). Value counted: ETH→USDC swap inputs + USDC→ETH swap outputs (at quote) + WETH wrap deposits + self-transfer amounts. Approvals and unwraps count 0. The script refuses to send any action that would push the day's total over the cap.
- Per-transaction value never exceeds 0.02 ETH in the script (the `aa` policy engine's own Sepolia caps — 0.05/tx, 0.4/day — remain as a second backstop).
- Mode safe and the kill switch (`~/.airdrop-agent/KILL`) are respected: if the kill switch file exists or the chain ID is wrong, the routine stops and reports instead of sending.
- Run the `drain-guard` pre-flight before treating any new target as in-scope. The routine's targets are fixed (below); anything outside that list is out of scope for this skill.

## Fixed targets (drain-guard pre-flight record)

Verified 2026-11-20 against official sources and live on-chain probes:

| Contract | Address | Source |
|---|---|---|
| Uniswap V3 Factory | `0x0227628f3F023bb0B980b67D528571c95c6DaC1c` | developers.uniswap.org Ethereum deployments |
| Uniswap V3 SwapRouter02 | `0x3bFA4769FB09eefC5a80d6E87c3B9C650f7Ae48E` | developers.uniswap.org Ethereum deployments |
| Uniswap V3 QuoterV2 | `0xEd1f6473345F45b75F8179591dd5bA1888cf2FB3` | Uniswap docs; live quote probe OK |
| WETH9 (Sepolia) | `0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14` | developers.uniswap.org (wrapped native token table) |
| USDC (Sepolia) | `0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238` | developers.circle.com USDC contract addresses |

Live check at install time: WETH/USDC pools exist at fee tiers 500/3000/10000 with liquidity; 0.01 ETH quoted ≈ 283 USDC (0.05% pool). The script re-quotes at runtime and picks the better of the 500/3000 tiers; if no pool quotes, the round is skipped, never forced.

Approvals: exact-amount only, only to SwapRouter02, only when the current allowance is insufficient. `setApprovalForAll` and unlimited approvals are forbidden and do not exist in the script.

## How it runs

- Script: `~/.hermes/scripts/sepolia_mining.py` (a copy also lives in this skill's `scripts/` folder; the cron runs the `~/.hermes/scripts/` copy).
- Schedule: Hermes cron job **"sepolia mining harian"**, daily at 11:40 Asia/Jakarta, `--no-agent` mode — the script's stdout is the report delivered to the owner, mirroring other auto-claim jobs.
- All sends go through `~/.hermes/scripts/aa_tx.py` → `aa wallet send`, so the `aa` policy engine, safe-mode gates, and the owner's blanket delegation apply exactly as for other scripted actions. The script holds no keys and signs nothing itself.
- Manual dry-run (sends nothing, writes nothing): `python3 ~/.hermes/scripts/sepolia_mining.py --dry-run` — prints balance, live quotes, and the day's planned actions.

## Daily flow (what the script does)

1. Pre-flight: kill switch, chain ID, balances.
2. Faucet step: if Sepolia ETH < 0.5, one `aa testnet claim --chain sepolia` attempt. Every Sepolia faucet in `faucets.yaml` needs a human step (login / mainnet balance / browser PoW) — if the balance is still under 0.15 ETH afterwards, the routine reports that and stops for the day. Never use captcha-solving services, never spam faucets.
3. Two swap rounds with randomized small amounts (0.004–0.012 ETH in, unique per run), natural pauses of 40–160 seconds between transactions, optional wrap and self-transfer mixed in for variety. Planned total ≤ 0.07 ETH so the exit legs always fit under the hard cap.
4. Exit: sell the full USDC balance back, unwrap any WETH — end flat, verified by final balance reads.
5. Report: date, ETH balance before → after, one line per transaction, total moved vs the 0.1 cap, flat status, and any skips/failures. Failures are reported, never retried blindly.

## Hard prohibitions

- No mainnet, no other chains, no other wallets or identities.
- No new contracts, tokens, or protocols under this skill — new targets need their own drain-guard pre-flight and owner-approved task first.
- No unlimited approvals, no `setApprovalForAll`, no Permit/Permit2/Seaport signatures.
- Never raise the cap, the per-tx limit, or the amounts in the script on your own — budget changes are the owner's decision.
- Do not run the live routine manually outside its schedule unless the owner asks; a dry-run is always safe.
