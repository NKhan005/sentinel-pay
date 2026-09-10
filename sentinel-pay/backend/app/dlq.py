"""
Dead Letter Queue (DLQ) Quarantine Manager
Handles anti-harassment circuit breaker isolations, test fixtures, and audited manual pardons.
"""
from typing import List, Dict, Optional
from datetime import datetime

class DeadLetterQueueManager:
    def __init__(self):
        self._quarantined_records: Dict[str, Dict] = {}
        self._pardon_audit_log: List[Dict] = []
        self.seed_defaults()

    def seed_defaults(self) -> None:
        """Seed initial records for dashboard demonstration."""
        self._quarantined_records = {
            "txn_ind_014": {
                "transaction_id": "txn_ind_014",
                "customer_name": "Neha Gupta",
                "customer_phone": "+919876543224",
                "amount": 1499.00,
                "payment_method": "upi",
                "triage_code": "DLQ_MAX_RETRIES_EXCEEDED",
                "quarantine_reason": "Exceeded maximum automated retry ceiling (3). Enforced anti-harassment stopping rule.",
                "quarantined_at": "2026-09-08T10:14:00Z",
                "status": "QUARANTINED"
            },
            "txn_ind_023": {
                "transaction_id": "txn_ind_023",
                "customer_name": "Sneha Patel",
                "customer_phone": "+919876543233",
                "amount": 999.00,
                "payment_method": "card",
                "triage_code": "DLQ_MAX_RETRIES_EXCEEDED",
                "quarantine_reason": "Exceeded maximum automated retry ceiling (3). Enforced anti-harassment stopping rule.",
                "quarantined_at": "2026-09-08T10:18:20Z",
                "status": "QUARANTINED"
            },
            "txn_ind_036": {
                "transaction_id": "txn_ind_036",
                "customer_name": "Aarav Kulkarni",
                "customer_phone": "+919876543246",
                "amount": 499.00,
                "payment_method": "upi",
                "triage_code": "DLQ_MAX_RETRIES_EXCEEDED",
                "quarantine_reason": "Exceeded maximum automated retry ceiling (3). Enforced anti-harassment stopping rule.",
                "quarantined_at": "2026-09-08T10:22:11Z",
                "status": "QUARANTINED"
            },
            "txn_ind_050": {
                "transaction_id": "txn_ind_050",
                "customer_name": "Ananya Nair",
                "customer_phone": "+919876543260",
                "amount": 499.00,
                "payment_method": "netbanking",
                "triage_code": "DLQ_MAX_RETRIES_EXCEEDED",
                "quarantine_reason": "Exceeded maximum automated retry ceiling (3). Enforced anti-harassment stopping rule.",
                "quarantined_at": "2026-09-08T10:29:45Z",
                "status": "QUARANTINED"
            }
        }

    def push(self, record_dict: Optional[Dict] = None, **kwargs) -> None:
        data = dict(record_dict) if record_dict else {}
        data.update(kwargs)

        txn_id = data.get("transaction_id")
        if not txn_id:
            return

        self._quarantined_records[txn_id] = {
            "triage_code": data.get("triage_code", "DLQ_MAX_RETRIES_EXCEEDED"),
            **data,
            "quarantined_at": data.get("quarantined_at") or (datetime.utcnow().isoformat() + "Z"),
            "status": data.get("status", "QUARANTINED")
        }

    def isolate(self, record_dict: Optional[Dict] = None, **kwargs) -> None:
        self.push(record_dict, **kwargs)

    def clear(self) -> None:
        self._quarantined_records.clear()
        self._pardon_audit_log.clear()

    def get_all(self) -> List[Dict]:
        return list(self._quarantined_records.values())

    def pardon_transaction(self, txn_id: str, officer_reason: str, officer_id: str = "FIN_OFFICER_01") -> Optional[Dict]:
        if txn_id not in self._quarantined_records:
            return None
        
        pardoned_item = self._quarantined_records.pop(txn_id)
        pardon_entry = {
            "transaction_id": txn_id,
            "officer_id": officer_id,
            "officer_reason": officer_reason,
            "pardoned_at": datetime.utcnow().isoformat() + "Z",
            "dispatch_link": f"https://rzp.io/i/pardon_{str(txn_id)[-6:]}"
        }
        self._pardon_audit_log.append(pardon_entry)
        return {**pardoned_item, **pardon_entry, "status": "FORCE_DISPATCHED"}

    def get_pardon_history(self) -> List[Dict]:
        return self._pardon_audit_log

dlq_manager = DeadLetterQueueManager()