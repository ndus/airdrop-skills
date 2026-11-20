#!/usr/bin/env python3
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

TIMEOUT = 15
USER_AGENT = "Mozilla/5.0 (compatible; sentiment-snapshot/1.0)"
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
OKX_SYMBOLS = {
    "BTCUSDT": "BTC-USDT-SWAP",
    "ETHUSDT": "ETH-USDT-SWAP",
    "SOLUSDT": "SOL-USDT-SWAP",
}


def get_json(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_number(value, decimals=2):
    if value is None:
        return "n/a"
    text = f"{value:,.{decimals}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def format_price(value):
    if value is None:
        return "n/a"
    return f"{value:,.1f}"


def format_percent(value, decimals=2, signed=False):
    if value is None:
        return "n/a"
    return f"{value:+.{decimals}f}%" if signed else f"{value:.{decimals}f}%"


def get_fear_greed():
    try:
        payload = get_json("https://api.alternative.me/fng/", {"limit": 2})
        data = payload.get("data", [])
        if not data:
            return None
        current = data[0]
        yesterday = data[1] if len(data) > 1 else None
        value = current.get("value", "n/a")
        classification = current.get("value_classification", "n/a")
        yesterday_value = yesterday.get("value", "n/a") if yesterday else "n/a"
        return f"Fear & Greed: {value} ({classification}), yesterday {yesterday_value}"
    except Exception:
        return None


def fetch_okx(symbol):
    inst_id = OKX_SYMBOLS[symbol]
    funding = get_json(
        "https://www.okx.com/api/v5/public/funding-rate",
        {"instId": inst_id},
    )
    open_interest = get_json(
        "https://www.okx.com/api/v5/public/open-interest",
        {"instType": "SWAP", "instId": inst_id},
    )
    ticker = get_json(
        "https://www.okx.com/api/v5/market/ticker",
        {"instId": inst_id},
    )

    if funding.get("code") != "0" or open_interest.get("code") != "0" or ticker.get("code") != "0":
        raise ValueError("OKX returned an error")

    funding_data = funding.get("data", [])
    oi_data = open_interest.get("data", [])
    ticker_data = ticker.get("data", [])
    if not funding_data or not oi_data or not ticker_data:
        raise ValueError("OKX returned no data")

    rate = parse_float(funding_data[0].get("fundingRate"))
    oi_coin = parse_float(oi_data[0].get("oiCcy"))
    price = parse_float(ticker_data[0].get("last"))
    open24h = parse_float(ticker_data[0].get("open24h"))

    change = None
    if price is not None and open24h not in (None, 0):
        change = (price - open24h) / open24h * 100

    return {
        "funding": rate * 100 if rate is not None else None,
        "oi": oi_coin,
        "price": price,
        "change": change,
    }


def fetch_bybit(symbol):
    payload = get_json(
        "https://api.bybit.com/v5/market/tickers",
        {"category": "linear", "symbol": symbol},
    )
    if payload.get("retCode") != 0:
        raise ValueError("Bybit returned an error")
    rows = payload.get("result", {}).get("list", [])
    if not rows:
        raise ValueError("Bybit returned no data")
    row = rows[0]

    funding = parse_float(row.get("fundingRate"))
    oi = parse_float(row.get("openInterest"))
    price = parse_float(row.get("lastPrice"))
    prev_price = parse_float(row.get("prevPrice24h"))
    change = None
    if price is not None and prev_price not in (None, 0):
        change = (price - prev_price) / prev_price * 100

    return {
        "funding": funding * 100 if funding is not None else None,
        "oi": oi,
        "price": price,
        "change": change,
    }


def fetch_binance(symbol):
    premium = get_json(
        "https://fapi.binance.com/fapi/v1/premiumIndex",
        {"symbol": symbol},
    )
    open_interest = get_json(
        "https://fapi.binance.com/fapi/v1/openInterest",
        {"symbol": symbol},
    )
    ticker = get_json(
        "https://fapi.binance.com/fapi/v1/ticker/24hr",
        {"symbol": symbol},
    )

    funding = parse_float(premium.get("lastFundingRate"))
    oi = parse_float(open_interest.get("openInterest"))
    price = parse_float(ticker.get("lastPrice"))
    change = parse_float(ticker.get("priceChangePercent"))

    return {
        "funding": funding * 100 if funding is not None else None,
        "oi": oi,
        "price": price,
        "change": change,
    }


def fetch_symbol(symbol):
    if symbol in OKX_SYMBOLS:
        try:
            return fetch_okx(symbol)
        except Exception:
            pass

    try:
        return fetch_bybit(symbol)
    except Exception:
        pass

    try:
        return fetch_binance(symbol)
    except Exception:
        return {
            "funding": None,
            "oi": None,
            "price": None,
            "change": None,
        }


def funding_note(funding):
    if funding is None:
        return ""
    if funding > 0.1 or funding < -0.1:
        base = "longs crowded" if funding > 0.05 else "shorts crowded" if funding < -0.05 else "funding neutral"
        return f"{base}; extreme — squeeze risk"
    if funding > 0.05:
        return "longs crowded"
    if funding < -0.05:
        return "shorts crowded"
    return "funding neutral"


def format_funding(funding):
    if funding is None:
        return "n/a"
    return f"{funding:+.4f}%/8h"


def main():
    symbols = [s.upper() for s in sys.argv[1:]] or DEFAULT_SYMBOLS
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    print(f"SENTIMENT {timestamp}")

    fear_greed = get_fear_greed()
    if fear_greed:
        print(fear_greed)
    else:
        print("Fear & Greed: n/a")

    succeeded = False
    for symbol in symbols:
        try:
            metrics = fetch_symbol(symbol)
            if any(value is not None for value in metrics.values()):
                succeeded = True
        except Exception:
            metrics = {"funding": None, "oi": None, "price": None, "change": None}

        funding = metrics["funding"]
        oi = format_number(metrics["oi"], 2)
        price = format_price(metrics["price"])
        change = format_percent(metrics["change"], 2, signed=True)
        note = funding_note(funding)
        funding_text = format_funding(funding)
        if not note:
            note = "funding neutral" if funding is None else ""

        print(
            f"{symbol}: funding {funding_text} ({note}), "
            f"OI {oi} {symbol.replace('USDT', '')}, price {price}, 24h {change}"
        )

    return 0 if fear_greed or succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
