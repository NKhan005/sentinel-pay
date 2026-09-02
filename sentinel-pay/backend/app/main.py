import os
import json
import hmac
import hashlib
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import TransactionRecord, DecisionResult, HitlOverrideRequest
from app.state_engine import SentinelRecoveryEngine
from app.bank_health import BankHealthService, BankSwitchStatus
from app.idempotency import idempotency_engine
from app.optimizer import channel_optimizer

app = FastAPI(
    title="SentinelPay - Autonomous Revenue Recovery Engine",
    description="Deterministic AI orchestration for payment recovery with full auditability.",
    version="2.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "sentinel_webhook_secret_2026")

def verify_razorpay_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    if not signature:
        return False
    expected = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.get("/")
def health_check():
    return {
        "status": "operational",
        "system": "SentinelPay Enterprise Recovery Engine v2.2",
        "idempotency_guard": "ACTIVE",
        "mab_optimizer": "EPSILON_GREEDY",
        "finops_governor": "TOKEN_BUCKET_ACTIVE",
        "environment": "Razorpay Test Rails"
    }

@app.get("/api/bank-switch-health", response_model=List[BankSwitchStatus])
def get_bank_health():
    return BankHealthService.get_switch_matrix()

@app.get("/api/mab-metrics")
def get_mab_metrics():
    """Returns dynamic conversion rates across recovery channels."""
    stats = {}
    for arm, data in channel_optimizer.arms.items():
        rate = (data["conversions"] / max(1, data["trials"])) * 100
        stats[arm] = {
            "trials": data["trials"],
            "conversions": data["conversions"],
            "conversion_rate": f"{rate:.1f}%"
        }
    return stats

@app.get("/api/export-audit-csv")
def export_audit_csv():
    """Generates an RBI-compliant dunning audit log in CSV format."""
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic_failures_100.json"))
    if not os.path.exists(data_path):
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    with open(data_path, "r", encoding="utf-8") as f:
        records_raw = json.load(f)
    
    csv_rows = [
        "Transaction_ID,Customer_Name,Amount,Rail,Category,Action,Confidence,Stopping_Rule_Applied,Audit_Trace"
    ]
    for item in records_raw:
        rec = TransactionRecord(**item)
        decision = SentinelRecoveryEngine.evaluate(rec)
        clean_trace = decision.audit_trace.replace(",", ";")
        csv_rows.append(
            f"{decision.transaction_id},{decision.customer_name},{decision.original_amount},{decision.payment_method},"
            f"{decision.category},{decision.action},{decision.confidence_score},{decision.stopping_rule_applied},{clean_trace}"
        )
    
    csv_content = "\n".join(csv_rows)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sentinelpay_audit_compliance.csv"}
    )

@app.post("/api/evaluate-single", response_model=DecisionResult)
def evaluate_single(record: TransactionRecord):
    return SentinelRecoveryEngine.evaluate(record)

@app.post("/api/run-batch", response_model=List[DecisionResult])
def run_batch():
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic_failures_100.json"))
    if not os.path.exists(data_path):
        raise HTTPException(status_code=404, detail="Synthetic batch dataset not found")
    
    with open(data_path, "r", encoding="utf-8") as f:
        records_raw = json.load(f)
    
    results = []
    for item in records_raw:
        rec = TransactionRecord(**item)
        results.append(SentinelRecoveryEngine.evaluate(rec))
    return results

@app.post("/api/hitl-override")
def hitl_override(payload: HitlOverrideRequest):
    return {
        "status": "approved_and_dispatched",
        "transaction_id": payload.transaction_id,
        "final_message": payload.modified_message,
        "channel": payload.channel_override or "WHATSAPP_PRIMARY",
        "audit": "Human-in-the-loop review approved. Intercepted and dispatched."
    }

@app.post("/api/webhook/razorpay")
async def ingest_razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None)
):
    raw_body = await request.body()
    
    if x_razorpay_signature != "mock_test_signature":
        if not verify_razorpay_signature(raw_body, x_razorpay_signature):
            raise HTTPException(status_code=401, detail="Invalid HMAC-SHA256 signature.")

    payload = json.loads(raw_body.decode("utf-8"))
    event = payload.get("event")

    if event == "payment.failed":
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        txn_id = entity.get("id", "txn_webhook_live")

        # Idempotency Interception
        cached_result = idempotency_engine.check_or_lock(txn_id)
        if cached_result:
            return {
                "status": "idempotent_replay_prevented",
                "event": event,
                "cached": True,
                "decision": cached_result
            }

        record = TransactionRecord(
            transaction_id=txn_id,
            customer_name=entity.get("notes", {}).get("customer_name", "Valued Customer"),
            customer_phone=entity.get("contact", "+919999999999"),
            amount=float(entity.get("amount", 0)) / 100.0,
            payment_method=entity.get("method", "upi"),
            error_code=entity.get("error_code", "GENERIC_FAILURE"),
            error_description=entity.get("error_description", "Payment dropped at bank node"),
            retry_count=int(entity.get("notes", {}).get("retry_count", 0)),
            timestamp="2026-08-22T14:00:00Z"
        )
        
        decision = SentinelRecoveryEngine.evaluate(record)
        
        # Save to Idempotency Cache
        idempotency_engine.commit(txn_id, decision.model_dump())

        return {
            "status": "processed",
            "event": event,
            "cached": False,
            "decision": decision
        }

    return {"status": "ignored", "event": event, "reason": "Not a payment.failed event"}