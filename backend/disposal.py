# disposal.py
# Stage 3 — Expiry watchdog, incinerator routing, disposal certificates

import time
import threading
import hashlib
from datetime import datetime
from backend.database import surplus_db

# ── CPCB Licensed Facilities — Tamil Nadu ─────────────────────────────────────
INCINERATORS = [
    {"id":"CBMWTF_TN_001","name":"Ramky Energy & Environment Ltd","location":"Salem, Tamil Nadu","pincode":"636010","contact":"0427-2345678","status":"ACTIVE"},
    {"id":"CBMWTF_TN_002","name":"Koval Bio Waste Management Pvt Ltd","location":"Coimbatore, Tamil Nadu","pincode":"641001","contact":"0422-2345678","status":"ACTIVE"},
    {"id":"CBMWTF_TN_003","name":"Tamil Nadu Waste Management Ltd","location":"Gummidipoondi, Chennai","pincode":"601201","contact":"044-27929292","status":"ACTIVE"},
    {"id":"CBMWTF_TN_004","name":"Aseptic System Bio Medical Waste","location":"Ambattur, Chennai","pincode":"600053","contact":"044-26581234","status":"ACTIVE"}
]

# ── In-memory stores ───────────────────────────────────────────────────────────
disposal_queue        = {}   # surplus_id → disposal record
disposal_certificates = {}   # cert_id    → certificate record


# ── Helpers ───────────────────────────────────────────────────────────────────

def months_to_expiry(expiry_str: str) -> int:
    try:
        y, m = map(int, expiry_str.split("-"))
        now  = datetime.utcnow()
        return (y - now.year) * 12 + (m - now.month)
    except Exception:
        return -1


def nearest_incinerator(pincode: str) -> dict:
    if not pincode:
        return INCINERATORS[0]
    prefix = pincode[:3]
    if prefix in ["600","601","602","603"]:
        return INCINERATORS[2]  # Gummidipoondi, Chennai
    if prefix in ["641","642"]:
        return INCINERATORS[1]  # Coimbatore
    if prefix in ["636","637"]:
        return INCINERATORS[0]  # Salem
    return INCINERATORS[0]


def generate_cert_id(surplus_id: str) -> str:
    raw = f"{surplus_id}-{int(time.time())}"
    return "CERT-" + hashlib.sha256(raw.encode()).hexdigest()[:10].upper()


# ── Watchdog ──────────────────────────────────────────────────────────────────

def run_watchdog():
    while True:
        flagged  = 0
        now_ts   = int(time.time())
        for surplus_id, surplus in list(surplus_db.items()):
            if surplus.get("matched"):
                continue
            if surplus_id in disposal_queue:
                continue
            months = months_to_expiry(surplus.get("expiry_date",""))
            if months <= 1:
                facility = nearest_incinerator(surplus.get("location_pincode",""))
                disposal_queue[surplus_id] = {
                    "surplus_id":        surplus_id,
                    "drug_name":         surplus.get("drug_name",""),
                    "quantity":          surplus.get("quantity", 0),
                    "expiry_date":       surplus.get("expiry_date",""),
                    "sender_id":         surplus.get("sender_id",""),
                    "status":            "EXPIRED" if months < 0 else "DISPOSAL_PENDING",
                    "flagged_at":        now_ts,
                    "months_left":       months,
                    "facility":          facility,
                    "pickup_scheduled":  False,
                    "certificate_id":    None
                }
                surplus_db[surplus_id]["disposal_status"] = "DISPOSAL_PENDING"
                flagged += 1
                print(f"[WATCHDOG] Flagged {surplus.get('drug_name')} ({surplus_id}) → {facility['name']}")

        print(f"[WATCHDOG] Scan complete — {flagged} new batch(es) flagged")
        time.sleep(3600)  # Every hour; change to 86400 for daily in production


def start_watchdog():
    thread = threading.Thread(target=run_watchdog, daemon=True)
    thread.start()
    print("[WATCHDOG] Started — scanning every hour")


# ── Pickup scheduling + certificate ───────────────────────────────────────────

def schedule_pickup(surplus_id: str) -> dict:
    record = disposal_queue.get(surplus_id)
    if not record:
        return {"error": "Surplus not in disposal queue"}
    if record.get("pickup_scheduled"):
        return {"error": "Already scheduled", "certificate_id": record["certificate_id"]}

    cert_id = generate_cert_id(surplus_id)
    now     = datetime.utcnow()

    certificate = {
        "certificate_id":    cert_id,
        "issued_at":         now.isoformat(),
        "surplus_id":        surplus_id,
        "drug_name":         record["drug_name"],
        "quantity":          record["quantity"],
        "expiry_date":       record["expiry_date"],
        "sender_id":         record["sender_id"],
        "disposal_method":   "INCINERATION",
        "facility_id":       record["facility"]["id"],
        "facility_name":     record["facility"]["name"],
        "facility_location": record["facility"]["location"],
        "facility_contact":  record["facility"]["contact"],
        "pickup_date":       now.strftime("%Y-%m-%d"),
        "status":            "SCHEDULED",
        "compliance_note":   "Bio-Medical Waste Management Rules 2016 — Schedule I, Category 4",
        "cpcb_auth":         "AUTHORIZED TREATMENT FACILITY"
    }

    disposal_certificates[cert_id]              = certificate
    disposal_queue[surplus_id]["pickup_scheduled"] = True
    disposal_queue[surplus_id]["certificate_id"]   = cert_id
    disposal_queue[surplus_id]["status"]           = "PICKUP_SCHEDULED"

    print(f"[DISPOSAL] Certificate {cert_id} issued for {record['drug_name']}")
    return certificate


def mark_disposed(surplus_id: str) -> dict:
    record = disposal_queue.get(surplus_id)
    if not record:
        return {"error": "Not in disposal queue"}
    disposal_queue[surplus_id]["status"]      = "DISPOSED"
    disposal_queue[surplus_id]["disposed_at"] = int(time.time())
    cert_id = record.get("certificate_id")
    if cert_id and cert_id in disposal_certificates:
        disposal_certificates[cert_id]["status"] = "COMPLETED"
    surplus_db[surplus_id]["disposal_status"] = "DISPOSED"
    return {"message": "Marked as disposed", "certificate_id": cert_id}