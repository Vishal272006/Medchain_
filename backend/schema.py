# schema.py
# Defines the QR payload structure for every medicine batch

import uuid
import time

def create_batch_payload(
    drug_name: str,
    quantity: int,
    expiry_date: str,        # format: "YYYY-MM"
    sender_id: str,          # hospital/pharmacy ID
    receiver_id: str,        # clinic ID
    storage_type: str        # "AMBIENT" | "COLD" | "FROZEN"
) -> dict:
    """
    Creates an unsigned batch payload.
    This is the data contract between all system components.
    """
    return {
        "batch_id": str(uuid.uuid4())[:8].upper(),   # e.g. "A3F1B2C4"
        "drug_name": drug_name,
        "quantity": quantity,
        "expiry_date": expiry_date,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "storage_type": storage_type,
        "packed_at": int(time.time()),               # unix timestamp
        "schema_version": "1.0",

        # Sensor thresholds — checked against transit log at receiver end
        "thresholds": {
            "temp_min_c": 2  if storage_type == "COLD" else 15,
            "temp_max_c": 8  if storage_type == "COLD" else 30,
            "humidity_max_pct": 75,
            "light_exposure_allowed": storage_type == "AMBIENT"
        }
    }


# --- Quick test ---
if __name__ == "__main__":
    import json
    payload = create_batch_payload(
        drug_name="Amoxicillin 500mg",
        quantity=200,
        expiry_date="2025-09",
        sender_id="HOSP_CHENNAI_001",
        receiver_id="PHC_VILLUPURAM_007",
        storage_type="AMBIENT"
    )
    print(json.dumps(payload, indent=2))