import pandas as pd
from sklearn.model_selection import train_test_split        
import numpy as np
import os

train_df = pd.read_csv("../data/train.csv")
test_df = pd.read_csv("../data/test.csv")
val_df = pd.read_csv("../data/validation.csv")

## Check Fraud distribution

print(f'Train set: {len(train_df)} rows | Fraud: {train_df["label"].mean()*100:.2f}%    ')
print(f'Test set: {len(test_df)} rows | Fraud: {test_df["label"].mean()*100:.2f}%    ')
print(f'Validation set: {len(val_df)} rows | Fraud: {val_df["label"].mean()*100:.2f}%    ') 

                                                                                                                                                                                                                                  
print("Feature Engineering...")

from config_model import SUSPICIOUS_MERCHANTS, FOREIGN_LOCATIONS

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add engineered features based on config thresholds."""
    df = df.copy()
    
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour_of_day"] = df["timestamp"].dt.hour
    df['is_night'] = df['hour_of_day'].apply( lambda x: 1 if x >= 23 or x <= 4 else 0)

    df['amount_vs_avg_ratio'] = df['amount'] / df['avg_spend'] 


    df['amount_log'] = np.log1p(df['amount'])

    df['is_foreign_int'] = df['is_foreign'].astype(int)

    df['is_suspicious_merchant'] = df['merchant'].isin(SUSPICIOUS_MERCHANTS).astype(int)

    df['is_new_account'] = ( df['account_age_days'] < 90 ).astype(int)

    df["is_high_amount"] = (df["amount"] > 50000).astype(int)
    df["amount_zscore"] = (
        (df["amount"] - df["avg_spend"]) / df["spend_std"].replace(0, 1)
    )

    txn_type_map = {
        "UPI": 0, "NEFT": 1, "IMPS": 2,
        "ATM": 3, "POS": 4, "online": 5
    }   

    df['txn_type_encoded'] = df['txn_type'].map(txn_type_map).fillna(0)

    return df

train_df = engineer_features(train_df)
test_df = engineer_features(test_df)
val_df = engineer_features(val_df)

FEATURES = [
    "amount_log",             # Log-scaled transaction amount
    "amount_vs_avg_ratio",    # How unusual is this amount for this customer
    "is_high_amount",   # Global high amount flag
    "amount_zscore",      
    "hour_of_day",            # What time of day
    "is_night",               # Late night flag
    "is_foreign_int",         # Foreign transaction
    "is_suspicious_merchant", # Suspicious merchant category
    "is_new_account",         # New account flag
    "txn_type_encoded",       # Type of transaction
    "account_age_days",       # Account age
]

LABEL = "label"

print(f"Features created : {len(FEATURES)}")
print(f"Features list    : {FEATURES}")
print("cols of X_train  :", train_df.columns.tolist())

X_train, y_train = train_df[FEATURES], train_df[LABEL]
X_test, y_test   = test_df[FEATURES], test_df[LABEL]
X_val, y_val     = val_df[FEATURES], val_df[LABEL]

print("Training the XGBoost model...  ")

from xgboost import XGBClassifier

normal_count = (y_train == 0).sum()
fraud_count = (y_train == 1).sum()
scale_weight = normal_count / fraud_count

model = XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    scale_pos_weight=scale_weight,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    eval_metric="aucpr",
    early_stopping_rounds=20
)   

model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],  # Monitor validation performance
    verbose=50                    # Print progress every 50 trees
)

print("\nTraining complete!")


# ─────────────────────────────────────────────────────────────────
# STEP 4 — Evaluate the Model
#
# WHY NOT ACCURACY:
# A model that says "everything is normal" = 92% accurate
# but catches ZERO fraud. So we use better metrics.
# ─────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 4 — Model Evaluation")
print("=" * 60)

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    average_precision_score,
    recall_score,
    precision_score
)

# Get predictions
y_pred      = model.predict(X_test)
y_pred_prob = model.predict_proba(X_test)[:, 1]  # Fraud probability

# ── Key metrics ───────────────────────────────────────────────────
recall    = recall_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
roc_auc   = roc_auc_score(y_test, y_pred_prob)
pr_auc    = average_precision_score(y_test, y_pred_prob)

print(f"\n── Core Metrics ─────────────────────────────────────")
print(f"Recall    : {recall:.4f}   (target: > 0.85)")
print(f"Precision : {precision:.4f}   (target: > 0.60)")
print(f"ROC-AUC   : {roc_auc:.4f}   (target: > 0.90)")
print(f"PR-AUC    : {pr_auc:.4f}   (target: > 0.70)")

print(f"\n── Classification Report ────────────────────────────")
print(classification_report(y_test, y_pred,
      target_names=["Normal", "Fraud"]))

print(f"\n── Confusion Matrix ─────────────────────────────────")
cm = confusion_matrix(y_test, y_pred)
print(f"                  Predicted Normal  Predicted Fraud")
print(f"Actual Normal  :  {cm[0][0]:>14,}  {cm[0][1]:>14,}")
print(f"Actual Fraud   :  {cm[1][0]:>14,}  {cm[1][1]:>14,}")
print(f"\nTrue Negatives  (correctly said normal) : {cm[0][0]:,}")
print(f"False Positives (said fraud, was normal) : {cm[0][1]:,}")
print(f"False Negatives (missed real fraud)      : {cm[1][0]:,}  ← minimize this!")
print(f"True Positives  (correctly caught fraud) : {cm[1][1]:,}  ← maximize this!")

# ── Feature importance ────────────────────────────────────────────
print(f"\n── Feature Importance ───────────────────────────────")
importance_df = pd.DataFrame({
    "feature":    FEATURES,
    "importance": model.feature_importances_
}).sort_values("importance", ascending=False)
print(importance_df.to_string(index=False))

# ── Threshold tuning ──────────────────────────────────────────────
from report_writer import save_evaluation_report

# Build threshold results
threshold_results = []
for threshold in [0.2, 0.3, 0.4, 0.5, 0.6]:
    y_thresh    = (y_pred_prob >= threshold).astype(int)
    t_recall    = recall_score(y_test, y_thresh, zero_division=0)
    t_precision = precision_score(y_test, y_thresh, zero_division=0)
    caught      = int(y_thresh[y_test == 1].sum())
    threshold_results.append({
        "threshold":    threshold,
        "recall":       round(t_recall, 4),
        "precision":    round(t_precision, 4),
        "fraud_caught": caught,
        "fraud_missed": int((y_test == 1).sum()) - caught
    })

save_evaluation_report(
    output_path      = "../saved_model/evaluation_report.json",
    X_train=X_train, X_val=X_val, X_test=X_test,
    y_test=y_test,
    y_pred=y_pred,   y_pred_prob=y_pred_prob,
    recall=recall,   precision=precision,
    roc_auc=roc_auc, pr_auc=pr_auc,
    model=model,
    FEATURES=FEATURES,
    scale_weight=scale_weight,
    importance_df=importance_df,
    cm=cm,
    threshold_results=threshold_results
)











import pickle
import os
import json

print("\n" + "=" * 60)
print("STEP 5 — Saving Model")
print("=" * 60)

os.makedirs("../saved_model", exist_ok=True)

# ── File paths ────────────────────────────────────────────────────
model_path    = "../saved_model/fraud_model.pkl"
features_path = "../saved_model/features.pkl"
metadata_path = "../saved_model/model_metadata.json"

# ── Save model ────────────────────────────────────────────────────
with open(model_path, "wb") as f:
    pickle.dump(model, f)
print(f"Model saved    → {model_path}")

# ── Save feature list ─────────────────────────────────────────────
# Critical — Databricks streaming must use
# EXACT same features in EXACT same order
with open(features_path, "wb") as f:
    pickle.dump(FEATURES, f)
print(f"Features saved → {features_path}")

# ── Save metadata (human readable) ───────────────────────────────
metadata = {
    "model_name":        "FraudDetectionModel",
    "version":           "v1",
    "algorithm":         "XGBoost",
    "threshold":         0.5,
    "features":          FEATURES,
    "train_size":        len(X_train),
    "metrics": {
        "recall":        round(recall, 4),
        "precision":     round(precision, 4),
        "roc_auc":       round(roc_auc, 4),
        "pr_auc":        round(pr_auc, 4),
    },
    "params": {
        "n_estimators":      200,
        "max_depth":         6,
        "learning_rate":     0.05,
        "scale_pos_weight":  round(scale_weight, 2),
    }
}
with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=2)
print(f"Metadata saved → {metadata_path}")

# ── Verify model loads correctly ──────────────────────────────────
print("\nVerifying model loads correctly...")
with open(model_path, "rb") as f:
    loaded_model = pickle.load(f)
with open(features_path, "rb") as f:
    loaded_features = pickle.load(f)

test_pred = loaded_model.predict(X_test[loaded_features])
print(f"Verification passed!")
print(f"Predictions shape : {test_pred.shape}")
print(f"Features          : {loaded_features}")
print(f"\nModel is ready for Databricks streaming!")