#!/usr/bin/env python3

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile


def reject_json_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def load_registry(path):
    try:
        with path.open("r", encoding="utf-8") as registry:
            entries = json.load(registry, parse_constant=reject_json_constant)
    except FileNotFoundError:
        return []

    if not isinstance(entries, list) or any(
        not isinstance(entry, dict) for entry in entries
    ):
        raise ValueError("registry must contain a JSON list of objects")

    return entries


def write_registry(path, entries):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".gtd-registry-",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump(entries, temp_file, indent=2, allow_nan=False)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())

        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="Append one GTD NFT registration to the registry."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--chain", required=True)
    parser.add_argument("--wallet", required=True)
    parser.add_argument("--register-url", default="")
    parser.add_argument("--result-source", default="")
    parser.add_argument("--mint-deadline", default=None, metavar="ISO8601")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    override = os.environ.get("GTD_REGISTRY")
    if override is None:
        registry_path = Path(__file__).resolve().with_name("registry.json")
    else:
        registry_path = Path(override)

    try:
        entries = load_registry(registry_path)

        if any(
            entry.get("project") == args.project
            and entry.get("wallet") == args.wallet
            and entry.get("status") == "pending"
            for entry in entries
        ):
            print("DUPLICATE: already tracked")
            return 2

        entries.append(
            {
                "project": args.project,
                "chain": args.chain,
                "wallet": args.wallet,
                "register_url": args.register_url,
                "result_source": args.result_source,
                "mint_deadline": args.mint_deadline,
                "submitted_at": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "status": "pending",
                "notes": args.notes,
            }
        )
        write_registry(registry_path, entries)
    except (OSError, ValueError, RecursionError) as error:
        print(f"ERROR: {registry_path}: {error}", file=sys.stderr)
        return 1

    print(
        f"ADDED {args.project} ({args.chain}) wallet {args.wallet} "
        f"deadline {args.mint_deadline or '-'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
