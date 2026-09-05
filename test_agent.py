from ai_agent import analyze_payment


transaction = {
    "transaction_id": "TX-DEMO-001",
    "customer_id": "C1001",
    "amount": 4999,
    "status": "failed",
    "failure_reason": "insufficient_funds",
    "previous_success": 8,
    "previous_failures": 1,
    "recovery_attempts": 0,
    "subscription_active": True
}


result = analyze_payment(transaction)


print("\n========== RECOVERAI AI AGENT ==========\n")


if "error" in result:

    print("AI ERROR:")
    print(result["error"])

    if "raw_response" in result:
        print("\nRaw response:")
        print(result["raw_response"])

else:

    print("Diagnosis:")
    print(result["diagnosis"])

    print("\nRecovery Probability:")
    print(
        f"{result['recovery_probability'] * 100:.1f}%"
    )

    print("\nRecommended Action:")
    print(result["recommended_action"])

    print("\nReason:")
    print(result["reason"])

    print("\nConfidence:")
    print(
        f"{result['confidence'] * 100:.1f}%"
    )


print("\n========================================\n")