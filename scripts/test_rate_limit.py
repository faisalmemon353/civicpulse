#!/usr/bin/env python3
"""
Test Distributed Rate Limiting on POST /api/complaints (§2.4)
Sends requests until the Redis distributed rate limiter triggers HTTP 429.
"""

import json
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000"


def test_rate_limit():
    print(f"Testing rate limit against {BASE_URL}/api/complaints...")
    limit_triggered = False

    payload = json.dumps({
        "text": "Rate limit verification burst test string",
        "location": "Lahore",
    }).encode("utf-8")

    for i in range(1, 150):
        req = urllib.request.Request(
            f"{BASE_URL}/api/complaints",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req) as resp:
                if i % 20 == 0:
                    print(f"  Sent {i} requests... status: {resp.status}")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = e.headers.get("Retry-After")
                print("\n[SUCCESS] Distributed Rate Limit Successfully Triggered!")
                print(f"  HTTP Status Code : {e.code} Too Many Requests")
                print(f"  Retry-After Header: {retry_after} seconds")
                limit_triggered = True
                break
            else:
                print(f"  Unexpected HTTP error: {e.code}")
                break

    if not limit_triggered:
        print("[WARNING] Did not hit 429 within 120 requests.")


if __name__ == "__main__":
    test_rate_limit()
