"""
Walmart Enterprise - Machine Learning Demand Forecasting Engine
Project - 10: Inventory Optimization

Implements multi-horizon predictive demand forecasting:
- Temporal feature engineering (day of week, month, rolling stats, lag variables, promo lift)
- HistGradientBoostingRegressor / Gradient Boosting ensemble
- Quantifies forecast accuracy (R², MAE, RMSE, WAPE) vs classical moving average
- Generates 7-day, 14-day, and 30-day forward demand projections
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import pickle

class DemandForecaster:
    def __init__(self, models_dir=None):
        self.models_dir = models_dir or os.path.dirname(__file__)
        os.makedirs(self.models_dir, exist_ok=True)
        self.model = None
        self.feature_cols = [
            "unit_cost", "unit_price", "gross_margin_pct", "promotion_active",
            "day_of_week", "month", "seasonality_factor",
            "supplier_lead_time_days", "supplier_fill_rate",
            "lag_demand_1", "lag_demand_7", "rolling_mean_7", "rolling_std_7"
        ]
        self.metrics = {}
        self.category_means = {}

    def prepare_features(self, df):
        """Builds predictive lag and temporal features from telemetry observations."""
        data = df.sort_values(by=["sku_id", "location_id", "date"]).copy()

        # Group-wise lags and rolling stats
        grouped = data.groupby(["sku_id", "location_id"])["daily_demand"]
        data["lag_demand_1"] = grouped.shift(1).fillna(data["daily_demand"].mean())
        data["lag_demand_7"] = grouped.shift(7).fillna(data["daily_demand"].mean())
        data["rolling_mean_7"] = grouped.transform(lambda s: s.rolling(7, min_periods=1).mean())
        data["rolling_std_7"] = grouped.transform(lambda s: s.rolling(7, min_periods=1).std().fillna(1.0))

        return data

    def train_or_load(self, csv_path, force_train=False):
        """Trains or loads the serialized HistGradientBoosting demand forecasting model."""
        pkl_path = os.path.join(self.models_dir, "demand_forecaster_model.pkl")

        if os.path.exists(pkl_path) and not force_train:
            try:
                with open(pkl_path, "rb") as f:
                    saved_state = pickle.load(f)
                    self.model = saved_state["model"]
                    self.metrics = saved_state["metrics"]
                    self.feature_cols = saved_state["feature_cols"]
                    self.category_means = saved_state.get("category_means", {})
                    print(f"[DemandForecaster] Loaded pre-trained model from {pkl_path}")
                    return self.metrics
            except Exception as e:
                print(f"[DemandForecaster] Failed to load {pkl_path} ({e}), retraining...")

        print("[DemandForecaster] Training multi-horizon demand forecasting model...")
        df = pd.read_csv(csv_path)
        data = self.prepare_features(df)

        # Store baseline category means
        self.category_means = data.groupby("category")["daily_demand"].mean().to_dict()

        X = data[self.feature_cols].copy()
        y = data["daily_demand"].copy()

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)

        self.model = HistGradientBoostingRegressor(
            max_iter=150,
            learning_rate=0.08,
            max_depth=7,
            l2_regularization=1.5,
            random_state=42
        )
        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        y_pred = np.clip(y_pred, 0, None)

        # Benchmark comparison: 7-day Naive Moving Average
        naive_pred = X_test["rolling_mean_7"].values

        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        wape = (np.sum(np.abs(y_test - y_pred)) / max(1e-5, np.sum(y_test))) * 100.0

        naive_r2 = r2_score(y_test, naive_pred)
        naive_mae = mean_absolute_error(y_test, naive_pred)
        naive_wape = (np.sum(np.abs(y_test - naive_pred)) / max(1e-5, np.sum(y_test))) * 100.0

        self.metrics = {
            "r2_score": round(float(r2), 4),
            "mae": round(float(mae), 3),
            "rmse": round(float(rmse), 3),
            "wape_pct": round(float(wape), 2),
            "naive_r2": round(float(naive_r2), 4),
            "naive_mae": round(float(naive_mae), 3),
            "naive_wape_pct": round(float(naive_wape), 2),
            "forecast_accuracy_gain_pct": round(float(naive_wape - wape), 2),
            "test_sample_size": len(y_test)
        }

        # Save artifacts
        with open(pkl_path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "metrics": self.metrics,
                "feature_cols": self.feature_cols,
                "category_means": self.category_means
            }, f)

        print(f"[DemandForecaster] Model trained. R²={self.metrics['r2_score']:.4f}, MAE={self.metrics['mae']} (Accuracy Gain: +{self.metrics['forecast_accuracy_gain_pct']}%)")
        return self.metrics

    def forecast_sku_demand(self, sku_row, horizon_days=30, promo_boost=False):
        """
        Generates forward day-by-day demand forecasts for a given SKU operational context.
        """
        if self.model is None:
            raise ValueError("Model is not initialized. Train or load first.")

        forecasts = []
        base_demand = sku_row.get("daily_demand", sku_row.get("base_daily_demand", 25.0))
        cur_cost = sku_row.get("unit_cost", 10.0)
        cur_price = sku_row.get("unit_price", 15.0)
        margin = ((cur_price - cur_cost) / cur_price) * 100.0
        lt = sku_row.get("supplier_lead_time_days", 7.0)
        fill_rate = sku_row.get("supplier_fill_rate", 0.95)

        rolling_m = base_demand
        rolling_s = max(1.0, base_demand * 0.22)
        lag1 = base_demand
        lag7 = base_demand

        for day in range(1, horizon_days + 1):
            dow = (day % 7)
            dow_mult = 1.35 if dow in [4, 5, 6] else 0.92
            promo = 1 if (promo_boost or (day % 14 in [0, 1, 2])) else 0
            season_factor = dow_mult * (1.30 if promo else 1.00)

            feat = pd.DataFrame([{
                "unit_cost": cur_cost,
                "unit_price": cur_price,
                "gross_margin_pct": margin,
                "promotion_active": promo,
                "day_of_week": dow,
                "month": 11 if day > 20 else 10,
                "seasonality_factor": season_factor,
                "supplier_lead_time_days": lt,
                "supplier_fill_rate": fill_rate,
                "lag_demand_1": lag1,
                "lag_demand_7": lag7,
                "rolling_mean_7": rolling_m,
                "rolling_std_7": rolling_s
            }])

            pred_val = float(self.model.predict(feat[self.feature_cols])[0])
            pred_val = max(1.0, round(pred_val, 1))

            forecasts.append({
                "day": day,
                "projected_demand": pred_val,
                "dow": dow,
                "promotion_active": promo
            })

            # Update rolling state
            lag7 = lag1
            lag1 = pred_val
            rolling_m = 0.85 * rolling_m + 0.15 * pred_val

        return forecasts

