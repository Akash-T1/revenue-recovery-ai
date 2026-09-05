"""
RecoverAI - AI Decision Layer Stress Test

Tests:
- extract_decision()
- malformed/empty AI responses
- invalid actions
- probability/confidence bounds
- API failures
- hard STOP boundary
- adversarial AI responses
- failure-reason policy behavior

Does NOT require real OpenRouter calls.
"""

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

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


def fake_response(content):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content)
            )
        ]
    )


def main():

    try:
        ai = importlib.import_module("ai_agent")
    except Exception as e:
        print("[STOP] Could not import ai_agent.py")
        print(e)
        return

    print("\n=== 1. EXTRACT_DECISION TESTS ===")

    extract = ai.extract_decision

    # Valid JSON
    r = extract("""
    {
        "diagnosis": "Temporary network issue",
        "recovery_probability": 0.85,
        "recommended_action": "RETRY",
        "reason": "Transient failure",
        "confidence": 0.92
    }
    """)

    check(
        "Valid JSON parsed",
        r.get("recommended_action") == "RETRY"
    )

    check(
        "Probability preserved",
        abs(r.get("recovery_probability", 0) - 0.85) < 1e-9
    )

    check(
        "Confidence preserved",
        abs(r.get("confidence", 0) - 0.92) < 1e-9
    )

    # Plain action
    r = extract("RETRY")

    check(
        "Plain RETRY response handled",
        r.get("recommended_action") == "RETRY"
    )

    # Invalid action
    r = extract("""
    {
        "diagnosis": "Unknown",
        "recovery_probability": 0.7,
        "recommended_action": "DELETE_ACCOUNT",
        "reason": "bad",
        "confidence": 0.8
    }
    """)

    check(
        "Invalid action does not crash",
        isinstance(r, dict)
    )

    # Malformed JSON
    r = extract("""
    {"recommended_action": "RETRY",
    """)

    check(
        "Malformed JSON handled",
        isinstance(r, dict)
    )

    # Empty
    r = extract("")

    check(
        "Empty response handled",
        isinstance(r, dict)
    )

    print("\n=== 2. ANALYZE_PAYMENT MOCKED AI TESTS ===")

    original_create = ai.client.chat.completions.create

    def set_ai_response(content):
        ai.client.chat.completions.create = lambda **kwargs: fake_response(content)

    def set_ai_error():
        def failing_call(**kwargs):
            raise RuntimeError("MOCK_API_FAILURE")

        ai.client.chat.completions.create = failing_call

    base_tx = {
        "transaction_id": "TX-AI-TEST",
        "customer_id": "C1001",
        "amount": 2499,
        "status": "failed",
        "failure_reason": "network_error",
        "previous_success": 5,
        "previous_failures": 0,
        "recovery_attempts": 0,
        "subscription_active": True,
    }

    # Valid response
    set_ai_response("""
    {
        "diagnosis": "Temporary network failure",
        "recovery_probability": 0.85,
        "recommended_action": "RETRY",
        "reason": "Network failures are often transient",
        "confidence": 0.90
    }
    """)

    r = ai.analyze_payment(base_tx)

    check(
        "Valid AI response produces decision",
        r.get("recommended_action") == "RETRY",
        str(r)
    )

    check(
        "Probability remains bounded",
        0 <= r.get("recovery_probability", -1) <= 1,
        str(r)
    )

    check(
        "Confidence remains bounded",
        0 <= r.get("confidence", -1) <= 1,
        str(r)
    )

    # Invalid action
    set_ai_response("""
    {
        "diagnosis": "test",
        "recovery_probability": 0.8,
        "recommended_action": "HACK",
        "reason": "test",
        "confidence": 0.8
    }
    """)

    r = ai.analyze_payment(base_tx)

    check(
        "Invalid AI action safely becomes STOP",
        r.get("recommended_action") == "STOP",
        str(r)
    )

    # Out-of-range probability
    set_ai_response("""
    {
        "diagnosis": "test",
        "recovery_probability": 5,
        "recommended_action": "RETRY",
        "reason": "test",
        "confidence": -4
    }
    """)

    r = ai.analyze_payment(base_tx)

    check(
        "Probability > 1 is clamped",
        r.get("recovery_probability") == 1.0,
        str(r)
    )

    check(
        "Confidence < 0 is clamped",
        r.get("confidence") == 0.0,
        str(r)
    )

    # Empty response
    set_ai_response("")

    r = ai.analyze_payment(base_tx)

    check(
        "Empty AI response handled",
        isinstance(r, dict) and "error" in r,
        str(r)
    )

    # API failure
    set_ai_error()

    r = ai.analyze_payment(base_tx)

    check(
        "API failure handled without crash",
        isinstance(r, dict) and "error" in r,
        str(r)
    )

    print("\n=== 3. HARD BOUNDED-POLICY TEST ===")

    # Deliberately make AI recommend RETRY.
    # The policy MUST override this at 3+ attempts.

    set_ai_response("""
    {
        "diagnosis": "Looks recoverable",
        "recovery_probability": 0.99,
        "recommended_action": "RETRY",
        "reason": "Retry aggressively",
        "confidence": 0.99
    }
    """)

    for attempts in [0, 1, 2, 3, 4, 10]:

        tx = dict(base_tx)
        tx["recovery_attempts"] = attempts

        r = ai.analyze_payment(tx)

        if attempts >= 3:
            check(
                f"{attempts} attempts -> forced STOP",
                r.get("recommended_action") == "STOP",
                str(r)
            )
        else:
            check(
                f"{attempts} attempts remains AI-controlled",
                r.get("recommended_action") == "RETRY",
                str(r)
            )

    print("\n=== 4. FAILURE-REASON COVERAGE ===")

    expected = {
        "network_error": {"RETRY"},
        "bank_declined": {"RETRY"},
        "payment_limit": {"REMINDER"},
        "authentication_failed": {"REMINDER"},
        "expired_card": {"UPDATE_PAYMENT"},
        "insufficient_funds": {"RETRY"},
    }

    for reason, allowed in expected.items():

        tx = dict(base_tx)
        tx["failure_reason"] = reason
        tx["recovery_attempts"] = 0

        # Give the model the expected answer.
        action = list(allowed)[0]

        set_ai_response(f"""
        {{
            "diagnosis": "Test diagnosis",
            "recovery_probability": 0.80,
            "recommended_action": "{action}",
            "reason": "Policy test",
            "confidence": 0.90
        }}
        """)

        r = ai.analyze_payment(tx)

        check(
            f"{reason} -> {action}",
            r.get("recommended_action") == action,
            str(r)
        )

    print("\n=== 5. ADVERSARIAL RESPONSE TEST ===")

    adversarial_cases = [
        ("DELETE_ALL_DATA", "Invalid action"),
        ("TRANSFER_MONEY", "Dangerous action"),
        ("REFUND", "Unsupported action"),
        ("", "Empty action"),
        ("retry", "Lowercase action"),
    ]

    for action, label in adversarial_cases:

        set_ai_response(f"""
        {{
            "diagnosis": "Adversarial",
            "recovery_probability": 0.99,
            "recommended_action": "{action}",
            "reason": "Adversarial test",
            "confidence": 0.99
        }}
        """)

        tx = dict(base_tx)
        tx["recovery_attempts"] = 0

        r = ai.analyze_payment(tx)

        if action == "retry":
            expected_action = "RETRY"
        else:
            expected_action = "STOP"

        check(
            label,
            r.get("recommended_action") == expected_action,
            str(r)
        )

    # Restore
    ai.client.chat.completions.create = original_create

    print("\n=== FINAL AI TEST REPORT ===")
    print(f"PASS:  {PASS}")
    print(f"FAIL:  {FAIL}")
    print(f"TOTAL: {PASS + FAIL}")

    if FAILURES:
        print("\nFAILURES:")
        for name, detail in FAILURES:
            print(f"- {name}: {detail}")

    if FAIL == 0:
        print("\n*** AI DECISION LAYER: ALL TESTS PASSED ***")
    else:
        print("\n*** AI DECISION LAYER: REVIEW FAILURES ***")


if __name__ == "__main__":
    main()