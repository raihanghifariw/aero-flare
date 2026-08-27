"""
XGBoost fire spread prediction model training script.
Trains 4 regressors (one per spread target) with 5-fold cross-validation.

Usage:
    python ml/train.py --data ml/data/training_synthetic.csv --version 1.0.0

Output:
    ml/models/xgboost_spread_v{version}.ubj
    ml/models/metrics_v{version}.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

FEATURE_COLUMNS = [
    "wind_speed", "wind_direction", "humidity",
    "ndvi", "land_cover", "fire_area_ha", "frp",
]
TARGET_COLUMNS = [
    "spread_direction_deg", "radius_6h_km", "radius_12h_km", "radius_24h_km",
]


def train(data_path: str, version: str) -> None:
    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / f"xgboost_spread_v{version}.ubj"
    metrics_path = models_dir / f"metrics_v{version}.json"

    # --- Load data ---
    df = pd.read_csv(data_path)
    missing = set(FEATURE_COLUMNS + TARGET_COLUMNS) - set(df.columns)
    if missing:
        print(f"Missing columns: {missing}", file=sys.stderr)
        sys.exit(1)

    X = df[FEATURE_COLUMNS].values
    y = df[TARGET_COLUMNS].values

    print(f"Training on {len(df)} rows | {len(FEATURE_COLUMNS)} features | {len(TARGET_COLUMNS)} targets")

    # --- Scale features ---
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # --- Cross-validate each target ---
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_metrics: dict[str, dict[str, float]] = {}

    for i, target in enumerate(TARGET_COLUMNS):
        maes, rmses = [], []
        for fold, (train_idx, val_idx) in enumerate(kf.split(X_scaled)):
            model = XGBRegressor(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
            )
            model.fit(
                X_scaled[train_idx], y[train_idx, i],
                eval_set=[(X_scaled[val_idx], y[val_idx, i])],
                verbose=False,
            )
            preds = model.predict(X_scaled[val_idx])
            maes.append(mean_absolute_error(y[val_idx, i], preds))
            rmses.append(np.sqrt(mean_squared_error(y[val_idx, i], preds)))

        cv_metrics[target] = {
            "mae_mean": round(float(np.mean(maes)), 4),
            "rmse_mean": round(float(np.mean(rmses)), 4),
        }
        print(f"  {target}: MAE={cv_metrics[target]['mae_mean']:.4f}  RMSE={cv_metrics[target]['rmse_mean']:.4f}")

    # --- Train final model on all data (multi-output) ---
    final_model = XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        multi_strategy="multi_output_tree",
    )
    final_model.fit(X_scaled, y)
    final_model.save_model(str(model_path))

    # --- Save metrics ---
    metrics = {
        "version": version,
        "n_samples": len(df),
        "features": FEATURE_COLUMNS,
        "targets": TARGET_COLUMNS,
        "cv_5fold": cv_metrics,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2))

    print(f"\n✅ Model saved → {model_path}")
    print(f"✅ Metrics saved → {metrics_path}")

    # Gate check assertions
    assert cv_metrics["spread_direction_deg"]["rmse_mean"] <= 90, "Spread direction RMSE too high"
    for t in ["radius_6h_km", "radius_12h_km", "radius_24h_km"]:
        assert cv_metrics[t]["rmse_mean"] <= 15.0, f"{t} RMSE too high (synthetic data)"
    print("\n✅ All RMSE gate checks passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="ml/data/training_synthetic.csv")
    parser.add_argument("--version", default="1.0.0")
    args = parser.parse_args()
    train(args.data, args.version)
