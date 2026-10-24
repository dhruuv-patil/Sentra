import json
import logging
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval.train_ml")

DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(ROOT_DIR, "models")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

def build_model_pipeline(random_state: int = 42) -> Pipeline:
    """Builds a scikit-learn TF-IDF + Logistic Regression pipeline."""
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            analyzer="word",
            max_features=5000,
            sublinear_tf=True,
            strip_accents="unicode",
            lowercase=True
        )),
        ("clf", LogisticRegression(
            C=2.0,
            solver="liblinear",
            random_state=random_state,
            class_weight="balanced",
            max_iter=1000
        ))
    ])

def train_and_evaluate(random_state: int = 42):
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    train_path = os.path.join(DATA_DIR, "deepset_train.parquet")
    test_path = os.path.join(DATA_DIR, "deepset_test.parquet")

    if not os.path.exists(train_path) or not os.path.exists(test_path):
        from eval.data.download_datasets import main as dl_main
        dl_main()

    df_train = pd.read_parquet(train_path)
    df_test = pd.read_parquet(test_path)

    X_train = df_train["text"].astype(str).tolist()
    y_train = df_train["label"].astype(int).tolist()

    X_test = df_test["text"].astype(str).tolist()
    y_test = df_test["label"].astype(int).tolist()

    logger.info(f"Loaded training split: {len(X_train)} samples ({sum(y_train)} positive, {len(y_train) - sum(y_train)} negative)")
    logger.info(f"Loaded held-out test split: {len(X_test)} samples ({sum(y_test)} positive, {len(y_test) - sum(y_test)} negative)")

    # 1. Stratified 5-Fold Cross Validation on Train Split (Fixed Seed 42, Zero Data Leakage)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
    cv_pipeline = build_model_pipeline(random_state=random_state)

    scoring = ["accuracy", "precision", "recall", "f1"]
    cv_results = cross_validate(cv_pipeline, X_train, y_train, cv=skf, scoring=scoring, return_train_score=False)

    cv_metrics = {
        "cv_folds": 5,
        "cv_accuracy_mean": round(float(np.mean(cv_results["test_accuracy"])), 4),
        "cv_accuracy_std": round(float(np.std(cv_results["test_accuracy"])), 4),
        "cv_precision_mean": round(float(np.mean(cv_results["test_precision"])), 4),
        "cv_precision_std": round(float(np.std(cv_results["test_precision"])), 4),
        "cv_recall_mean": round(float(np.mean(cv_results["test_recall"])), 4),
        "cv_recall_std": round(float(np.std(cv_results["test_recall"])), 4),
        "cv_f1_mean": round(float(np.mean(cv_results["test_f1"])), 4),
        "cv_f1_std": round(float(np.std(cv_results["test_f1"])), 4)
    }

    logger.info("-" * 55)
    logger.info(f"5-Fold Cross-Validation F1: {cv_metrics['cv_f1_mean']:.4f} (+/- {cv_metrics['cv_f1_std']:.4f})")
    logger.info(f"5-Fold Cross-Validation Recall: {cv_metrics['cv_recall_mean']:.4f}")
    logger.info(f"5-Fold Cross-Validation Precision: {cv_metrics['cv_precision_mean']:.4f}")

    # 2. Train final model on entire train split
    final_model = build_model_pipeline(random_state=random_state)
    final_model.fit(X_train, y_train)

    # 3. Test on Held-Out Test Split (no leakage)
    y_pred = final_model.predict(X_test)

    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    test_metrics = {
        "test_samples": len(y_test),
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred)), 4),
        "recall": round(float(recall_score(y_test, y_pred)), 4),
        "f1_score": round(float(f1_score(y_test, y_pred)), 4),
        "false_positive_rate": round(float(fp / (fp + tn)), 4) if (fp + tn) > 0 else 0.0,
        "confusion_matrix": {
            "TN": int(tn),
            "FP": int(fp),
            "FN": int(fn),
            "TP": int(tp)
        }
    }

    logger.info("-" * 55)
    logger.info(f"Held-Out Test Set Performance (n={len(y_test)}):")
    logger.info(f"  Accuracy:  {test_metrics['accuracy']:.4f}")
    logger.info(f"  Precision: {test_metrics['precision']:.4f}")
    logger.info(f"  Recall:    {test_metrics['recall']:.4f}")
    logger.info(f"  F1 Score:  {test_metrics['f1_score']:.4f}")
    logger.info(f"  FPR:       {test_metrics['false_positive_rate']:.4f}")
    logger.info(f"  Confusion: TN={tn}, FP={fp}, FN={fn}, TP={tp}")
    logger.info("-" * 55)

    # 4. Save trained pipeline artifact
    model_save_path = os.path.join(MODELS_DIR, "injection_classifier.joblib")
    joblib.dump(final_model, model_save_path)
    logger.info(f"Saved trained classifier artifact to {model_save_path}")

    # 5. Save training summary
    summary_payload = {
        "algorithm": "TF-IDF (1,2 ngrams, max_features=5000) + LogisticRegression(C=2.0, class_weight='balanced')",
        "random_state": random_state,
        "cross_validation": cv_metrics,
        "held_out_test": test_metrics
    }

    with open(os.path.join(RESULTS_DIR, "ml_training_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    return summary_payload

if __name__ == "__main__":
    train_and_evaluate()
