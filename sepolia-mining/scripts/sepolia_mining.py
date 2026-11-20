#!/usr/bin/env python3
"""
Daily Sepolia activity for an unattended Hermes agent.

Hard limit: 0.1 ETH per Asia/Jakarta calendar day. Counted value comprises
buy inputs, sell outputs valued at their quote, wrap deposits, and self-
transfers. Approvals and unwraps count zero. Gas is outside this value cap.

Drain-guard facts: chain 11155111, Sepolia testnet only; signer identity
is a burner. Contract addresses and official reference sources:
Factory: 0x0227628f3F023bb0B980b67D528571c95c6DaC1c
Router:  0x3bFA4769FB09eefC5a80d6E87c3B9C650f7Ae48E
Quoter:  0xEd1f6473345F45b75F8179591dd5bA1888cf2FB3
WETH:    0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14
Source: https://docs.uniswap.org/contracts/v3/reference/deployments/ethereum-deployments
USDC:    0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238
Source: https://developers.circle.com/stablecoins/usdc-contract-addresses

All sends go through aa_tx.py, so the aa policy engine and gates apply.
No signing material is loaded by this script.
"""

import json
import os
import random
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo


CHAIN = "sepolia"
CHAIN_ID = 11155111
RPC = "https://ethereum-sepolia-rpc.publicnode.com"
WALLET = "0xALAMAT_BURNER_EVM_KAMU"  # ganti dengan alamat burner kamu
IDENTITY = "id-burner-kamu"  # ganti dengan id identitas burner kamu
AA_TX = os.path.expanduser("~/.hermes/scripts/aa_tx.py")
KILL_FILE = os.path.expanduser("~/.airdrop-agent/KILL")
LEDGER_PATH = os.environ.get(
    "SEPOLIA_MINING_LEDGER",
    os.path.expanduser("~/.hermes/scripts/sepolia_mining_ledger.json"),
)

DAILY_CAP_ETH = 0.1
PER_TX_MAX_ETH = 0.02
PLANNED_BUDGET_ETH = 0.07

FACTORY = "0x0227628f3F023bb0B980b67D528571c95c6DaC1c"
SWAP_ROUTER = "0x3bFA4769FB09eefC5a80d6E87c3B9C650f7Ae48E"
QUOTER = "0xEd1f6473345F45b75F8179591dd5bA1888cf2FB3"
WETH = "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14"
USDC = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
USDC_DECIMALS = 6
FEE_TIERS = (500, 3000)

GET_POOL = "0x1698ee82"
POOL_LIQUIDITY = "0x1a686502"
QUOTE_EXACT_INPUT_SINGLE = "0xc6a5026a"
EXACT_INPUT_SINGLE = "0x04e45aaf"
APPROVE = "0x095ea7b3"
ALLOWANCE = "0xdd62ed3e"
BALANCE_OF = "0x70a08231"
WETH_DEPOSIT = "0xd0e30db0"
WETH_WITHDRAW = "0x2e1a7d4d"

WEI = 10**18
CAP_WEI = round(DAILY_CAP_ETH * WEI)
PER_TX_WEI = round(PER_TX_MAX_ETH * WEI)
BUDGET_WEI = round(PLANNED_BUDGET_ETH * WEI)
TZ = ZoneInfo("Asia/Jakarta")

ledger = None
dry_run = False


def today():
    return datetime.now(TZ).date().isoformat()


def fmt_units(value, decimals, places=None):
    value = int(value)
    sign = "-" if value < 0 else ""
    value = abs(value)
    whole, fraction = divmod(value, 10**decimals)
    digits = str(fraction).zfill(decimals)
    if places is not None:
        digits = digits[:places]
    digits = digits.rstrip("0")
    return sign + str(whole) + ("." + digits if digits else "")


def fmt_eth(wei):
    return fmt_units(wei, 18, 6)


def word_uint(value):
    if not isinstance(value, int) or not 0 <= value < 2**256:
        raise ValueError("Nilai ABI uint tidak valid")
    return format(value, "064x")


def word_address(address):
    raw = address.removeprefix("0x")
    if len(raw) != 40:
        raise ValueError("Alamat ABI tidak valid")
    int(raw, 16)
    return raw.lower().zfill(64)


