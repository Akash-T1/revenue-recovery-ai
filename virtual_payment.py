# ============================================================
# RECOVERAI VIRTUAL PAYMENT SYSTEM
# ============================================================


# ============================================================
# VIRTUAL ACCOUNT
# ============================================================

class VirtualAccount:

    def __init__(self, account_id, balance):

        self.account_id = account_id
        self.balance = float(balance)

    # --------------------------------------------------------
    # DEBIT ACCOUNT
    # --------------------------------------------------------

    def debit(self, amount):

        amount = float(amount)

        if amount > self.balance:
            return False

        self.balance -= amount

        return True

    # --------------------------------------------------------
    # CREDIT ACCOUNT
    # --------------------------------------------------------

    def credit(self, amount):

        self.balance += float(amount)


# ============================================================
# VIRTUAL PAYMENT GATEWAY
# ============================================================

class VirtualPaymentGateway:

    def __init__(self):

        self.accounts = {}

        # Store every payment attempt
        self.transaction_history = []

        # ----------------------------------------------------
        # MERCHANT ACCOUNT
        # ----------------------------------------------------

        self.accounts["MERCHANT"] = VirtualAccount(
            "MERCHANT",
            0
        )

    # ========================================================
    # CREATE ACCOUNT
    # ========================================================

    def create_account(
        self,
        account_id,
        balance
    ):

        self.accounts[account_id] = VirtualAccount(
            account_id,
            balance
        )

    # ========================================================
    # GET ACCOUNT
    # ========================================================

    def get_account(
        self,
        account_id
    ):

        return self.accounts.get(
            account_id
        )

    # ========================================================
    # CHECK BALANCE
    # ========================================================

    def get_balance(
        self,
        account_id
    ):

        account = self.get_account(
            account_id
        )

        if not account:
            return 0

        return account.balance

    # ========================================================
    # EXECUTE PAYMENT
    # ========================================================

    def execute_payment(
        self,
        customer_id,
        amount,
        failure_reason=None,
        transaction_id=None,
        attempt_type="INITIAL"
    ):

        amount = float(amount)

        customer = self.get_account(
            customer_id
        )

        merchant = self.get_account(
            "MERCHANT"
        )

        # ----------------------------------------------------
        # ACCOUNT DOES NOT EXIST
        # ----------------------------------------------------

        if not customer:

            result = {

                "success": False,

                "reason":
                    "account_not_found",

                "amount":
                    amount,

                "customer_id":
                    customer_id,

                "merchant_id":
                    "MERCHANT",

                "attempt_type":
                    attempt_type
            }

            self.transaction_history.append(result)

            return result

        # ----------------------------------------------------
        # BALANCE BEFORE
        # ----------------------------------------------------

        customer_balance_before = (
            customer.balance
        )

        merchant_balance_before = (
            merchant.balance
        )

        # ----------------------------------------------------
        # REAL BALANCE CHECK
        # ----------------------------------------------------

        if amount > customer.balance:

            result = {

                "success": False,

                "reason":
                    "insufficient_funds",

                "amount":
                    amount,

                "customer_id":
                    customer_id,

                "merchant_id":
                    "MERCHANT",

                "customer_balance_before":
                    customer_balance_before,

                "customer_balance_after":
                    customer.balance,

                "merchant_balance_before":
                    merchant_balance_before,

                "merchant_balance_after":
                    merchant.balance,

                "attempt_type":
                    attempt_type
            }

            self.transaction_history.append(result)

            return result

        # ----------------------------------------------------
        # SIMULATED FAILURE
        # ----------------------------------------------------

        if failure_reason:

            result = {

                "success": False,

                "reason":
                    failure_reason,

                "amount":
                    amount,

                "customer_id":
                    customer_id,

                "merchant_id":
                    "MERCHANT",

                "customer_balance_before":
                    customer_balance_before,

                "customer_balance_after":
                    customer.balance,

                "merchant_balance_before":
                    merchant_balance_before,

                "merchant_balance_after":
                    merchant.balance,

                "attempt_type":
                    attempt_type
            }

            self.transaction_history.append(result)

            return result

        # ----------------------------------------------------
        # ACTUAL VIRTUAL MONEY MOVEMENT
        # ----------------------------------------------------

        debit_success = customer.debit(
            amount
        )

        if not debit_success:

            result = {

                "success": False,

                "reason":
                    "insufficient_funds",

                "amount":
                    amount,

                "customer_id":
                    customer_id,

                "merchant_id":
                    "MERCHANT",

                "customer_balance_before":
                    customer_balance_before,

                "customer_balance_after":
                    customer.balance,

                "merchant_balance_before":
                    merchant_balance_before,

                "merchant_balance_after":
                    merchant.balance,

                "attempt_type":
                    attempt_type
            }

            self.transaction_history.append(result)

            return result

        # ----------------------------------------------------
        # CREDIT MERCHANT
        # ----------------------------------------------------

        merchant.credit(
            amount
        )

        # ----------------------------------------------------
        # SUCCESS RESULT
        # ----------------------------------------------------

        result = {

            "success":
                True,

            "reason":
                None,

            "amount":
                amount,

            "customer_id":
                customer_id,

            "merchant_id":
                "MERCHANT",

            "customer_balance_before":
                customer_balance_before,

            "customer_balance_after":
                customer.balance,

            "merchant_balance_before":
                merchant_balance_before,

            "merchant_balance_after":
                merchant.balance,

            "attempt_type":
                attempt_type,

            "transaction_id":
                transaction_id
        }

        self.transaction_history.append(
            result
        )

        return result

    # ========================================================
    # RECOVER PAYMENT
    # ========================================================

    def recover_payment(
        self,
        transaction
    ):

        customer_id = transaction[
            "customer_id"
        ]

        amount = transaction[
            "amount"
        ]

        original_reason = transaction.get(
            "failure_reason"
        )

        # ----------------------------------------------------
        # RULE 1
        # INSUFFICIENT FUNDS CANNOT BE FIXED
        # BY BLIND RETRY
        # ----------------------------------------------------

        if original_reason == "insufficient_funds":

            return {

                "success": False,

                "reason":
                    "insufficient_funds",

                "recovery_action":
                    "STOP",

                "amount_recovered":
                    0
            }

        # ----------------------------------------------------
        # RETRY PAYMENT
        #
        # For simulated transient failures we remove
        # the artificial failure reason.
        # The gateway then performs a REAL balance check
        # and REAL virtual money transfer.
        # ----------------------------------------------------

        result = self.execute_payment(

            customer_id,

            amount,

            failure_reason=None,

            transaction_id=
                transaction.get(
                    "transaction_id"
                ),

            attempt_type="RECOVERY_RETRY"
        )

        # ----------------------------------------------------
        # RECOVERY SUCCESS
        # ----------------------------------------------------

        if result["success"]:

            return {

                "success":
                    True,

                "reason":
                    None,

                "recovery_action":
                    "RETRY",

                "amount_recovered":
                    amount,

                "customer_balance":
                    result[
                        "customer_balance_after"
                    ],

                "merchant_balance":
                    result[
                        "merchant_balance_after"
                    ]
            }

        # ----------------------------------------------------
        # RECOVERY FAILED
        # ----------------------------------------------------

        return {

            "success":
                False,

            "reason":
                result.get(
                    "reason"
                ),

            "recovery_action":
                "RETRY",

            "amount_recovered":
                0,

            "customer_balance":
                result.get(
                    "customer_balance_after"
                ),

            "merchant_balance":
                result.get(
                    "merchant_balance_after"
                )
        }

    # ========================================================
    # TRANSACTION HISTORY
    # ========================================================

    def get_transaction_history(self):

        return self.transaction_history


