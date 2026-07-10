# serial_reader.py
# Background thread that reads ESP32 sensor logs over USB serial

import serial
import json
import threading
import time
from backend.database import sensor_logs_db

SERIAL_PORT = "COM9"        # Windows: COM3/COM4 | Linux/Mac: /dev/ttyUSB0
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
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        time.sleep(2)
        print(f"Connected to ESP32 on {port}")

        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            try:
                log_entry = json.loads(line)

                # Attach to active batch if one is in transit
                if ACTIVE_BATCH_ID:
                    if ACTIVE_BATCH_ID not in sensor_logs_db:
                        sensor_logs_db[ACTIVE_BATCH_ID] = []
                    sensor_logs_db[ACTIVE_BATCH_ID].append(log_entry)
                    print(f"[LOG] Batch {ACTIVE_BATCH_ID} → {log_entry['status']}")

            except json.JSONDecodeError:
                pass    # skip non-JSON lines (boot messages etc.)

    except serial.SerialException as e:
        print(f"Serial error: {e} — running without ESP32")