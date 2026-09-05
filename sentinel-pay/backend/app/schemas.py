from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class FailureCategory(str, Enum):
    BANK_DOWNTIME = "BANK_DOWNTIME"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    PERMANENT_FAIL = "PERMANENT_FAIL"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    AUTH_DECLINE = "AUTH_DECLINE"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    CHECKOUT_ABANDONED = "CHECKOUT_ABANDONED"

class RecoveryAction(str, Enum):
    SMART_RETRY = "SMART_RETRY"
    DYNAMIC_LINK_WHATSAPP = "DYNAMIC_LINK_WHATSAPP"
    ALTERNATIVE_UPI_NUDGE = "ALTERNATIVE_UPI_NUDGE"
    HARD_STOP = "HARD_STOP"

class TransactionRecord(BaseModel):
    transaction_id: str
    customer_name: str
    customer_phone: Optional[str] = "+919876543210"
    amount: float
    payment_method: str = "upi"
    error_code: str
    error_description: str
    retry_count: int = 0
    timestamp: str = "2026-08-22T14:00:00Z"

class RecoveryDecision(BaseModel):
    transaction_id: str
    customer_name: str
    customer_phone: Optional[str] = None
    original_amount: float
    payment_method: str
    category: FailureCategory
    action: RecoveryAction
    confidence_score: float
    stopping_rule_applied: bool
    audit_trace: str
    customer_message: Optional[str] = None
    raw_error_code: Optional[str] = None
    raw_error_description: Optional[str] = None
    retry_delay_minutes: int = 0
    recovery_payment_link: Optional[str] = None

# Backwards-compatible alias for state_engine.py imports
DecisionResult = RecoveryDecision

class WebhookEvent(BaseModel):
    event: str = "payment.failed"
    payload: Dict[str, Any] = Field(default_factory=dict)