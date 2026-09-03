import random
from datetime import datetime, timedelta
from typing import List
import uuid

from synthetic.generator import SyntheticCustomer, SyntheticMerchant, TransactionState
from synthetic.config import FraudLabel

def generate_normal_sequence(
    customer: SyntheticCustomer, 
    merchants: List[SyntheticMerchant], 
    start_time: datetime, 
    end_time: datetime, 
    random_state: random.Random
) -> List[TransactionState]:
    """Generates a normal baseline sequence for a customer."""
    txs = []
    current_time = start_time
    
    # Approx transactions per day
    tx_per_day = customer.config.tx_per_month_mean / 30.0
    if tx_per_day <= 0:
        tx_per_day = 0.1
        
    while current_time < end_time:
        # Determine if transaction happens today
        if random_state.random() < tx_per_day:
            # Pick a random time during the day
            hour = random_state.randint(8, 22)
            minute = random_state.randint(0, 59)
            tx_time = current_time.replace(hour=hour, minute=minute)
            
            if tx_time > end_time:
                break
                
            merchant = random_state.choice(merchants)
            
            # Amount based on profile distribution
            amount = max(1.0, random_state.gauss(customer.config.avg_tx_value, customer.config.tx_value_std))
            
            tx = TransactionState(
                customer=customer,
                merchant=merchant,
                amount=round(amount, 2),
                timestamp=tx_time,
                label=FraudLabel.LEGITIMATE,
                scenario="normal"
            )
            txs.append(tx)
            
        current_time += timedelta(days=1)
        
    return txs

def inject_high_value_anomaly(txs: List[TransactionState], random_state: random.Random):
    """Scenario 2: High-value anomaly."""
    if not txs: return
    idx = random_state.randint(0, len(txs)-1)
    tx = txs[idx]
    
    tx.amount = round(tx.amount * random_state.uniform(10, 50), 2)
    tx.label = FraudLabel.HIGH_VALUE_ANOMALY
    tx.scenario = "high_value_anomaly"

def inject_velocity_attack(txs: List[TransactionState], random_state: random.Random):
    """Scenario 3: Transaction velocity attack."""
    if len(txs) < 2: return
    idx = random_state.randint(0, len(txs)-2)
    base_tx = txs[idx]
    
    # Generate 5-10 rapid transactions
    num_attacks = random_state.randint(5, 10)
    attack_txs = []
    
    for i in range(num_attacks):
        attack_tx = TransactionState(
            customer=SyntheticCustomer(random_state), # Temp, just to copy fields, will overwrite
            merchant=SyntheticMerchant(random_state, "retail"),
            amount=round(base_tx.amount * random_state.uniform(0.8, 1.2), 2),
            timestamp=base_tx.timestamp + timedelta(seconds=i*30),
            label=FraudLabel.VELOCITY_ATTACK,
            scenario="velocity_attack"
        )
        # Fix temp fields
        attack_tx.customer_id = base_tx.customer_id
        attack_tx.device_id = base_tx.device_id
        attack_tx.merchant_id = base_tx.merchant_id
        attack_tx.ip_address = base_tx.ip_address
        attack_tx.country = base_tx.country
        attack_tx.city = base_tx.city
        attack_tx.latitude = base_tx.latitude
        attack_tx.longitude = base_tx.longitude
        
        attack_txs.append(attack_tx)
        
    txs.extend(attack_txs)
    txs.sort(key=lambda x: x.timestamp)

def inject_account_takeover(txs: List[TransactionState], random_state: random.Random):
    """Scenario 5: Account takeover (ATO). normal -> new device/IP -> strange locations -> high value"""
    if len(txs) < 5: return
    idx = random_state.randint(len(txs)//2, len(txs)-2)
    
    # All transactions after idx are ATO
    new_device = uuid.uuid4()
    # Add the new device to the customer's device list so it gets saved to the DB!
    # All txs belong to the same customer.
    customer = txs[0].customer if hasattr(txs[0], 'customer') else None
    if customer:
        customer.devices.append(new_device)
        
    new_ip = f"{random_state.randint(1,255)}.{random_state.randint(1,255)}.{random_state.randint(1,255)}.{random_state.randint(1,255)}"
    
    for i in range(idx, len(txs)):
        tx = txs[i]
        tx.device_id = new_device
        tx.ip_address = new_ip
        tx.country = "RU" if random_state.random() > 0.5 else "CN"
        tx.city = "Unknown"
        tx.latitude = random_state.uniform(30.0, 60.0)
        tx.longitude = random_state.uniform(30.0, 100.0)
        tx.amount = round(tx.amount * 5, 2)
        tx.label = FraudLabel.ACCOUNT_TAKEOVER
        tx.scenario = "account_takeover"

def inject_multiple_failed_then_success(txs: List[TransactionState], random_state: random.Random):
    """Scenario 11: Multiple failed payments followed by success."""
    if len(txs) < 2: return
    idx = random_state.randint(0, len(txs)-1)
    base_tx = txs[idx]
    
    num_fails = random_state.randint(3, 7)
    fail_txs = []
    
    for i in range(num_fails):
        fail_tx = TransactionState(
            customer=SyntheticCustomer(random_state),
            merchant=SyntheticMerchant(random_state, "retail"),
            amount=base_tx.amount,
            timestamp=base_tx.timestamp - timedelta(minutes=(num_fails-i)*2),
            label=FraudLabel.MULTIPLE_FAILED,
            scenario="multiple_failed"
        )
        fail_tx.customer_id = base_tx.customer_id
        fail_tx.device_id = base_tx.device_id
        fail_tx.merchant_id = base_tx.merchant_id
        fail_tx.ip_address = base_tx.ip_address
        fail_tx.country = base_tx.country
        fail_tx.city = base_tx.city
        fail_tx.latitude = base_tx.latitude
        fail_tx.longitude = base_tx.longitude
        fail_tx.status = "failed"
        
        fail_txs.append(fail_tx)
        
    txs.extend(fail_txs)
    txs.sort(key=lambda x: x.timestamp)
