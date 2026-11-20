import sys
import json
import math
import urllib.request
import urllib.error
from datetime import datetime, timezone

SOURCES = ("Bybit", "Binance", "OKX")
DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
UA = "Mozilla/5.0 (compatible; market-snapshot/1.0)"
TIMEOUT = 15


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize(rows, source):
    candles = []
    for row in rows:
        if source == "Bybit":
            if len(row) < 6:
                continue
            values = row[0:6]
        elif source == "Binance":
            if len(row) < 6:
                continue
            values = row[0:6]
        else:
            if len(row) < 6:
                continue
            values = row[0:6]

        try:
            candles.append((
                float(values[0]),
                float(values[1]),
                float(values[2]),
                float(values[3]),
                float(values[4]),
                float(values[5]),
            ))
        except (TypeError, ValueError):
            continue

    if source in ("Bybit", "OKX"):
        candles.reverse()

    if len(candles) < 60:
        raise ValueError("insufficient candle data")
    return candles[-200:]


def fetch_klines(symbol, source):
    if source == "Bybit":
        url = (
            "https://api.bybit.com/v5/market/kline"
            "?category=linear&symbol=%s&interval=60&limit=200" % symbol
        )
        data = fetch_json(url)
        if data.get("retCode") not in (None, 0):
            raise ValueError("Bybit error")
        rows = data.get("result", {}).get("list", [])
    elif source == "Binance":
        url = (
            "https://api.binance.com/api/v3/klines"
            "?symbol=%s&interval=1h&limit=200" % symbol
        )
        rows = fetch_json(url)
        if not isinstance(rows, list):
            raise ValueError("Binance error")
    else:
        inst_id = symbol[:-4] + "-USDT"
        url = (
            "https://www.okx.com/api/v5/market/candles"
            "?instId=%s&bar=1H&limit=200" % inst_id
        )
        data = fetch_json(url)
        if data.get("code") not in (None, "0", 0):
            raise ValueError("OKX error")
        rows = data.get("data", [])

    return normalize(rows, source)


def ema(values, period):
    if len(values) < period:
        return float("nan")
    result = sum(values[:period]) / period
    multiplier = 2.0 / (period + 1)
    for value in values[period:]:
        result = (value - result) * multiplier + result
    return result


def rsi_wilder(closes, period=14):
    if len(closes) <= period:
        return float("nan")
    gains = []
    losses = []
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))


def atr_wilder(candles, period=14):
    if len(candles) <= period:
        return float("nan")
    true_ranges = []
    for i in range(1, len(candles)):
        _, high, low, _, _, _ = candles[i]
        previous_close = candles[i - 1][4]
        true_ranges.append(max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close),
        ))

    atr = sum(true_ranges[:period]) / period
    for value in true_ranges[period:]:
        atr = (atr * (period - 1) + value) / period
    return atr


def fmt(value, digits=2):
    return "nan" if not math.isfinite(value) else ("%.*f" % (digits, value))


def snapshot(symbol):
    candles = None
    source_used = None
    for source in SOURCES:
        try:
            candles = fetch_klines(symbol, source)
            source_used = source
            break
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue

    if candles is None:
        return None, None

    closes = [c[4] for c in candles]
    current = closes[-1]
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)
    rsi = rsi_wilder(closes, 14)
    atr = atr_wilder(candles, 14)

    change_24h = ((current / closes[-25]) - 1.0) * 100.0
    window = candles[-49:-1]
    resistance = max(c[2] for c in window)
    support = min(c[3] for c in window)
    support_distance = ((current - support) / current) * 100.0
    resistance_distance = ((resistance - current) / current) * 100.0
    atr_percent = (atr / current) * 100.0

    if current > ema21 > ema50:
        trend = "BULL"
    elif current < ema21 < ema50:
        trend = "BEAR"
    else:
        trend = "RANGE"

    if rsi > 70:
        rsi_note = "RSI overbought"
    elif rsi < 30:
        rsi_note = "RSI oversold"
    else:
        rsi_note = "RSI neutral"

    ema_note = "price above EMA9" if current > ema9 else "price below EMA9"
    momentum = "%s; %s" % (rsi_note, ema_note)

    lines = [
        "== %s ==" % symbol,
        "last: %s" % fmt(current),
        "24h_change: %s%%" % fmt(change_24h),
        "EMA9: %s" % fmt(ema9),
        "EMA21: %s" % fmt(ema21),
        "EMA50: %s" % fmt(ema50),
        "RSI14: %s" % fmt(rsi),
        "ATR14: %s (%s%%)" % (fmt(atr), fmt(atr_percent)),
        "resistance: %s (distance %s%%)" % (fmt(resistance), fmt(resistance_distance)),
        "support: %s (distance %s%%)" % (fmt(support), fmt(support_distance)),
        "trend: %s" % trend,
        "momentum: %s" % momentum,
    ]
    return lines, source_used


def main():
    symbols = sys.argv[1:] or list(DEFAULT_SYMBOLS)
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    output = ["SNAPSHOT %s source=per-symbol fallback" % timestamp]
    failed = 0

    for symbol in symbols:
        lines, _ = snapshot(symbol.upper())
        if lines is None:
            output.extend(["== %s ==" % symbol.upper(), "ERROR: all sources failed"])
            failed += 1
        else:
            output.extend(lines)

    print("\n".join(output))
    return 1 if failed == len(symbols) else 0


if __name__ == "__main__":
    sys.exit(main())