def first_uint(data):
    if not isinstance(data, str) or not data.startswith("0x"):
        raise ValueError("Respons ABI tidak valid")
    raw = data[2:]
    if len(raw) < 64:
        raise ValueError("Respons ABI terlalu pendek")
    return int(raw[:64], 16)


def rpc(method, params):
    last_error = None
    for attempt in range(3):
        try:
            payload = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params,
            }).encode("utf-8")
            request = urllib.request.Request(
                RPC, data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=25) as response:
                result = json.load(response)
            if result.get("error"):
                raise RuntimeError(str(result["error"]))
            if "result" not in result:
                raise RuntimeError("RPC tidak mengembalikan hasil")
            return result["result"]
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError(f"RPC {method} gagal: {last_error}")


def eth_call(to, data):
    return rpc("eth_call", [{"from": WALLET, "to": to, "data": data}, "latest"])


def eth_balance():
    return int(rpc("eth_getBalance", [WALLET, "latest"]), 16)


def token_balance(token):
    return first_uint(eth_call(token, BALANCE_OF + word_address(WALLET)))


def allowance(token, owner=WALLET, spender=SWAP_ROUTER):
    return first_uint(eth_call(
        token, ALLOWANCE + word_address(owner) + word_address(spender)
    ))


def best_quote(token_in, token_out, amount_in):
    best = None
    for fee in FEE_TIERS:
        try:
            pool_result = first_uint(eth_call(
                FACTORY,
                GET_POOL + word_address(token_in)
                + word_address(token_out) + word_uint(fee),
            ))
            if not pool_result or pool_result >= 2**160:
                continue
            pool = "0x" + format(pool_result, "040x")
            if first_uint(eth_call(pool, POOL_LIQUIDITY)) <= 0:
                continue
            data = (
                QUOTE_EXACT_INPUT_SINGLE
                + word_address(token_in)
                + word_address(token_out)
                + word_uint(amount_in)
                + word_uint(fee)
                + word_uint(0)
            )
            amount_out = first_uint(eth_call(QUOTER, data))
            if amount_out > 0 and (best is None or amount_out > best["out"]):
                best = {"fee": fee, "out": amount_out}
        except Exception:
            continue
    return best


def swap_data(token_in, token_out, fee, amount_in, minimum):
    return (
        EXACT_INPUT_SINGLE
        + word_uint(0x20)
        + word_address(token_in)
        + word_address(token_out)
        + word_uint(fee)
        + word_address(WALLET)
        + word_uint(amount_in)
        + word_uint(minimum)
        + word_uint(0)
    )


def load_ledger():
    global ledger
    try:
        with open(LEDGER_PATH, encoding="utf-8") as handle:
            stored = json.load(handle)
    except FileNotFoundError:
        stored = {}
    if not isinstance(stored, dict):
        raise ValueError("Ledger rusak; transaksi dihentikan")
    if stored.get("date") != today():
        ledger = {"date": today(), "moved_eth": 0.0, "txs": []}
        return ledger
    moved = stored.get("moved_eth")
    if (
        isinstance(moved, bool)
        or not isinstance(moved, (int, float))
        or not 0 <= moved <= float("inf")
        or moved == float("inf")
        or not isinstance(stored.get("txs"), list)
    ):
        raise ValueError("Ledger tidak valid; transaksi dihentikan")
    ledger = stored
    return ledger


def save_ledger():
    if dry_run:
        raise RuntimeError("Penulisan ledger dilarang saat dry-run")
    parent = os.path.dirname(os.path.abspath(LEDGER_PATH))
    os.makedirs(parent, exist_ok=True)
    temporary = f"{LEDGER_PATH}.tmp.{os.getpid()}"
    try:
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(ledger, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, LEDGER_PATH)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def moved_wei():
    return round(ledger["moved_eth"] * WEI)


def can_afford(eth_value):
    return ledger["moved_eth"] + eth_value <= DAILY_CAP_ETH + 1e-12


def record(kind, eth_value, tx):
    ledger["moved_eth"] = (moved_wei() + round(eth_value * WEI)) / WEI
    ledger["txs"].append({
        "ts": datetime.now(TZ).isoformat(),
        "kind": kind,
        "eth_value": eth_value,
        "tx": tx,
    })
    save_ledger()


