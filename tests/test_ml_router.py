from ml_router import benchmark_router, load_examples, predict_route, HOLDOUT_PATH, TRAIN_PATH


def test_synthetic_train_and_holdout_are_nonempty_and_disjoint():
    train = load_examples(TRAIN_PATH)
    holdout = load_examples(HOLDOUT_PATH)
    assert len(train) >= 80
    assert len(holdout) >= 20
    train_texts = {row["inquiry"] for row in train}
    assert not any(row["inquiry"] in train_texts for row in holdout)


def test_ml_router_returns_allowlisted_candidate_and_caveat():
    result = predict_route("We need to analyze customer reviews and draft responses for multiple store locations.")
    assert result["category"] == "Reputation management (Revio)"
    assert result["top_candidates"]
    assert "not a conversion probability" in result["disclaimer"].lower()
    assert result["dataset_type"] == "synthetic only"


def test_benchmark_has_both_ml_and_rules_results_with_caveat():
    report = benchmark_router()
    assert report["holdout_count"] == len(report["cases"])
    assert 0 <= report["ml"]["accuracy"] <= 1
    assert 0 <= report["rules"]["accuracy"] <= 1
    assert "not representative" in report["caveat"].lower()
    assert {"ml_match", "rule_match"}.issubset(report["cases"][0])
