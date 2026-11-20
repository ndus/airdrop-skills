#!/usr/bin/env python3

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class HTTPOnlyRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme.lower() not in ("http", "https"):
            raise HTTPError(newurl, code, "Unsupported redirect scheme", headers, fp)
        redirected = super().redirect_request(
            req, fp, code, msg, headers, newurl
        )
        if redirected is not None and redirected.get_method() != "GET":
            raise HTTPError(newurl, code, "Only GET is permitted", headers, fp)
        return redirected


def display(value):
    return "" if value is None else str(value)


def parse_deadline(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        value = value.strip()
        if value.endswith(("Z", "z")):
            value = value[:-1] + "+00:00"
        deadline = datetime.fromisoformat(value)
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        return deadline.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def result_found(opener, source, wallet):
    if not isinstance(source, str) or not source.startswith(
        ("http://", "https://")
    ):
        return False

    try:
        request = Request(
            source,
            headers={"User-Agent": "Mozilla/5.0 (compatible; GTDWatch/1.0)"},
            method="GET",
        )
        with opener.open(request, timeout=20) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read()
            try:
                text = body.decode(charset, errors="replace")
            except (LookupError, UnicodeError):
                text = body.decode("utf-8", errors="replace")

        text = text.casefold()
        address = wallet.strip() if isinstance(wallet, str) else ""
        handle = os.environ.get("GTD_HANDLE", "").casefold()
        return (bool(handle) and handle in text) or bool(
            address and address.casefold() in text
        )
    except Exception:
        return False


def atomic_write(path, registry):
    directory = os.path.dirname(os.path.abspath(path))
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=".gtd-registry-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = temporary.name
            json.dump(registry, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass


def main():
    default_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "registry.json"
    )
    path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get("GTD_REGISTRY") or default_path
    )

    try:
        with open(path, "r", encoding="utf-8") as registry_file:
            registry = json.load(registry_file)
        if not isinstance(registry, list):
            raise ValueError("Registry must be a list")
    except FileNotFoundError:
        registry = []
    except (OSError, ValueError, UnicodeError, RecursionError):
        print("ERROR: cannot read registry", file=sys.stderr)
        return 1

    opener = build_opener(HTTPOnlyRedirectHandler())
    attention = []
    changed = False

    for entry in registry:
        if not isinstance(entry, dict) or entry.get("status") != "pending":
            continue

        project = display(entry.get("project"))
        chain = display(entry.get("chain"))
        wallet = display(entry.get("wallet"))
        raw_deadline = entry.get("mint_deadline")
        deadline_text = display(raw_deadline)
        deadline = parse_deadline(raw_deadline)
        now = datetime.now(timezone.utc)

        if deadline is not None:
            if deadline < now:
                entry["status"] = "expired"
                changed = True
                attention.append(
                    "⌛ EXPIRED {} — mint deadline {} passed with no "
                    "confirmed result".format(project, deadline_text)
                )
            elif deadline - now <= timedelta(hours=24):
                attention.append(
                    "⏰ DEADLINE {} — mint deadline {} ({}, wallet {})".format(
                        project, deadline_text, chain, wallet
                    )
                )

        source = entry.get("result_source")
        if result_found(opener, source, entry.get("wallet")):
            entry["status"] = "won"
            changed = True
            attention.append(
                "🎉 GTD WON {} — wallet found in results ({}). "
                "Mint deadline: {}".format(project, source, deadline_text)
            )

    if changed:
        try:
            atomic_write(path, registry)
        except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
            print("ERROR: cannot write registry", file=sys.stderr)
            return 1

    if attention:
        print("GTD WATCH — attention needed:")
        for line in attention:
            print(line)
    else:
        print("NO_NEWS")

    return 0


if __name__ == "__main__":
    sys.exit(main())
