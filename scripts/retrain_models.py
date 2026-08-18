"""Retrain all models from the training notebook and save fitted joblib files."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import joblib
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import (
    RandomForestRegressor,
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
)
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

DATA_PATH = Path("data/raw/updated_crop_prediction_gee_computations.csv")
MODEL_DIR = Path("data/model_registry")

# ── Load & engineer features ──────────────────────────────────────────────────
crop = pd.read_csv(DATA_PATH)
crop_gee = crop.drop(
    ["gee_gndvi", "gee_ndvi", "gee_ndwi", "gee_savi", "field_id", "gee_rainfall", "gee_temp"],
    axis=1,
)
crop_gee["date_of_image"] = pd.to_datetime(
    crop_gee["date_of_image"], format="%d-%m-%Y", errors="coerce"
)
crop_gee["year"] = crop_gee["date_of_image"].dt.year
crop_gee["month"] = crop_gee["date_of_image"].dt.month
crop_gee["day"] = crop_gee["date_of_image"].dt.day
season_map = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
}
crop_gee["season"] = crop_gee["month"].map(season_map)
crop_gee.sort_values(by="date_of_image", inplace=True)

FEATURE_COLS = ["GNDVI", "NDVI", "NDWI", "SAVI", "crop_type", "latitude",
                "longitude", "rainfall", "soil_moisture", "temperature",
                "year", "month", "day", "season"]
TARGET = "yield"

X = crop_gee[FEATURE_COLS]
y = crop_gee[TARGET]

# ── Preprocessor ─────────────────────────────────────────────────────────────
numeric_features = ["GNDVI", "NDVI", "NDWI", "SAVI", "latitude", "longitude",
                    "rainfall", "soil_moisture", "temperature", "year", "month", "day"]
categorical_features = ["crop_type", "season"]

preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), numeric_features),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
    ]
)

# ── Models ────────────────────────────────────────────────────────────────────
models = {
    "histgbm_model": HistGradientBoostingRegressor(),
    "randomforest_model": RandomForestRegressor(n_estimators=100, random_state=42),
    "extratrees_model": ExtraTreesRegressor(n_estimators=100, random_state=42),
    "gradientboosting_model": GradientBoostingRegressor(n_estimators=100, random_state=42),
    "ridge_model": Ridge(),
}

for name, estimator in models.items():
    pipeline = Pipeline(steps=[("preprocess", preprocessor), ("model", estimator)])
    pipeline.fit(X, y)
    out_path = MODEL_DIR / f"{name}.joblib"
    joblib.dump(pipeline, out_path)
    print(f"Saved {out_path}")

print("\nAll models retrained and saved.")
