import os
import sys
import json
import asyncio
from datetime import datetime
import pandas as pd
import numpy as np
import math
from joblib import dump
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import engine

def haversine(lat1, lon1, lat2, lon2):
    if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
        return 0.0
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

async def load_data():
    query = """
    SELECT 
        t.id, t.customer_id, t.merchant_id, t.device_id, t.amount, 
        t.ip_address, t.latitude, t.longitude, t.status, t.created_at,
        g.label
    FROM transactions t
    JOIN ground_truth g ON t.id = g.transaction_id
    ORDER BY t.created_at ASC
    """
    async with engine.connect() as conn:
        result = await conn.execute(text(query))
        rows = result.fetchall()
        columns = result.keys()
        
    df = pd.DataFrame(rows, columns=columns)
    return df

def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    print("Engineering features...")
    # Convert types
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['amount'] = df['amount'].astype(float)
    df['latitude'] = df['latitude'].astype(float)
    df['longitude'] = df['longitude'].astype(float)
    df['customer_id'] = df['customer_id'].astype(str)
    df['device_id'] = df['device_id'].astype(str)
    df['ip_address'] = df['ip_address'].astype(str)
    
    # Sort chronologically
    df = df.sort_values('created_at')
    
    features = pd.DataFrame(index=df.index)
    
    features['amount'] = df['amount']
    
    # Customer historical avg amount & count (expanding window)
    grouped = df.groupby('customer_id')
    features['historical_tx_count'] = grouped.cumcount()
    features['historical_avg_amount'] = grouped['amount'].transform(lambda x: x.expanding().mean().shift(1).fillna(0))
    features['amount_deviation'] = np.where(features['historical_avg_amount'] > 0, 
                                            features['amount'] / features['historical_avg_amount'], 
                                            1.0)
    
    # Is New Device
    features['is_new_device'] = (~df.duplicated(subset=['customer_id', 'device_id'])).astype(int)
    
    # Device sharing (how many customers used this device before this tx)
    device_customers = {}
    device_customer_counts = []
    
    ip_customers = {}
    ip_customer_counts = []
    
    for _, row in df.iterrows():
        dev = row['device_id']
        cust = row['customer_id']
        ip = row['ip_address']
        
        # for device
        if dev not in device_customers:
            device_customers[dev] = set()
        device_customer_counts.append(len(device_customers[dev]) if len(device_customers[dev]) > 0 else 1)
        device_customers[dev].add(cust)
        
        # for IP
        if ip not in ip_customers:
            ip_customers[ip] = set()
        ip_customer_counts.append(len(ip_customers[ip]) if len(ip_customers[ip]) > 0 else 1)
        ip_customers[ip].add(cust)

    features['device_customer_count'] = device_customer_counts
    features['ip_customer_count'] = ip_customer_counts
    
    # Target label
    features['is_fraud'] = (df['label'] != 'LEGITIMATE').astype(int)
    
    features = features.fillna(0)
    return features

async def main():
    print("Loading data from database...")
    df = await load_data()
    print(f"Loaded {len(df)} transactions.")
    
    features_df = feature_engineering(df)
    
    print("Splitting dataset (time-based)...")
    split_idx = int(len(features_df) * 0.8)
    
    # Drop target from X
    X = features_df.drop(columns=['is_fraud'])
    y = features_df['is_fraud']
    
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"Training set: {len(X_train)} | Test set: {len(X_test)}")
    print(f"Fraud prevalence in train: {y_train.mean():.4f} | test: {y_test.mean():.4f}")
    
    print("Training Logistic Regression...")
    lr_model = LogisticRegression(max_iter=1000, class_weight='balanced')
    lr_model.fit(X_train, y_train)
    lr_preds = lr_model.predict(X_test)
    lr_probs = lr_model.predict_proba(X_test)[:, 1]
    
    print("Training XGBoost...")
    xgb_model = XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, scale_pos_weight=(len(y_train) - sum(y_train)) / max(1, sum(y_train)))
    xgb_model.fit(X_train, y_train)
    xgb_preds = xgb_model.predict(X_test)
    xgb_probs = xgb_model.predict_proba(X_test)[:, 1]
    
    def evaluate(name, preds, probs):
        metrics = {
            "model": name,
            "precision": float(precision_score(y_test, preds)),
            "recall": float(recall_score(y_test, preds)),
            "f1": float(f1_score(y_test, preds)),
            "roc_auc": float(roc_auc_score(y_test, probs)),
            "pr_auc": float(average_precision_score(y_test, probs)),
        }
        cm = confusion_matrix(y_test, preds)
        metrics["tn"], metrics["fp"], metrics["fn"], metrics["tp"] = [float(x) for x in cm.ravel()]
        return metrics

    lr_metrics = evaluate("Logistic Regression", lr_preds, lr_probs)
    xgb_metrics = evaluate("XGBoost", xgb_preds, xgb_probs)
    
    print("\n--- Logistic Regression ---")
    for k, v in lr_metrics.items(): print(f"{k}: {v}")
    
    print("\n--- XGBoost ---")
    for k, v in xgb_metrics.items(): print(f"{k}: {v}")
    
    # Save the best model (using PR-AUC as the tiebreaker)
    best_model = xgb_model if xgb_metrics['pr_auc'] > lr_metrics['pr_auc'] else lr_model
    best_metrics = xgb_metrics if xgb_metrics['pr_auc'] > lr_metrics['pr_auc'] else lr_metrics
    
    os.makedirs(os.path.join(_backend_dir, "models"), exist_ok=True)
    model_path = os.path.join(_backend_dir, "models", "fraud_model_v1.joblib")
    metrics_path = os.path.join(_backend_dir, "models", "metrics_v1.json")
    
    print(f"\nSaving best model ({best_metrics['model']}) to {model_path}")
    dump(best_model, model_path)
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "model_version": "v1",
        "dataset_size": len(df),
        "features": list(X.columns),
        "metrics": best_metrics
    }
    with open(metrics_path, "w") as f:
        json.dump(report, f, indent=2)
        
    print("Training complete.")

if __name__ == "__main__":
    asyncio.run(main())
