"""Run the deterministic smoke test and the separate synthetic ML-vs-rules benchmark.

Outputs are intentionally caveated; these are handcrafted synthetic datasets, not
representative evidence of performance on real Cynbit inquiries.
Usage: python scripts/evaluate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from leadlens import analyze_inquiry  # noqa: E402
from ml_router import benchmark_router  # noqa: E402


def main() -> int:
    examples = json.loads((ROOT / "data" / "sample_inquiries.json").read_text(encoding="utf-8"))
    correct = 0
    cases = []
    for example in examples:
        result = analyze_inquiry(example["inquiry"], use_llm=False)
        predicted = result["fields"]["service_category"]
        match = predicted == example["expected_category"]
        correct += int(match)
        cases.append({"id": example["id"], "expected": example["expected_category"], "predicted": predicted, "match": match})
    total = len(examples)
    ml_report = benchmark_router()
    output = {
        "rules_smoke_test": {
            "dataset": "six handcrafted synthetic inquiries",
            "correct": correct,
            "total": total,
            "accuracy": round(correct / total, 3) if total else 0.0,
            "cases": cases,
        },
        "ml_vs_rules_holdout": {
            "training_examples": ml_report["training_count"],
            "holdout_examples": ml_report["holdout_count"],
            "ml_accuracy": round(ml_report["ml"]["accuracy"], 3),
            "ml_macro_f1": round(ml_report["ml"]["macro_f1"], 3),
            "rules_accuracy": round(ml_report["rules"]["accuracy"], 3),
            "rules_macro_f1": round(ml_report["rules"]["macro_f1"], 3),
            "cases": ml_report["cases"],
        },
        "caveat": "All datasets are handcrafted synthetic examples. Results demonstrate repeatable prototype behavior only and do not establish real-world accuracy, calibrated confidence, or generalization.",
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0 if correct == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
