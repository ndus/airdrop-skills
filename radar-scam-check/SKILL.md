---
name: radar-scam-check
description: Vet airdrop posts with read-only radar scripts (Telegram fetch, heuristic scam check, GARAP scoring) before queueing any task. A block verdict means never queue the item.
---

# Radar Scam Check

Read-only vetting scripts audited clean: no wallet code, no signing, no sends — the only network calls are GET https://t.me (public channel previews) and GET https://rdap.org (domain age).

Scripts live in this skill's `scripts/` folder:

- `fetch_tg.py` — fetch recent posts from public Telegram channels via t.me/s previews.
- `scam_check.py` — heuristic scam screen. BLOCKS on: seed-phrase / private-key requests, "claim-airdrop / validate / rectify / sync-wallet / restore / recover" flows, lookalike domains, and similar drainer patterns.
- `score.py` — scores a vetted item: **>=70 GARAP**, **50-69 GARAP SANTAI**, **<50 SKIP**.
- `radar_state.py` — dedupe state so the same item is not re-queued within 14 days.

## Rules

- Run `scam_check.py` on every candidate item BEFORE it enters the task queue. A block verdict is final: never queue it, never open its links in the wallet browser.
- Scores inform priority only. The owner still approves tasks (`approve <ID> <CODE>`); a high score is not permission to execute.
- These scripts complement the airdrop-agent package's built-in radar; when the two disagree, take the stricter verdict.
- Never modify the block patterns to make an item pass.
