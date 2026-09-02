from typing import Dict, List
from pydantic import BaseModel

class BankSwitchStatus(BaseModel):
    bank_code: str
    bank_name: str
    rail: str  # UPI, Mandate, Cards, Netbanking
    success_rate: float
    status: str  # OPERATIONAL, DEGRADED, DOWNTIME
    avg_latency_ms: int

class BankHealthService:
    @staticmethod
    def get_switch_matrix() -> List[BankSwitchStatus]:
        return [
            BankSwitchStatus(
                bank_code="HDFC",
                bank_name="HDFC Bank UPI Switch",
                rail="UPI 2.0",
                success_rate=98.4,
                status="OPERATIONAL",
                avg_latency_ms=210
            ),
            BankSwitchStatus(
                bank_code="SBI",
                bank_name="State Bank of India Core Switch",
                rail="e-Mandate / eNACH",
                success_rate=74.2,
                status="DEGRADED",
                avg_latency_ms=1840
            ),
            BankSwitchStatus(
                bank_code="ICICI",
                bank_name="ICICI NetBanking Switch",
                rail="NetBanking",
                success_rate=99.1,
                status="OPERATIONAL",
                avg_latency_ms=180
            ),
            BankSwitchStatus(
                bank_code="NPCI",
                bank_name="NPCI Central Switch",
                rail="UPI Auto-Pay",
                success_rate=96.8,
                status="OPERATIONAL",
                avg_latency_ms=310
            ),
            BankSwitchStatus(
                bank_code="AXIS",
                bank_name="Axis Card Gateway",
                rail="Cards (RuPay/Visa)",
                success_rate=58.0,
                status="DOWNTIME",
                avg_latency_ms=4200
            )
        ]