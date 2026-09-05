import csv
import random

from virtual_payment import VirtualPaymentGateway
from ai_agent import analyze_payment


# ============================================================
# CONFIGURATION
# ============================================================

TRANSACTION_COUNT = 50

PAYMENT_AMOUNTS = [
    499,
    999,
    1499,
    2499,
    4999,
    7999,
    9999
]


# ============================================================
# CREATE VIRTUAL CUSTOMERS
# ============================================================

def create_customers(gateway):

    customers = []

    for i in range(1001, 1051):

        balance = random.choice([
            5000,
            8000,
            12000,
            18000,
            25000,
            40000
        ])

        customer_id = f"C{i}"

        gateway.create_account(
            customer_id,
            balance
        )

        customers.append(customer_id)

    return customers


# ============================================================
# GENERATE ONE TRANSACTION
# ============================================================

def generate_transaction(
    gateway,
    transaction_number,
    customer_id
):

    customer = gateway.get_account(customer_id)

    if customer is None:
        raise ValueError(
            f"Customer {customer_id} does not exist"
        )

    balance_before = customer.balance

    amount = random.choice(
        PAYMENT_AMOUNTS
    )

    # --------------------------------------------------------
    # DECIDE FAILURE REASON
    # --------------------------------------------------------

    failure_reason = None

    # If customer does not have enough money,
    # insufficient_funds MUST be the reason.
    if amount > balance_before:

        failure_reason = "insufficient_funds"

    else:

        possible_failures = [
            None,
            None,
            None,
            None,
            "network_error",
            "authentication_failed",
            "expired_card",
            "payment_limit",
            "bank_declined"
        ]

        failure_reason = random.choice(
            possible_failures
        )

    # --------------------------------------------------------
    # EXECUTE INITIAL PAYMENT
    # --------------------------------------------------------

    result = gateway.execute_payment(
        customer_id,
        amount,
        failure_reason=failure_reason
    )

    # --------------------------------------------------------
    # DETERMINE STATUS
    # --------------------------------------------------------

    if result["success"]:
        status = "success"
    else:
        status = "failed"

    # --------------------------------------------------------
    # CUSTOMER HISTORY
    # --------------------------------------------------------

    previous_success = random.randint(
        1,
        12
    )

    previous_failures = random.randint(
        0,
        3
    )

    recovery_attempts = 0

    subscription_active = random.choice([
        True,
        True,
        True,
        False
    ])

    # --------------------------------------------------------
    # BALANCES AFTER INITIAL PAYMENT
    # --------------------------------------------------------

    balance_after = gateway.get_balance(
        customer_id
    )

    merchant_balance = gateway.get_balance(
        "MERCHANT"
    )

    # --------------------------------------------------------
    # BUILD TRANSACTION
    # --------------------------------------------------------

    transaction = {

        "transaction_id":
            f"TX-{transaction_number:04d}",

        "customer_id":
            customer_id,

        "merchant_id":
            "MERCHANT",

        "amount":
            amount,

        "status":
            status,

        "failure_reason":
            result.get("reason"),

        "previous_success":
            previous_success,

        "previous_failures":
            previous_failures,

        "recovery_attempts":
            recovery_attempts,

        "subscription_active":
            subscription_active,

        "balance_before":
            balance_before,

        "balance_after":
            balance_after,

        "merchant_balance":
            merchant_balance,

        # ----------------------------------------------------
        # RECOVERY FIELDS
        # ----------------------------------------------------

        "recovery_status":
            "NOT_REQUIRED",

        "recovery_action":
            "NOT_REQUIRED",

        "recovered_amount":
            0,

        "recovery_balance_after":
            balance_after,

        "recovery_merchant_balance":
            merchant_balance
    }

    return transaction


# ============================================================
# GENERATE TRANSACTION BATCH
# ============================================================

def generate_transactions(
    gateway,
    customers,
    count=50
):

    transactions = []

    for i in range(
        1,
        count + 1
    ):

        customer_id = random.choice(
            customers
        )

        transaction = generate_transaction(
            gateway,
            i,
            customer_id
        )

        transactions.append(
            transaction
        )

    return transactions


# ============================================================
# DISPLAY INITIAL LEDGER
# ============================================================

