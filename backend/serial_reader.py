# serial_reader.py
# Background thread that reads ESP32 sensor logs over USB serial

import serial
import json
import os
import threading
import time
from backend.database import sensor_logs_db

SERIAL_PORT = os.getenv("MEDCHAIN_SERIAL_PORT", "COM3").strip()
BAUD_RATE   = 115200
ACTIVE_BATCH_ID = None      # Set this when a batch is in transit


def start_serial_reader(port: str = SERIAL_PORT):
    thread = threading.Thread(
        target=_read_loop,
        args=(port,),
        daemon=True
    )
    thread.start()
    print(f"Serial reader started on {port}")


def _read_loop(port: str):
    global ACTIVE_BATCH_ID
    last_error = None
    while True:
        try:
            with serial.Serial(port, BAUD_RATE, timeout=1) as ser:
                time.sleep(2)
                last_error = None
                print(f"Connected to ESP32 on {port}")

                while True:
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue
                    try:
                        log_entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(log_entry, dict) or log_entry.get("status") not in {"OK", "BREACH"}:
                        continue

                    # Attach readings only while a batch is in transit.
                    if ACTIVE_BATCH_ID:
                        if ACTIVE_BATCH_ID not in sensor_logs_db:
                            sensor_logs_db[ACTIVE_BATCH_ID] = []
                        sensor_logs_db[ACTIVE_BATCH_ID].append(log_entry)
                        print(f"[LOG] Batch {ACTIVE_BATCH_ID} -> {log_entry['status']}")
        except serial.SerialException as e:
            if str(e) != last_error:
                print(f"Serial error: {e} — retrying {port} in 5 seconds")
            last_error = str(e)
            time.sleep(5)