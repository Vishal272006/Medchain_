# demo_run.py
# Full end-to-end demo — run this once to populate the system

import requests
import json
import time

BASE = "http://localhost:8000"

print("\n=== MEDCHAIN DEMO RUN ===\n")

# ── Step 1: Hospital lists surplus ──────────────────────────
print("[ 1/4 ] Hospital listing surplus stock...")
r = requests.post(f"{BASE}/surplus/list", json={
    "sender_id":        "HOSP_CHENNAI_001",
    "drug_name":        "Metformin 500mg",
    "quantity":         500,
    "expiry_date":      "2026-09",
    "storage_type":     "AMBIENT",
    "location_pincode": "600001"
})
surplus = r.json()
surplus_id = surplus["surplus_id"]
print(f"    Surplus ID: {surplus_id} ✓")

time.sleep(1)

# ── Step 2: Rural clinic makes a request ─────────────────────
print("[ 2/4 ] Rural clinic requesting medicines...")
r = requests.post(f"{BASE}/clinic/request", json={
    "receiver_id":      "PHC_VILLUPURAM_007",
    "drug_name":        "Metformin 500mg",
    "quantity_needed":  200,
    "location_pincode": "605001"
})
request = r.json()
request_id = request["request_id"]
print(f"    Request ID: {request_id} ✓")

time.sleep(1)

# ── Step 3: System creates and signs the batch ───────────────
print("[ 3/4 ] Creating signed batch + generating QR...")
r = requests.post(f"{BASE}/batch/create", json={
    "surplus_id": surplus_id,
    "request_id": request_id
})
batch = r.json()
batch_id    = batch["batch_id"]
signed_payload = batch["signed_payload"]
print(f"    Batch ID:  {batch_id} ✓")
print(f"    QR saved:  {batch['qr_saved_at']} ✓")

time.sleep(1)

# ── Step 4: Verify the batch ─────────────────────────────────
print("[ 4/4 ] Verifying batch (simulating clinic scan)...")
r = requests.post(f"{BASE}/verify", json={
    "qr_data": json.dumps(signed_payload)
})
result = r.json()

print(f"\n{'='*40}")
print(f"  VERDICT  : {result['verdict']}")
print(f"  REASON   : {result['reason']}")
print(f"  DRUG     : {result.get('drug_name', '—')}")
print(f"  QUANTITY : {result.get('quantity', '—')} units")
print(f"  SENDER   : {result.get('sender', '—')}")
print(f"  RECEIVER : {result.get('receiver', '—')}")
print(f"  SIG OK   : {result.get('signature_valid', False)}")

if "sensor_summary" in result:
    ss = result["sensor_summary"]
    print(f"  SENSOR   : {ss['total_readings']} readings, "
          f"{ss['breach_count']} breaches, "
          f"{'CLEAN' if ss['transit_clean'] else 'COMPROMISED'}")

print(f"{'='*40}\n")

# ── Save batch ID for reference ──────────────────────────────
with open("demo_batch.txt", "w") as f:
    f.write(batch_id)
print(f"Batch ID saved to demo_batch.txt")
print(f"QR image at: backend/qr_{batch_id}.png")
print(f"\nOpen http://localhost:3000 and paste this to verify in PWA:")
print(json.dumps(signed_payload, indent=2))