# 🛡️ Real-Time Fraud Detection Pipeline

A production-grade, end-to-end real-time fraud detection system built on **Azure** and **Databricks**, combining streaming data engineering with machine learning to detect fraudulent banking transactions in real time.

---

## 📌 Architecture Overview

```
Python Simulator
      │
      ▼
Azure Event Hub (Kafka)
      │
      ▼
Databricks Structured Streaming
   ├── Feature Engineering
   └── XGBoost ML Scoring 
      │
      ├──▶ Bronze Layer (ADLS) — All raw transactions
      ├──▶ Silver Layer (ADLS) — Fraud flagged + Cleaned
      └──▶ Gold Layer  (ADLS) — Aggregated metrics
                                      │
                                      ▼
                            Synapse Serverless Pool
                            (Views on Gold Layer)
                                      │
                                      ▼
                                  Power BI
                            (Live Fraud Dashboard)
```

---

## 🗂️ Project Structure

```
fraud-detection-pipeline/
│
├── .env.example                        # Environment variable template
├── .gitignore
├── README.md
│
├── producer/                           # Transaction simulator
│   ├── config.py                       # Shared configuration & data pools
│   ├── transaction_generator.py        # Core transaction generation logic
│   ├── generate_training_data.py       # Bulk data generator for ML training
│   ├── realtime_simulator.py           # Live stream to Azure Event Hub
│   └── requirements.txt
│
├── model/                              # ML model training
│   ├── train.py                        # XGBoost training + MLflow tracking
│   ├── config_model.py                 # Feature engineering config
│   └── requirements.txt
│
├── databricks/                         # Databricks notebooks
│   ├── 01_bronze_ingestion.py          # Stream from Event Hub → Bronze
│   ├── 02_silver_processing.py         # Feature engineering + ML scoring
│   └── 03_gold_aggregation.py          # Aggregated metrics → Gold
│
├── data/                               # Generated training data (gitignored)
│   ├── train.csv                       # 50,000 rows
│   ├── validation.csv                  # 10,000 rows
│   └── test.csv                        # 10,000 rows
│
└── synapse/                            # Synapse Serverless SQL scripts
    └── create_views.sql                # Views on Gold layer for Power BI
```

---


### ML Features Used

| Feature | Description |
|---|---|
| `amount_log` | Log-scaled transaction amount |
| `amount_vs_avg_ratio` | Amount relative to customer's avg spend |
| `is_high_amount` | Global high amount flag |
| `hour_of_day` | Hour of transaction |
| `is_night` | Late night transaction flag |
| `is_foreign_int` | Foreign transaction flag |
| `is_suspicious_merchant` | Suspicious merchant flag |
| `is_new_account` | Account age < 90 days |
| `txn_type_encoded` | Encoded transaction type |
| `account_age_days` | Age of the customer account |

---

## 📊 Medallion Architecture

| Layer | Path | Contents |
|---|---|---|
| **Bronze** | `adls/bronze/transactions` | All raw transactions — no cleaning |
| **Silver/fraud** | `adls/silver/fraud` | Fraud-flagged transactions |
| **Silver/clean** | `adls/silver/clean` | Cleaned normal transactions |
| **Gold** | `adls/gold/metrics` | Aggregated fraud metrics by date/location |

---


## 👤 Author

**Sathya P**
Data Engineer | Azure | PySpark | Databricks | ML Engineering
