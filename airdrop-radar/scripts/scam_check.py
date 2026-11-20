"""Periksa sinyal penipuan pada URL dan teks."""

import argparse
import json
import re
from difflib import SequenceMatcher
from urllib.parse import unquote_plus, urlsplit


OFFICIAL = {
    "metamask": "metamask.io", "rabby": "rabby.io", "phantom": "phantom.com",
    "uniswap": "uniswap.org", "opensea": "opensea.io", "binance": "binance.com",
    "arbitrum": "arbitrum.io", "optimism": "optimism.io", "zksync": "zksync.io",
    "linea": "linea.build", "scroll": "scroll.io", "layerzero": "layerzero.network",
    "eigenlayer": "eigenlayer.xyz", "hyperliquid": "hyperliquid.xyz",
    "monad": "monad.xyz", "jupiter": "jup.ag", "telegram": "telegram.org t.me",
    "discord": "discord.com discord.gg", "galxe": "galxe.com galxe.xyz",
}
RISKY_TLDS = set("top click cfd sbs buzz rest monster icu cyou lol quest beauty hair bond zip mov".split())
URL_PATTERN = re.compile(r'https?://[^\s<>"\x27]+', re.I)
PATH_PATTERN = re.compile(r"\b(?:claim-airdrop|validate|rectify|sync-wallet|restore|recover|migration|seed|phrase)\b", re.I)
TEXT_RULES = [
    ("block", "permintaan seed phrase atau private key",
     r"\b(?:enter|provide|submit|share|send|reply|type|input|paste|give|masukkan|kirim|berikan|isi|balas|butuh|requires?)\b[^.!?;]{0,60}\b(?:seed phrase|private key)\b"),
    ("block", "validasi atau sinkronisasi wallet",
     r"\b(?:validate|sync|rectify)\s+(?:(?:your|the)\s+)?wallet\b"),
    ("block", "diminta kirim dana untuk imbalan",
     r"\b(?:kirim|send)\b[^.!?;]{1,160}?\b(?:untuk\s+(?:dapat\w*|dobel|bonus)|(?:to|for)\s+(?:get|receive|double|earn|the\s+airdrop|a\s+reward))\b"),
    ("block", "diminta bayar untuk membuka klaim",
     r"\b(?:bayar\w*|pay)\b[^.!?;]{0,45}\b(?:fee|gas|biaya)\b[^.!?;]{0,45}\b(?:unlock|claim|klaim|buka)\b"),
    ("warn", "tekanan waktu",
     r"\b(?:urgent|last chance|only\s+\d+\s+minutes?\s+left|segera|terakhir|limited time)\b"),
    ("warn", "admin atau support mengajak DM",
     r"\b(?:admin|support)\b[^.!?;]{0,50}\b(?:dm|direct message)\b|\b(?:dm|direct message)\b[^.!?;]{0,35}\b(?:admin|support)\b"),
    ("warn", "klaim meminta connect wallet",
     r"\b(?:claim|klaim)\b.{0,100}\bconnect\s+(?:your\s+)?wallet\b|\bconnect\s+(?:your\s+)?wallet\b.{0,100}\b(?:claim|klaim)\b"),
]
AMOUNT_DOT = re.compile(r"(?<=\d)\.(?=\d)")


def split_url(url):
    try:
        return urlsplit(url if "://" in url or url.startswith("//") else "//" + url)
    except ValueError:
        return urlsplit("")


def root_domain(host):
    """Perkirakan domain induk, termasuk akhiran umum seperti co.uk."""
    labels = host.rstrip(".").lower().split(".")
    size = 3 if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in {
        "ac", "co", "com", "edu", "gov", "net", "org",
    } else 2
    return ".".join(labels[-size:])


def matches_domain(host, domain):
    return host == domain or host.endswith("." + domain)


def scam_check(url="", text="", official=""):
    findings = {}
    official_host = split_url(official).hostname if official else None

    def flag(level, reason):
        if level == "block" or reason not in findings:
            findings[reason] = level

    chunks = [URL_PATTERN.sub(" ", text)]
    urls = ([url] if url else []) + URL_PATTERN.findall(text)
    for candidate in urls:
        parsed = split_url(candidate.rstrip(".,;!)]}"))
        host = (parsed.hostname or "").lower().rstrip(".")
        labels = host.split(".")
        root = root_domain(host)
        names = set(labels[:-1])
        if len(labels) > 1:
            names.add(root.split(".")[0])
        if any(label.startswith("xn--") for label in labels):
            flag("warn", "domain punycode")
        if labels[-1] in RISKY_TLDS:
            flag("warn", "TLD berisiko")

        for brand, domains in OFFICIAL.items():
            refs = domains.split()
            if official_host and any(matches_domain(official_host, ref) for ref in refs):
                refs.append(official_host)
            if any(matches_domain(host, ref) for ref in refs):
                continue
            keys = {brand, *(ref.split(".")[0] for ref in domains.split() if len(ref.split(".")[0]) >= 3)}
            if any(SequenceMatcher(None, name, key).ratio() > 0.8
                   for name in names for key in keys):
                flag("block", "domain lookalike")
                break
        if official_host and not matches_domain(host, official_host):
            key = root_domain(official_host).split(".")[0]
            if len(key) >= 3 and any(SequenceMatcher(None, name, key).ratio() > 0.8 for name in names):
                flag("block", "domain lookalike")

        path = unquote_plus(parsed.path)
        path = re.sub(r"[_–]", "-", path)
        if PATH_PATTERN.search(path):
            level = "block" if re.search(r"\bwallet\b", path, re.I) else "warn"
            flag(level, "pola path URL mencurigakan")
        for component in (path, unquote_plus(parsed.query)):
            chunks.append(re.sub(r"[-_/=&]+", " ", component))

    for chunk in chunks:
        chunk = AMOUNT_DOT.sub(",", chunk)
        for level, reason, pattern in TEXT_RULES:
            if re.search(pattern, chunk, re.I | re.S):
                flag(level, reason)
    verdict = "block" if "block" in findings.values() else "warn" if findings else "ok"
    return {"verdict": verdict, "reasons": list(findings)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="")
    parser.add_argument("--text", default="")
    args = parser.parse_args()
    if not (args.url or args.text):
        parser.error("sertakan --url atau --text")
    print(json.dumps(scam_check(args.url, args.text), ensure_ascii=False))


if __name__ == "__main__":
    main()
