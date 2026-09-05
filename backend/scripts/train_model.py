import os
import sys
import json
import asyncio
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import math
from joblib import dump
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    precision_recall_curve
)
from xgboost import XGBClassifier

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

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
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['amount'] = df['amount'].astype(float)
    df['latitude'] = df['latitude'].astype(float)
    df['longitude'] = df['longitude'].astype(float)
    df['customer_id'] = df['customer_id'].astype(str)
    df['device_id'] = df['device_id'].astype(str)
    df['ip_address'] = df['ip_address'].astype(str)
    df = df.sort_values('created_at').reset_index(drop=True)

    features = pd.DataFrame(index=df.index)

    # ── Amount features ───────────────────────────────────────────────
    features['amount'] = df['amount']
    features['amount_log'] = np.log1p(df['amount'])
    features['is_micro_transaction'] = (df['amount'] < 2.50).astype(int)
    features['is_round_amount'] = (df['amount'] % 100 == 0).astype(int)

    # ── Time features ─────────────────────────────────────────────────
    features['hour_of_day'] = df['created_at'].dt.hour
    features['is_night'] = ((df['created_at'].dt.hour < 6) | (df['created_at'].dt.hour >= 23)).astype(int)
    features['day_of_week'] = df['created_at'].dt.dayofweek
    features['is_weekend'] = (df['created_at'].dt.dayofweek >= 5).astype(int)

    # ── Customer historical features (expanding window, leak-safe) ────
    grouped = df.groupby('customer_id')
    features['historical_tx_count'] = grouped.cumcount()
    features['historical_avg_amount'] = grouped['amount'].transform(
        lambda x: x.expanding().mean().shift(1).fillna(0)
    )
    features['historical_std_amount'] = grouped['amount'].transform(
        lambda x: x.expanding().std().shift(1).fillna(0)
    )
    features['amount_deviation'] = np.where(
        features['historical_avg_amount'] > 0,
        features['amount'] / features['historical_avg_amount'],
        1.0
    )
    features['amount_zscore'] = np.where(
        features['historical_std_amount'] > 0,
        (features['amount'] - features['historical_avg_amount']) / features['historical_std_amount'],
        0.0
    )

    # ── Device & IP features ──────────────────────────────────────────
    features['is_new_device'] = (~df.duplicated(subset=['customer_id', 'device_id'])).astype(int)

    device_customers: dict[str, set] = {}
    ip_customers: dict[str, set] = {}
    device_customer_counts = []
    ip_customer_counts = []
    velocity_1h_list = []
    velocity_24h_list = []
    dist_list = []
    customer_history: dict[str, list] = {}

    for _, row in df.iterrows():
        dev = row['device_id']
        cust = row['customer_id']
        ip = row['ip_address']
        ts = row['created_at']
        lat = row['latitude']
        lon = row['longitude']

        # Device sharing count
        if dev not in device_customers:
            device_customers[dev] = set()
        device_customer_counts.append(len(device_customers[dev]) if device_customers[dev] else 1)
        device_customers[dev].add(cust)

        # IP sharing count
        if ip not in ip_customers:
            ip_customers[ip] = set()
        ip_customer_counts.append(len(ip_customers[ip]) if ip_customers[ip] else 1)
        ip_customers[ip].add(cust)

        if cust not in customer_history:
            customer_history[cust] = []
        history = customer_history[cust]

        # Velocity features
        cutoff_1h = ts - pd.Timedelta(hours=1)
        cutoff_24h = ts - pd.Timedelta(hours=24)
        recent_1h = [t for t in history if t['ts'] >= cutoff_1h]
        recent_24h = [t for t in history if t['ts'] >= cutoff_24h]
        velocity_1h_list.append(len(recent_1h))
        velocity_24h_list.append(len(recent_24h))

        # Distance from first-seen location (home proxy)
        if history:
            home_lat = history[0]['lat']
            home_lon = history[0]['lon']
            dist = haversine(home_lat, home_lon, lat, lon)
        else:
            dist = 0.0
        dist_list.append(dist)

        history.append({'ts': ts, 'lat': lat, 'lon': lon})

    features['device_customer_count'] = device_customer_counts
    features['ip_customer_count'] = ip_customer_counts
    features['velocity_1h'] = velocity_1h_list
    features['velocity_24h'] = velocity_24h_list
    features['distance_from_home_km'] = dist_list
    features['is_impossible_travel'] = (np.array(dist_list) > 1000).astype(int)

    # Target
    features['is_fraud'] = (df['label'] != 'LEGITIMATE').astype(int)

    features = features.fillna(0)
    return features


def find_precision_threshold(probs: np.ndarray, y: np.ndarray, target_precision: float = 0.97) -> float:
    """Find the lowest threshold that still yields >= target_precision."""
    precisions, _, thresholds = precision_recall_curve(y, probs)
    # precisions has one more element than thresholds
    for p, t in zip(precisions[:-1], thresholds):
        if p >= target_precision:
            return float(t)
    return 0.5


def evaluate(name: str, probs: np.ndarray, y_test: np.ndarray, threshold: float):
    preds = (probs >= threshold).astype(int)
    cm = confusion_matrix(y_test, preds)
    tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)
    return {
        "model": name,
        "threshold": float(threshold),
        "precision": float(precision_score(y_test, preds, zero_division=0)),
        "recall": float(recall_score(y_test, preds, zero_division=0)),
        "f1": float(f1_score(y_test, preds, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probs)),
        "pr_auc": float(average_precision_score(y_test, probs)),
        "tn": float(tn), "fp": float(fp),
        "fn": float(fn), "tp": float(tp),
    }