def display_transactions(
    transactions
):

    print("\n==============================================")
    print("          VIRTUAL TRANSACTION LEDGER")
    print("==============================================")

    for tx in transactions:

        print(
            f"\n{tx['transaction_id']} | "
            f"{tx['customer_id']} → "
            f"{tx['merchant_id']}"
        )

        print(
            f"Amount         : "
            f"₹{tx['amount']:,.2f}"
        )

        print(
            f"Balance Before : "
            f"₹{tx['balance_before']:,.2f}"
        )

        print(
            f"Status         : "
            f"{tx['status'].upper()}"
        )

        if tx["failure_reason"]:

            print(
                f"Failure Reason : "
                f"{tx['failure_reason']}"
            )

        print(
            f"Balance After  : "
            f"₹{tx['balance_after']:,.2f}"
        )

        print(
            f"Merchant       : "
            f"₹{tx['merchant_balance']:,.2f}"
        )


# ============================================================
# EXECUTE RECOVERY
# ============================================================

def execute_recovery(
    gateway,
    transaction,
    action
):

    customer_id = transaction[
        "customer_id"
    ]

    amount = transaction[
        "amount"
    ]

    transaction_id = transaction[
        "transaction_id"
    ]

    # --------------------------------------------------------
    # NORMALIZE AI ACTION
    # --------------------------------------------------------

    if action is None:
        action = "ERROR"

    action = str(action).strip().upper()

    # ========================================================
    # REMINDER
    # ========================================================

    if action == "REMINDER":

        print(
            f"      ↳ Sending payment reminder "
            f"for {transaction_id}"
        )

        return {
            "recovery_status":
                "REMINDER_SENT",

            "recovered_amount":
                0,

            "recovery_balance_after":
                gateway.get_balance(
                    customer_id
                ),

            "recovery_merchant_balance":
                gateway.get_balance(
                    "MERCHANT"
                )
        }

    # ========================================================
    # ESCALATE
    # ========================================================

    if action == "ESCALATE":

        print(
            f"      ↳ Escalating transaction "
            f"{transaction_id}"
        )

        return {
            "recovery_status":
                "ESCALATED",

            "recovered_amount":
                0,

            "recovery_balance_after":
                gateway.get_balance(
                    customer_id
                ),

            "recovery_merchant_balance":
                gateway.get_balance(
                    "MERCHANT"
                )
        }

    # ========================================================
    # STOP
    # ========================================================

    if action == "STOP":

        print(
            f"      ↳ Stopping recovery for "
            f"{transaction_id}"
        )

        return {
            "recovery_status":
                "STOPPED",

            "recovered_amount":
                0,

            "recovery_balance_after":
                gateway.get_balance(
                    customer_id
                ),

            "recovery_merchant_balance":
                gateway.get_balance(
                    "MERCHANT"
                )
        }

    # ========================================================
    # RETRY
    # ========================================================

    if action == "RETRY":

        print(
            f"      ↳ Retrying payment "
            f"for {transaction_id}"
        )

        # Retry without simulated failure.
        retry_result = gateway.execute_payment(
            customer_id,
            amount
        )

        if retry_result["success"]:

            print(
                "      ↳ Payment recovered successfully"
            )

            # We intentionally use gateway.get_balance()
            # instead of depending on customer_balance keys.
            #
            # This makes the code safe even if the gateway
            # returns only {"success": True}.
            return {
                "recovery_status":
                    "RECOVERED",

                "recovered_amount":
                    amount,

                "recovery_balance_after":
                    gateway.get_balance(
                        customer_id
                    ),

                "recovery_merchant_balance":
                    gateway.get_balance(
                        "MERCHANT"
                    )
            }

        print(
            f"      ↳ Retry failed: "
            f"{retry_result.get('reason', 'unknown')}"
        )

        return {
            "recovery_status":
                "RECOVERY_FAILED",

            "recovered_amount":
                0,

            "recovery_balance_after":
                gateway.get_balance(
                    customer_id
                ),

            "recovery_merchant_balance":
                gateway.get_balance(
                    "MERCHANT"
                ),

            "recovery_failure_reason":
                retry_result.get(
                    "reason",
                    "unknown"
                )
        }

    # ========================================================
    # UPDATE PAYMENT
    # ========================================================

    if action == "UPDATE_PAYMENT":

        print(
            f"      ↳ Updating payment method "
            f"for {transaction_id}"
        )

        # ----------------------------------------------------
        # In this virtual MVP, changing the payment method
        # allows us to retry the payment.
        # ----------------------------------------------------

        print(
            "      ↳ Payment method updated"
        )

        retry_result = gateway.execute_payment(
            customer_id,
            amount
        )

        if retry_result["success"]:

            print(
                "      ↳ Payment recovered successfully"
            )

            return {
                "recovery_status":
                    "RECOVERED",

                "recovered_amount":
                    amount,

                "recovery_balance_after":
                    gateway.get_balance(
                        customer_id
                    ),

                "recovery_merchant_balance":
                    gateway.get_balance(
                        "MERCHANT"
                    )
            }

        print(
            f"      ↳ Updated payment failed: "
            f"{retry_result.get('reason', 'unknown')}"
        )

        return {
            "recovery_status":
                "RECOVERY_FAILED",

            "recovered_amount":
                0,

            "recovery_balance_after":
                gateway.get_balance(
                    customer_id
                ),

            "recovery_merchant_balance":
                gateway.get_balance(
                    "MERCHANT"
                ),

            "recovery_failure_reason":
                retry_result.get(
                    "reason",
                    "unknown"
                )
        }

    # ========================================================
    # UNKNOWN ACTION
    # ========================================================
    # --------------------------------------------------------
