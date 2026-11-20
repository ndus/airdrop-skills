---
name: claim-tge-watcher
description: Track claim windows, TGE dates, and other hard deadlines for projects Hermes works, and report them to the owner before they close — never let a deadline slip by silently.
---

# Claim / TGE Watcher

The owner has lost real money to missed deadlines (free-trial drops were missed repeatedly). This skill exists so that never happens again: every claim window, TGE, unlock, snapshot, or mint/claim deadline for a project you are actively working gets recorded once, watched daily, and reported to the owner at T-3 days, T-1 day, and on the day — earlier for FCFS or short windows.

## Watchlist and helper

- Watchlist data: `scripts/watchlist.json` in this skill folder (starts empty).
- Helper: `python3 scripts/watchlist.py` run from this skill folder. Subcommands:
  - `add --project P --what W --deadline YYYY-MM-DD --where URL --source S [--wallet burner|owner] [--fcfs]`
  - `list` (open entries, sorted by deadline) / `list --all`
  - `due` — prints only entries needing a report today (tags: T-3, T-1, T-0, OVERDUE, FCFS-SOON), or `NOTHING DUE`
  - `mark --id N --status claimed|done|missed|open`
- Entry format is documented in `watchlist.example.json`. The helper refuses an `add` without `--source`; that refusal is by design (see below).

## Recording deadlines — the extraction rule

- Whenever a concrete date or window appears in anything you process — a radar item, a project page or docs, an approved task, a quest page, or a message from the owner — and it is a claim window, TGE, unlock, snapshot, registration close, or claim-by date for a project in your queue or already being worked, add it to the watchlist immediately, in the same session, before moving on.
- `--source` must name where you saw it: the project page URL, the radar item/post reference, or "owner message <date>". If you cannot name the source, you did not see a deadline — do not add it.
- NEVER invent, guess, or round a deadline. Vague timing ("soon", "Q4", "after mainnet") is NOT a deadline: do not add it. Instead mention it once in your task report as an unrecorded vague date so the owner knows it exists.
- `--wallet`: use `burner` only when the claim is executable by you (testnet/burner rules below). Use `owner` when claiming needs the owner (main wallet, mainnet, his signature, his accounts, KYC). This label decides who acts — get it right.
- Add `--fcfs` for first-come-first-served or otherwise short windows (a day or less, limited slots, or first-N claims): these are reported as soon as they are recorded and again via FCFS-SOON, not just at T-3.

## Daily check and reporting

- Once a day, as part of your daily rhythm (e.g. when preparing the daily report), run `due` from this skill folder.
- Report every printed line to the owner via your normal Telegram reporting channel, in plain language: what it is, when it closes (date + WIB), where to claim, and who must act.
  - `burner` entries you can execute yourself: say you will handle it (or that you already did — see below).
  - `owner` entries: mark the report clearly as an action for the owner, with the exact step he must take. Repeat at T-1 and T-0 until he confirms or the entry is marked done — do not assume a T-3 report was seen.
- OVERDUE entries: report once as missed/late, then `mark` them `missed` if the window has truly closed, or leave open with a note in your report if a grace period is documented in the source.
- If `due` prints `NOTHING DUE`, say nothing about this skill that day. No empty reports.

## Executing a claim yourself

- You may execute a due claim only when ALL of these hold: the entry's wallet is `burner`; the project is already approved/worked by you; the claim is on a testnet or uses faucet/test funds only; and the `drain-guard` skill's pre-flight passes for the exact transaction.
- After executing, report the result (with tx hash) and `mark` the entry `claimed`.
- If any condition fails — mainnet, main wallet, owner's signature or accounts, drain-guard stop, unclear claim contract — do NOT execute. Report it as an owner action instead, at the earliest report point (T-3, or immediately for FCFS).
- Never let an executable claim expire because you waited for permission you already have under these rules; equally, never stretch these rules to execute something outside them.

## Housekeeping

- When a claim is completed (by you or confirmed by the owner), mark it `claimed` or `done` the same day so it stops generating reports.
- Do not delete entries; status history is the audit trail.
- This skill tracks deadlines only. GTD whitelist registrations for NFT mints are tracked by the `gtd-watch` skill, not here; radar vetting stays with `radar-scam-check`; on-chain execution rules stay with `drain-guard` and `testnet-routine`.
