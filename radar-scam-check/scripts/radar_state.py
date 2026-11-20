"""Simpan dan pangkas riwayat deduplikasi radar."""

import argparse
import fcntl
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile


STORE = Path(__file__).resolve().parents[1] / "data" / "seen.json"


def read_store():
    try:
        with STORE.open(encoding="utf-8") as stream:
            return json.load(stream)
    except FileNotFoundError:
        return {"items": {}}


def write_store(state):
    """Ganti file secara atomik agar pembaca tidak melihat JSON parsial."""
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=STORE.parent, delete=False) as stream:
        temp = Path(stream.name)
        try:
            json.dump(state, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.close()
            os.replace(temp, STORE)
        finally:
            temp.unlink(missing_ok=True)


def digest(key):
    return hashlib.sha1(" ".join(key.lower().split()).encode("utf-8")).hexdigest()


def update(args):
    if args.command == "check":
        return {"seen": digest(args.key) in read_store()["items"]}

    STORE.parent.mkdir(parents=True, exist_ok=True)
    with STORE.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = read_store()
        items = state["items"]
        now = datetime.now(timezone.utc)
        if args.command == "add":
            key = digest(args.key)
            added = key not in items
            if added:
                items[key] = {"first_seen": now.isoformat(), "title": args.title}
                write_store(state)
            return {"added": added}

        cutoff = now - timedelta(days=14)
        len_before = len(items)
        for key, item in list(items.items()):
            date = datetime.fromisoformat(item["first_seen"].replace("Z", "+00:00"))
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            if date < cutoff:
                del items[key]
        removed = len_before - len(items)
        if removed:
            write_store(state)
        return {"removed": removed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check").add_argument("--key", required=True)
    add = commands.add_parser("add")
    add.add_argument("--key", required=True)
    add.add_argument("--title", required=True)
    commands.add_parser("prune")
    try:
        result = update(parser.parse_args())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
