# simulator/realtime_simulator.py

import json
import time
import logging
import signal
import sys
from datetime import datetime
from kafka import KafkaProducer
from transaction_generator import (
    generate_customers,
    generate_transaction,
    display_transaction
)
from config import (
    TOTAL_CUSTOMERS,
    TRANSACTIONS_PER_SEC,
    FRAUD_RATE
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

EH_NAMESPACE   = os.getenv("EH_NAMESPACE", "your-eventhub-namespace")
EH_NAME        = os.getenv("EH_NAME", "transactions")
EH_CONN_STRING = os.getenv("EH_CONN_STRING", "your-connection-string")

print(f"Using Event Hub Namespace: {EH_NAMESPACE}")
print(f"Using Event Hub Name: {EH_NAME}")   

KAFKA_BOOTSTRAP = f"{EH_NAMESPACE}.servicebus.windows.net:9093"
JAAS_CONFIG = (
    "org.apache.kafka.common.security.plain.PlainLoginModule required "
    f'username="$ConnectionString" '
    f'password="{EH_CONN_STRING}";'
)


def create_producer() -> KafkaProducer:
    """Create and return a Kafka producer connected to Event Hub."""
    log.info(f"Connecting to Event Hub: {EH_NAMESPACE}...")
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        security_protocol="SASL_SSL",
        sasl_mechanism="PLAIN",
        sasl_plain_username="$ConnectionString",
        sasl_plain_password=EH_CONN_STRING,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),
        retries=5,                    # Retry on transient failures
        retry_backoff_ms=1000,        # Wait 1s between retries
        request_timeout_ms=30000,     # 30s timeout
    )
    log.info("Connected to Event Hub successfully!")
    return producer


def run_realtime(producer: KafkaProducer):
    """
    Stream transactions to Event Hub continuously.
    Sends TRANSACTIONS_PER_SEC transactions every second.
    Gracefully shuts down on Ctrl+C.
    """
    customers = generate_customers(TOTAL_CUSTOMERS)
    count     = 0
    errors    = 0

    # ── Graceful shutdown on Ctrl+C ───────────────────────────────
    def shutdown(sig, frame):
        log.info(f"\nShutting down... Total sent: {count} | Errors: {errors}")
        producer.flush()
        producer.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)

    log.info(f"Starting real-time simulator...")
    log.info(f"Topic: {EH_NAME} | Rate: {TRANSACTIONS_PER_SEC}/sec | Fraud: {FRAUD_RATE*100}%")
    log.info("Press Ctrl+C to stop\n")

    while True:
        try:
            
            txn = generate_transaction(customers)

            # Send to Event Hub — key by customer_id
            # This ensures all transactions for same customer
            # go to the same partition (ordering guarantee)
            producer.send(
                topic=EH_NAME,
                key=txn["customer_id"],
                value=txn
            )

            count += 1
            display_transaction(txn, count)

            # Optional: flush every 100 messages for reliability
            if count % 100 == 0:
                producer.flush()
                log.info(f"── Flushed at {count} messages ──")

        except Exception as e:
            errors += 1
            log.error(f"Send failed (error #{errors}): {e}")
            if errors > 10:
                log.error("Too many errors — stopping simulator")
                break

        time.sleep(1 / TRANSACTIONS_PER_SEC)


if __name__ == "__main__":
    ## For local testing without Event Hub, run in "local mode" which outputs to a file instead of streaming.
    if EH_CONN_STRING == "your-connection-string":
        log.warning("Event Hub not configured yet!")
        log.warning("Set EH_NAMESPACE, EH_NAME, EH_CONN_STRING as environment variables")
        log.warning("Running local mode instead...\n")

        # Fallback to local file output
        from transaction_generator import run_local
        run_local(output_file="../data/realtime_preview.jsonl", max_count=100)  
    else:
        producer = create_producer()
        run_realtime(producer)
