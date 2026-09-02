import json
import random

first_names = ["Aarav", "Sneha", "Rohan", "Priya", "Vikram", "Ananya", "Karan", "Pooja", "Rahul", "Neha", "Aditya", "Meera"]
last_names = ["Sharma", "Verma", "Patel", "Nair", "Reddy", "Kulkarni", "Gupta", "Iyer", "Chopra", "Deshmukh"]

scenarios = [
    {"code": "ISSUER_BANK_TIMEOUT", "desc": "HDFC UPI switch unavailable", "method": "upi", "retries": [0, 1]},
    {"code": "INSUFFICIENT_FUNDS", "desc": "Account balance below threshold", "method": "upi", "retries": [0, 1, 2]},
    {"code": "USER_DROPPED", "desc": "User exited checkout window at OTP screen", "method": "upi", "retries": [0]},
    {"code": "CARD_EXPIRED", "desc": "Debit card expiry date reached", "method": "card", "retries": [0]},
    {"code": "LIMIT_EXCEEDED", "desc": "Recurring mandate limit exceeded", "method": "mandate", "retries": [3, 4]}, # Triggers Circuit Breaker
    {"code": "NPCI_SWITCH_DEGRADED", "desc": "SBI Netbanking node unresponsive", "method": "netbanking", "retries": [0, 1]},
    {"code": "INTERNATIONAL_BLOCKED", "desc": "International card auth disabled by issuer", "method": "card", "retries": [1]}
]

dataset = []

for i in range(1, 51):
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    scenario = random.choice(scenarios)
    amount = random.choice([299.0, 499.0, 999.0, 1499.0, 2499.0, 4999.0, 8999.0])
    retry = random.choice(scenario["retries"])
    
    dataset.append({
        "transaction_id": f"txn_ind_{i:03d}",
        "customer_name": name,
        "customer_phone": f"+9198{random.randint(10000000, 99999999)}",
        "amount": amount,
        "payment_method": scenario["method"],
        "error_code": scenario["code"],
        "error_description": scenario["desc"],
        "retry_count": retry,
        "timestamp": "2026-08-22T10:00:00Z"
    })

with open("../data/synthetic_failures_100.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2)

print(f"Successfully generated {len(dataset)} diverse FinTech failure records in data/synthetic_failures_100.json")