import requests
import time
from datetime import datetime
import random

URL = "http://localhost:8000/orders/"

def create_order_payload():
    now = datetime.utcnow().isoformat()
    mrp = random.randint(500, 1500)
    quantity = random.randint(1, 3)
    order_amount = mrp * quantity

    return {
        "order_date": now,
        "order_amount": order_amount,
        "shipping_date": now,
        "order_status": "pending",
        "cart_id": 9,
        "user_id": 1,
        "items": [
            {
                "product_id": random.choice([1, 2, 3]),
                "mrp": mrp,
                "quantity": quantity
            }
        ]
    }

for i in range(5):
    payload = create_order_payload()
    response = requests.post(URL, json=payload)

    print(f"[{i+1}] Status: {response.status_code}, Response: {response.json()}")
    time.sleep(5)