# ERROR / INVALID AI DECISION
# --------------------------------------------------------

    if action == "ERROR":

        print(
            f"      ↳ AI could not determine a safe recovery action "
            f"for {transaction['transaction_id']}"
        )

        return {
            "recovery_status":
                "BLOCKED",

            "recovered_amount":
                0,

            "recovery_balance_after":
                gateway.get_balance(
                    customer_id
                ),

            "recovery_merchant_balance":
                gateway.get_balance(
                    "MERCHANT"
                ),

            "recovery_failure_reason":
                "AI_DECISION_ERROR"
        }
    print(
        f"      ↳ Unknown recovery action: "
        f"{action}"
    )

    return {
        "recovery_status":
            "BLOCKED",

        "recovered_amount":
            0,

        "recovery_balance_after":
            gateway.get_balance(
                customer_id
            ),

        "recovery_merchant_balance":
            gateway.get_balance(
                "MERCHANT"
            ),

        "recovery_failure_reason":
            "unknown_action"
    }


# ============================================================
# PROCESS ONE TRANSACTION WITH AI
# ============================================================

def process_transaction(
    gateway,
    transaction
):

    # --------------------------------------------------------
    # ALREADY SUCCESSFUL
    # --------------------------------------------------------

    if transaction["status"] == "success":

        return {
            **transaction,

            "recommended_action":
                "NOT_REQUIRED",

            "recovery_action":
                "NOT_REQUIRED",

            "recovery_status":
                "NOT_REQUIRED",

            "recovered_amount":
                0
        }

    # --------------------------------------------------------
    # SEND FAILED PAYMENT TO AI
    # --------------------------------------------------------

    try:

        ai_result = analyze_payment(
            transaction
        )

    except Exception as e:

        return {
            **transaction,

            "recommended_action":
                "ERROR",

            "recovery_action":
                "ERROR",

            "recovery_status":
                "AI_ERROR",

            "recovered_amount":
                0,

            "error":
                str(e)
        }

    # --------------------------------------------------------
    # GET AI ACTION
    # --------------------------------------------------------

    action = ai_result.get(
        "recommended_action",
        "ERROR"
    )

    if action is None:
        action = "ERROR"

    action = str(
        action
    ).strip().upper()

    # --------------------------------------------------------
    # EXECUTE AI DECISION
    # --------------------------------------------------------

    recovery_result = execute_recovery(
        gateway,
        transaction,
        action
    )
    # --------------------------------------------------------
    # CLASSIFY INSUFFICIENT FUNDS
    # --------------------------------------------------------

    if (
        recovery_result.get("recovery_status") == "RECOVERY_FAILED"
        and recovery_result.get("recovery_failure_reason") == "insufficient_funds"
    ):

        recovery_result["recovery_status"] = "CURRENTLY_UNRECOVERABLE"

        recovery_result["recovery_failure_reason"] = (
            "insufficient_funds"
        )

    # --------------------------------------------------------
    # COMBINE EVERYTHING
    # --------------------------------------------------------

    return {
        **transaction,
        **ai_result,

        "recommended_action":
            action,

        "recovery_action":
            action,

        **recovery_result
    }


# ============================================================
# PROCESS COMPLETE BATCH
# ============================================================

