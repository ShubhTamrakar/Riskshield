import os
import joblib
import pandas as pd
import numpy as np
from app.engine.features.extractor import FeatureContext

class FraudModelLoader:
    _instance = None
    _model = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        model_path = os.path.join(backend_dir, "models", "fraud_model_v1.joblib")
        if os.path.exists(model_path):
            self._model = joblib.load(model_path)
        else:
            self._model = None

    def predict_proba(self, context: FeatureContext) -> float:
        if self._model is None:
            return 0.0
            
        # Match the features from feature_engineering in train_model.py
        # Features needed: amount, historical_tx_count, historical_avg_amount, amount_deviation, 
        # is_new_device, device_customer_count, ip_customer_count
        
        amount = context.request.amount
        avg_amount = context.customer_historical_avg_amount
        deviation = (amount / avg_amount) if avg_amount > 0 else 1.0
        
        features = {
            'amount': amount,
            'historical_tx_count': context.customer_historical_tx_count,
            'historical_avg_amount': avg_amount,
            'amount_deviation': deviation,
            'is_new_device': 1 if context.is_new_device else 0,
            'device_customer_count': context.device_customer_count,
            'ip_customer_count': context.ip_customer_count
        }
        
        df = pd.DataFrame([features])
        
        try:
            # Get probability of class 1 (Fraud)
            prob = self._model.predict_proba(df)[0][1]
            return float(prob)
        except Exception as e:
            print(f"ML Model prediction failed: {e}")
            return 0.0
