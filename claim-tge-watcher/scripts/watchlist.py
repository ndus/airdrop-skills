#!/usr/bin/env python3
"""Manage claim and TGE deadlines.

Usage:
    watchlist.py [--file PATH] add --project P --what W --deadline D --where U --source S
    watchlist.py [--file PATH] list [--all]
    watchlist.py [--file PATH] due [--today YYYY-MM-DD]
    watchlist.py [--file PATH] mark --id N --status open|claimed|done|missed
"""

import argparse
import json
import os
import sys
import datetime


STATUSES = ("open", "claimed", "done", "missed")


def nonempty(value):
    if not value.strip():
        raise argparse.ArgumentTypeError("must not be empty")
    return value


def parse_date(value):
    try:
        parsed = datetime.date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError("invalid date {!r}; expected YYYY-MM-DD".format(value))
    if parsed.isoformat() != value:
        raise ValueError("invalid date {!r}; expected YYYY-MM-DD".format(value))
    return parsed


def deadline_date(value):
    if not isinstance(value, str) or not value:
        raise ValueError("deadline must be a nonempty ISO date or datetime")
    if len(value) == 10:
        return parse_date(value)
    if len(value) <= 10 or value[10] not in ("T", "t", " "):
        raise ValueError("invalid ISO deadline {!r}".format(value))
    parse_date(value[:10])
    try:
        return datetime.datetime.fromisoformat(value).date()
    except ValueError:
        raise ValueError("invalid ISO deadline {!r}".format(value))


def load_watchlist(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {"entries": []}

    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise ValueError("watchlist must be an object containing an entries list")

    seen_ids = set()
    for entry in data["entries"]:
        if not isinstance(entry, dict):
            raise ValueError("each watchlist entry must be an object")
        entry_id = entry.get("id")
        if type(entry_id) is not int or entry_id < 1:
            raise ValueError("each entry must have a positive integer id")
        if entry_id in seen_ids:
            raise ValueError("duplicate entry id #{}".format(entry_id))
        seen_ids.add(entry_id)
        for field in ("project", "what", "deadline", "where", "wallet",
                      "source", "status", "added_at"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    "entry #{} has missing or empty {}".format(entry_id, field)
                )
        if entry["status"] not in STATUSES:
            raise ValueError("entry #{} has an invalid status".format(entry_id))
        if type(entry.get("fcfs")) is not bool:
            raise ValueError("entry #{} must have a boolean fcfs".format(entry_id))
        deadline_date(entry["deadline"])
        parse_date(entry["added_at"])

    return data


def save_watchlist(path, data):
    path = os.path.abspath(path)
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)

    counter = 0
    while True:
        temporary = "{}.{}.{}.tmp".format(path, os.getpid(), counter)
        try:
            descriptor = os.open(
                temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
            break
        except FileExistsError:
            counter += 1

    try:
        try:
            handle = os.fdopen(descriptor, "w", encoding="utf-8")
        except BaseException:
            os.close(descriptor)
            raise
        with handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "watchlist.json"
        ),
        help="watchlist JSON path (place before the subcommand)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="add a sourced deadline")
    for name in ("project", "what", "deadline", "where", "source"):
        add.add_argument("--" + name, required=True, type=nonempty)
    add.add_argument("--wallet", default="burner", type=nonempty)
    add.add_argument("--fcfs", action="store_true")

    listing = commands.add_parser("list", help="list deadlines")
    listing.add_argument("--all", action="store_true")

    due = commands.add_parser("due", help="report deadlines needing attention")
    due.add_argument("--today", metavar="YYYY-MM-DD")

    mark = commands.add_parser("mark", help="change an entry's status")
    mark.add_argument("--id", type=int, required=True)
    mark.add_argument("--status", choices=STATUSES, required=True)
    return parser


def run(args):
    today = datetime.date.today()
    if args.command == "due" and args.today is not None:
        today = parse_date(args.today)
    if args.command == "add":
        deadline_date(args.deadline)

    data = load_watchlist(args.file)
    entries = data["entries"]

    if args.command == "add":
        entry_id = max((entry["id"] for entry in entries), default=0) + 1
        entry = {
            "id": entry_id,
            "project": args.project,
            "what": args.what,
            "deadline": args.deadline,
            "where": args.where,
            "wallet": args.wallet,
            "source": args.source,
            "fcfs": args.fcfs,
            "status": "open",
            "added_at": today.isoformat(),
        }
        entries.append(entry)
        save_watchlist(args.file, data)
        print("added #{id}: {project} — {what} @ {deadline}".format(**entry))

    elif args.command == "list":
        for entry in sorted(entries, key=lambda item: deadline_date(item["deadline"])):
            if not args.all and entry["status"] != "open":
                continue
            days = (deadline_date(entry["deadline"]) - today).days
            print(
                "#{id} [{status}] {deadline} ({days} left) "
                "{project} — {what} | claim: {where} | wallet: {wallet} "
                "| src: {source}".format(days=days, **entry)
            )

    elif args.command == "due":
        reported = False
        for entry in sorted(entries, key=lambda item: deadline_date(item["deadline"])):
            if entry["status"] != "open":
                continue
            days = (deadline_date(entry["deadline"]) - today).days
            if days < 0:
                tag = "OVERDUE"
            elif days in (3, 1, 0):
                tag = "T-{}".format(days)
            elif entry["fcfs"] and 0 <= days <= 7:
                tag = "FCFS-SOON"
            else:
                continue
            print(
                "{tag} #{id} {project} — {what} @ {deadline} "
                "| claim: {where} | wallet: {wallet}".format(tag=tag, **entry)
            )
            reported = True
        if not reported:
            print("NOTHING DUE")

    elif args.command == "mark":
        for entry in entries:
            if entry["id"] == args.id:
                entry["status"] = args.status
                save_watchlist(args.file, data)
                print("marked #{} -> {}".format(args.id, args.status))
                return
        raise ValueError("unknown id #{}".format(args.id))


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        run(args)
    except (OSError, ValueError, TypeError, OverflowError, RecursionError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
