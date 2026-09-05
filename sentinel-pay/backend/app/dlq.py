from typing import List, Dict, Any, Optional
from datetime import datetime

class DeadLetterQueueManager:
    def __init__(self):
        self._queue: List[Dict[str, Any]] = []

    def push(
        self,
        record: Any = None,
        reason: Optional[str] = None,
        transaction_id: Optional[str] = None,
        customer_name: Optional[str] = None,
        amount: Optional[float] = None,
        payment_method: Optional[str] = None,
        error_code: Optional[str] = None,
        quarantine_reason: Optional[str] = None,
        triage_code: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        # Handle call if passed via record object or via direct kwargs
        t_id = transaction_id or getattr(record, "transaction_id", "unknown")
        c_name = customer_name or getattr(record, "customer_name", "unknown")
        amt = amount if amount is not None else getattr(record, "amount", 0.0)
        p_method = payment_method or getattr(record, "payment_method", "upi")
        e_code = error_code or getattr(record, "error_code", "UNKNOWN_FAIL")
        q_reason = quarantine_reason or reason or "Exceeded retry threshold or failed policy"
        t_code = triage_code or kwargs.get("triage_code", "DLQ_ISOLATION")

        item = {
            "transaction_id": t_id,
            "customer_name": c_name,
            "amount": amt,
            "payment_method": p_method,
            "error_code": e_code,
            "quarantine_reason": q_reason,
            "reason": q_reason,
            "triage_code": t_code,
            "quarantined_at": datetime.utcnow().isoformat()
        }
        self._queue.append(item)
        return item

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self._queue)

    def get_records(self) -> List[Dict[str, Any]]:
        return list(self._queue)

    def clear(self):
        self._queue.clear()

# Singleton instance
dlq_manager = DeadLetterQueueManager()