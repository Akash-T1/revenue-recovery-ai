import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise RuntimeError(
        "OPENROUTER_API_KEY is missing from .env"
    )


# ============================================================
# OPENROUTER CLIENT
# ============================================================

client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1"
)


# ============================================================
# ALLOWED ACTIONS
# ============================================================

ALLOWED_ACTIONS = {
    "RETRY",
    "REMINDER",
    "UPDATE_PAYMENT",
    "ESCALATE",
    "STOP"
}


# ============================================================
# EXTRACT DECISION FROM MODEL TEXT
# ============================================================

def extract_decision(content):

    content_lower = content.lower()

    # --------------------------------------------------------
    # 1. Try normal JSON first
    # --------------------------------------------------------

    try:
        return json.loads(content)

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # 2. Try to find JSON inside the response
    # --------------------------------------------------------

    match = re.search(
        r'\{.*\}',
        content,
        re.DOTALL
    )

    if match:

        try:
            return json.loads(match.group(0))

        except json.JSONDecodeError:
            pass

    # --------------------------------------------------------
    # 3. Extract recommended action
    # --------------------------------------------------------

    action = "STOP"

    # Look for explicit "Recommended Action" section
    action_match = re.search(
        r'Recommended Action.*?\*\*(RETRY|REMINDER|UPDATE_PAYMENT|ESCALATE|STOP)\*\*',
        content,
        re.IGNORECASE | re.DOTALL
    )

    if action_match:

        action = action_match.group(1).upper()

    else:

        # Fallback: look for the allowed action anywhere
        # near the recommendation

        for possible_action in [
            "UPDATE_PAYMENT",
            "REMINDER",
            "ESCALATE",
            "RETRY",
            "STOP"
        ]:

            if possible_action.lower() in content_lower:

                action = possible_action
                break

    # --------------------------------------------------------
    # 4. Determine diagnosis
    # --------------------------------------------------------

    if "insufficient_funds" in content_lower:

        diagnosis = "Insufficient funds payment failure"

    elif "expired" in content_lower:

        diagnosis = "Expired payment method"

    elif "authentication" in content_lower:

        diagnosis = "Payment authentication issue"

    elif "network" in content_lower:

        diagnosis = "Temporary network payment failure"

    else:

        diagnosis = "Payment failure analyzed"

    # --------------------------------------------------------
    # 5. Determine probability
    # --------------------------------------------------------

    probability_match = re.search(
        r'recovery_probability["\']?\s*[:=]\s*(0?\.\d+|1(?:\.0+)?)',
        content,
        re.IGNORECASE
    )

    if probability_match:

        probability = float(
            probability_match.group(1)
        )

    else:

        # Reasonable rule-based fallback
        if action == "RETRY":

            probability = 0.75

        elif action == "REMINDER":

            probability = 0.60

        elif action == "UPDATE_PAYMENT":

            probability = 0.55

        elif action == "ESCALATE":

            probability = 0.30

        else:

            probability = 0.10

    # --------------------------------------------------------
    # 6. Determine confidence
    # --------------------------------------------------------

    confidence_match = re.search(
        r'confidence["\']?\s*[:=]\s*(0?\.\d+|1(?:\.0+)?)',
        content,
        re.IGNORECASE
    )

    if confidence_match:

        confidence = float(
            confidence_match.group(1)
        )

    else:

        confidence = 0.85

    # --------------------------------------------------------
    # 7. Generate reason
    # --------------------------------------------------------

    reason = (
        f"AI analyzed the payment failure and "
        f"recommended {action} based on the "
        f"failure reason and customer payment history."
    )

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    return {
        "diagnosis": diagnosis,
        "recovery_probability": probability,
        "recommended_action": action,
        "reason": reason,
        "confidence": confidence
    }


# ============================================================
# MAIN AI AGENT
# ============================================================

def analyze_payment(transaction):

    prompt = f"""
You are RecoverAI, an AI revenue recovery agent.
Analyze this failed payment.

Transaction ID: {transaction.get('transaction_id')}
Customer ID: {transaction.get('customer_id')}
Amount: ₹{transaction.get('amount')}
Status: {transaction.get('status')}
Failure Reason: {transaction.get('failure_reason')}
Previous Successful Payments: {transaction.get('previous_success')}
Previous Failures: {transaction.get('previous_failures')}
Previous Recovery Attempts: {transaction.get('recovery_attempts')}
Subscription Active: {transaction.get('subscription_active')}

Allowed actions:
RETRY
REMINDER
UPDATE_PAYMENT
ESCALATE
STOP

Rules:
- Temporary/network/insufficient-funds -> RETRY
- Authentication/limit problem -> REMINDER
- Expired card/payment method -> UPDATE_PAYMENT
- Repeated failures -> ESCALATE or STOP
- 3 or more recovery attempts -> STOP
- Consider previous successful payments
- Do not invent customer information

Return a recovery decision.
"""

    try:

        # ====================================================
        # AI REQUEST
        # ====================================================

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": """
You are RecoverAI, a payment recovery decision engine.

Analyze the payment data provided by the user.

Return ONLY one of these actions:
RETRY
REMINDER
UPDATE_PAYMENT
ESCALATE
STOP

Do not discuss safety.
Do not provide a safety classification.
Do not provide a thinking process.
"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=300
        )

        content = response.choices[0].message.content

        if not content:

            return {
                "error": "AI returned no content"
            }

        print("\nDEBUG AI RESPONSE:")
        print(content)

        # ====================================================
        # EXTRACT DECISION
        # ====================================================

        result = extract_decision(content)

        # ====================================================
        # VALIDATE ACTION
        # ====================================================

        action = str(
            result.get(
                "recommended_action",
                "STOP"
            )
        ).upper()

        if action not in ALLOWED_ACTIONS:

            action = "STOP"

        result["recommended_action"] = action

        # ====================================================
        # VALIDATE PROBABILITY
        # ====================================================

        try:

            probability = float(
                result.get(
                    "recovery_probability",
                    0
                )
            )

        except:

            probability = 0

        result["recovery_probability"] = max(
            0.0,
            min(1.0, probability)
        )

        # ====================================================
        # VALIDATE CONFIDENCE
        # ====================================================

        try:

            confidence = float(
                result.get(
                    "confidence",
                    0
                )
            )

        except:

            confidence = 0

        result["confidence"] = max(
            0.0,
            min(1.0, confidence)
        )

        # ====================================================
        # HARD SAFETY RULE
        # ====================================================

        try:

            attempts = int(
                transaction.get(
                    "recovery_attempts",
                    0
                )
            )

        except:

            attempts = 0

        if attempts >= 3:

            result["recommended_action"] = "STOP"

            result["reason"] = (
                "Maximum automated recovery "
                "attempts reached."
            )

        # ====================================================
        # FINAL RESULT
        # ====================================================

        return {
            "diagnosis": result.get(
                "diagnosis",
                "Payment failure analyzed."
            ),

            "recovery_probability":
                result["recovery_probability"],

            "recommended_action":
                result["recommended_action"],

            "reason":
                result.get(
                    "reason",
                    "AI recovery analysis completed."
                ),

            "confidence":
                result["confidence"]
        }

    except Exception as e:

        return {
            "error": str(e)
        }