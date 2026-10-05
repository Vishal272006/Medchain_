# signer.py
# Signs a batch payload with HMAC-SHA256
# The secret key lives on the backend — never sent in the QR

import hmac
import hashlib
import json
import os
import qrcode
from backend.schema import create_batch_payload


SECRET_KEY = os.getenv("MEDCHAIN_SIGNING_SECRET", "medchain-secret-change-in-production").encode()


def sign_payload(payload: dict) -> dict:
    """
    Attaches an HMAC-SHA256 signature to the payload.
    Signature covers all fields — any tampering invalidates it.
    """
    # Serialize deterministically (sorted keys) so signature is reproducible
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    
    signature = hmac.new(SECRET_KEY, payload_bytes, hashlib.sha256).hexdigest()
    
    signed = payload.copy()
    signed["signature"] = signature
    return signed


def generate_qr(signed_payload: dict, output_path: str = "batch_qr.png", qr_data: str = None):
    if qr_data is None:
        qr_data = json.dumps(signed_payload, sort_keys=True, separators=(",", ":"))

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_path)
    print(f"QR saved → {output_path}")
    return qr_data


# --- Test: create, sign, and generate QR for a sample batch ---
if __name__ == "__main__":
    payload = create_batch_payload(
        drug_name="Metformin 500mg",
        quantity=500,
        expiry_date="2025-11",
        sender_id="HOSP_CHENNAI_001",
        receiver_id="PHC_VILLUPURAM_007",
        storage_type="AMBIENT"
    )

    signed = sign_payload(payload)
    
    print("Signed payload:")
    print(json.dumps(signed, indent=2))
    
    generate_qr(signed, output_path="backend/batch_qr.png")