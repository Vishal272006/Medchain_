# database.py
# Simple in-memory store — no SQL setup needed for prototype

from typing import Dict, List

# Surplus stock listed by hospitals/pharmacies
surplus_db: Dict[str, dict] = {}

# Requests made by rural clinics
requests_db: Dict[str, dict] = {}

# Created and signed batches
batches_db: Dict[str, dict] = {}

# Sensor logs received from ESP32 (keyed by batch_id)
sensor_logs_db: Dict[str, List[dict]] = {}