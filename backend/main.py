# main.py — MedChain v2.0 Full Lifecycle

import uuid, time, json, os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

from backend.schema import create_batch_payload
from backend.signer import sign_payload, generate_qr
from backend.verifier import verify_payload
from backend.database import surplus_db, requests_db, batches_db, sensor_logs_db
import backend.serial_reader as serial_reader
import backend.disposal as disposal_module
from backend.disposal import disposal_queue, disposal_certificates, INCINERATORS, schedule_pickup, mark_disposed, months_to_expiry, nearest_incinerator
from backend.cert_generator import generate_disposal_certificate

app = FastAPI(title="MedChain API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
PROJECT_DIR = Path(__file__).resolve().parent.parent

class SurplusListing(BaseModel):
    sender_id: str; drug_name: str; quantity: int
    expiry_date: str; storage_type: str; location_pincode: str

class ClinicRequest(BaseModel):
    receiver_id: str; drug_name: str
    quantity_needed: int; location_pincode: str

class BatchCreate(BaseModel):
    surplus_id: str; request_id: str

class VerifyRequest(BaseModel):
    qr_data: str

class PickupRequest(BaseModel):
    surplus_id: str

class DisposedRequest(BaseModel):
    surplus_id: str

@app.get("/")
def root():
    return FileResponse(PROJECT_DIR / "dashboard" / "index.html")

@app.get("/health")
def health():
    return {"status": "MedChain API running", "version": "2.0"}

@app.post("/surplus/list")
def list_surplus(data: SurplusListing):
    sid    = str(uuid.uuid4())[:8].upper()
    months = months_to_expiry(data.expiry_date)
    surplus_db[sid] = {**data.dict(), "surplus_id": sid, "listed_at": int(time.time()),
                       "matched": False, "disposal_status": "DISPOSAL_PENDING" if months <= 1 else None}
    return {"surplus_id": sid, "message": "Surplus listed", "months_to_expiry": months}

@app.get("/surplus/all")
def get_all_surplus():
    return list(surplus_db.values())

@app.post("/clinic/request")
def clinic_request(data: ClinicRequest):
    rid = str(uuid.uuid4())[:8].upper()
    requests_db[rid] = {**data.dict(), "request_id": rid, "requested_at": int(time.time()), "fulfilled": False}
    return {"request_id": rid, "message": "Request submitted"}

@app.get("/clinic/requests")
def get_all_requests():
    return list(requests_db.values())

@app.post("/batch/create")
def create_batch(data: BatchCreate):
    surplus = surplus_db.get(data.surplus_id)
    request = requests_db.get(data.request_id)
    if not surplus: raise HTTPException(404, "Surplus not found")
    if not request: raise HTTPException(404, "Request not found")
    if surplus["matched"]: raise HTTPException(400, "Already matched")
    payload  = create_batch_payload(drug_name=surplus["drug_name"], quantity=min(surplus["quantity"], request["quantity_needed"]),
                                    expiry_date=surplus["expiry_date"], sender_id=surplus["sender_id"],
                                    receiver_id=request["receiver_id"], storage_type=surplus["storage_type"])
    signed   = sign_payload(payload)
    batch_id = signed["batch_id"]
    batches_db[batch_id] = signed
    surplus_db[data.surplus_id]["matched"]    = True
    requests_db[data.request_id]["fulfilled"] = True
    if data.surplus_id in disposal_queue:
        del disposal_queue[data.surplus_id]
        surplus_db[data.surplus_id]["disposal_status"] = None
    qr_path = PROJECT_DIR / "backend" / f"qr_{batch_id}.png"
    generate_qr(signed, output_path=str(qr_path))
    serial_reader.ACTIVE_BATCH_ID = batch_id
    return {
        "batch_id": batch_id,
        "signed_payload": signed,
        "qr_url": f"/batch/{batch_id}/qr",
        "qr_saved_at": str(qr_path.relative_to(PROJECT_DIR))
    }

@app.get("/batch/{batch_id}/qr")
def get_batch_qr(batch_id: str):
    if batch_id not in batches_db:
        raise HTTPException(404, "Batch not found")
    qr_path = PROJECT_DIR / "backend" / f"qr_{batch_id}.png"
    if not qr_path.exists():
        generate_qr(batches_db[batch_id], output_path=str(qr_path))
    return FileResponse(qr_path, media_type="image/png", filename=f"MedChain_{batch_id}.png")

@app.get("/batch/{batch_id}/sensor-log")
def get_sensor_log(batch_id: str):
    logs = sensor_logs_db.get(batch_id, [])
    breach = sum(1 for l in logs if l.get("status") == "BREACH")
    return {"batch_id": batch_id, "total_readings": len(logs), "breach_count": breach, "logs": logs}

@app.post("/verify")
def verify_qr(data: VerifyRequest):
    try: scanned = json.loads(data.qr_data)
    except: raise HTTPException(400, "Invalid QR data")
    result = verify_payload(scanned)
    batch_id = scanned.get("batch_id")
    if result.get("signature_valid") and batch_id in batches_db:
        logs = sensor_logs_db.get(batch_id, [])
        breach = sum(1 for l in logs if l.get("status") == "BREACH")
        result["sensor_summary"] = {
            "total_readings": len(logs),
            "breach_count": breach,
            "transit_clean": breach == 0,
            "readings": logs[-20:]
        }
    return result

@app.get("/disposal/queue")
def get_disposal_queue():
    return list(disposal_queue.values())

@app.get("/disposal/incinerators")
def get_incinerators():
    return INCINERATORS

@app.post("/disposal/schedule-pickup")
def schedule_disposal(data: PickupRequest):
    result = schedule_pickup(data.surplus_id)
    if "error" in result: raise HTTPException(400, result["error"])
    try:
        generate_disposal_certificate(result, f"backend/certificates/{result['certificate_id']}.pdf")
    except Exception as e:
        print(f"PDF warning: {e}")
    return result

@app.post("/disposal/mark-disposed")
def confirm_disposal(data: DisposedRequest):
    result = mark_disposed(data.surplus_id)
    if "error" in result: raise HTTPException(400, result["error"])
    return result

@app.get("/disposal/certificates")
def get_certificates():
    return list(disposal_certificates.values())

@app.get("/disposal/certificate/{cert_id}")
def get_certificate(cert_id: str):
    cert = disposal_certificates.get(cert_id)
    if not cert: raise HTTPException(404, "Certificate not found")
    return cert

@app.get("/disposal/certificate/{cert_id}/download")
def download_certificate(cert_id: str):
    cert = disposal_certificates.get(cert_id)
    if not cert: raise HTTPException(404, "Certificate not found")
    pdf_path = PROJECT_DIR / "backend" / "certificates" / f"{cert_id}.pdf"
    if not os.path.exists(pdf_path):
        generate_disposal_certificate(cert, str(pdf_path))
    return FileResponse(path=str(pdf_path), media_type="application/pdf",
                        filename=f"MedChain_Disposal_{cert_id}.pdf")

@app.post("/disposal/run-watchdog")
def trigger_watchdog():
    flagged = 0
    now_ts  = int(time.time())
    for surplus_id, surplus in list(surplus_db.items()):
        if surplus.get("matched") or surplus_id in disposal_queue: continue
        months = months_to_expiry(surplus.get("expiry_date",""))
        if months <= 1:
            facility = nearest_incinerator(surplus.get("location_pincode",""))
            disposal_queue[surplus_id] = {
                "surplus_id": surplus_id, "drug_name": surplus.get("drug_name",""),
                "quantity": surplus.get("quantity",0), "expiry_date": surplus.get("expiry_date",""),
                "sender_id": surplus.get("sender_id",""),
                "status": "EXPIRED" if months < 0 else "DISPOSAL_PENDING",
                "flagged_at": now_ts, "months_left": months, "facility": facility,
                "pickup_scheduled": False, "certificate_id": None
            }
            surplus_db[surplus_id]["disposal_status"] = "DISPOSAL_PENDING"
            flagged += 1
    return {"flagged": flagged, "message": f"{flagged} batch(es) flagged"}

@app.get("/network/summary")
def network_summary():
    return {
        "total_surplus":    len(surplus_db),
        "available":        len([s for s in surplus_db.values() if not s.get("matched")]),
        "matched":          len([s for s in surplus_db.values() if s.get("matched")]),
        "total_requests":   len(requests_db),
        "pending_requests": len([r for r in requests_db.values() if not r.get("fulfilled")]),
        "disposal_pending": len([d for d in disposal_queue.values() if d["status"] in ["DISPOSAL_PENDING","EXPIRED"]]),
        "certificates":     len(disposal_certificates)
    }

app.mount("/pwa", StaticFiles(directory=PROJECT_DIR / "pwa", html=True), name="pwa")
app.mount("/", StaticFiles(directory=PROJECT_DIR / "dashboard", html=True), name="dashboard")

@app.on_event("startup")
def startup():
    os.makedirs(PROJECT_DIR / "backend" / "certificates", exist_ok=True)
    try:
        if serial_reader.SERIAL_PORT:
            serial_reader.start_serial_reader(port=serial_reader.SERIAL_PORT)
        else:
            print("Serial reader disabled; set MEDCHAIN_SERIAL_PORT to enable it")
    except Exception as e: print(f"Serial reader skipped: {e}")
    disposal_module.start_watchdog()
    print("MedChain v2.0 online")