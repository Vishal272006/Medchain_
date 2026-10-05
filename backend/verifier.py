# verifier.py
# Verifies a scanned QR payload — runs on backend OR offline in PWA

import hmac
import hashlib
import json
import os
import time


SECRET_KEY = os.getenv("MEDCHAIN_SIGNING_SECRET", "medchain-secret-change-in-production").encode()


def verify_payload(signed_payload: dict) -> dict:
    """
    Returns a verification result dict with:
    - signature_valid: bool
    - expired: bool  
    - days_to_expiry: int
    - verdict: "ACCEPT" | "FLAG" | "REJECT"
    - reason: str
    """
    # 1. Extract and remove signature before re-hashing
    received_sig = signed_payload.get("signature", "")
    payload_without_sig = {k: v for k, v in signed_payload.items() if k != "signature"}
    
    # 2. Recompute expected signature
    payload_bytes = json.dumps(payload_without_sig, sort_keys=True).encode("utf-8")
    expected_sig = hmac.new(SECRET_KEY, payload_bytes, hashlib.sha256).hexdigest()
    
    # 3. Constant-time comparison (prevents timing attacks)
    sig_valid = hmac.compare_digest(received_sig, expected_sig)
    
    if not sig_valid:
        return {
            "signature_valid": False,
            "verdict": "REJECT",
            "reason": "Signature mismatch — payload tampered or QR forged"
        }
    
    # 4. Check expiry
    expiry_str = signed_payload.get("expiry_date", "")  # "YYYY-MM"
    try:
        exp_year, exp_month = map(int, expiry_str.split("-"))
        now = time.gmtime()
        months_left = (exp_year - now.tm_year) * 12 + (exp_month - now.tm_mon)
    except:
        months_left = -1

    if months_left < 0:
        return {
            "signature_valid": True,
            "verdict": "REJECT",
            "reason": f"Medicine expired — {expiry_str}"
        }
    
    if months_left < 1:
        verdict = "FLAG"
        reason = f"Expires this month ({expiry_str}) — use immediately"
    else:
        verdict = "ACCEPT"
        reason = f"Valid — {months_left} month(s) to expiry"

    return {
        "signature_valid": True,
        "batch_id": signed_payload.get("batch_id"),
        "drug_name": signed_payload.get("drug_name"),
        "quantity": signed_payload.get("quantity"),
        "sender": signed_payload.get("sender_id"),
        "receiver": signed_payload.get("receiver_id"),
        "verdict": verdict,
        "reason": reason,
        "days_to_expiry_approx": months_left * 30
    }


# --- Test ---
if __name__ == "__main__":
    # Simulate scanning the QR we generated in signer.py
    with open("backend/batch_qr.png", "rb"):
        pass  # QR exists, good

    # Manually load the signed payload to simulate a scan
    from backend.signer import sign_payload
    from backend.schema import create_batch_payload

    payload = create_batch_payload(
        drug_name="Metformin 500mg",
        quantity=500,
        expiry_date="2025-11",
        sender_id="HOSP_CHENNAI_001",
        receiver_id="PHC_VILLUPURAM_007",
        storage_type="AMBIENT"
    )
    signed = sign_payload(payload)

    result = verify_payload(signed)
    print("Verification result:")
    print(json.dumps(result, indent=2))

    # Test tamper detection
    signed["quantity"] = 9999  # tamper!
    tampered_result = verify_payload(signed)
    print("\nTampered payload result:")
    print(json.dumps(tampered_result, indent=2))