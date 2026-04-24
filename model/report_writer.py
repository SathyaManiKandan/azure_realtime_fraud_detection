# model/report_writer.py

import json
import os
from datetime import datetime


def save_evaluation_report(
    output_path: str,
    # Data info
    X_train, X_val, X_test,
    y_test,
    # Predictions
    y_pred,
    y_pred_prob,
    # Metrics
    recall, precision, roc_auc, pr_auc,
    # Model info
    model,
    FEATURES,
    scale_weight,
    importance_df,
    # Confusion matrix
    cm,
    # Threshold results
    threshold_results
):
    """
    Generate and save a detailed evaluation report as JSON.
    Called from train.py after model evaluation.
    """

    tn, fp, fn, tp = cm.ravel()

    report = {

        "report_generated_at": datetime.utcnow().isoformat(),

        # ── Dataset Info ──────────────────────────────────────────
        "dataset": {
            "train_size":           len(X_train),
            "validation_size":      len(X_val),
            "test_size":            len(X_test),
            "fraud_rate":           "8%",
            "total_fraud_in_test":  int((y_test == 1).sum()),
            "total_normal_in_test": int((y_test == 0).sum()),
        },

        # ── Section 1: Metric Definitions ─────────────────────────
        "metric_definitions": {
            "recall": {
                "value":   round(recall, 4),
                "formula": "TP / (TP + FN)",
                "meaning": (
                    "Out of ALL real fraud transactions, what % did the model catch? "
                    "Most important metric for fraud detection — missing real fraud "
                    "is dangerous. Target: > 0.85"
                ),
                "our_result": (
                    f"Model caught {tp} out of {tp + fn} real fraud transactions "
                    f"({round(recall * 100, 1)}%). Missed {fn} fraud transactions."
                )
            },
            "precision": {
                "value":   round(precision, 4),
                "formula": "TP / (TP + FP)",
                "meaning": (
                    "Out of ALL transactions flagged as fraud, what % were actually fraud? "
                    "Low precision = too many false alarms = review team overwhelmed. "
                    "Target: > 0.60"
                ),
                "our_result": (
                    f"Of {tp + fp} total fraud alerts raised, {tp} were genuine "
                    f"and {fp} were false alarms ({round(precision * 100, 1)}% hit rate)."
                )
            },
            "roc_auc": {
                "value":   round(roc_auc, 4),
                "formula": "Area under ROC curve (True Positive Rate vs False Positive Rate)",
                "meaning": (
                    "Overall model quality — how well it distinguishes fraud from normal "
                    "across ALL thresholds. 0.5 = random guessing, 1.0 = perfect. "
                    "Target: > 0.90"
                ),
                "our_result": (
                    f"Score of {round(roc_auc, 4)} means excellent discriminating "
                    f"ability between fraud and normal transactions."
                )
            },
            "pr_auc": {
                "value":   round(pr_auc, 4),
                "formula": "Area under Precision-Recall curve",
                "meaning": (
                    "Better than ROC-AUC for imbalanced datasets like fraud detection. "
                    "Measures model quality specifically on the minority class (fraud). "
                    "Random classifier baseline = fraud rate (0.08). Target: > 0.70"
                ),
                "our_result": (
                    f"Score of {round(pr_auc, 4)} is significantly above the random "
                    f"baseline of 0.08 — model is highly effective on fraud class."
                )
            },
            "f1_score": {
                "meaning": (
                    "Harmonic mean of precision and recall. Useful single number "
                    "when you want balance between both. For fraud detection recall "
                    "matters more, so we use it alongside F1 not instead of it."
                )
            },
            "accuracy": {
                "meaning": (
                    "Overall % of correct predictions. MISLEADING for fraud detection "
                    "— a model predicting everything as normal gets 92% accuracy "
                    "but catches zero fraud. Not used as primary metric."
                )
            }
        },

        # ── Section 2: Confusion Matrix ───────────────────────────
        "confusion_matrix": {
            "true_negatives": {
                "value":   int(tn),
                "meaning": "Normal transactions correctly identified as normal — no action needed"
            },
            "false_positives": {
                "value":   int(fp),
                "meaning": (
                    "Normal transactions incorrectly flagged as fraud — false alarms. "
                    "Go to manual review. Annoying but not dangerous."
                )
            },
            "false_negatives": {
                "value":   int(fn),
                "meaning": (
                    "Real fraud transactions missed by the model — most dangerous outcome. "
                    "These fraudulent transactions go undetected. Must minimize this."
                )
            },
            "true_positives": {
                "value":   int(tp),
                "meaning": "Real fraud transactions correctly caught — the best outcome"
            }
        },

        # ── Section 3: Threshold Analysis ─────────────────────────
        "threshold_analysis": {
            "explanation": (
                "The model outputs a fraud probability (0.0 to 1.0) per transaction. "
                "The threshold decides at what probability we call it fraud. "
                "Lower = catch more fraud (higher recall) but more false alarms. "
                "Higher = fewer false alarms but miss more fraud. "
                "Recommended for banking: 0.5"
            ),
            "recommended_threshold": 0.5,
            "results": threshold_results
        },

        # ── Section 4: Feature Importance ─────────────────────────
        "feature_importance": {
            "explanation": (
                "How much each feature contributed to the model's decisions. "
                "Higher = more important. A healthy model has importance spread "
                "across multiple features — not dominated by one."
            ),
            "values": importance_df.set_index("feature")["importance"]
                                   .round(6).to_dict()
        },

        # ── Section 5: Model Parameters ───────────────────────────
        "model_parameters": {
            "algorithm": "XGBoost (Gradient Boosted Trees)",
            "algorithm_explanation": (
                "An ensemble of decision trees where each tree learns from "
                "the mistakes of the previous one. Industry standard for "
                "tabular fraud detection."
            ),
            "parameters": {
                "n_estimators": {
                    "value":   200,
                    "meaning": "Number of trees in the ensemble. More = better but slower."
                },
                "max_depth": {
                    "value":   6,
                    "meaning": (
                        "Max depth of each tree. Too deep = memorises training data. "
                        "Too shallow = misses patterns. 6 is a good default."
                    )
                },
                "learning_rate": {
                    "value":   0.05,
                    "meaning": (
                        "How much each new tree corrects the previous ones. "
                        "Lower = more careful learning, better generalization."
                    )
                },
                "scale_pos_weight": {
                    "value":   round(scale_weight, 2),
                    "meaning": (
                        f"Ratio of normal to fraud samples ({round(scale_weight, 2)}x). "
                        "Tells XGBoost to weight fraud examples more heavily "
                        "to compensate for class imbalance."
                    )
                },
                "subsample": {
                    "value":   0.8,
                    "meaning": "Use 80% of rows per tree — adds randomness, prevents overfitting."
                },
                "colsample_bytree": {
                    "value":   0.8,
                    "meaning": "Use 80% of features per tree — adds randomness, prevents overfitting."
                }
            }
        },

        # ── Section 6: Features Used ──────────────────────────────
        "features_used": {
            "total_count": len(FEATURES),
            "list": FEATURES,
            "descriptions": {
                "amount_log":             "Log-scaled transaction amount — compresses wide value range",
                "amount_vs_avg_ratio":    "Transaction amount / customer avg spend — detects unusual spend",
                "amount_zscore":          "Std deviations from customer's normal spend — personalised signal",
                "is_high_amount":         "1 if amount > ₹50,000 globally, else 0",
                "hour_of_day":            "Hour of transaction (0–23) — time pattern signal",
                "is_night":               "1 if transaction between 11 PM and 4 AM, else 0",
                "is_foreign_int":         "1 if transaction from a foreign location, else 0",
                "is_suspicious_merchant": "1 if merchant is CASINO / CRYPTO etc., else 0",
                "is_new_account":         "1 if account age < 90 days — new accounts are higher risk",
                "txn_type_encoded":       "Transaction type as number (UPI=0, NEFT=1, IMPS=2 etc.)",
                "account_age_days":       "Age of customer account in days",
                "spend_std":              "Customer's spending std deviation — measures spend variability"
            }
        }
    }

    # ── Write to file ─────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Evaluation report saved → {output_path}")
    print("\nReport sections:")
    print("  1. Metric definitions  — meaning of each metric + our results")
    print("  2. Confusion matrix    — TP, TN, FP, FN with explanations")
    print("  3. Threshold analysis  — which threshold to use in production")
    print("  4. Feature importance  — which features the model relies on")
    print("  5. Model parameters    — XGBoost settings with explanations")
    print("  6. Features used       — full feature list with descriptions")