def send(to, amount_eth_str, data_hex):
    try:
        completed = subprocess.run(
            [sys.executable, AA_TX, CHAIN, to, amount_eth_str, data_hex],
            capture_output=True, text=True, timeout=500, check=False,
        )
        res = json.loads(completed.stdout)
        if not isinstance(res, dict):
            return False, "Respons aa_tx bukan objek JSON"
        if not res.get("ok"):
            return False, str(res.get("error") or res.get("data") or "aa_tx gagal")
        data = res.get("data") or {}
        tx = data.get("tx")
        proof = data.get("proof")
        if isinstance(proof, str) and os.path.isfile(proof):
            try:
                with open(proof, encoding="utf-8") as handle:
                    proof_data = json.load(handle)
                tx = proof_data.get("tx") or tx
            except Exception:
                pass
        return True, str(tx or "")
    except subprocess.TimeoutExpired:
        return False, "UNKNOWN: aa_tx timeout; status pengiriman belum diketahui"
    except Exception as exc:
        return False, f"UNKNOWN: respons aa_tx gagal dibaca: {exc}"


def make_plan():
    used = set()
    buys = []
    while len(buys) < 2:
        amount = round(round(random.uniform(0.004, 0.012), 5) * WEI)
        if amount not in used:
            used.add(amount)
            buys.append(amount)

    wrap = (
        round(round(random.uniform(0.003, 0.008), 6) * WEI)
        if random.random() < 0.5 else 0
    )
    transfer = (
        round(round(random.uniform(0.001, 0.004), 6) * WEI)
        if random.random() < 0.4 else 0
    )

    def total():
        return sum(amount + amount * 995 // 1000 for amount in buys) + wrap + transfer

    if total() > BUDGET_WEI:
        transfer = 0
    if total() > BUDGET_WEI:
        wrap = 0
    while total() > BUDGET_WEI:
        excess = total() - BUDGET_WEI
        index = 0 if buys[0] >= buys[1] else 1
        reduction = max(10**13, ((excess + 1) // 2 // 10**13 + 1) * 10**13)
        buys[index] = max(10**13, buys[index] - reduction)
        if buys[0] == buys[1]:
            buys[index] -= 10**13

    plan = [("buy", buys[0])]
    if transfer:
        plan.append(("self-transfer", transfer))
    plan.append(("sell", 0))
    if wrap:
        plan.append(("wrap", wrap))
    plan.extend([("buy", buys[1]), ("sell", 0), ("unwrap", 0)])
    return plan, total()


def short_tx(tx):
    return tx if len(tx) <= 12 else tx[:12] + "…"


class Runner:
    def __init__(self):
        self.notes = []
        self.executed = []
        self.sent = False
        self.halted = False
        self.round_open = False

    def do_action(self, kind, eth_value, to, amount_str, data):
        if self.halted:
            return False
        if os.path.exists(KILL_FILE):
            self.notes.append("Sepolia mining berhenti: kill switch aktif.")
            self.halted = True
            return False
        if ledger["date"] != today():
            self.notes.append("Tanggal berganti; pengiriman dihentikan.")
            self.halted = True
            return False
        if eth_value > PER_TX_WEI:
            self.notes.append(f"PERINGATAN: {kind} dilewati, melebihi 0.02 ETH/tx.")
            return False
        if (
            not can_afford(eth_value / WEI)
            or moved_wei() + eth_value > CAP_WEI
        ):
            prefix = "PERINGATAN KERAS" if kind.startswith(("sell", "unwrap")) else "Catatan"
            self.notes.append(f"{prefix}: {kind} dilewati, batas harian tidak cukup.")
            return False
        if self.sent:
            time.sleep(random.uniform(40, 160))
        if os.path.exists(KILL_FILE):
            self.notes.append("Sepolia mining berhenti: kill switch aktif.")
            self.halted = True
            return False

        self.sent = True
        ok, result = send(to, amount_str, data)
        if not ok:
            self.notes.append(f"{kind} gagal: {result}")
            if result.startswith("UNKNOWN:"):
                # Reserve uncertain value; do not risk sending it a second time.
                record("uncertain-" + kind, eth_value / WEI, result)
                self.halted = True
            return False

        record(kind, eth_value / WEI, result)
        self.executed.append(
            f"{kind} {fmt_eth(eth_value)} ETH | tx {short_tx(result) or 'tidak tersedia'}"
        )
        if not result.startswith("0x") or len(result) != 66:
            self.notes.append("Hash transaksi tidak tersedia; pengiriman lanjutan dihentikan.")
            self.halted = True
            return True

        # Resolve inclusion before reading balances for dependent actions.
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            receipt = rpc("eth_getTransactionReceipt", [result])
            if receipt is not None:
                if int(receipt.get("status", "0x0"), 16) != 1:
                    self.notes.append(f"{kind}: transaksi revert; nilai tetap dicadangkan.")
                    return False
                return True
            time.sleep(5)
        self.notes.append(f"{kind}: konfirmasi tertunda; pengiriman lanjutan dihentikan.")
        self.halted = True
        return True

    def buy(self, amount):
        quote = best_quote(WETH, USDC, amount)
        if quote is None:
            self.notes.append("buy dilewati: tidak ada pool likuid dengan quote.")
            return False
        return self.do_action(
            "buy", amount, SWAP_ROUTER, fmt_eth(amount),
            swap_data(WETH, USDC, quote["fee"], amount, quote["out"] * 97 // 100),
        )

    def sell(self, kind="sell", final=False):
        if self.halted:
            return False
        amount = token_balance(USDC)
        if amount < 10000 or (final and amount <= 10000):
            self.notes.append(f"{kind} dilewati: saldo USDC di bawah ambang.")
            return False
        quote = best_quote(USDC, WETH, amount)
        if quote is None:
            self.notes.append(f"{kind} dilewati: quote tidak tersedia.")
            return False
        if quote["out"] > PER_TX_WEI or moved_wei() + quote["out"] > CAP_WEI:
            self.notes.append(f"PERINGATAN KERAS: {kind} tidak muat dalam batas nilai.")
            return False
        if allowance(USDC) < amount:
            if not self.do_action(
                "approve", 0, USDC, "0",
                APPROVE + word_address(SWAP_ROUTER) + word_uint(amount),
            ):
                return False
            # Refresh the quote after approval and its confirmation.
            quote = best_quote(USDC, WETH, amount)
            if quote is None:
                self.notes.append(f"{kind} dilewati: quote terbaru tidak tersedia.")
                return False
        return self.do_action(
            kind, quote["out"], SWAP_ROUTER, "0",
            swap_data(USDC, WETH, quote["fee"], amount, quote["out"] * 97 // 100),
        )

    def unwrap(self):
        if self.halted:
            return False
        amount = token_balance(WETH)
        if amount <= 0:
            return False
        return self.do_action(
            "unwrap", 0, WETH, "0", WETH_WITHDRAW + word_uint(amount)
        )


def print_dry_plan(plan, total, usdc_before, weth_before):
    print(f"⛏️ Sepolia mining — {today()}")
    print(f"Rencana nilai: {fmt_eth(total)} / {PLANNED_BUDGET_ETH} ETH")
    pending_usdc = usdc_before
    estimated_weth = weth_before
    for kind, amount in plan:
        if kind == "buy":
            quote = best_quote(WETH, USDC, amount)
            if quote:
                pending_usdc += quote["out"]
                print(
                    f"buy {fmt_eth(amount)} ETH → "
                    f"~{fmt_units(quote['out'], USDC_DECIMALS)} USDC "
                    f"| fee {quote['fee']}"
                )
            else:
                print(f"buy {fmt_eth(amount)} ETH | dilewati: quote tidak tersedia")
        elif kind == "sell":
            quote = best_quote(USDC, WETH, pending_usdc) if pending_usdc >= 10000 else None
            if quote:
                print(
                    f"sell semua ~{fmt_units(pending_usdc, USDC_DECIMALS)} USDC → "
                    f"~{fmt_eth(quote['out'])} ETH | fee {quote['fee']}"
                )
                estimated_weth += quote["out"]
                pending_usdc = 0
            else:
                print("sell semua USDC | quote tidak tersedia atau saldo terlalu kecil")
        elif kind == "wrap":
            estimated_weth += amount
            print(f"wrap {fmt_eth(amount)} ETH")
        elif kind == "unwrap":
            print(f"unwrap seluruh WETH, perkiraan {fmt_eth(estimated_weth)} WETH")
        else:
            print(f"{kind} {fmt_eth(amount)} ETH")
    print("sell-final semua sisa USDC > 0.01; unwrap semua sisa WETH jika ada.")
    print("DRY-RUN: tidak ada transaksi dikirim.")


def main():
    global dry_run
    dry_run = "--dry-run" in sys.argv[1:]
    lock_path = LEDGER_PATH + ".lock"
    locked = False
    try:
        if os.path.exists(KILL_FILE):
            print("Sepolia mining berhenti: kill switch aktif.")
            return 0
        if int(rpc("eth_chainId", []), 16) != CHAIN_ID:
            print("Sepolia mining berhenti: chain ID bukan 11155111.")
            return 0

        if not dry_run:
            os.makedirs(os.path.dirname(os.path.abspath(LEDGER_PATH)), exist_ok=True)
            try:
                descriptor = os.open(
                    lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
                )
            except FileExistsError:
                print("Sepolia mining berhenti: ledger terkunci oleh proses lain.")
                return 0
            locked = True
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(str(os.getpid()))

        before = eth_balance()
        usdc_before = token_balance(USDC)
        weth_before = token_balance(WETH)
        load_ledger()
        notes = []

        if not dry_run and before < round(0.5 * WEI):
            try:
                subprocess.run(
                    ["aa", "testnet", "claim", "--chain", "sepolia",
                     "--identity", IDENTITY],
                    capture_output=True, text=True, timeout=180, check=False,
                )
                notes.append("Faucet Sepolia: percobaan klaim selesai.")
            except Exception:
                notes.append("Faucet Sepolia: percobaan klaim gagal atau timeout.")
            current = eth_balance()
            if current < round(0.15 * WEI):
                print(f"⛏️ Sepolia mining — {today()}")
                print(f"Saldo ETH: {fmt_eth(before)} → {fmt_eth(current)}")
                print(
                    "Saldo terlalu rendah (< 0.15 ETH). Semua faucet Sepolia "
                    "di faucets.yaml memerlukan langkah manusia "
                    "(login / mainnet balance / browser PoW). Tidak ada transaksi dikirim."
                )
                return 0

        random.seed(time.time_ns())
        plan, total = make_plan()
        if dry_run:
            print_dry_plan(plan, total, usdc_before, weth_before)
            return 0

        runner = Runner()
        runner.notes.extend(notes)
        # Cleanup first: close any position left over from an interrupted
        # previous run before opening new rounds.
        if usdc_before > 10000:
            runner.sell("sell-final", final=True)
        if token_balance(WETH) > 0:
            runner.unwrap()
        for kind, amount in plan:
            if runner.halted:
                break
            if kind == "buy":
                runner.round_open = runner.buy(amount)
            elif kind == "sell":
                if runner.round_open:
                    runner.sell()
                else:
                    runner.notes.append("sell ronde dilewati: buy tidak berhasil.")
                runner.round_open = False
            elif kind == "wrap":
                runner.do_action("wrap", amount, WETH, fmt_eth(amount), WETH_DEPOSIT)
            elif kind == "self-transfer":
                runner.do_action(kind, amount, WALLET, fmt_eth(amount), "0x")
            elif kind == "unwrap":
                runner.unwrap()

        remaining_usdc = token_balance(USDC)
        remaining_weth = token_balance(WETH)
        if remaining_usdc > 10000:
            runner.sell("sell-final", final=True)
        if remaining_weth > 0 or remaining_usdc > 10000:
            runner.unwrap()

        after = eth_balance()
        remaining_usdc = token_balance(USDC)
        remaining_weth = token_balance(WETH)

        print(f"⛏️ Sepolia mining — {ledger['date']}")
        print(f"Saldo ETH: {fmt_eth(before)} → {fmt_eth(after)}")
        for line in runner.executed:
            print(line)
        print(
            f"Total digerakkan: {fmt_eth(moved_wei())} / 0.1 ETH "
            f"({len(ledger['txs'])} tx)"
        )
        if remaining_usdc == 0 and remaining_weth == 0:
            print("Posisi akhir: flat ✓")
        else:
            print(
                f"Posisi akhir: sisa USDC "
                f"{fmt_units(remaining_usdc, USDC_DECIMALS)} / WETH "
                f"{fmt_units(remaining_weth, 18)} (tidak flat)"
            )
        for note in runner.notes:
            print(note)
        return 0
    except Exception as exc:
        print(f"Sepolia mining error: {exc}")
        return 0
    finally:
        if locked:
            try:
                os.unlink(lock_path)
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(main())