def process_batch(
    gateway,
    transactions
):

    results = []

    print("\n==============================================")
    print("          RECOVERAI AI PROCESSING")
    print("==============================================")

    for index, transaction in enumerate(
        transactions,
        start=1
    ):

        result = process_transaction(
            gateway,
            transaction
        )

        results.append(
            result
        )

        print(
            f"\n[{index}/{len(transactions)}] "
            f"{transaction['transaction_id']} | "
            f"{transaction['customer_id']} → "
            f"MERCHANT | "
            f"₹{transaction['amount']:,.0f}"
        )

        print(
            f"      Initial Status : "
            f"{transaction['status'].upper()}"
        )

        if transaction["failure_reason"]:

            print(
                f"      Failure Reason : "
                f"{transaction['failure_reason']}"
            )

        print(
            f"      AI Action      : "
            f"{result.get('recommended_action', 'ERROR')}"
        )

        print(
            f"      Recovery       : "
            f"{result.get('recovery_status', 'UNKNOWN')}"
        )

        print(
            f"      Amount Recovered: "
            f"₹{result.get('recovered_amount', 0):,.2f}"
        )

    return results


# ============================================================
# CALCULATE METRICS
# ============================================================


def calculate_metrics(results):

    # --------------------------------------------------------
    # REVENUE AT RISK
    #
    # Exclude insufficient-funds transactions because they are
    # currently unrecoverable by the automated system.
    # --------------------------------------------------------

    revenue_at_risk = sum(
        float(r.get("amount", 0))
        for r in results
        if (
            r.get("status") == "failed"
            and r.get("failure_reason") != "insufficient_funds"
        )
    )

    # --------------------------------------------------------
    # TOTAL RECOVERED
    # --------------------------------------------------------

    revenue_recovered = sum(
        float(r.get("recovered_amount", 0))
        for r in results
    )

    # --------------------------------------------------------
    # RECOVERY RATE
    # --------------------------------------------------------

    recovery_rate = (
        revenue_recovered / revenue_at_risk
        if revenue_at_risk > 0
        else 0
    )

    # --------------------------------------------------------
    # SUCCESSFUL RECOVERY CASES
    # --------------------------------------------------------

    recovery_cases = [
        r for r in results
        if r.get("recovery_status") == "RECOVERED"
    ]

    # --------------------------------------------------------
    # NOT RECOVERED - REMINDER
    # --------------------------------------------------------

    reminder_cases = [
        r for r in results
        if r.get("recovery_status") == "REMINDER_SENT"
    ]

    reminder_amount = sum(
        float(r.get("amount", 0))
        for r in reminder_cases
    )

    # --------------------------------------------------------
    # NOT RECOVERED - AI ERROR
    # --------------------------------------------------------

    ai_error_cases = [
        r for r in results
        if (
            r.get("recovery_status") == "AI_ERROR"
            or r.get("recommended_action") == "ERROR"
        )
    ]

    ai_error_amount = sum(
        float(r.get("amount", 0))
        for r in ai_error_cases
    )

    # --------------------------------------------------------
    # NOT RECOVERED - ESCALATED
    # --------------------------------------------------------

    escalated_cases = [
        r for r in results
        if r.get("recovery_status") == "ESCALATED"
    ]

    escalated_amount = sum(
        float(r.get("amount", 0))
        for r in escalated_cases
    )

    # --------------------------------------------------------
    # NOT RECOVERED - RECOVERY FAILED
    #
    # Only include actual recovery failures.
    # Insufficient funds are classified separately.
    # --------------------------------------------------------

    recovery_failed_cases = [
        r for r in results
        if r.get("recovery_status") == "RECOVERY_FAILED"
    ]

    recovery_failed_amount = sum(
        float(r.get("amount", 0))
        for r in recovery_failed_cases
    )

    # --------------------------------------------------------
    # CURRENTLY UNRECOVERABLE
    # --------------------------------------------------------

    unrecoverable_cases = [
        r for r in results
        if r.get("recovery_status") == "CURRENTLY_UNRECOVERABLE"
        or r.get("failure_reason") == "insufficient_funds"
    ]

    unrecoverable_amount = sum(
        float(r.get("amount", 0))
        for r in unrecoverable_cases
    )

    # --------------------------------------------------------
    # TOTAL NOT RECOVERED
    #
    # This does NOT include currently unrecoverable payments.
    # --------------------------------------------------------

    total_not_recovered = (
        reminder_amount
        + ai_error_amount
        + escalated_amount
        + recovery_failed_amount
    )

    # --------------------------------------------------------
    # REMAINING REVENUE AT RISK
    # --------------------------------------------------------

    remaining_at_risk = (
        revenue_at_risk
        - revenue_recovered
    )

    # --------------------------------------------------------
    # ACTION COUNTS
    # --------------------------------------------------------

    actions = {}

    for result in results:

        action = result.get(
            "recommended_action",
            "ERROR"
        )

        actions[action] = (
            actions.get(action, 0) + 1
        )

    return {

        "revenue_at_risk":
            revenue_at_risk,

        "revenue_recovered":
            revenue_recovered,

        "recovery_rate":
            recovery_rate,

        "recovery_cases":
            len(recovery_cases),

        "reminder_cases":
            reminder_cases,

        "reminder_amount":
            reminder_amount,

        "ai_error_cases":
            ai_error_cases,

        "ai_error_amount":
            ai_error_amount,

        "escalated_cases":
            escalated_cases,

        "escalated_amount":
            escalated_amount,

        "recovery_failed_cases":
            recovery_failed_cases,

        "recovery_failed_amount":
            recovery_failed_amount,

        "unrecoverable_cases":
            unrecoverable_cases,

        "unrecoverable_amount":
            unrecoverable_amount,

        "total_not_recovered":
            total_not_recovered,

        "remaining_at_risk":
            remaining_at_risk,

        "actions":
            actions
    }


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(
    results
):

    fieldnames = [

        "transaction_id",
        "customer_id",
        "merchant_id",

        "amount",

        "status",
        "failure_reason",

        "balance_before",
        "balance_after",
        "merchant_balance",

        "recommended_action",
        "recovery_action",

        "recovery_status",
        "recovery_failure_reason",
        "recovered_amount",

        "recovery_balance_after",
        "recovery_merchant_balance",

        "recovery_probability",
        "confidence",

        "diagnosis",
        "reason",
        "error"
    ]

    with open(
        "recovery_results.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        writer.writeheader()

        for result in results:

            writer.writerow({

                field:
                    result.get(
                        field,
                        ""
                    )

                for field in fieldnames
            })

    print(
        "\nResults saved to "
        "recovery_results.csv"
    )


# ============================================================
# DISPLAY FINAL ACCOUNT BALANCES
# ============================================================

def display_final_balances(
    gateway
):

    print("\n==============================================")
    print("          FINAL ACCOUNT BALANCES")
    print("==============================================")

    for account_id, account in gateway.accounts.items():

        print(
            f"{account_id:<10} "
            f"₹{account.balance:,.2f}"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("\n==============================================")
    print("        RECOVERAI VIRTUAL BATCH")
    print("==============================================")

    # --------------------------------------------------------
    # CREATE FRESH VIRTUAL PAYMENT ENVIRONMENT
    # --------------------------------------------------------

    gateway = VirtualPaymentGateway()

    customers = create_customers(
        gateway
    )

    print(
        f"\nCreated {len(customers)} "
        f"virtual customers."
    )

    # --------------------------------------------------------
    # GENERATE TRANSACTIONS
    # --------------------------------------------------------

    transactions = generate_transactions(
        gateway,
        customers,
        TRANSACTION_COUNT
    )

    # --------------------------------------------------------
    # SHOW INITIAL TRANSACTIONS
    # --------------------------------------------------------

    display_transactions(
        transactions
    )

    # --------------------------------------------------------
    # AI + VIRTUAL RECOVERY
    # --------------------------------------------------------

    results = process_batch(
        gateway,
        transactions
    )

    # --------------------------------------------------------
    # FINAL BALANCES
    # --------------------------------------------------------

    display_final_balances(
        gateway
    )

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    metrics = calculate_metrics(
        results
    )

    # --------------------------------------------------------
    # SAVE CSV
    # --------------------------------------------------------

    save_results(
        results
    )

    # --------------------------------------------------------
    # FINAL REPORT
    # --------------------------------------------------------


    print("\n==============================================")
    print("             RECOVERAI RESULTS")
    print("==============================================")

    print(
        f"\nRevenue At Risk: "
        f"₹{metrics['revenue_at_risk']:,.2f}"
    )

    print(
        f"Revenue Recovered: "
        f"₹{metrics['revenue_recovered']:,.2f}"
    )

    print(
        f"Recovery Rate: "
        f"{metrics['recovery_rate'] * 100:.1f}%"
    )

    print(
        f"Successful Recovery Cases: "
        f"{metrics['recovery_cases']}"
    )


    print(
        f"Remaining Revenue At Risk: "
        f"₹{metrics['remaining_at_risk']:,.2f}"
    )


    # ============================================================
    # NOT RECOVERED
    # ============================================================

    print("\n==============================================")
    print("              NOT RECOVERED")
    print("==============================================")


    # ------------------------------------------------------------
    # 1. REMINDER
    # ------------------------------------------------------------

    print("\n1. REMINDER")

    if metrics["reminder_cases"]:

        for tx in metrics["reminder_cases"]:

            print(
                f"   {tx['transaction_id']:<10} | "
                f"{tx.get('failure_reason', 'unknown'):<22} | "
                f"₹{float(tx['amount']):,.2f}"
            )

    else:

        print("   None")

    print(
        f"   Total Reminder Amount: "
        f"₹{metrics['reminder_amount']:,.2f}"
    )


    # ------------------------------------------------------------
    # 2. RECOVERY FAILED
    # ------------------------------------------------------------

    print("\n2. RECOVERY FAILED")

    if metrics["recovery_failed_cases"]:

        for tx in metrics["recovery_failed_cases"]:

            reason = tx.get(
                "recovery_failure_reason",
                tx.get("failure_reason", "unknown")
            )

            print(
                f"   {tx['transaction_id']:<10} | "
                f"{reason:<22} | "
                f"₹{float(tx['amount']):,.2f}"
            )

    else:

        print("   None")

    print(
        f"   Total Recovery Failed Amount: "
        f"₹{metrics['recovery_failed_amount']:,.2f}"
    )


    # ------------------------------------------------------------
    # 3. AI ERROR
    # ------------------------------------------------------------

    print("\n3. AI ERROR")

    if metrics["ai_error_cases"]:

        for tx in metrics["ai_error_cases"]:

            reason = (
                tx.get("error")
                or "AI decision error"
            )

            print(
                f"   {tx['transaction_id']:<10} | "
                f"{reason:<35} | "
                f"₹{float(tx['amount']):,.2f}"
            )

    else:

        print("   None")

    print(
        f"   Total AI Error Amount: "
        f"₹{metrics['ai_error_amount']:,.2f}"
    )


    # ------------------------------------------------------------
    # 4. ESCALATED
    #    ------------------------------------------------------------

    print("\n4. ESCALATED")

    if metrics["escalated_cases"]:

        for tx in metrics["escalated_cases"]:

            reason = tx.get(
                "failure_reason",
                "manual intervention required"
            )

            print(
                f"   {tx['transaction_id']:<10} | "
                f"{reason:<22} | "
                f"₹{float(tx['amount']):,.2f}"
            )

    else:

        print("   None")

    print(
        f"   Total Escalated Amount: "
        f"₹{metrics['escalated_amount']:,.2f}"
    )


    # ------------------------------------------------------------
    # TOTAL NOT RECOVERED
    # ------------------------------------------------------------

    print("\n----------------------------------------------")

    print(
        f"TOTAL NOT RECOVERED: "
        f"₹{metrics['total_not_recovered']:,.2f}"
    )


    # ============================================================
    # CURRENTLY UNRECOVERABLE
    # ============================================================

    print("\n==============================================")
    print("         CURRENTLY UNRECOVERABLE")
    print("==============================================")


    if metrics["unrecoverable_cases"]:

        for tx in metrics["unrecoverable_cases"]:

            print(
                f"   {tx['transaction_id']:<10} | "
                f"insufficient_funds     | "
                f"₹{float(tx['amount']):,.2f}"
            )

    else:

        print("   None")

    print(
        f"\n   Total Currently Unrecoverable: "
        f"₹{metrics['unrecoverable_amount']:,.2f}"
    )


    # ============================================================
    # AGENT ACTIONS
    # ============================================================

    print("\n==============================================")
    print("              AGENT ACTIONS")
    print("==============================================")

    for action, count in metrics["actions"].items():

        print(
            f"  {action:<18}: {count}"
        )


    print("\n==============================================")
    print("              BATCH COMPLETE")
    print("==============================================")