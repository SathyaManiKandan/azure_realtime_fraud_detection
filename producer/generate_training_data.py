# simulator/generate_training_data.py

import json
import pandas as pd
import os
import logging
from datetime import datetime
from faker import Faker
from transaction_generator import (
    generate_customers,
    generate_normal_transaction,
    generate_fraud_transaction
)
from config import TOTAL_CUSTOMERS, FRAUD_RATE
from sklearn.model_selection import train_test_split

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


def generate_dataset(n_rows: int, output_path: str) -> pd.DataFrame:
    """
    Generate n_rows transactions.
    Since transactions have no label field, we track fraud/normal
    here during generation and add label only to the saved CSV
    — used exclusively for ML training, never sent to Event Hub.
    """
    os.makedirs(output_path, exist_ok=True)
    customers = generate_customers(TOTAL_CUSTOMERS)
    records   = []

    n_fraud  = int(n_rows * FRAUD_RATE)
    n_normal = n_rows - n_fraud

    log.info(f"Generating {n_rows:,} transactions "
             f"({n_normal:,} normal + {n_fraud:,} fraud)...")
    start = datetime.now()

    # Generate normal transactions
    for i in range(n_normal):
        txn = generate_normal_transaction(
            customers[i % len(customers)]
        )
        txn["label"] = 0    # Add label ONLY for training data
        records.append(txn)

        if (i + 1) % 10000 == 0:
            log.info(f"  Normal: {i+1:,} / {n_normal:,}")

    # Generate fraud transactions
    for i in range(n_fraud):
        txn = generate_fraud_transaction(
            customers[i % len(customers)]
        )
        txn["label"] = 1    # Add label ONLY for training data
        records.append(txn)

        if (i + 1) % 1000 == 0:
            log.info(f"  Fraud:  {i+1:,} / {n_fraud:,}")

    # Shuffle so fraud isn't all at the end
    import random
    random.shuffle(records)

    elapsed = (datetime.now() - start).seconds
    log.info(f"Done! {n_rows:,} rows generated in {elapsed}s")

    # ── Save as JSONL ─────────────────────────────────────────────
    jsonl_path = os.path.join(output_path, "transactions.jsonl")
    with open(jsonl_path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    log.info(f"Saved JSONL → {jsonl_path}")

    # ── Save as CSV ───────────────────────────────────────────────
    df       = pd.DataFrame(records)
    csv_path = os.path.join(output_path, "transactions.csv")
    df.to_csv(csv_path, index=False)
    log.info(f"Saved CSV  → {csv_path}")

    # ── Summary stats ─────────────────────────────────────────────
    log.info("\n── Dataset Summary ──────────────────────────")
    log.info(f"Total : {len(df):,}")
    log.info(f"Normal: {(df['label']==0).sum():,} ({(df['label']==0).mean()*100:.1f}%)")
    log.info(f"Fraud : {(df['label']==1).sum():,}  ({(df['label']==1).mean()*100:.1f}%)")
    log.info("─────────────────────────────────────────────\n")

    return df


def generate_train_val_test_split(output_path: str = "data/"):
    """Generate and split into train / validation / test sets."""
    df = generate_dataset(n_rows=70000, output_path=output_path)

    # Stratified split — preserves fraud ratio in each split
    train_val, test = train_test_split(
        df, test_size=10000, random_state=42, stratify=df["label"]
    )
    train, val = train_test_split(
        train_val, test_size=10000, random_state=42,
        stratify=train_val["label"]
    )

    splits = {"train": train, "validation": val, "test": test}
    for name, split_df in splits.items():
        path = os.path.join(output_path, f"{name}.csv")
        split_df.to_csv(path, index=False)
        fraud_pct = (split_df["label"] == 1).mean() * 100
        log.info(f"{name:>12}: {len(split_df):,} rows | "
                 f"fraud: {fraud_pct:.1f}% → {path}")

    log.info("\nAll splits ready for XGBoost training!")
    return train, val, test


if __name__ == "__main__":
    generate_train_val_test_split(output_path="../data/")