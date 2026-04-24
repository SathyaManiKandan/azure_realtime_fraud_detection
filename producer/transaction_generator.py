# simulator/transaction_generator.py

import json
import random
import time
import uuid
import logging
from datetime import datetime
from faker import Faker
from config import (
    FRAUD_RATE,
    TRANSACTIONS_PER_SEC,
    TOTAL_CUSTOMERS,
    NORMAL_MERCHANTS,
    SUSPICIOUS_MERCHANTS,
    NORMAL_LOCATIONS,
    FOREIGN_LOCATIONS,
    TXN_TYPES,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

fake = Faker("en_IN")
random.seed()


# ─────────────────────────────────────────────────────────────────
# Customer generation
# ─────────────────────────────────────────────────────────────────

def generate_customers(n: int) -> list[dict]:
    """Generate a pool of n synthetic bank customers."""
    customers = []
    for i in range(n):
        # Base average spend
        base_avg = round(random.uniform(500, 15000), 2)
        customers.append({
            "customer_id":       f"CUST{str(i).zfill(4)}",
            "name":              fake.name(),
            "home_city":         random.choice(NORMAL_LOCATIONS),
            "avg_spend":         base_avg,
            # NEW: spending variability — how inconsistent this customer is
            # High variability customers naturally have large amount swings
            # making ratio-based detection harder
            "spend_std":         round(base_avg * random.uniform(0.3, 1.5), 2),
            "account_age_days":  random.randint(30, 3650),
            "phone":             fake.phone_number(),
        })
    log.info(f"Generated {n} customer profiles")
    return customers
    """Generate a pool of n synthetic bank customers."""
    customers = []
    for i in range(n):
        customers.append({
            "customer_id":       f"CUST{str(i).zfill(4)}",
            "name":              fake.name(),
            "home_city":         random.choice(NORMAL_LOCATIONS),
            "avg_spend":         round(random.uniform(500, 15000), 2),
            "account_age_days":  random.randint(30, 3650),
            "phone":             fake.phone_number(),
        })
    log.info(f"Generated {n} customer profiles")
    return customers


# ─────────────────────────────────────────────────────────────────
# Transaction generators
# ─────────────────────────────────────────────────────────────────

def _base_transaction(customer: dict) -> dict:
    return {
        "transaction_id":   str(uuid.uuid4()),
        "customer_id":      customer["customer_id"],
        "customer_name":    customer["name"],
        "account_age_days": customer["account_age_days"],
        "avg_spend":        customer["avg_spend"],
        "spend_std":        customer["spend_std"],      # ← ADD THIS
        "amount":           None,
        "merchant":         None,
        "location":         None,
        "is_foreign":       False,
        "txn_type":         random.choice(TXN_TYPES),
        "timestamp":        datetime.utcnow().isoformat(),
    }


def generate_normal_transaction(customer: dict) -> dict:
    txn = _base_transaction(customer)

    # Use normal distribution around avg_spend with spend_std
    # This means some normal transactions are naturally high
    # making it harder for the model to rely on ratio alone
    amount = round(abs(random.gauss(
        customer["avg_spend"],
        customer["spend_std"]
    )), 2)

    # Cap at a reasonable max to avoid extreme outliers in normal
    amount = min(amount, customer["avg_spend"] * 3)
    amount = max(amount, 50)   # minimum ₹50

    txn.update({
        "amount":   amount,
        "merchant": random.choice(NORMAL_MERCHANTS),
        "location": customer["home_city"],
    })
    return txn
    txn = _base_transaction(customer)

    # Occasionally normal customers make large purchases (sales, festivals etc.)
    # This creates overlap with fraud → forces model to learn combinations
    if random.random() < 0.05:    # 5% of normal txns are large
        amount = round(random.uniform(
            customer["avg_spend"] * 2,
            customer["avg_spend"] * 4
        ), 2)
    else:
        amount = round(random.uniform(50, customer["avg_spend"]), 2)

    txn.update({
        "amount":   amount,
        "merchant": random.choice(NORMAL_MERCHANTS),
        "location": customer["home_city"],
    })
    return txn
    """Generate a completely legitimate-looking transaction."""
    txn = _base_transaction(customer)
    txn.update({
        "amount":   round(random.uniform(50, customer["avg_spend"]), 2),
        "merchant": random.choice(NORMAL_MERCHANTS),
        "location": customer["home_city"],
    })
    return txn


def generate_fraud_transaction(customer: dict) -> dict:
    txn = _base_transaction(customer)
    roll = random.random()

    if roll < 0.20:
        # High amount — but with noise, sometimes only moderately high
        txn.update({
            "amount":   round(random.uniform(
                            customer["avg_spend"] * 2,
                            customer["avg_spend"] * 6    # reduced ceiling
                        ), 2),
            "merchant": random.choice(NORMAL_MERCHANTS),
            "location": customer["home_city"],
        })

    elif roll < 0.35:
        # Exceeds personal avg — tighter range to create overlap
        multiplier = random.uniform(1.2, 4.0)   # reduced from 1.5–10
        txn.update({
            "amount":   round(customer["avg_spend"] * multiplier, 2),
            "merchant": random.choice(NORMAL_MERCHANTS),
            "location": customer["home_city"],
        })

    elif roll < 0.50:
        # Foreign — amount often in normal range
        txn.update({
            "amount":     round(abs(random.gauss(
                              customer["avg_spend"] * 1.5,
                              customer["spend_std"]
                          )), 2),
            "merchant":   random.choice(NORMAL_MERCHANTS),
            "location":   random.choice(FOREIGN_LOCATIONS),
            "is_foreign": True,
        })

    elif roll < 0.65:
        # Suspicious merchant — amount can be small
        txn.update({
            "amount":   round(random.uniform(500, 30000), 2),
            "merchant": random.choice(SUSPICIOUS_MERCHANTS),
            "location": customer["home_city"],
        })

    elif roll < 0.80:
        # Odd hours — amount very close to normal range
        odd_hour  = random.choice([23, 0, 1, 2, 3, 4])
        fake_time = datetime.utcnow().replace(
            hour=odd_hour,
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        txn.update({
            "amount":    round(abs(random.gauss(
                             customer["avg_spend"] * 1.8,
                             customer["spend_std"]
                         )), 2),
            "merchant":  random.choice(NORMAL_MERCHANTS),
            "location":  customer["home_city"],
            "timestamp": fake_time.isoformat(),
        })

    else:
        # Combo — still realistic
        odd_hour  = random.choice([23, 0, 1, 2, 3])
        fake_time = datetime.utcnow().replace(hour=odd_hour)
        txn.update({
            "amount":     round(random.uniform(
                              customer["avg_spend"] * 3,
                              customer["avg_spend"] * 8
                          ), 2),
            "merchant":   random.choice(SUSPICIOUS_MERCHANTS),
            "location":   random.choice(FOREIGN_LOCATIONS),
            "is_foreign": True,
            "timestamp":  fake_time.isoformat(),
        })

    # Safety net
    if txn["amount"] is None:
        txn["amount"] = round(random.uniform(50, customer["avg_spend"]), 2)
    if txn["merchant"] is None:
        txn["merchant"] = random.choice(NORMAL_MERCHANTS)
    if txn["location"] is None:
        txn["location"] = customer["home_city"]

    return txn
    txn = _base_transaction(customer)
    roll = random.random()

    if roll < 0.20:
        # High absolute amount — but add overlap with normal range
        # NOT always > threshold, sometimes borderline
        txn.update({
            "amount":   round(random.uniform(
                            customer["avg_spend"] * 1.5,   # reduced from 75k fixed
                            customer["avg_spend"] * 8      # reduced from 500k fixed
                        ), 2),
            "merchant": random.choice(NORMAL_MERCHANTS),
            "location": customer["home_city"],
        })

    elif roll < 0.35:
        # Exceeds personal avg — but with more realistic variance
        # Sometimes only 1.5x (subtle fraud), sometimes 10x (obvious)
        multiplier = random.uniform(1.5, 10)
        txn.update({
            "amount":   round(customer["avg_spend"] * multiplier, 2),
            "merchant": random.choice(NORMAL_MERCHANTS),
            "location": customer["home_city"],
        })

    elif roll < 0.50:
        # Foreign location — amount can be normal range
        # Not always high — sometimes small foreign txns are fraud too
        txn.update({
            "amount":     round(random.uniform(500, 50000), 2),
            "merchant":   random.choice(NORMAL_MERCHANTS),
            "location":   random.choice(FOREIGN_LOCATIONS),
            "is_foreign": True,
        })

    elif roll < 0.65:
        # Suspicious merchant — small amounts too
        txn.update({
            "amount":   round(random.uniform(1000, 50000), 2),
            "merchant": random.choice(SUSPICIOUS_MERCHANTS),
            "location": customer["home_city"],
        })

    elif roll < 0.80:
        # Odd hours — amount in normal range
        # Fraud doesn't always mean huge amount at night
        odd_hour  = random.choice([23, 0, 1, 2, 3, 4])
        fake_time = datetime.utcnow().replace(
            hour=odd_hour,
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        txn.update({
            "amount":    round(random.uniform(
                             customer["avg_spend"] * 0.5,
                             customer["avg_spend"] * 5
                         ), 2),
            "merchant":  random.choice(NORMAL_MERCHANTS),
            "location":  customer["home_city"],
            "timestamp": fake_time.isoformat(),
        })

    else:
        # Combo — still realistic amounts
        odd_hour  = random.choice([23, 0, 1, 2, 3])
        fake_time = datetime.utcnow().replace(hour=odd_hour)
        txn.update({
            "amount":     round(random.uniform(10000, 200000), 2),
            "merchant":   random.choice(SUSPICIOUS_MERCHANTS),
            "location":   random.choice(FOREIGN_LOCATIONS),
            "is_foreign": True,
            "timestamp":  fake_time.isoformat(),
        })

    # Safety net
    if txn["amount"] is None:
        txn["amount"] = round(random.uniform(50, customer["avg_spend"]), 2)
    if txn["merchant"] is None:
        txn["merchant"] = random.choice(NORMAL_MERCHANTS)
    if txn["location"] is None:
        txn["location"] = customer["home_city"]

    return txn
    """
    Generate a transaction that mimics fraud behaviour.
    No label or pattern field — looks like any other transaction.
    Suspicious signals are embedded naturally in the field values.
    """
    txn = _base_transaction(customer)

    roll = random.random()

    if roll < 0.20:
        # High absolute amount (above global threshold)
        txn.update({
            "amount":   round(random.uniform(75000, 500000), 2),
            "merchant": random.choice(NORMAL_MERCHANTS),
            "location": customer["home_city"],
        })

    elif roll < 0.35:
        # Amount exceeds customer's OWN average spend
        # e.g. customer normally spends ₹2,000 → suddenly ₹18,000
        # This is the most realistic fraud signal
        txn.update({
            "amount":   round(random.uniform(
                            customer["avg_spend"] * 3,   # 3x their normal
                            customer["avg_spend"] * 10   # up to 10x their normal
                        ), 2),
            "merchant": random.choice(NORMAL_MERCHANTS),
            "location": customer["home_city"],
        })

    elif roll < 0.50:
        # Foreign location
        txn.update({
            "amount":     round(random.uniform(10000, 100000), 2),
            "merchant":   random.choice(NORMAL_MERCHANTS),
            "location":   random.choice(FOREIGN_LOCATIONS),
            "is_foreign": True,
        })

    elif roll < 0.65:
        # Suspicious merchant
        txn.update({
            "amount":   round(random.uniform(5000, 80000), 2),
            "merchant": random.choice(SUSPICIOUS_MERCHANTS),
            "location": customer["home_city"],
        })

    elif roll < 0.80:
        # Odd hours — late night timestamp
        odd_hour  = random.choice([23, 0, 1, 2, 3, 4])
        fake_time = datetime.utcnow().replace(
            hour=odd_hour,
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        txn.update({
            "amount":    round(random.uniform(20000, 150000), 2),
            "merchant":  random.choice(NORMAL_MERCHANTS),
            "location":  customer["home_city"],
            "timestamp": fake_time.isoformat(),
        })

    else:
        # Combo — multiple suspicious signals at once
        odd_hour  = random.choice([23, 0, 1, 2, 3])
        fake_time = datetime.utcnow().replace(hour=odd_hour)
        txn.update({
            "amount":     round(random.uniform(100000, 1000000), 2),
            "merchant":   random.choice(SUSPICIOUS_MERCHANTS),
            "location":   random.choice(FOREIGN_LOCATIONS),
            "is_foreign": True,
            "timestamp":  fake_time.isoformat(),
        })
    

    """
    Generate a transaction that mimics fraud behaviour.
    No label or pattern field — looks like any other transaction.
    The suspicious signals are embedded naturally in the field values.
    """
    txn = _base_transaction(customer)

    # Randomly apply one of 5 fraud behaviours
    # The transaction itself has NO idea it's fraud
    roll = random.random()

    if roll < 0.20:
        # High amount
        txn.update({
            "amount":   round(random.uniform(75000, 500000), 2),
            "merchant": random.choice(NORMAL_MERCHANTS),
            "location": customer["home_city"],
        })

    elif roll < 0.40:
        # Foreign location
        txn.update({
            "amount":     round(random.uniform(10000, 100000), 2),
            "merchant":   random.choice(NORMAL_MERCHANTS),
            "location":   random.choice(FOREIGN_LOCATIONS),
            "is_foreign": True,
        })

    elif roll < 0.60:
        # Suspicious merchant
        txn.update({
            "amount":   round(random.uniform(5000, 80000), 2),
            "merchant": random.choice(SUSPICIOUS_MERCHANTS),
            "location": customer["home_city"],
        })

    elif roll < 0.80:
        # Odd hours — late night timestamp
        odd_hour  = random.choice([23, 0, 1, 2, 3, 4])
        fake_time = datetime.utcnow().replace(
            hour=odd_hour,
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        txn.update({
            "amount":    round(random.uniform(20000, 150000), 2),
            "merchant":  random.choice(NORMAL_MERCHANTS),
            "location":  customer["home_city"],
            "timestamp": fake_time.isoformat(),
        })

    else:
        # Combo — multiple suspicious signals
        odd_hour  = random.choice([23, 0, 1, 2, 3])
        fake_time = datetime.utcnow().replace(hour=odd_hour)
        txn.update({
            "amount":     round(random.uniform(100000, 1000000), 2),
            "merchant":   random.choice(SUSPICIOUS_MERCHANTS),
            "location":   random.choice(FOREIGN_LOCATIONS),
            "is_foreign": True,
            "timestamp":  fake_time.isoformat(),
        })

    

    return txn




def generate_transaction(customers: list[dict]) -> dict:
    """Pick a random customer → generate a transaction."""
    customer = random.choice(customers)
    if random.random() < FRAUD_RATE:
        return generate_fraud_transaction(customer)
    return generate_normal_transaction(customer)

def display_transaction(txn: dict, count: int):
    """Pretty print a transaction to console."""
    print(
        f"[{count:05d}] "
        f"{txn['customer_id']} | "
        f"₹{txn['amount']:>12,.2f} | "
        f"{txn['merchant']:<22} | "
        f"{txn['location']:<15} | "
        f"{txn['txn_type']:<8} | "
        f"{txn['timestamp']}"
    )

def run_local(output_file: str = "transactions.jsonl", max_count: int = None):
    """
    Run simulator locally — writes to JSONL with realistic delays.
    Used for previewing output before Event Hub is set up.
    Imported by realtime_simulator.py as fallback.
    """             
    customers = generate_customers(TOTAL_CUSTOMERS)
    count     = 0

    log.info(f"Starting LOCAL simulator → {output_file}")
    log.info(f"Rate: {TRANSACTIONS_PER_SEC} txn/sec")
    log.info("Press Ctrl+C to stop\n")
    

    with open(output_file, "w") as f:
        try:
            while True:
                txn = generate_transaction(customers)
                
                f.write(json.dumps(txn) + "\n")
                f.flush()

                count += 1
                display_transaction(txn, count)

                if max_count and count >= max_count:
                    log.info(f"\nReached max count: {max_count}")
                    break

                time.sleep(1 / TRANSACTIONS_PER_SEC)

        except KeyboardInterrupt:
            log.info(f"\nStopped. Written: {count} transactions → {output_file}")