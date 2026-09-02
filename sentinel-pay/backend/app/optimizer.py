import random
from typing import Dict

class RecoveryChannelOptimizer:
    """
    Multi-Armed Bandit (Epsilon-Greedy) to autonomously optimize 
    recovery conversion across WhatsApp, SMS, and UPI Auto-Pay.
    """
    def __init__(self, epsilon: float = 0.15):
        self.epsilon = epsilon
        # Arms: channel -> [attempts, estimated_conversions]
        self.arms: Dict[str, Dict[str, float]] = {
            "WHATSAPP_1CLICK": {"trials": 120, "conversions": 86},  # ~71% CR
            "SMS_PRIORITY": {"trials": 95, "conversions": 42},       # ~44% CR
            "UPI_AUTOPAY_MIGRATE": {"trials": 60, "conversions": 49} # ~81% CR (High-intent)
        }

    def select_optimal_channel(self, failure_category: str) -> str:
        # Strict rule: Permanent Card Failures must always route to UPI Auto-pay migration
        if failure_category == "PERMANENT_FAIL":
            return "UPI_AUTOPAY_MIGRATE"

        # Epsilon-Greedy Exploration vs Exploitation
        if random.random() < self.epsilon:
            return random.choice(["WHATSAPP_1CLICK", "SMS_PRIORITY"])
        
        # Exploit the best performing channel
        best_channel = max(
            ["WHATSAPP_1CLICK", "SMS_PRIORITY"],
            key=lambda arm: self.arms[arm]["conversions"] / max(1, self.arms[arm]["trials"])
        )
        return best_channel

channel_optimizer = RecoveryChannelOptimizer()