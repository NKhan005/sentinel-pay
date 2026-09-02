import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import TransactionRecord, FailureCategory, RecoveryAction
from app.state_engine import SentinelRecoveryEngine

client = TestClient(app)

def test_health_check_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "operational"

def test_circuit_breaker_trips_at_three_retries():
    record = TransactionRecord(
        transaction_id="txn_test_circuit_01",
        customer_name="Aarav Sharma",
        customer_phone="+919876543210",
        amount=1499.0,
        payment_method="upi",
        error_code="INSUFFICIENT_FUNDS",
        error_description="Account balance low",
        retry_count=3,
        timestamp="2026-08-22T14:00:00Z"
    )
    result = SentinelRecoveryEngine.evaluate(record)
    assert result.action == RecoveryAction.HARD_STOP
    assert result.stopping_rule_applied is True
    assert result.confidence_score == 1.0

def test_bank_downtime_triggers_silent_retry():
    record = TransactionRecord(
        transaction_id="txn_test_downtime_01",
        customer_name="Priya Patel",
        customer_phone="+919876543210",
        amount=4999.0,
        payment_method="netbanking",
        error_code="ISSUER_BANK_TIMEOUT",
        error_description="HDFC switch down",
        retry_count=0,
        timestamp="2026-08-22T14:00:00Z"
    )
    result = SentinelRecoveryEngine.evaluate(record)
    assert result.category == FailureCategory.BANK_DOWNTIME
    assert result.action == RecoveryAction.SMART_RETRY
    assert result.retry_delay_minutes >= 15
    assert result.customer_message is None

def test_permanent_failure_routes_to_mandate_nudge():
    record = TransactionRecord(
        transaction_id="txn_test_expired_01",
        customer_name="Rohan Verma",
        customer_phone="+919876543210",
        amount=899.0,
        payment_method="card",
        error_code="CARD_EXPIRED",
        error_description="Debit card has expired",
        retry_count=0,
        timestamp="2026-08-22T14:00:00Z"
    )
    result = SentinelRecoveryEngine.evaluate(record)
    assert result.category == FailureCategory.PERMANENT_FAIL
    assert result.action == RecoveryAction.ALTERNATIVE_UPI_NUDGE
    assert "mandate_update" in result.recovery_payment_link

def test_webhook_signature_verification():
    raw_payload = json.dumps({"event": "payment.failed"}).encode("utf-8")
    
    # Valid mock bypass signature
    response = client.post(
        "/api/webhook/razorpay",
        headers={"X-Razorpay-Signature": "mock_test_signature"},
        content=raw_payload
    )
    assert response.status_code == 200

    # Invalid signature must return 401 Unauthorized
    invalid_response = client.post(
        "/api/webhook/razorpay",
        headers={"X-Razorpay-Signature": "invalid_forged_signature"},
        content=raw_payload
    )
    assert invalid_response.status_code == 401

def test_idempotent_duplicate_webhook_prevention():
    raw_payload = json.dumps({
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_idempotent_unique_99",
                    "amount": 199900,
                    "method": "upi",
                    "error_code": "USER_DROPPED",
                    "error_description": "User dropped checkout",
                    "contact": "+919876543210",
                    "notes": {"customer_name": "Test User", "retry_count": 0}
                }
            }
        }
    }).encode("utf-8")

    # First attempt: Fresh processing
    res1 = client.post(
        "/api/webhook/razorpay",
        headers={"X-Razorpay-Signature": "mock_test_signature"},
        content=raw_payload
    )
    assert res1.status_code == 200
    assert res1.json()["cached"] is False

    # Second immediate attempt with same payload: Must be caught by Idempotency engine
    res2 = client.post(
        "/api/webhook/razorpay",
        headers={"X-Razorpay-Signature": "mock_test_signature"},
        content=raw_payload
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "idempotent_replay_prevented"
    assert res2.json()["cached"] is True

def test_adaptive_cooling_window_with_jitter():
    record = TransactionRecord(
        transaction_id="txn_test_jitter_01",
        customer_name="Karan Verma",
        customer_phone="+919876543210",
        amount=3499.0,
        payment_method="card",
        error_code="GATEWAY_TIMEOUT_429",
        error_description="Axis Card Gateway switch timeout",
        retry_count=0,
        timestamp="2026-08-22T14:00:00Z"
    )
    result = SentinelRecoveryEngine.evaluate(record)
    assert result.category == FailureCategory.BANK_DOWNTIME
    assert result.action == RecoveryAction.SMART_RETRY
    assert result.retry_delay_minutes >= 15

def test_export_audit_csv_compliance_endpoint():
    response = client.get("/api/export-audit-csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "Transaction_ID,Customer_Name,Amount" in response.text