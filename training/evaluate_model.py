"""Standalone evaluation report for the saved model — run any time to print
its validation metrics and metadata without retraining."""
import sys
from pathlib import Path

import joblib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import RANKING_MODEL_PATH  # noqa: E402


def main():
    if not RANKING_MODEL_PATH.exists():
        print(f"No trained model found at {RANKING_MODEL_PATH}. Run: python -m training.train_model")
        sys.exit(1)

    bundle = joblib.load(RANKING_MODEL_PATH)  # our own locally-trained artifact, not untrusted input
    print("=" * 60)
    print("RANKING MODEL REPORT")
    print("=" * 60)
    print(f"Model type:          {bundle['model_name']}")
    print(f"Trained at (UTC):    {bundle['trained_at']}")
    print(f"Random seed:         {bundle['random_seed']}")
    print(f"Training examples:   {bundle['n_training_examples']}")
    print(f"Feature count:       {len(bundle['feature_names'])}")
    print(f"Features:            {', '.join(bundle['feature_names'])}")
    print("-" * 60)
    print("Validation metrics:")
    for k, v in bundle["validation_metrics"].items():
        if k == "name":
            continue
        try:
            print(f"  {k:30s}: {float(v):.4f}")
        except (TypeError, ValueError):
            print(f"  {k:30s}: {v}")
    print("=" * 60)


if __name__ == "__main__":
    main()
