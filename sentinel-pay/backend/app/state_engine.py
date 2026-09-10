import random
from typing import Dict, Any, Tuple, Optional
from app.schemas import TransactionRecord, RecoveryDecision, FailureCategory, RecoveryAction
from app.dlq import dlq_manager

class SentinelRecoveryEngine:
    RETRY_CEILING = 3
    COOLING_WINDOW_MINUTES = 20

    SWITCH_HEALTH_MAP = {
        "HDFC": {"status": "OPERATIONAL", "success_rate": 96.8, "fallback": "NPCI_CENTRAL"},
        "SBI": {"status": "DEGRADED", "success_rate": 78.4, "fallback": "ICICI_NETBANKING"},
        "ICICI": {"status": "OPERATIONAL", "success_rate": 98.1, "fallback": "AXIS_CARD"},
        "NPCI": {"status": "OPERATIONAL", "success_rate": 95.9, "fallback": "HDFC_UPI"},
        "AXIS": {"status": "OPERATIONAL", "success_rate": 94.2, "fallback": "NPCI_CENTRAL"}
    }

    @classmethod
    def evaluate(cls, record: TransactionRecord) -> RecoveryDecision:
        err_code = str(record.error_code or "").upper().strip()
        err_desc = str(record.error_description or "").upper().strip()
        payment_method = str(record.payment_method or "upi").lower().strip()
        cust_name = str(record.customer_name or "Valued Customer").strip()
        txn_id = str(record.transaction_id or "txn_000").strip()
        retries = int(record.retry_count or 0)
        amount = float(record.amount or 0.0)

        # 1. Anti-Harassment Circuit Breaker Hard Stop (>= 3 retries)
        if retries >= cls.RETRY_CEILING:
            dlq_manager.push(
                transaction_id=txn_id,
                customer_name=cust_name,
                customer_phone=str(record.customer_phone or "+919876543210"),
                amount=amount,
                payment_method=payment_method,
                triage_code="DLQ_MAX_RETRIES_EXCEEDED",
                quarantine_reason=f"Exceeded max retry ceiling ({cls.RETRY_CEILING}). Enforced RBI anti-harassment stopping rule."
            )
            return RecoveryDecision(
                transaction_id=txn_id,
                customer_name=cust_name,
                original_amount=amount,
                category=FailureCategory.PERMANENT_FAIL,
                action=RecoveryAction.HARD_STOP,
                confidence_score=1.0,
                stopping_rule_applied=True,
                audit_trace=f"Anti-harassment ceiling reached ({retries}/{cls.RETRY_CEILING}). Quarantined into DLQ.",
                customer_message=None,
                payment_method=payment_method,
                raw_error_code=record.error_code,
                raw_error_description=record.error_description,
                retry_delay_minutes=0,
                recovery_payment_link=None
            )

        # 2. Permanent Failure / Mandate / Card Expiry -> Alternative UPI Nudge
        is_mandate_or_card_fail = (
            any(kw in err_code for kw in ["CARD_EXPIRED", "EXPIRED", "MANDATE", "ACCOUNT_CLOSED", "AUTH_FAILED", "REVOKED", "LIMIT_EXCEEDED"])
            or any(kw in err_desc for kw in ["EXPIRED", "MANDATE", "CARD", "REVOKED", "CLOSED"])
            or payment_method in ["mandate", "recurring", "autopay"]
        )

        is_bank_downtime = (
            any(kw in err_code for kw in ["TIMEOUT", "GATEWAY_TIMEOUT", "ISSUER_BANK_TIMEOUT", "SWITCH_DOWN", "BANK_DOWNTIME", "DOWN"])
            or any(kw in err_desc for kw in ["SWITCH DOWN", "BANK DOWNTIME", "NPCI TIMEOUT", "ISSUER TIMEOUT", "SWITCH DEGRADED"])
        )

        if is_mandate_or_card_fail and not is_bank_downtime:
            short_id = txn_id[-5:] if len(txn_id) >= 5 else txn_id
            mandate_link = f"https://rzp.io/l/mandate_update_{short_id}"
            nudge_copy = (
                f"Hi {cust_name}, aapka {payment_method.upper()} payment method update hona baaki hai. "
                f"Tap to switch to UPI Auto-Pay mandate: {mandate_link}"
            )
            return RecoveryDecision(
                transaction_id=txn_id,
                customer_name=cust_name,
                original_amount=amount,
                category=FailureCategory.PERMANENT_FAIL,
                action=RecoveryAction.ALTERNATIVE_UPI_NUDGE,
                confidence_score=0.99,
                stopping_rule_applied=False,
                audit_trace="Non-recoverable permanent failure or mandate decline. Autonomous migration route initiated to UPI Auto-Pay mandate.",
                customer_message=nudge_copy,
                payment_method=payment_method,
                raw_error_code=record.error_code,
                raw_error_description=record.error_description,
                retry_delay_minutes=0,
                recovery_payment_link=mandate_link
            )

        # 3. Bank Switch Downtime / Timeout Failures -> Cascading Fallback + Smart Retry
        if is_bank_downtime:
            jitter = random.randint(2, 9)
            scheduled_delay = cls.COOLING_WINDOW_MINUTES + jitter
            fallback_route = "NPCI Central Switch (Direct UPI)" if payment_method == "upi" else "IMPS Immediate Rail"

            return RecoveryDecision(
                transaction_id=txn_id,
                customer_name=cust_name,
                original_amount=amount,
                category=FailureCategory.BANK_DOWNTIME,
                action=RecoveryAction.SMART_RETRY,
                confidence_score=0.96,
                stopping_rule_applied=False,
                audit_trace=f"Bank switch degraded. Scheduled decorrelated jitter retry (+{scheduled_delay}m). Self-healing fallback: {fallback_route}.",
                customer_message=None,
                payment_method=payment_method,
                raw_error_code=record.error_code,
                raw_error_description=record.error_description,
                retry_delay_minutes=scheduled_delay,
                recovery_payment_link=None
            )

        # 4. Soft Failures (Insufficient Funds, Checkout Drop) -> Dynamic WhatsApp Nudge
        short_id = txn_id[-5:] if len(txn_id) >= 5 else txn_id
        dynamic_link = f"https://rzp.io/i/test_{short_id}"
        nudge_copy = f"Hi {cust_name}! Aapka ₹{int(amount)} ka payment complete nahi ho paya. Tap here to retry securely via UPI: {dynamic_link}"
        return RecoveryDecision(
            transaction_id=txn_id,
            customer_name=cust_name,
            original_amount=amount,
            category=FailureCategory.INSUFFICIENT_FUNDS,
            action=RecoveryAction.DYNAMIC_LINK_WHATSAPP,
            confidence_score=0.94,
            stopping_rule_applied=False,
            audit_trace="Soft failure detected. Dynamic Razorpay link generated with FinOps-governed AI recovery copy.",
            customer_message=nudge_copy,
            payment_method=payment_method,
            raw_error_code=record.error_code,
            raw_error_description=record.error_description,
            retry_delay_minutes=0,
            recovery_payment_link=dynamic_link
        )