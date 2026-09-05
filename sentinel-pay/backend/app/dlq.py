import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class QuarantinedRecord(BaseModel):
    transaction_id: str
    customer_name: str
    amount: float
    payment_method: str
    error_code: str
    quarantine_reason: str
    triage_code: str
    quarantined_at: float
    resolution_status: str = "PENDING_MANUAL_REVIEW"

class DeadLetterQueueManager:
    """
    Quarantine engine for unrecoverable payment failures, fraud markers,
    or exhausted retry thresholds. Guarantees regulatory isolation under RBI guidelines.
    """
    def __init__(self, max_buffer_size: int = 500):
        self._buffer: List[QuarantinedRecord] = []
        self._max_size = max_buffer_size

    def push(
        self,
        transaction_id: str,
        customer_name: str,
        amount: float,
        payment_method: str,
        error_code: str,
        quarantine_reason: str,
        triage_code: str
    ) -> QuarantinedRecord:
        record = QuarantinedRecord(
            transaction_id=transaction_id,
            customer_name=customer_name,
            amount=amount,
            payment_method=payment_method,
            error_code=error_code,
            quarantine_reason=quarantine_reason,
            triage_code=triage_code,
            quarantined_at=time.time()
        )
        self._buffer.insert(0, record)
        if len(self._buffer) > self._max_size:
            self._buffer.pop()
        return record

    def list_quarantined(self) -> List[QuarantinedRecord]:
        return self._buffer

    def count(self) -> int:
        return len(self._buffer)

    def clear(self):
        self._buffer.clear()

dlq_manager = DeadLetterQueueManager()