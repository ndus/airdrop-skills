---
name: gtd-watch
description: Track GTD (guaranteed whitelist) NFT registrations made with the burner wallet — record every submission, check deadlines and results once a day, and notify the owner the moment a GTD spot is won.
---

# GTD Watch

GTD = guaranteed whitelist allocation for an NFT mint. Registrations are usually free (gas only at mint time). The owner's strategy: **chase GTD first** — register as early as possible so the allocation is locked; FCFS is only the fallback. This skill is the tracking half: nothing registered may be forgotten, no deadline missed, and a won GTD is reported to the owner immediately.

Scripts live in this skill's `scripts/` folder (the checker is read-only — GET requests only, no wallet/signing code anywhere):

- `add.py` — record a registration right after submitting it.
- `check.py` — one-shot check of the registry; prints attention lines or exactly `NO_NEWS`.
- `registry.json` — YOUR registry (burner entries only). `add.py`/`check.py` use the copy in this folder by default.

## Wallets — burner only, never the owner's main wallets

- EVM burner: `0xALAMAT_BURNER_EVM_KAMU` (identitas burner kamu di airdrop-agent)
- Solana burner: `ALAMAT_BURNER_SOLANA_KAMU`
- NEVER register, link, or submit the owner's main wallets anywhere. If a launch only accepts a main wallet, skip it and mention it in your report.

## Flow

1. **Spot it.** When your radar or work surfaces an NFT launch with an open GTD (guaranteed) registration, treat it as a priority item.
2. **Vet it first.** Run the `radar-scam-check` skill on the item; a block verdict = never register. Then run the `drain-guard` pre-flight before any on-chain or wallet-connecting step. Registration must be free (address submission) or gas-only; if it asks for payment, a deposit, a seed phrase, or an unlimited approval — stop and report.
3. **Register the burner** for the launch's chain, as early as possible. Social tasks (X/Discord) follow the owner's existing account-protection and pacing rules; never risk the accounts for a whitelist.
4. **Record it immediately** after submitting:
   ```
   python3 scripts/add.py --project "<name>" --chain <chain> \
     --wallet <burner address used> \
     --register-url <url> --result-source <URL of the results/winners announcement, or a note where results will appear> \
     --mint-deadline <ISO 8601, e.g. 2026-11-25T12:00:00Z> --notes "<anything relevant>"
   ```
   `mint_deadline` and `result_source` are what make the daily check useful — do not leave them empty if the launch publishes them.
5. **Check ONCE a day** — the deadline is visible on the project's own page, so do NOT poll continuously. In your normal daily rhythm (for example alongside your evening report), run:
   ```
   python3 scripts/check.py
   ```
   - Output `NO_NEWS` → say nothing about GTD that day.
   - A `🎉 GTD WON ...` line → **notify the owner in that same report, prominently**: 🎉 + project + mint deadline + the next step. A won GTD that is not reported the same day is a failure of this skill.
   - A `⏰ DEADLINE ...` line (deadline ≤24h) → include it in the report as a deadline warning.
   - A `⌛ EXPIRED ...` line → mention it briefly; the entry is closed.
6. **Minting** a won GTD follows the normal rules: drain-guard pre-flight, `aa` policy gates, burner funds only, total cost under $1 unless the owner approved more. If the mint needs the owner's own mainnet signature, do not do it — report it as ready-for-owner instead.

## Rules

- One registry entry per registration, recorded the same day it is submitted.
- Never edit `registry.json` statuses by hand to make an item look won; `check.py` updates status from evidence (the wallet/handle appearing on the results page).
- The checker running more than once a day is a defect, not diligence.
