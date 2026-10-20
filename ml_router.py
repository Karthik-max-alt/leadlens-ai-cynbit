"""Small TF-IDF + logistic regression route experiment trained on synthetic examples.

Its probability-like outputs are uncalibrated model scores and are not conversion
probabilities. The deterministic rules remain the baseline and a human confirms routes.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parent
TRAIN_PATH = ROOT / "data" / "routing_train.json"
HOLDOUT_PATH = ROOT / "data" / "routing_holdout.json"


def load_examples(path: Path) -> list[dict[str, str]]:
    examples = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(examples, list) or not examples:
        raise ValueError(f"Expected a non-empty JSON list in {path.name}.")
    valid: list[dict[str, str]] = []
    for item in examples:
        if isinstance(item, dict) and isinstance(item.get("inquiry"), str) and isinstance(item.get("category"), str):
            if item["inquiry"].strip() and item["category"].strip():
                valid.append({"inquiry": item["inquiry"].strip(), "category": item["category"].strip(), "id": str(item.get("id", ""))})
    if not valid:
        raise ValueError(f"No valid labeled examples in {path.name}.")
    return valid


@lru_cache(maxsize=1)
def build_model() -> Pipeline:
    train = load_examples(TRAIN_PATH)
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=18000, strip_accents="unicode", sublinear_tf=True, token_pattern=r"(?u)\b\w[\w+.-]*\b")),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42, C=2.0)),
    ])
    model.fit([row["inquiry"] for row in train], [row["category"] for row in train])
    return model


def predict_route(inquiry: str, top_k: int = 3) -> dict[str, Any]:
    text = inquiry.strip() if isinstance(inquiry, str) else ""
    if len(text) < 3:
        raise ValueError("Enter at least 3 characters to predict a route.")
    model = build_model()
    predicted = str(model.predict([text])[0])
    probabilities = model.predict_proba([text])[0]
    categories = model.named_steps["classifier"].classes_
    ranked = sorted(zip(categories, probabilities), key=lambda pair: float(pair[1]), reverse=True)
    candidates = [{"category": str(cat), "score": round(float(score), 4)} for cat, score in ranked[:max(1, min(int(top_k), len(ranked)))]]
    return {
        "category": predicted,
        "model_score_uncalibrated": float(dict((str(cat), float(score)) for cat, score in ranked)[predicted]),
        "top_candidates": candidates,
        "model": "TF-IDF (1–2 grams) + Logistic Regression",
        "training_examples": len(load_examples(TRAIN_PATH)),
        "dataset_type": "synthetic only",
        "disclaimer": "The displayed score is an uncalibrated classifier output, not a conversion probability or verified confidence. This small synthetic-trained model is a comparison candidate only; a human must confirm every route.",
    }


def benchmark_router() -> dict[str, Any]:
    """Compare a tiny synthetic-trained ML candidate with the deterministic route baseline."""
    from leadlens import _keyword_category

    holdout = load_examples(HOLDOUT_PATH)
    train = load_examples(TRAIN_PATH)
    model = build_model()
    texts = [row["inquiry"] for row in holdout]
    y_true = [row["category"] for row in holdout]
    ml_predictions = [str(x) for x in model.predict(texts)]
    rule_predictions = [_keyword_category(text) for text in texts]
    labels = sorted(set(y_true) | set(ml_predictions) | set(rule_predictions))
    rows = []
    for item, ml_pred, rule_pred in zip(holdout, ml_predictions, rule_predictions):
        rows.append({
            "id": item.get("id", ""), "expected": item["category"], "ml_prediction": ml_pred,
            "ml_match": ml_pred == item["category"], "rule_prediction": rule_pred,
            "rule_match": rule_pred == item["category"],
        })
    report = classification_report(y_true, ml_predictions, labels=labels, output_dict=True, zero_division=0)
    return {
        "training_count": len(train),
        "holdout_count": len(holdout),
        "labels": labels,
        "ml": {
            "accuracy": float(accuracy_score(y_true, ml_predictions)),
            "macro_precision": float(precision_score(y_true, ml_predictions, labels=labels, average="macro", zero_division=0)),
            "macro_recall": float(recall_score(y_true, ml_predictions, labels=labels, average="macro", zero_division=0)),
            "macro_f1": float(f1_score(y_true, ml_predictions, labels=labels, average="macro", zero_division=0)),
            "per_class": {label: report.get(label, {}) for label in labels},
        },
        "rules": {
            "accuracy": float(accuracy_score(y_true, rule_predictions)),
            "macro_precision": float(precision_score(y_true, rule_predictions, labels=labels, average="macro", zero_division=0)),
            "macro_recall": float(recall_score(y_true, rule_predictions, labels=labels, average="macro", zero_division=0)),
            "macro_f1": float(f1_score(y_true, rule_predictions, labels=labels, average="macro", zero_division=0)),
        },
        "cases": rows,
        "caveat": "The training and holdout sets are small, handcrafted synthetic data written for the prototype. They are not representative of real Cynbit inquiries and do not establish generalization, calibrated confidence, or production accuracy. Use the metrics only to inspect this implementation and its failure modes.",
    }
