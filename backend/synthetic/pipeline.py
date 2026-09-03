import random
from datetime import datetime, timedelta
from typing import List, Tuple

from synthetic.config import DatasetConfig, FraudLabel
from synthetic.generator import SyntheticCustomer, SyntheticMerchant, TransactionState
from synthetic.scenarios import (
    generate_normal_sequence,
    inject_high_value_anomaly,
    inject_velocity_attack,
    inject_account_takeover,
    inject_multiple_failed_then_success
)

def build_dataset(config: DatasetConfig) -> Tuple[List[SyntheticCustomer], List[SyntheticMerchant], List[TransactionState]]:
    random_state = random.Random(config.seed)
    
    # 1. Generate static entities
    merchants = [SyntheticMerchant(random_state, category=random_state.choice(["retail", "groceries", "electronics", "travel", "food", "services"])) 
                 for _ in range(config.num_merchants)]
    
    customers = [SyntheticCustomer(random_state) for _ in range(config.num_customers)]
    
    # 2. Generate transaction sequences
    all_transactions = []
    
    start_time = datetime.utcnow() - timedelta(days=90)
    end_time = datetime.utcnow()
    
    # To hit the target_transactions precisely, we can adjust the end_time or just take a slice.
    # We will generate sequences and stop when we exceed target.
    
    for customer in customers:
        if len(all_transactions) >= config.target_transactions:
            break
            
        # Normal baseline
        customer_txs = generate_normal_sequence(customer, merchants, start_time, end_time, random_state)
        
        # Inject fraud based on fraud_rate
        if random_state.random() < config.fraud_rate and len(customer_txs) > 0:
            scenario_choice = random_state.choice([
                "high_value_anomaly",
                "velocity_attack",
                "account_takeover",
                "multiple_failed"
            ])
            
            if scenario_choice == "high_value_anomaly":
                inject_high_value_anomaly(customer_txs, random_state)
            elif scenario_choice == "velocity_attack":
                inject_velocity_attack(customer_txs, random_state)
            elif scenario_choice == "account_takeover":
                inject_account_takeover(customer_txs, random_state)
            elif scenario_choice == "multiple_failed":
                inject_multiple_failed_then_success(customer_txs, random_state)
                
        all_transactions.extend(customer_txs)
        
    # Trim to exactly target_transactions
    if len(all_transactions) > config.target_transactions:
        all_transactions = all_transactions[:config.target_transactions]
        
    return customers, merchants, all_transactions
