"""Hitung skor awal berdasarkan URL dan isi postingan."""

import argparse
import ipaddress
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import yaml

from scam_check import root_domain, scam_check, split_url


KEYWORDS = Path(__file__).resolve().parents[1] / "config" / "keywords.yaml"
SIGNALS = [
    (r"testnet", 10, "testnet"),
    (r"points", 5, "points"),
    (r"incentivized", 5, "incentivized"),
    (r"pre[- ]tge", 5, "pre-TGE"),
    (r"no token yet|token belum", 5, "token belum launch"),
    (r"free|gratis", 5, "gratis"),
]


def domain_age(host):
    """Ambil umur domain dari tanggal registrasi RDAP."""
    try:
        ipaddress.ip_address(host)
        return None
    except ValueError:
        pass
    if not re.fullmatch(r"[\w-]+(?:\.[\w-]+)+", host):
        return None
    try:
        domain = quote(root_domain(host).encode("idna").decode("ascii"), safe="")
        request = Request("https://rdap.org/domain/" + domain, headers={"Accept": "application/rdap+json"})
        with urlopen(request, timeout=10) as response:
            events = json.load(response).get("events", [])
        for event in events:
            if event.get("eventAction") == "registration":
                try:
                    date = datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
                    date = date.replace(tzinfo=date.tzinfo or timezone.utc)
                    days = (datetime.now(timezone.utc) - date).days
                    if days >= 0:
                        return days
                except (ValueError, KeyError, AttributeError):
                    continue
    except (URLError, OSError, ValueError, TypeError, AttributeError):
        pass
    return None


def score_post(url, text="", official=""):
    result = scam_check(url, text, official)
    score = 50
    reasons = list(result["reasons"])
    parsed = split_url(url)
    age = domain_age((parsed.hostname or "").rstrip("."))
    facts = {"domain_age_days": age, "scam_verdict": result["verdict"]}

    def adjust(points, reason):
        nonlocal score
        score += points
        reasons.append(reason)

    if result["verdict"] == "warn":
        score -= min(30, 15 * len(reasons))
    if age is not None:
        if age < 30:
            adjust(-25, "umur domain <30 hari")
        elif age <= 180:
            adjust(-10, "umur domain 30–180 hari")
        elif age > 365:
            adjust(10, "umur domain >365 hari")
    if parsed.scheme == "https":
        adjust(5, "HTTPS")
    elif parsed.scheme == "http":
        adjust(-10, "HTTP")

    for pattern, points, reason in SIGNALS:
        if re.search(r"\b(?:" + pattern + r")\b", text, re.I):
            adjust(points, reason)
    if re.search(r"\b(?:token live|now trading|listed on)\b", text, re.I):
        adjust(-20, "token sudah launch (bukan pre-TGE)")

    if result["verdict"] == "block":
        score = min(score, 10)
    score = max(0, min(score, 100))
    band = "GARAP" if score >= 70 else "GARAP SANTAI" if score >= 50 else "SKIP"
    with KEYWORDS.open(encoding="utf-8") as config:
        platforms = yaml.safe_load(config)["quest_platforms"]
    haystack = text + " " + (parsed.hostname or "")
    if any(re.search(r"\b" + re.escape(platform) + r"\b", haystack, re.I) for platform in platforms):
        band = "SKIP"
        reasons.append("platform quest — di luar aturan user")
    return {"score": score, "band": band, "reasons": reasons, "facts": facts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--text", default="")
    parser.add_argument("--official", default="")
    args = parser.parse_args()
    print(json.dumps(score_post(args.url, args.text, args.official), ensure_ascii=False))


if __name__ == "__main__":
    main()
