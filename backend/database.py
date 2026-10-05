# database.py
import json
import os
import threading
from pathlib import Path
from typing import Dict, List

from sqlalchemy import create_engine, text


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL.startswith("postgres://"):
	DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
	DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif not DATABASE_URL:
	DATABASE_URL = f"sqlite:///{PROJECT_DIR / 'backend' / 'medchain.sqlite3'}"

engine = create_engine(
	DATABASE_URL,
	pool_pre_ping=True,
	connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {},
)
_save_lock = threading.Lock()

# Surplus stock listed by hospitals/pharmacies
surplus_db: Dict[str, dict] = {}

# Requests made by rural clinics
requests_db: Dict[str, dict] = {}

# Created and signed batches
batches_db: Dict[str, dict] = {}

# Sensor logs received from ESP32 (keyed by batch_id)
sensor_logs_db: Dict[str, List[dict]] = {}

# Disposal state is persisted alongside inventory so it survives restarts too.
disposal_queue: Dict[str, dict] = {}
disposal_certificates: Dict[str, dict] = {}
runtime_state = {"active_batch_id": None}

_collections = {
	"surplus": surplus_db,
	"requests": requests_db,
	"batches": batches_db,
	"sensor_logs": sensor_logs_db,
	"disposal_queue": disposal_queue,
	"disposal_certificates": disposal_certificates,
	"runtime": runtime_state,
}


def _load_state():
	with engine.begin() as connection:
		connection.execute(text(
			"CREATE TABLE IF NOT EXISTS medchain_state "
			"(state_id INTEGER PRIMARY KEY, payload TEXT NOT NULL)"
		))
		row = connection.execute(text(
			"SELECT payload FROM medchain_state WHERE state_id = 1"
		)).first()

	if row is None:
		return

	state = json.loads(row[0])
	for name, collection in _collections.items():
		collection.update(state.get(name, {}))


def save_state():
	payload = json.dumps(_collections, separators=(",", ":"))
	with _save_lock, engine.begin() as connection:
		connection.execute(text("DELETE FROM medchain_state WHERE state_id = 1"))
		connection.execute(
			text("INSERT INTO medchain_state (state_id, payload) VALUES (1, :payload)"),
			{"payload": payload},
		)


_load_state()