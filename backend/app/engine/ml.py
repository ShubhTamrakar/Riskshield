import os
import joblib
import json
import pandas as pd
import numpy as np
from app.engine.features.extractor import FeatureContext
from datetime import datetime


class FraudModelLoader:
    _instance = None
    _model = None
    _threshold: float = 0.5

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        model_path = os.path.join(backend_dir, "models", "fraud_model_v1.joblib")
        threshold_path = os.path.join(backend_dir, "models", "threshold_v1.json")

        if os.path.exists(model_path):
            self._model = joblib.load(model_path)
        else:
            self._model = None

        if os.path.exists(threshold_path):
            with open(threshold_path) as f:
                data = json.load(f)
            self._threshold = float(data.get("threshold", 0.5))
        else:
            self._threshold = 0.5

    def _build_features(self, context: FeatureContext) -> pd.DataFrame:
        amount = context.request.amount
        avg_amount = context.customer_historical_avg_amount
        std_amount = getattr(context, 'customer_historical_std_amount', 0.0) or 0.0
        deviation = (amount / avg_amount) if avg_amount > 0 else 1.0
        zscore = ((amount - avg_amount) / std_amount) if std_amount > 0 else 0.0
        distance = context.distance_from_home_km

        return pd.DataFrame([{
            # Amount
            'amount':                   amount,
            'amount_log':               np.log1p(amount),
            'is_micro_transaction':     int(amount < 2.50),
            'is_round_amount':          int(amount % 100 == 0),
            # Time
            'hour_of_day':              datetime.utcnow().hour,
            'is_night':                 int(datetime.utcnow().hour < 6 or datetime.utcnow().hour > 22),
            'day_of_week':              datetime.utcnow().weekday(),
            'is_weekend':               int(datetime.utcnow().weekday() >= 5),
            # Customer history
            'historical_tx_count':      context.customer_historical_tx_count,
            'historical_avg_amount':    avg_amount,
            'historical_std_amount':    std_amount,
            'amount_deviation':         deviation,
            'amount_zscore':            zscore,
            # Device / IP
            'is_new_device':            int(context.is_new_device),
            'device_customer_count':    context.device_customer_count,
            'ip_customer_count':        context.ip_customer_count,
            # Velocity
            'velocity_1h':              context.customer_velocity_1h,
            'velocity_24h':             getattr(context, 'customer_velocity_24h', 0),
            # Geography
            'distance_from_home_km':    distance,
            'is_impossible_travel':     int(distance > 1000),
        }])

    def predict_proba(self, context: FeatureContext) -> float:
        if self._model is None:
            return 0.0

        df = self._build_features(context)
        try:
            prob = float(self._model.predict_proba(df)[0][1])
            return prob
        except Exception as e:
            print(f"ML Model prediction failed: {e}")
            return 0.0

    @property
    def threshold(self) -> float:
        return self._threshold
