"""Forward ESP32 readings from a local USB serial port to the deployed API."""

import json
import os
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

import serial

from backend.serial_reader import BAUD_RATE, parse_sensor_reading


def api_request(api_url: str, token: str, path: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"X-Sensor-Token": token}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(f"{api_url}{path}", data=body, headers=headers)
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def run_bridge(api_url: str, token: str, port: str):
    while True:
        try:
            with serial.Serial(port, BAUD_RATE, timeout=1) as device:
                print(f"ESP32 bridge connected on {port}; forwarding to {api_url}")
                while True:
                    line = device.readline().decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue
                    reading = parse_sensor_reading(line)
                    if reading is None:
                        continue

                    active = api_request(api_url, token, "/sensor/active-batch")
                    batch_id = active.get("batch_id")
                    if not batch_id:
                        continue
                    api_request(api_url, token, "/sensor/log", {"batch_id": batch_id, "reading": reading})
                    print(f"Forwarded {reading['status']} reading for batch {batch_id}")
        except (serial.SerialException, URLError, OSError, json.JSONDecodeError) as error:
            print(f"Bridge connection error: {error}; retrying in 5 seconds")
            time.sleep(5)


if __name__ == "__main__":
    api_url = os.getenv("MEDCHAIN_API_URL", "").rstrip("/")
    sensor_token = os.getenv("MEDCHAIN_SENSOR_TOKEN", "")
    serial_port = os.getenv("MEDCHAIN_SERIAL_PORT", "COM3").strip()
    if not api_url or not sensor_token:
        raise SystemExit("Set MEDCHAIN_API_URL and MEDCHAIN_SENSOR_TOKEN before starting the bridge")
    if not serial_port:
        raise SystemExit("MEDCHAIN_SERIAL_PORT must name the ESP32 serial port")
    run_bridge(api_url, sensor_token, serial_port)
