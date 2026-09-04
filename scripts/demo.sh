#!/bin/bash
# Hackathon Demonstration Script for RiskShield

API_URL="http://localhost:8000/payments"
API_KEY="test_key"

echo "======================================"
echo " RiskShield - Hackathon Demonstration"
echo "======================================"

generate_id() {
    uuidgen | tr '[:upper:]' '[:lower:]'
}

echo -e "\n--- DEMO 1: Legitimate Payment ---"
read -p "Press Enter to submit a standard low-risk transaction..."
curl -s -X POST $API_URL \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "external_transaction_id": "'$(generate_id)'",
    "amount": 25.50,
    "currency": "USD",
    "payment_method": "card",
    "ip_address": "192.168.1.1",
    "country": "US",
    "city": "Seattle",
    "latitude": 47.6062,
    "longitude": -122.3321,
    "customer": {
      "external_customer_id": "cust_demo_good",
      "account_created_at": "2022-01-01T00:00:00Z",
      "status": "active"
    },
    "merchant": {
      "external_merchant_id": "merch_coffee",
      "category": "food",
      "status": "active"
    },
    "device": {
      "device_fingerprint": "dev_demo_good",
      "device_type": "mobile",
      "operating_system": "iOS"
    }
  }' | jq '{transaction_id: .id, status: .status, decision: .risk_evaluation.decision, risk_level: .risk_evaluation.risk_level, signals: .risk_evaluation.signals}'

echo -e "\n--- DEMO 2: Suspicious Payment (Geographic Anomaly) ---"
read -p "Press Enter to submit a payment from a radically different location for the same customer..."
curl -s -X POST $API_URL \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "external_transaction_id": "'$(generate_id)'",
    "amount": 499.99,
    "currency": "USD",
    "payment_method": "card",
    "ip_address": "10.0.0.99",
    "country": "RU",
    "city": "Moscow",
    "latitude": 55.7558,
    "longitude": 37.6173,
    "customer": {
      "external_customer_id": "cust_demo_good",
      "account_created_at": "2022-01-01T00:00:00Z",
      "status": "active"
    },
    "merchant": {
      "external_merchant_id": "merch_electronics",
      "category": "electronics",
      "status": "active"
    },
    "device": {
      "device_fingerprint": "dev_demo_suspicious",
      "device_type": "desktop",
      "operating_system": "Windows"
    }
  }' | jq '{transaction_id: .id, status: .status, decision: .risk_evaluation.decision, risk_level: .risk_evaluation.risk_level, signals: .risk_evaluation.signals}'

echo -e "\n--- DEMO 3: Velocity Attack (Fraud Sequence) ---"
read -p "Press Enter to blast 5 transactions sequentially to trigger Velocity rules..."
for i in {1..5}; do
  echo "Transaction $i..."
  curl -s -X POST $API_URL \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "external_transaction_id": "'$(generate_id)'",
      "amount": 10.00,
      "currency": "USD",
      "payment_method": "card",
      "ip_address": "8.8.8.8",
      "customer": {
        "external_customer_id": "cust_demo_fraud",
        "status": "active"
      },
      "merchant": {
        "external_merchant_id": "merch_test",
        "status": "active"
      },
      "device": {
        "device_fingerprint": "dev_demo_fraud"
      }
    }' > /dev/null
done
echo "Now submitting the final transaction to see the result..."
curl -s -X POST $API_URL \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "external_transaction_id": "'$(generate_id)'",
    "amount": 10.00,
    "currency": "USD",
    "payment_method": "card",
    "ip_address": "8.8.8.8",
    "customer": {
      "external_customer_id": "cust_demo_fraud",
      "status": "active"
    },
    "merchant": {
      "external_merchant_id": "merch_test",
      "status": "active"
    },
    "device": {
      "device_fingerprint": "dev_demo_fraud"
    }
  }' | jq '{transaction_id: .id, status: .status, decision: .risk_evaluation.decision, risk_level: .risk_evaluation.risk_level, signals: .risk_evaluation.signals}'

echo -e "\nDone! You can view these on the RiskShield Dashboard at http://localhost:3000"