# ============================================================
# CREATE DEMO GATEWAY
# ============================================================

def create_demo_gateway():

    gateway = VirtualPaymentGateway()

    gateway.create_account(
        "C1001",
        25000
    )

    gateway.create_account(
        "C1002",
        18000
    )

    gateway.create_account(
        "C1003",
        40000
    )

    gateway.create_account(
        "C1004",
        12000
    )

    gateway.create_account(
        "C1005",
        8000
    )

    return gateway


# ============================================================
# DEMO
# ============================================================

if __name__ == "__main__":

    gateway = create_demo_gateway()

    print()
    print("==============================================")
    print("       RECOVERAI VIRTUAL PAYMENT SYSTEM")
    print("==============================================")

    # ========================================================
    # INITIAL BALANCES
    # ========================================================

    print()
    print("INITIAL ACCOUNT BALANCES")
    print("----------------------------------------------")

    for account_id, account in gateway.accounts.items():

        print(
            f"{account_id:<10}"
            f" ₹{account.balance:,.2f}"
        )

    # ========================================================
    # TX-0001
    # SUCCESS
    # ========================================================

    print()
    print("==============================================")
    print("TRANSACTION: TX-0001")
    print("==============================================")

    result = gateway.execute_payment(

        "C1001",

        4999,

        transaction_id="TX-0001"
    )

    print("Customer       : C1001")
    print("Merchant       : MERCHANT")
    print("Amount         : ₹4,999")
    print(
        "Status         :",
        "SUCCESS"
        if result["success"]
        else "FAILED"
    )

    print(
        "Customer After :",
        f"₹{result['customer_balance_after']:,.2f}"
    )

    print(
        "Merchant After :",
        f"₹{result['merchant_balance_after']:,.2f}"
    )

    # ========================================================
    # TX-0002
    # NETWORK FAILURE
    # ========================================================

    print()
    print("==============================================")
    print("TRANSACTION: TX-0002")
    print("==============================================")

    result = gateway.execute_payment(

        "C1002",

        7999,

        failure_reason="network_error",

        transaction_id="TX-0002"
    )

    print("Customer       : C1002")
    print("Merchant       : MERCHANT")
    print("Amount         : ₹7,999")
    print("Status         : FAILED")
    print(
        "Failure Reason :",
        result["reason"]
    )

    print(
        "Customer After :",
        f"₹{result['customer_balance_after']:,.2f}"
    )

    print(
        "Merchant After :",
        f"₹{result['merchant_balance_after']:,.2f}"
    )

    # ========================================================
    # RECOVER TX-0002
    # ========================================================

    print()
    print("==============================================")
    print("RECOVERING TX-0002")
    print("==============================================")

    transaction = {

        "transaction_id":
            "TX-0002",

        "customer_id":
            "C1002",

        "merchant_id":
            "MERCHANT",

        "amount":
            7999,

        "failure_reason":
            "network_error"
    }

    recovery = gateway.recover_payment(
        transaction
    )

    print(
        "Recovery Action :",
        recovery["recovery_action"]
    )

    print(
        "Recovery Status :",
        "SUCCESS"
        if recovery["success"]
        else "FAILED"
    )

    print(
        "Amount Recovered:",
        f"₹{recovery['amount_recovered']:,.2f}"
    )

    print(
        "Customer Balance:",
        f"₹{gateway.get_balance('C1002'):,.2f}"
    )

    print(
        "Merchant Balance:",
        f"₹{gateway.get_balance('MERCHANT'):,.2f}"
    )

    # ========================================================
    # TX-0003
    # INSUFFICIENT FUNDS
    # ========================================================

    print()
    print("==============================================")
    print("TRANSACTION: TX-0003")
    print("==============================================")

    result = gateway.execute_payment(

        "C1005",

        9999,

        transaction_id="TX-0003"
    )

    print("Customer       : C1005")
    print("Merchant       : MERCHANT")
    print("Amount         : ₹9,999")
    print("Status         : FAILED")

    print(
        "Failure Reason :",
        result["reason"]
    )

    # ========================================================
    # FINAL BALANCES
    # ========================================================

    print()
    print("==============================================")
    print("FINAL ACCOUNT BALANCES")
    print("==============================================")

    for account_id, account in gateway.accounts.items():

        print(
            f"{account_id:<10}"
            f" ₹{account.balance:,.2f}"
        )

    print()
    print("==============================================")
    print("              DEMO COMPLETE")
    print("==============================================")