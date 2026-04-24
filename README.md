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

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python, PySpark, SQL |
| **Streaming** | Azure Event Hub (Kafka Protocol) |
| **Processing** | Azure Databricks, Spark Structured Streaming |
| **ML Model** | XGBoost, Scikit-learn |
| **ML Ops** | MLflow (Tracking, Model Registry, spark_udf) |
| **Storage** | Azure Data Lake Storage Gen2 (Delta Lake) |
| **Lakehouse** | Medallion Architecture (Bronze / Silver / Gold) |
| **Query Layer** | Azure Synapse Serverless Pool |
| **Reporting** | Power BI |
| **Alerting** | Azure Monitor, Azure Logic Apps |
| **Security** | Azure Key Vault, RBAC |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Azure Subscription (Event Hub, ADLS Gen2, Databricks, Synapse)
- Azure CLI installed

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/fraud-detection-pipeline.git
cd fraud-detection-pipeline
```

### 2. Set Up Environment

```bash
# Copy env template and fill in your values
cp .env.example .env
```

Edit `.env` with your Azure credentials:

```bash
EH_NAMESPACE=your-eventhub-namespace
EH_NAME=transactions
EH_CONN_STRING=Endpoint=sb://...
```

### 3. Install Producer Dependencies

```bash
cd producer
pip install -r requirements.txt
```

### 4. Generate Training Data

```bash
python generate_training_data.py

# Output:
# data/train.csv        → 50,000 rows
# data/validation.csv   → 10,000 rows
# data/test.csv         → 10,000 rows
```

### 5. Train the ML Model

```bash
cd ../model
pip install -r requirements.txt
python train.py


### 6. Run Real-Time Simulator

```bash
cd ../producer

# Local mode (before Event Hub setup)
python realtime_simulator.py

# Event Hub mode (after Azure setup)
# Set .env values and run the same command
python realtime_simulator.py
```

---

## 🔍 Fraud Detection Logic

The pipeline detects fraud using a combination of **rule-based signals** and an **XGBoost ML model**.

### Fraud Patterns Simulated

| Pattern | Description |
|---|---|
| High absolute amount | Transaction amount > ₹75,000 |
| Exceeds personal avg spend | 3x–10x the customer's own average spend |
| Foreign location | Transaction from a foreign country |
| Suspicious merchant | CASINO, CRYPTO\_EXCHANGE, UNKNOWN etc. |
| Odd hours | Transaction between 11 PM – 4 AM |
| Combo | Multiple suspicious signals at once |

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

## 🤖 MLflow Model Lifecycle

```
Train locally (train.py)
      │
      ▼
Log params + metrics + artifacts
      │
      ▼
Register → FraudDetectionModel (Version N)
      │
      ├──▶ Staging   (testing)
      └──▶ Production (live scoring in Databricks stream)
```

### Key Model Metrics (Targets)

| Metric | Target |
|---|---|
| Recall | > 85% |
| Precision | > 60% |
| ROC-AUC | > 0.90 |
| PR-AUC | > 0.70 |

---

## 🚨 Alerting

| Alert Type | Tool | Trigger |
|---|---|---|
| High-risk fraud | Azure Monitor | fraud\_score > 80 |
| Real-time notification | Azure Logic App | fraud alert topic on Event Hub |
| Dashboard threshold | Power BI | > 50 fraud txns/hour |
| Data quality | Dead Letter Queue | Malformed / unparseable records |

---

## 🔐 Security

- All secrets stored in **Azure Key Vault** — never hardcoded
- ADLS access controlled via **RBAC** (Role-Based Access Control)
- `.env` file is **gitignored** — use `.env.example` as template

---

## 🗺️ Roadmap

- [x] Transaction simulator (normal + fraud patterns)
- [x] Training data generator (70k rows)
- [x] XGBoost model training + MLflow
- [ ] Azure Event Hub setup
- [ ] Databricks Structured Streaming notebooks
- [ ] Bronze / Silver / Gold Delta Lake setup
- [ ] Synapse Serverless Pool views
- [ ] Power BI dashboard
- [ ] Azure Monitor + Logic App alerts

---

## 👤 Author

**Sathya P**
Data Engineer | Azure | PySpark | Databricks | ML Engineering