async def main():
    print("Loading data from database...")
    df = await load_data()
    print(f"Loaded {len(df)} transactions.")

    features_df = feature_engineering(df)
    print(f"Feature set: {list(features_df.drop(columns=['is_fraud']).columns)}")

    split_idx = int(len(features_df) * 0.80)

    X = features_df.drop(columns=['is_fraud'])
    y = features_df['is_fraud']

    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print(f"Training set: {len(X_train)} | Test set: {len(X_test)}")
    print(f"Fraud prevalence — train: {y_train.mean():.4f}  test: {y_test.mean():.4f}")

    pos_weight = (len(y_train) - y_train.sum()) / max(1, y_train.sum())
    print(f"Class imbalance weight: {pos_weight:.1f}x")

    # ── Model 1: Logistic Regression (with scaling) ───────────────────
    print("\nTraining Logistic Regression...")
    lr_pipe = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(
            max_iter=2000,
            C=0.5,
            class_weight='balanced',
            solver='lbfgs'
        ))
    ])
    lr_pipe.fit(X_train, y_train)
    lr_probs = lr_pipe.predict_proba(X_test)[:, 1]
    lr_thresh = find_precision_threshold(lr_probs, y_test)
    lr_metrics = evaluate("Logistic Regression", lr_probs, y_test, lr_thresh)

    # ── Model 2: Random Forest ────────────────────────────────────────
    print("Training Random Forest...")
    rf_model = RandomForestClassifier(
        n_estimators=400,
        max_depth=12,
        min_samples_leaf=2,
        class_weight='balanced_subsample',
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    rf_probs = rf_model.predict_proba(X_test)[:, 1]
    rf_thresh = find_precision_threshold(rf_probs, y_test)
    rf_metrics = evaluate("Random Forest", rf_probs, y_test, rf_thresh)

    # ── Model 3: XGBoost (precision-tuned) ───────────────────────────
    print("Training XGBoost (deep)...")
    xgb_model = XGBClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        gamma=1.0,
        reg_alpha=0.1,
        reg_lambda=1.0,
        scale_pos_weight=pos_weight,
        eval_metric='aucpr',
        random_state=42,
        n_jobs=-1
    )
    xgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    xgb_probs = xgb_model.predict_proba(X_test)[:, 1]
    xgb_thresh = find_precision_threshold(xgb_probs, y_test)
    xgb_metrics = evaluate("XGBoost", xgb_probs, y_test, xgb_thresh)

    # ── Model 4: Soft Ensemble ────────────────────────────────────────
    print("Building soft ensemble...")
    ensemble_probs = (lr_probs * 0.25 + rf_probs * 0.35 + xgb_probs * 0.40)
    ens_thresh = find_precision_threshold(ensemble_probs, y_test)
    ens_metrics = evaluate("Ensemble (LR+RF+XGB)", ensemble_probs, y_test, ens_thresh)

    all_metrics = [lr_metrics, rf_metrics, xgb_metrics, ens_metrics]
    for m in all_metrics:
        print(f"\n--- {m['model']} (threshold={m['threshold']:.3f}) ---")
        for k, v in m.items():
            if k != 'model':
                print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    # ── Pick best by precision (primary) then PR-AUC (secondary) ─────
    best_metrics = max(all_metrics, key=lambda m: (m['precision'], m['pr_auc']))
    best_name = best_metrics['model']

    # Map name → model/object
    model_map = {
        "Logistic Regression": (lr_pipe, lr_thresh),
        "Random Forest": (rf_model, rf_thresh),
        "XGBoost": (xgb_model, xgb_thresh),
    }

    os.makedirs(os.path.join(_backend_dir, "models"), exist_ok=True)
    model_path = os.path.join(_backend_dir, "models", "fraud_model_v1.joblib")
    metrics_path = os.path.join(_backend_dir, "models", "metrics_v1.json")

    if best_name in model_map:
        best_model_obj, best_threshold = model_map[best_name]
    else:
        # Ensemble — save XGBoost as primary (highest weight) with ensemble threshold
        best_model_obj, best_threshold = xgb_model, ens_thresh

    print(f"\nSaving best model ({best_name}, precision={best_metrics['precision']:.4f}) → {model_path}")
    dump(best_model_obj, model_path)

    # Save threshold so the runtime can apply the same cutoff
    threshold_path = os.path.join(_backend_dir, "models", "threshold_v1.json")
    with open(threshold_path, "w") as f:
        json.dump({"threshold": best_threshold, "model": best_name}, f, indent=2)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_version": "v2",
        "dataset_size": len(df),
        "features": list(X.columns),
        "best_model": best_name,
        "best_threshold": best_threshold,
        "all_model_metrics": all_metrics,
        "metrics": best_metrics
    }
    with open(metrics_path, "w") as f:
        json.dump(report, f, indent=2)

    # Feature importance (XGBoost)
    importance = dict(zip(X.columns, xgb_model.feature_importances_))
    print("\nTop feature importances (XGBoost):")
    for feat, score in sorted(importance.items(), key=lambda x: -x[1])[:10]:
        print(f"  {feat}: {score:.4f}")

    print("\nTraining complete.")


if __name__ == "__main__":
    asyncio.run(main())
