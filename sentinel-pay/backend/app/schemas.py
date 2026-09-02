from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel

class FailureCategory(str, Enum):
    BANK_DOWNTIME = "BANK_DOWNTIME"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    CHECKOUT_ABANDONED = "CHECKOUT_ABANDONED"
    PERMANENT_FAIL = "PERMANENT_FAIL"
    AUTH_EXPIRED = "AUTH_EXPIRED"

class RecoveryAction(str, Enum):
    SMART_RETRY = "SMART_RETRY"
    DYNAMIC_LINK_WHATSAPP = "DYNAMIC_LINK_WHATSAPP"
    ALTERNATIVE_UPI_NUDGE = "ALTERNATIVE_UPI_NUDGE"
    HARD_STOP = "HARD_STOP"

class TransactionRecord(BaseModel):
    transaction_id: str
    customer_name: str
    customer_phone: str
    amount: float
    payment_method: str
    error_code: str
    error_description: str
    retry_count: int
    timestamp: str

class DecisionResult(BaseModel):
    transaction_id: str
    customer_name: str
    customer_phone: str
    original_amount: float
    payment_method: str
    category: FailureCategory
    action: RecoveryAction
    confidence_score: float
    retry_delay_minutes: int
    recovery_payment_link: Optional[str] = None
    customer_message: Optional[str] = None
    stopping_rule_applied: bool
    audit_trace: str
    raw_error_code: str
    raw_error_description: str

class HitlOverrideRequest(BaseModel):
    transaction_id: str
    modified_message: str
    channel_override: Optional[str] = None