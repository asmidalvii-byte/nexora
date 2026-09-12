"""Trains and selects the ML relevance model.

Tries a few lightweight, explainable model families (per project spec
Phase 9/19), evaluates on a held-out validation split with both error
metrics (MAE/RMSE) and ranking metrics (Spearman correlation, pairwise
ranking accuracy — this is a ranking problem, not just a regression one),
and saves the best one with its metadata to models/ranking_model.joblib.
"""
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import RANDOM_SEED, RANKING_MODEL_PATH, TRAINING_DATA_PATH  # noqa: E402
from src.feature_engineering import FEATURE_NAMES  # noqa: E402


def pairwise_ranking_accuracy(y_true: np.ndarray, y_pred: np.ndarray, sample_size: int = 20000, seed: int = RANDOM_SEED) -> float:
    """Fraction of (i, j) pairs where predicted order agrees with true
    order. Sampled when there are too many pairs to enumerate."""
    n = len(y_true)
    rng = np.random.default_rng(seed)
    idx_pairs = list(combinations(range(min(n, 400)), 2))  # cap pool for combinatorics
    if len(idx_pairs) > sample_size:
        chosen = rng.choice(len(idx_pairs), size=sample_size, replace=False)
        idx_pairs = [idx_pairs[i] for i in chosen]

    correct = 0
    total = 0
    for i, j in idx_pairs:
        true_diff = y_true[i] - y_true[j]
        pred_diff = y_pred[i] - y_pred[j]
        if abs(true_diff) < 1e-6:
            continue
        total += 1
        if np.sign(true_diff) == np.sign(pred_diff):
            correct += 1
    return correct / total if total else float("nan")


def evaluate(name, model, X_val, y_val):
    preds = model.predict(X_val)
    mae = mean_absolute_error(y_val, preds)
    rmse = mean_squared_error(y_val, preds) ** 0.5
    spearman_corr, _ = spearmanr(y_val, preds)
    pairwise_acc = pairwise_ranking_accuracy(np.asarray(y_val), preds)
    return {
        "name": name,
        "mae": mae,
        "rmse": rmse,
        "spearman": spearman_corr,
        "pairwise_ranking_accuracy": pairwise_acc,
    }


def main():
    df = pd.read_csv(TRAINING_DATA_PATH)
    X = df[FEATURE_NAMES].values
    y = df["relevance_label"].values

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED
    )

    candidates = {
        "LinearRegression": LinearRegression(),
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=200, max_depth=8, random_state=RANDOM_SEED, n_jobs=-1
        ),
        "HistGradientBoostingRegressor": HistGradientBoostingRegressor(
            max_depth=4, learning_rate=0.08, random_state=RANDOM_SEED
        ),
    }

    results = []
    fitted = {}
    for name, model in candidates.items():
        model.fit(X_train, y_train)
        fitted[name] = model
        results.append(evaluate(name, model, X_val, y_val))

    results_df = pd.DataFrame(results).sort_values("rmse")
    print("\nModel evaluation (validation set):")
    print(results_df.to_string(index=False))

    # Select by RMSE, tie-broken by ranking quality — this is a ranking
    # problem, so a model that ranks well matters as much as raw error.
    best_row = results_df.sort_values(["rmse", "pairwise_ranking_accuracy"], ascending=[True, False]).iloc[0]
    best_name = best_row["name"]
    best_model = fitted[best_name]
    print(f"\nSelected model: {best_name}")

    RANKING_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": best_model,
            "model_name": best_name,
            "feature_names": FEATURE_NAMES,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "random_seed": RANDOM_SEED,
            "validation_metrics": best_row.to_dict(),
            "n_training_examples": len(X_train),
        },
        RANKING_MODEL_PATH,
    )
    print(f"Saved model + metadata to {RANKING_MODEL_PATH}")


if __name__ == "__main__":
    main()
