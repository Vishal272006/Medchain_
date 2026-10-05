# MedChain Local Setup

## Start the website and API

Use Python 3.11 and run these commands in PowerShell from the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install fastapi uvicorn "qrcode[pil]" pyserial reportlab
$env:MEDCHAIN_SERIAL_PORT = "COM3"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Keep that terminal running. Open the website at <http://127.0.0.1:8000/>. The dashboard, API, and verifier are served by the same backend. API documentation is at <http://127.0.0.1:8000/docs>; the QR scanner is at <http://127.0.0.1:8000/pwa/>.

## Deploy to Render

Connect this GitHub repository in Render and create a Blueprint from `render.yaml`. It builds with the Linux runtime dependencies, serves the site and API over HTTPS, and generates separate signing and sensor-relay secrets. Keep both values private.

The Render service cannot access the PC's COM3 port. After Render creates the service, copy its `MEDCHAIN_SENSOR_TOKEN` value privately and run this bridge on the PC connected to the ESP32. Replace the URL with the service's actual `https://<name>.onrender.com` address:

```powershell
$env:MEDCHAIN_API_URL = "https://<name>.onrender.com"
$env:MEDCHAIN_SENSOR_TOKEN = "<copy privately from Render environment settings>"
$env:MEDCHAIN_SERIAL_PORT = "COM3"
.\.venv\Scripts\python.exe -m backend.serial_bridge
```

Close Arduino Serial Monitor/Plotter before starting the bridge; it needs exclusive access to COM3. The bridge polls the cloud for the active batch and forwards valid ESP32 readings through the token-protected sensor API. Create a batch in the deployed Admin page, then keep the bridge running while it is in transit.

This Render configuration is for demos: application data is in memory and resets when the service restarts or sleeps, and the other dashboard write APIs are not authenticated. Do not use it for real medicine or patient records without adding persistent storage and user authorization.

## Connect the ESP32

The backend defaults to `COM3` at `115200` baud. Close Arduino IDE's Serial Monitor and Serial Plotter before starting or connecting the backend; only one program can own the COM port. If the port is busy at startup, the backend retries every five seconds. To use another port, set `$env:MEDCHAIN_SERIAL_PORT` before starting Uvicorn.

Flash [the sensor sketch](esp32/sensor_node/sensor_node.ino) with the Adafruit DHT sensor library, Adafruit Unified Sensor, and ArduinoJson 6 installed. The sketch reads every ten seconds. Its current pins are DHT11 data on GPIO 4 and the light sensor digital output on GPIO 35; connect grounds together and keep ESP32 input signals at 3.3 V. The sketch is configured for ambient storage thresholds (15-30 C, humidity up to 75%). Adjust `TEMP_MIN` and `TEMP_MAX` in the sketch for cold-chain testing before flashing.

## Test the full flow

1. On the Hospital page, list medicine with an expiry date in the future.
2. On the Clinic page, submit a request for that medicine.
3. On the Admin page, select the surplus and request, then choose **Generate Batch + QR**. The backend makes this the active sensor batch.
4. Wait for at least one ESP32 reading. The batch accepts newline-delimited JSON records with `status` set to `OK` or `BREACH`.
5. Scan the displayed QR from the verifier page, or copy the signed JSON into its manual verification field. The result includes the batch's sensor count, breach count, and recent readings.

Only one shipment can be associated with the USB sensor at a time because the ESP32 stream does not contain a batch ID. Data is held in memory and is cleared when the backend restarts. Camera access from another device requires serving the site over HTTPS; use a trusted HTTPS development tunnel and open its `/pwa/` URL on that device. This prototype is not configured for handling real patient or medicine records on a public network.