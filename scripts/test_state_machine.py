#!/usr/bin/env python3
"""
Test Explicit Status State Machine & HTTP 409 Conflict (§2.2)
Verifies:
  1. open -> resolved (valid transition)
  2. resolved -> in_progress (invalid transition, must return HTTP 409)
"""

import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000"


def test_state_machine():
    print(f"Testing state machine against {BASE_URL}...")

    # 1. Create a complaint (starts in status 'open')
    create_payload = json.dumps({
        "text": "Main water valve leaking profusely on Street 10",
        "location": "Karachi",
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/complaints",
        data=create_payload,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req) as resp:
        complaint = json.loads(resp.read().decode("utf-8"))
        cid = complaint["id"]
        status = complaint["status"]
        print(f"1. Created complaint {cid} with initial status: '{status}'")

    # 2. Advance status open -> in_progress (valid transition)
    in_progress_payload = json.dumps({"status": "in_progress"}).encode("utf-8")
    req_in_progress = urllib.request.Request(
        f"{BASE_URL}/api/complaints/{cid}/status",
        data=in_progress_payload,
        headers={"Content-Type": "application/json"},
        method="PATCH",
    )
    with urllib.request.urlopen(req_in_progress) as resp:
        updated = json.loads(resp.read().decode("utf-8"))
        print(f"2. Valid transition: open -> '{updated['status']}'")

    # 3. Advance status in_progress -> resolved (valid terminal state)
    resolved_payload = json.dumps({"status": "resolved"}).encode("utf-8")
    req_resolved = urllib.request.Request(
        f"{BASE_URL}/api/complaints/{cid}/status",
        data=resolved_payload,
        headers={"Content-Type": "application/json"},
        method="PATCH",
    )
    with urllib.request.urlopen(req_resolved) as resp:
        updated = json.loads(resp.read().decode("utf-8"))
        print(f"3. Valid transition: in_progress -> '{updated['status']}'")

    # 4. Attempt invalid transition resolved -> in_progress (Must return HTTP 409)
    invalid_payload = json.dumps({"status": "in_progress"}).encode("utf-8")
    req_invalid = urllib.request.Request(
        f"{BASE_URL}/api/complaints/{cid}/status",
        data=invalid_payload,
        headers={"Content-Type": "application/json"},
        method="PATCH",
    )

    try:
        urllib.request.urlopen(req_invalid)
        print("[FAIL] Invalid transition did NOT return HTTP 409!")
        sys.exit(1)
    except urllib.error.HTTPError as e:
        if e.code == 409:
            body = e.read().decode("utf-8")
            print(f"\n[SUCCESS] Caught expected HTTP 409 Conflict!")
            print(f"  Status Code : {e.code} Conflict")
            print(f"  Server Detail: {body}")
        else:
            print(f"[FAIL] Unexpected HTTP status code: {e.code}")
            sys.exit(1)


if __name__ == "__main__":
    test_state_machine()
