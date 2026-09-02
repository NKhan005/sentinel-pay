import os
import random
import time
from typing import Optional
from dotenv import load_dotenv
from app.schemas import TransactionRecord, DecisionResult, FailureCategory, RecoveryAction
from app.razorpay_client import RazorpayClientService
from app.bank_health import BankHealthService

load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

class FinOpsGovernor:
    """
    Token-bucket rate limiter to protect merchant margins during major bank outages.
    Prevents runaway LLM API token spend during failure spikes.
    """
    def __init__(self, capacity: int = 15, refill_rate: float = 2.0):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_update = time.time()

    def allow_llm_generation(self) -> bool:
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_update = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

finops_governor = FinOpsGovernor()

class SentinelRecoveryEngine:
    @staticmethod
    def classify_failure(record: TransactionRecord) -> FailureCategory:
        code = record.error_code.upper()
        if "TIMEOUT" in code or "BANK_UNAVAILABLE" in code or "ISSUER" in code or "DEGRADED" in code or "429" in code:
            return FailureCategory.BANK_DOWNTIME
        elif "INSUFFICIENT" in code or "LIMIT_EXCEEDED" in code:
            return FailureCategory.INSUFFICIENT_FUNDS
        elif "USER_DROPPED" in code or "ABANDONED" in code:
            return FailureCategory.CHECKOUT_ABANDONED
        elif "EXPIRED" in code or "BLOCKED" in code:
            return FailureCategory.PERMANENT_FAIL
        return FailureCategory.AUTH_EXPIRED

    @classmethod
    def calculate_adaptive_delay(cls, method: str) -> int:
        """
        Dynamically adjusts retry cooling window based on live switch degradation.
        """
        switches = BankHealthService.get_switch_matrix()
        # Find matching or fallback switch
        target_switch = next((s for s in switches if s.rail.lower() in method.lower() or s.bank_code in method.upper()), None)
        
        base_delay = 30
        if target_switch:
            if target_switch.status == "DOWNTIME":
                base_delay = 90
            elif target_switch.status == "DEGRADED":
                base_delay = 60
        
        # Add Full Jitter (+/- 10 minutes) to avoid synchronized thundering herd retries
        jitter = random.randint(-5, 10)
        return max(15, base_delay + jitter)

    @staticmethod
    def generate_ai_nudge(customer_name: str, amount: float, link: str, reason: str) -> str:
        # Check FinOps Governor to avoid LLM rate limit exhaustion
        if not finops_governor.allow_llm_generation():
            return f"Hi {customer_name}! Aapka ₹{amount:.0f} ka payment verify nahi ho paya. Tap here to retry securely via UPI: {link}"

        if GEMINI_KEY and GEMINI_KEY != "your_gemini_api_key_here":
            try:
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = (
                    f"Write a friendly, polite 1-sentence WhatsApp message in natural conversational Hinglish "
                    f"to customer {customer_name} whose payment of ₹{amount:.0f} failed due to '{reason}'. "
                    f"Include this 1-click recovery payment link directly in the message: {link}. Keep it under 25 words."
                )
                res = model.generate_content(prompt)
                if res.text:
                    return res.text.strip().replace('"', '')
            except Exception:
                pass
        
        return f"Hi {customer_name}! Aapka ₹{amount:.0f} ka payment complete nahi ho paya. Tap here to retry securely via UPI: {link}"

    @classmethod
    def evaluate(cls, record: TransactionRecord) -> DecisionResult:
        category = cls.classify_failure(record)
        
        # Hard FinTech Guardrail: Max 3 Retries
        if record.retry_count >= 3:
            return DecisionResult(
                transaction_id=record.transaction_id,
                customer_name=record.customer_name,
                customer_phone=record.customer_phone,
                original_amount=record.amount,
                payment_method=record.payment_method,
                category=category,
                action=RecoveryAction.HARD_STOP,
                confidence_score=1.0,
                retry_delay_minutes=0,
                recovery_payment_link=None,
                customer_message=None,
                stopping_rule_applied=True,
                audit_trace="Circuit Breaker: Maximum retry threshold reached (3). Enforced anti-harassment stopping rule under RBI dunning guidelines.",
                raw_error_code=record.error_code,
                raw_error_description=record.error_description
            )

        # Permanent Failures: Route away from Dead Cards to UPI 2.0 Auto-Pay
        if category == FailureCategory.PERMANENT_FAIL:
            link = f"https://rzp.io/l/mandate_update_{record.transaction_id[-4:]}"
            return DecisionResult(
                transaction_id=record.transaction_id,
                customer_name=record.customer_name,
                customer_phone=record.customer_phone,
                original_amount=record.amount,
                payment_method=record.payment_method,
                category=category,
                action=RecoveryAction.ALTERNATIVE_UPI_NUDGE,
                confidence_score=0.99,
                retry_delay_minutes=0,
                recovery_payment_link=link,
                customer_message=f"Hi {record.customer_name}, aapka card expire ho chuka hai. Tap to switch to UPI Auto-pay: {link}",
                stopping_rule_applied=False,
                audit_trace="Non-recoverable card decline detected. Autonomous migration route initiated to UPI Auto-Pay mandate.",
                raw_error_code=record.error_code,
                raw_error_description=record.error_description
            )

        # Bank Downtime: Dynamic cooling based on Switch Latency & Success Rate
        if category == FailureCategory.BANK_DOWNTIME:
            adaptive_delay = cls.calculate_adaptive_delay(record.payment_method)
            return DecisionResult(
                transaction_id=record.transaction_id,
                customer_name=record.customer_name,
                customer_phone=record.customer_phone,
                original_amount=record.amount,
                payment_method=record.payment_method,
                category=category,
                action=RecoveryAction.SMART_RETRY,
                confidence_score=0.96,
                retry_delay_minutes=adaptive_delay,
                recovery_payment_link=None,
                customer_message=None,
                stopping_rule_applied=False,
                audit_trace=f"Bank switch degraded. Scheduled adaptive silent backoff with jitter ({adaptive_delay} mins) to avoid thundering herd.",
                raw_error_code=record.error_code,
                raw_error_description=record.error_description
            )

        # Soft Failures: Dynamic Link + AI Recovery Copy
        pay_link = RazorpayClientService.create_payment_link(
            amount_inr=record.amount,
            customer_name=record.customer_name,
            customer_phone=record.customer_phone,
            description=f"Recovery for {record.transaction_id}"
        )
        ai_msg = cls.generate_ai_nudge(record.customer_name, record.amount, pay_link, record.error_description)

        return DecisionResult(
            transaction_id=record.transaction_id,
            customer_name=record.customer_name,
            customer_phone=record.customer_phone,
            original_amount=record.amount,
            payment_method=record.payment_method,
            category=category,
            action=RecoveryAction.DYNAMIC_LINK_WHATSAPP,
            confidence_score=0.94,
            retry_delay_minutes=5,
            recovery_payment_link=pay_link,
            customer_message=ai_msg,
            stopping_rule_applied=False,
            audit_trace="Soft failure detected. Dynamic Razorpay link generated with FinOps-governed AI recovery copy.",
            raw_error_code=record.error_code,
            raw_error_description=record.error_description
        )