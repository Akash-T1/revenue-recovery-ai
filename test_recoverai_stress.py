"""
RecoverAI_MVP - Financial Integrity + Stress Test
Run from the project folder:
    python test_recoverai_stress.py

This test is intentionally deterministic and does NOT call the LLM.
It validates the money-moving layer and recovery policy under edge cases.
"""

import importlib
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0
FAILURES = []

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"[FAIL] {name} :: {detail}")

def load_modules():
    try:
        vp = importlib.import_module("virtual_payment")
        bp = importlib.import_module("batch_processor")
        return vp, bp
    except Exception as e:
        print(f"\n[STOP] Could not import project modules: {e}")
        print("Place this file beside virtual_payment.py and batch_processor.py.")
        raise SystemExit(2)

def balance_snapshot(gateway):
    if not hasattr(gateway, "accounts"):
        return None
    return {
        k: float(getattr(v, "balance", 0))
        for k, v in gateway.accounts.items()
    }

def total_money(gateway):
    snap = balance_snapshot(gateway)
    return round(sum(snap.values()), 2) if snap is not None else None

def main():
    vp, bp = load_modules()
    Gateway = getattr(vp, "VirtualPaymentGateway")

    # ---------- direct gateway integrity ----------
    print("\n=== 1. DIRECT PAYMENT INTEGRITY ===")
    g = Gateway()
    g.create_account("TEST", 10000)
    initial_total = total_money(g)

    r = g.execute_payment("TEST", 2000)
    check("Successful payment returns success", r.get("success") is True, str(r))
    check("Customer balance decreases exactly", abs(g.get_balance("TEST") - 8000) < 1e-9,
          f"balance={g.get_balance('TEST')}")
    check("Merchant receives exact amount", abs(g.get_balance("MERCHANT") - 2000) < 1e-9,
          f"merchant={g.get_balance('MERCHANT')}")
    check("Ledger total is conserved after success",
          total_money(g) == initial_total,
          f"before={initial_total}, after={total_money(g)}")

    before = balance_snapshot(g)
    r = g.execute_payment("TEST", 1000, failure_reason="network_error")
    after = balance_snapshot(g)
    check("Failed payment returns failure", r.get("success") is False, str(r))
    check("Failed payment moves NO money", before == after, f"before={before}, after={after}")
    check("Ledger total conserved after failure", total_money(g) == initial_total)

    # ---------- recovery action integrity ----------
    print("\n=== 2. RECOVERY ACTION INTEGRITY ===")
    tx = {
        "transaction_id": "TX-TEST",
        "customer_id": "TEST",
        "amount": 500,
        "status": "failed",
        "failure_reason": "network_error",
        "recovery_attempts": 0,
        "previous_failures": 0,
        "previous_success": 5,
        "subscription_active": True,
    }

    for action in ("REMINDER", "ESCALATE", "STOP"):
        before = balance_snapshot(g)
        try:
            rr = bp.execute_recovery(g, tx, action)
            after = balance_snapshot(g)
            check(f"{action} executes without crash", isinstance(rr, dict), str(rr))
            check(f"{action} recovers zero", float(rr.get("recovered_amount", 0)) == 0,
                  str(rr))
            check(f"{action} moves no money", before == after)
        except Exception as e:
            check(f"{action} executes without crash", False, repr(e))

    # RETRY should recover when funds are available.
    tx2 = dict(tx)
    tx2["amount"] = 500
    before_customer = g.get_balance("TEST")
    before_merchant = g.get_balance("MERCHANT")
    try:
        rr = bp.execute_recovery(g, tx2, "RETRY")
        check("RETRY returns a structured result", isinstance(rr, dict), str(rr))
        if rr.get("recovery_status") == "RECOVERED":
            check("Successful RETRY recovers exact amount",
                  float(rr.get("recovered_amount", 0)) == 500, str(rr))
            check("Successful RETRY decreases customer by exact amount",
                  abs(g.get_balance("TEST") - (before_customer - 500)) < 1e-9)
            check("Successful RETRY increases merchant by exact amount",
                  abs(g.get_balance("MERCHANT") - (before_merchant + 500)) < 1e-9)
        else:
            check("RETRY can recover an affordable payment", False, str(rr))
    except Exception as e:
        check("RETRY executes without crash", False, repr(e))

    # ---------- insufficient funds boundary ----------
    print("\n=== 3. INSUFFICIENT-FUNDS BOUNDARY ===")
    g2 = Gateway()
    g2.create_account("POOR", 100)
    tx3 = dict(tx)
    tx3.update({"customer_id": "POOR", "amount": 1000,
                "failure_reason": "insufficient_funds"})
    before = balance_snapshot(g2)
    try:
        rr = bp.execute_recovery(g2, tx3, "RETRY")
        after = balance_snapshot(g2)
        check("Insufficient-funds retry does not crash", isinstance(rr, dict), str(rr))
        check("Insufficient-funds retry recovers zero",
              float(rr.get("recovered_amount", 0)) == 0, str(rr))
        check("Insufficient-funds retry moves no money", before == after)
        check("Insufficient-funds retry is not marked recovered",
              rr.get("recovery_status") != "RECOVERED", str(rr))
    except Exception as e:
        check("Insufficient-funds retry does not crash", False, repr(e))

    # ---------- bounded-attempt policy ----------
    print("\n=== 4. BOUNDED RECOVERY POLICY ===")
    if hasattr(bp, "process_transaction"):
        for attempts in (0, 1, 2, 3, 4, 10):
            t = dict(tx)
            t["recovery_attempts"] = attempts
            # We cannot safely call the AI here; inspect the policy through
            # the public processor only when an AI decision is not required.
            if attempts >= 3:
                try:
                    result = bp.process_transaction(g2, t)
                    action = str(result.get("recommended_action", "")).upper()
                    check(f"{attempts} attempts blocks further automation",
                          action in {"STOP", "ERROR", ""} or result.get("recovery_status") in
                          {"STOPPED", "NO_PAYMENT_EXECUTED"},
                          f"action={action}, result={result}")
                except Exception as e:
                    check(f"{attempts} attempts does not crash", False, repr(e))
    else:
        check("process_transaction exists for bounded policy test", False)

    # ---------- deterministic stress on gateway ----------
    print("\n=== 5. STRESS: 10,000 MONEY OPERATIONS ===")
    random.seed(42)
    gs = Gateway()
    customers = []
    for i in range(100):
        cid = f"S{i:03d}"
        bal = 5000 + (i % 10) * 1000
        gs.create_account(cid, bal)
        customers.append(cid)

    stress_initial = total_money(gs)
    errors = 0
    successful = 0
    failed = 0

    for i in range(10000):
        cid = random.choice(customers)
        amount = random.choice([1, 49, 99, 499, 999, 1499, 2499, 4999])
        reason = random.choice([
            None, None, None,
            "network_error",
            "authentication_failed",
            "expired_card",
            "payment_limit",
            "bank_declined",
            "insufficient_funds",
        ])
        try:
            result = gs.execute_payment(cid, amount, failure_reason=reason)
            if result.get("success"):
                successful += 1
            else:
                failed += 1
        except Exception:
            errors += 1
            if errors <= 3:
                print("  stress exception:", sys.exc_info()[1])

    snap = balance_snapshot(gs)
    nonnegative = all(v >= -1e-9 for v in snap.values())
    check("10,000 operations complete without exceptions", errors == 0, f"errors={errors}")
    check("No account has negative balance", nonnegative,
          str({k:v for k,v in snap.items() if v < 0}))
    check("Money conservation survives 10,000 operations",
          total_money(gs) == stress_initial,
          f"before={stress_initial}, after={total_money(gs)}")
    check("Stress produced both success and failure paths",
          successful > 0 and failed > 0,
          f"success={successful}, failed={failed}")

    print("\n=== FINAL TEST REPORT ===")
    print(f"PASS: {PASS}")
    print(f"FAIL: {FAIL}")
    print(f"TOTAL: {PASS + FAIL}")

    if FAILURES:
        print("\nCritical failures:")
        for name, detail in FAILURES:
            print(f"- {name}: {detail}")

    return 0 if FAIL == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())