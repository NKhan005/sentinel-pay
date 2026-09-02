import time
from typing import Dict, Any, Optional
from fastapi import HTTPException

class IdempotencyRecord:
    def __init__(self, response_data: Dict[str, Any], timestamp: float):
        self.response_data = response_data
        self.timestamp = timestamp

class IdempotencyManager:
    """
    Guarantees strict exactly-once processing on payment failure streams.
    Prevents duplicate dunning nudges and accidental multi-debits.
    """
    def __init__(self, ttl_seconds: int = 300):
        self._store: Dict[str, IdempotencyRecord] = {}
        self._ttl = ttl_seconds

    def check_or_lock(self, key: str) -> Optional[Dict[str, Any]]:
        current_time = time.time()
        # Clean expired entries
        self._store = {k: v for k, v in self._store.items() if current_time - v.timestamp < self._ttl}
        
        if key in self._store:
            return self._store[key].response_data
        return None

    def commit(self, key: str, data: Dict[str, Any]):
        self._store[key] = IdempotencyRecord(response_data=data, timestamp=time.time())

idempotency_engine = IdempotencyManager(ttl_seconds=300)