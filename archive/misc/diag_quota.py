import requests
import time
import uuid
import hmac
import hashlib
import json
import sys
import os

# 模拟 src 路径加载
sys.path.append(os.path.join(os.getcwd(), 'src'))

from core.auth import _load_local_token, _generate_api_signature
from config.settings import AI_QUOTA_URL

def test_quota():
    print(f"Testing AI Quota URL: {AI_QUOTA_URL}")
    token, _, _ = _load_local_token()
    if not token:
        print("Error: No local token found. Please activate first.")
        return

    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    signature = _generate_api_signature("", timestamp, nonce)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Request-Timestamp": timestamp,
        "X-Request-Nonce": nonce,
        "X-Request-Signature": signature,
        "User-Agent": "ZenClean-Diag/1.0"
    }

    try:
        res = requests.get(AI_QUOTA_URL, headers=headers, timeout=10)
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")
        if res.status_code == 200:
            data = res.json()
            if data.get("success"):
                print("Success! Quota:", data.get("quota"))
            else:
                print("Business Failure:", data.get("msg"))
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_quota()
