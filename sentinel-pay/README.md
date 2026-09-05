# 🛡️ SentinelPay | Autonomous Revenue Recovery Engine

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2.0+-E92063?style=flat&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/PyTest-10%2F10%20Passing-brightgreen?style=flat&logo=pytest&logoColor=white)](https://pytest.org)
[![Compliance](https://img.shields.io/badge/RBI-Cybersecurity%20Framework-blue?style=flat)](#compliance--auditability)
[![Accessibility](https://img.shields.io/badge/WCAG-2.1%20AA%20Compliant-orange?style=flat)](#human-in-the-loop-hitl--dashboard)

SentinelPay is an enterprise-grade autonomous revenue recovery engine purpose-built for Indian payment rails (UPI, NetBanking, Recurring Mandates, and Cards). Rather than treating every transaction failure identically or overwhelming consumers with immediate, naive retries, SentinelPay correlates gateway health telemetry with error classifications to maximize recovered GMV while eliminating customer fatigue and upstream switch saturation.

## ⚡ Key Highlights & Production Architecture

### 1. Deterministic State Transition Machine
* **Dynamic Failure Classification:** Webhook payloads are categorized into `BANK_DOWNTIME`, `INSUFFICIENT_FUNDS`, `PERMANENT_FAIL`, `AUTH_DECLINE`, `NETWORK_TIMEOUT`, `AUTH_EXPIRED`, or `CHECKOUT_ABANDONED`.
* **Tailored Action Routing:** Dynamically pairs failures with `SMART_RETRY`, `DYNAMIC_LINK_WHATSAPP`, `ALTERNATIVE_UPI_NUDGE`, or `HARD_STOP`.

### 2. Decorrelated Full-Jitter Exponential Backoff
* Prevents the **Thundering Herd Problem** against degraded Indian banking switches (SBI, HDFC, NPCI).
* Distributes programmatic retries across an adaptive window using mathematical jitter:
  $$T = \text{random}(\text{base\_delay}, \min(\text{cap}, \text{base\_delay} \times 2^{\text{attempt}}))$$

### 3. Dead Letter Queue (DLQ) & Circuit Breaking
* Enforces an anti-harassment stopping rule at $\ge 3$ retry attempts.
* Trapped transactions transition automatically to `HARD_STOP` and isolate into a dedicated DLQ buffer (`DLQ_MAX_RETRIES_EXCEEDED`) with full audit provenance for ops review.

### 4. Cryptographic Security & Idempotency
* **HMAC SHA-256 Webhook Verification:** Ensures incoming failure payloads originate exclusively from authentic payment gateway sources using timing-attack resistant signature checks (`hmac.compare_digest`).
* **In-Memory Idempotency Cache:** Eliminates duplicate execution risks during network retries by tracking payment IDs atomically.
* **Fintech Security Headers Middleware:** Enforces `nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, and `Strict-Transport-Security` across all endpoints.

### 5. FinOps Governor & Contextual Hinglish Dunning
* Integrates **Google Gemini 1.5 Flash** to synthesize empathetic, culturally localized Hinglish recovery copy.
* Governed by an in-memory **Token-Bucket FinOps Governor** to throttle LLM spend and prevent margin depletion during large-scale banking switch outages.

## 🏗️ System Architecture
[ Incoming Webhook (payment.failed) ]
│
▼
[ HMAC SHA-256 Signature Verification ]
│
▼
[ Idempotency & Replay Cache ]
│
▼
[ Switch Health Telemetry Engine ]
│
▼
[ Deterministic State Machine ]
├── Retry Count >= 3  ──► [ Dead Letter Queue (DLQ) ] ──► [ Circuit Breaker STOP ]
├── Bank Degradation  ──► [ Full-Jitter Backoff ]     ──► [ Silent Retry Queue ]
├── Expired Mandate   ──► [ UPI Migration Path ]      ──► [ Alternative Nudge ]
└── Customer-side Fail──► [ FinOps Token Bucket ]     ──► [ Contextual Hinglish Copy ]
│
▼
[ Live Telemetry Console & HITL Inspector ] ──► [ One-Click RBI Audit CSV Stream ]

## 🧪 Verification & Automated Test Suite

SentinelPay enforces 100% pass rates across critical payment resilience, idempotency, and regulatory constraints.

```bash
# Run the complete test suite
cd backend
python -m pytest -v


Verified Scenarios (10/10 Suites Passing):
test_health_check_endpoint: Base system readiness, DLQ status, and framework flags.

test_circuit_breaker_trips_at_three_retries: Anti-harassment ceiling enforcement.

test_bank_downtime_triggers_silent_retry: Switch downtime cooling windows without user notification.

test_permanent_failure_routes_to_mandate_nudge: Recurring card expiries migrating to UPI AutoPay.

test_webhook_signature_verification: Rejection of untrusted or forged webhook signatures.

test_idempotent_duplicate_webhook_prevention: Caching of transaction states to block duplicate runs.

test_adaptive_cooling_window_with_jitter: Math verification of full-jitter interval distributions.

test_export_audit_csv_compliance_endpoint: Dynamic generation and streaming of audit trail CSVs.

test_dead_letter_queue_quarantine_isolation: Memory isolation and tracking of quarantined records.

test_production_fintech_security_headers: Middleware validation of banking-grade security headers.

🚀 Quickstart & Local Setup
Prerequisites
Python 3.11+
Docker (Optional for containerized run)
1. Clone & Setup Virtual Environment :
git clone [https://github.com/NKhan005/sentinel-pay.git](https://github.com/NKhan005/sentinel-pay.git)
cd sentinel-pay
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
2. Install Dependencies :
cd backend
pip install -r requirements.txt
3. Launch Backend API Server :
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
Interactive API Documentation: http://localhost:8000/docs
Health Check: http://localhost:8000/
4. Launch Operations Console :
In a separate terminal or Live Server:
cd ../frontend
# Run with Python standard HTTP module or VS Code Live Server
python -m http.server 3000
Access the console at: http://localhost:3000

🐳 Docker Containerization
Deploy SentinelPay as an isolated, non-root microservice :
# Build the production image
docker build -t sentinelpay:latest .
# Run the container
docker run -d -p 8000:8000 --name sentinelpay-service sentinelpay:latest
# Check container health probe
docker ps

🛡️ Compliance & Auditability :
RBI Regulatory Alignment: SentinelPay conforms to digital lending and collections recovery guidelines by prohibiting persistent automated retries after explicit terminal decline codes and limiting retries strictly to three attempts.
Provable Audit Logs: Every state change, jitter calculation, and dunning intervention is streamed to /api/export-audit-csv, providing full lifecycle explainability for financial reconciliations and compliance audits.