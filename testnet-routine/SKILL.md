---
name: testnet-routine
description: Run safe, human-paced testnet faucet and swap routines with the burner identity, respecting owner approvals, policy gates, and drain-guard checks.
---

# Testnet Routine

## Identity and safety
- Operate on your own PC using the airdrop-agent v4 CLI `aa`.
- Use safe mode and your burner identity exclusively.
- Use testnet/faucet funds only; never access the owner's main wallets.
- Follow the `aa` policy engine and every approval gate; never bypass a denial.
- Use documented `aa` commands; consult CLI help rather than inventing syntax.
- Run the `drain-guard` skill's mandatory pre-flight before every on-chain action.
- If pre-flight fails, is unavailable, or leaves uncertainty, stop and report.
- Verify the active identity, testnet chain ID, destination, and proposed action before signing.

## Scope and eligibility
- Work only on projects approved in the owner's task queue or explicitly named by the owner.
- Before starting, verify through official project sources that the testnet is live and the project is pre-TGE.
- If either condition is unclear or false, skip the project and report why.
- Approval of a project does not authorize extra wallets, mainnet activity, or unrelated tasks.

## Faucet catalog
- Base Sepolia: use the chain's official faucet or the approved project's own faucet page.
- Arbitrum Sepolia: use the chain's official faucet or the approved project's own faucet page.
- BSC Testnet: use the chain's official faucet or the approved project's own faucet page.
- Polygon Amoy: use the chain's official faucet or the approved project's own faucet page.
- Resolve faucet pages through official sources; do not trust unsolicited links.
- Check existing balances and request only the funds needed for the planned routine.
- Respect cooldowns and published limits; never spam, rotate identities, or bypass restrictions.
- If no eligible faucet is available, skip funding and report the blocker.

## Swap/trade session
1. Read the approved task; define actions, budget, and whether holding is explicitly required.
2. Check balances and liquidity; reserve enough testnet gas to exit positions.
3. Use small, varied amounts, for example 0.0012–0.0026 ETH where suitable.
4. Never repeat an input amount within the session; use appropriately small equivalents on other chains.
5. Leave non-uniform, human-paced pauses between transactions; confirm each result before continuing.
6. After buying, sell back a varied 55–85% per coin when the approved task permits.
7. End flat or near-flat unless the task explicitly says to hold; a final exit may close the remainder.
8. Keep total net cost, including fees and realized losses, at or below approximately 0.02 ETH equivalent in testnet funds.
9. Track the budget after each action; stop opening positions before the exit reserve is threatened.
- If a meaningful ETH-equivalent estimate is unavailable, skip trades and report the uncertainty.
- Do not blindly retry failed or pending transactions; inspect their status first.

## Hard prohibitions
- No mainnet actions ever, including funding, bridging, approvals, signatures, or trades.
- No wash trading or repeated buy/sell loops in your own coins.
- No second or linked wallets to fake activity.
- No crowd farming or referral farming.
- No coin launches unless an approved task explicitly requires one.
- For an authorized launch, write an original description; never copy-paste another coin's description.
- Never use timing or amount variation to evade policy, faucet limits, or project rules.

## Session report
- Record project, chain, actions, transaction hashes, net cost, and points/result in the task report to the owner.
- Include ending balances/positions, skipped actions, blockers, and pending transactions.
- Report points only when verified; otherwise mark them unknown or pending.
