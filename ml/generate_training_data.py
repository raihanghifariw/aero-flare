"""
Synthetic training data generator for XGBoost fire spread model v1.0.
Generates 1,000 realistic rows for initial model training.
Real FIRMS + ERA5 data used in v1.1.

Usage: python ml/generate_training_data.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RANDOM_SEED = 42
N_SAMPLES = 1_000
OUTPUT_PATH = Path(__file__).parent / "data" / "training_synthetic.csv"

ESA_LAND_COVER_CLASSES = [10, 20, 30, 40, 60, 90]  # common Indonesian types


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)

    wind_speed = rng.uniform(0.5, 15.0, N_SAMPLES)          # m/s
    wind_direction = rng.uniform(0.0, 360.0, N_SAMPLES)     # degrees
    humidity = rng.uniform(20.0, 95.0, N_SAMPLES)           # %
    ndvi = rng.uniform(0.1, 0.8, N_SAMPLES)
    land_cover = rng.choice(ESA_LAND_COVER_CLASSES, N_SAMPLES)
    fire_area_ha = rng.uniform(1.0, 500.0, N_SAMPLES)
    frp = rng.uniform(5.0, 300.0, N_SAMPLES)                # MW

    # Physics-informed synthetic targets
    # Spread direction influenced by wind direction + noise
    spread_direction_deg = (wind_direction + rng.normal(0, 20, N_SAMPLES)) % 360

    # Radius proportional to wind speed, inversely to humidity, FRP boosts
    base_radius = (wind_speed * 0.8 + frp * 0.02) * (1 - humidity / 150)
    dryness = (100 - humidity) / 100
    fuel = ndvi * 2.0
    radius_6h = np.clip(base_radius * dryness * fuel + rng.normal(0, 0.3, N_SAMPLES), 0.1, 30.0)
    radius_12h = np.clip(radius_6h * rng.uniform(1.4, 2.0, N_SAMPLES), 0.2, 60.0)
    radius_24h = np.clip(radius_12h * rng.uniform(1.3, 1.8, N_SAMPLES), 0.3, 100.0)

    return pd.DataFrame({
        "wind_speed": wind_speed,
        "wind_direction": wind_direction,
        "humidity": humidity,
        "ndvi": ndvi,
        "land_cover": land_cover.astype(float),
        "fire_area_ha": fire_area_ha,
        "frp": frp,
        "spread_direction_deg": spread_direction_deg,
        "radius_6h_km": radius_6h,
        "radius_12h_km": radius_12h,
        "radius_24h_km": radius_24h,
    })


if __name__ == "__main__":
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = generate()
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Saved {len(df)} training rows to {OUTPUT_PATH}")
    print(df.describe().to_string())
