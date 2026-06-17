from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from dental_agent.config.settings import CSV_PATH, DB_PATH
from dental_agent.utils import format_date_slot

SCHEMA = """
CREATE TABLE IF NOT EXISTS slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_slot TEXT NOT NULL,
    specialization TEXT NOT NULL,
    doctor_name TEXT NOT NULL,
    is_available INTEGER NOT NULL CHECK (is_available IN (0, 1)),
    patient_to_attend TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_slots_doctor_date
    ON slots (doctor_name, date_slot);

CREATE INDEX IF NOT EXISTS idx_slots_availability
    ON slots (is_available, date_slot);

CREATE INDEX IF NOT EXISTS idx_slots_patient
    ON slots (patient_to_attend);
"""

_DATE_FORMATS = (
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %I:%M %p",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
)


def _connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def ensure_database() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


def _normalize_text(value: Any) -> str:
    return str(value).strip().lower()


def _normalize_patient(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"none", "nan"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().upper() in {"TRUE", "1", "YES", "Y"}


def _parse_datetime(value: Any) -> datetime:
    text = str(value).strip()
    if not text:
        raise ValueError("date_slot cannot be empty")

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    raise ValueError(f"Invalid date_slot format: {value}")


def _store_slot(value: Any) -> str:
    return _parse_datetime(value).strftime("%Y-%m-%d %H:%M")


def _display_slot(value: str) -> str:
    return format_date_slot(value)


def _iter_csv_rows() -> list[tuple[str, str, str, int, str]]:
    csv_path = Path(CSV_PATH)
    if not csv_path.exists():
        return []

    rows: list[tuple[str, str, str, int, str]] = []
    with csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for raw_row in reader:
            try:
                slot = _store_slot(raw_row.get("date_slot", ""))
            except Exception:
                continue

            rows.append(
                (
                    slot,
                    _normalize_text(raw_row.get("specialization", "")),
                    _normalize_text(raw_row.get("doctor_name", "")),
                    int(_normalize_bool(raw_row.get("is_available", False))),
                    _normalize_patient(raw_row.get("patient_to_attend", "")),
                )
            )
    return rows


def migrate_from_csv(force: bool = False) -> int:
    ensure_database()

    with _connect() as conn:
        existing_count = conn.execute("SELECT COUNT(*) FROM slots").fetchone()[0]
        if existing_count and not force:
            return 0

        if force:
            conn.execute("DELETE FROM slots")

        rows = _iter_csv_rows()
        if not rows:
            return 0

        conn.executemany(
            """
            INSERT OR IGNORE INTO slots (
                date_slot,
                specialization,
                doctor_name,
                is_available,
                patient_to_attend
            ) VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        return conn.total_changes


def _ready() -> None:
    ensure_database()
    migrate_from_csv()


def _find_slot(conn: sqlite3.Connection, doctor_name: str, date_slot: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT *
        FROM slots
        WHERE doctor_name = ? AND date_slot = ?
        """,
        (_normalize_text(doctor_name), date_slot),
    ).fetchone()


def get_available_slots(
    specialization: str = "",
    doctor_name: str = "",
    date_filter: str = "",
) -> list[dict[str, Any]]:
    _ready()

    clauses = ["is_available = 1"]
    params: list[Any] = []

    if specialization:
        clauses.append("specialization = ?")
        params.append(_normalize_text(specialization))

    if doctor_name:
        clauses.append("doctor_name = ?")
        params.append(_normalize_text(doctor_name))

    if date_filter:
        try:
            target_date = _parse_datetime(date_filter).date()
        except Exception:
            return []
        clauses.append("date_slot LIKE ?")
        params.append(f"{target_date.isoformat()} %")

    query = f"""
        SELECT date_slot, specialization, doctor_name
        FROM slots
        WHERE {' AND '.join(clauses)}
        ORDER BY date_slot ASC, doctor_name ASC
        LIMIT 20
    """

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        {
            "date_slot": _display_slot(row["date_slot"]),
            "specialization": row["specialization"],
            "doctor_name": row["doctor_name"],
        }
        for row in rows
    ]


def get_patient_appointments(patient_id: str) -> list[dict[str, Any]]:
    _ready()

    pid = _normalize_patient(patient_id)
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT date_slot, specialization, doctor_name, patient_to_attend
            FROM slots
            WHERE patient_to_attend = ? AND is_available = 0
            ORDER BY date_slot ASC
            """,
            (pid,),
        ).fetchall()

    return [
        {
            "date_slot": _display_slot(row["date_slot"]),
            "specialization": row["specialization"],
            "doctor_name": row["doctor_name"],
            "patient_to_attend": row["patient_to_attend"],
        }
        for row in rows
    ]


def check_slot_availability(doctor_name: str, date_slot: str) -> dict[str, Any]:
    _ready()

    try:
        slot = _store_slot(date_slot)
    except Exception:
        return {"found": False, "is_available": False, "patient_to_attend": ""}

    with _connect() as conn:
        row = _find_slot(conn, doctor_name, slot)

    if row is None:
        return {"found": False, "is_available": False, "patient_to_attend": ""}

    return {
        "found": True,
        "is_available": bool(row["is_available"]),
        "patient_to_attend": row["patient_to_attend"],
    }


def list_doctors_by_specialization(specialization: str) -> list[str]:
    _ready()

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT doctor_name
            FROM slots
            WHERE specialization = ?
            ORDER BY doctor_name ASC
            """,
            (_normalize_text(specialization),),
        ).fetchall()

    return [row["doctor_name"] for row in rows]


def list_all_specializations_and_doctors() -> list[dict[str, Any]]:
    _ready()

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT specialization, GROUP_CONCAT(doctor_name, ', ') AS doctors
            FROM (
                SELECT DISTINCT specialization, doctor_name
                FROM slots
                ORDER BY specialization ASC, doctor_name ASC
            )
            GROUP BY specialization
            ORDER BY specialization ASC
            """
        ).fetchall()

    return [
        {
            "specialization": row["specialization"],
            "doctors": [
                doctor.strip()
                for doctor in (row["doctors"] or "").split(",")
                if doctor.strip()
            ],
        }
        for row in rows
    ]


def get_available_doctors_by_date(date_filter: str) -> list[dict[str, Any]]:
    _ready()

    try:
        target_date = _parse_datetime(date_filter).date()
    except Exception:
        return []

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT doctor_name, specialization, COUNT(*) AS available_count
            FROM slots
            WHERE is_available = 1 AND date_slot LIKE ?
            GROUP BY doctor_name, specialization
            ORDER BY doctor_name ASC, specialization ASC
            """,
            (f"{target_date.isoformat()} %",),
        ).fetchall()

    return [
        {
            "doctor_name": row["doctor_name"],
            "specialization": row["specialization"],
            "available_count": int(row["available_count"]),
        }
        for row in rows
    ]


def book_appointment(patient_id: str, doctor_name: str, date_slot: str) -> dict[str, Any]:
    _ready()

    try:
        slot = _store_slot(date_slot)
    except Exception:
        return {"success": False, "message": f"Invalid date_slot format: {date_slot}"}

    doctor = _normalize_text(doctor_name)
    patient = _normalize_patient(patient_id)

    with _connect() as conn:
        row = _find_slot(conn, doctor, slot)
        if row is None:
            return {"success": False, "message": "Slot not found for this doctor."}
        if not row["is_available"]:
            return {"success": False, "message": "Slot is already booked."}

        conn.execute(
            """
            UPDATE slots
            SET is_available = 0,
                patient_to_attend = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (patient, row["id"]),
        )

    return {
        "success": True,
        "message": f"Appointment booked for patient {patient} with {doctor_name} at {date_slot}.",
    }


def cancel_appointment(patient_id: str, date_slot: str) -> dict[str, Any]:
    _ready()

    try:
        slot = _store_slot(date_slot)
    except Exception:
        return {"success": False, "message": f"Invalid date_slot format: {date_slot}"}

    patient = _normalize_patient(patient_id)

    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE slots
            SET is_available = 1,
                patient_to_attend = '',
                updated_at = CURRENT_TIMESTAMP
            WHERE patient_to_attend = ?
              AND date_slot = ?
              AND is_available = 0
            """,
            (patient, slot),
        )
        updated = cursor.rowcount

    if updated == 0:
        return {
            "success": False,
            "message": f"No booked appointment found for patient {patient_id} at {date_slot}.",
        }

    return {
        "success": True,
        "message": f"Appointment at {date_slot} for patient {patient_id} has been cancelled.",
    }


def reschedule_appointment(
    patient_id: str,
    current_date_slot: str,
    new_date_slot: str,
    doctor_name: str,
) -> dict[str, Any]:
    _ready()

    try:
        current_slot = _store_slot(current_date_slot)
        new_slot = _store_slot(new_date_slot)
    except Exception as exc:
        return {"success": False, "message": f"Date parse error: {exc}"}

    patient = _normalize_patient(patient_id)
    doctor = _normalize_text(doctor_name)

    with _connect() as conn:
        old_row = _find_slot(conn, doctor, current_slot)
        if (
            old_row is None
            or old_row["patient_to_attend"] != patient
            or old_row["is_available"]
        ):
            return {
                "success": False,
                "message": f"No existing booking found for patient {patient} at {current_date_slot}.",
            }

        new_row = _find_slot(conn, doctor, new_slot)
        if new_row is None:
            return {"success": False, "message": f"Slot {new_date_slot} does not exist for {doctor_name}."}
        if not new_row["is_available"]:
            return {"success": False, "message": f"Slot {new_date_slot} is already taken."}

        conn.execute(
            """
            UPDATE slots
            SET is_available = 1,
                patient_to_attend = '',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (old_row["id"],),
        )
        conn.execute(
            """
            UPDATE slots
            SET is_available = 0,
                patient_to_attend = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (patient, new_row["id"]),
        )

    return {
        "success": True,
        "message": (
            f"Appointment for patient {patient} rescheduled from "
            f"{current_date_slot} to {new_date_slot} with {doctor_name}."
        ),
    }


def _verify_doctor(doctor_name: str, password: str) -> tuple[bool, str]:
    from dental_agent.config.settings import DOCTOR_PASSWORDS

    doctor = _normalize_text(doctor_name)
    if doctor not in DOCTOR_PASSWORDS:
        return False, "Doctor not found."
    if DOCTOR_PASSWORDS[doctor] != password:
        return False, "Invalid doctor password."
    return True, "Authenticated"


def doctor_add_availability(
    doctor_name: str,
    password: str,
    date_slot: str,
    specialization: str = "",
) -> dict[str, Any]:
    _ready()

    verified, message = _verify_doctor(doctor_name, password)
    if not verified:
        return {"success": False, "message": message}

    try:
        slot = _store_slot(date_slot)
    except Exception:
        return {"success": False, "message": f"Invalid date_slot format: {date_slot}"}

    doctor = _normalize_text(doctor_name)
    spec = _normalize_text(specialization)

    with _connect() as conn:
        row = _find_slot(conn, doctor, slot)
        if row is None:
            if not spec:
                return {
                    "success": False,
                    "message": "Specialization is required when creating a new slot.",
                }
            conn.execute(
                """
                INSERT INTO slots (
                    date_slot,
                    specialization,
                    doctor_name,
                    is_available,
                    patient_to_attend
                ) VALUES (?, ?, ?, 1, '')
                """,
                (slot, spec, doctor),
            )
        else:
            if _normalize_patient(row["patient_to_attend"]):
                return {
                    "success": False,
                    "message": "Cannot change availability for a slot that already has a patient booking.",
                }
            conn.execute(
                """
                UPDATE slots
                SET is_available = 1,
                    patient_to_attend = '',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (row["id"],),
            )

    return {
        "success": True,
        "message": f"Availability added/restored for {doctor_name} at {date_slot}.",
    }


def doctor_block_time_slot(
    doctor_name: str,
    password: str,
    date_slot: str,
) -> dict[str, Any]:
    _ready()

    verified, message = _verify_doctor(doctor_name, password)
    if not verified:
        return {"success": False, "message": message}

    try:
        slot = _store_slot(date_slot)
    except Exception:
        return {"success": False, "message": f"Invalid date_slot format: {date_slot}"}

    doctor = _normalize_text(doctor_name)
    with _connect() as conn:
        row = _find_slot(conn, doctor, slot)
        if row is None:
            return {"success": False, "message": f"No slot found for {doctor_name} at {date_slot}."}
        if not row["is_available"]:
            return {"success": False, "message": "Slot is already unavailable."}
        conn.execute(
            """
            UPDATE slots
            SET is_available = 0,
                patient_to_attend = '',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (row["id"],),
        )

    return {"success": True, "message": f"Slot blocked for {doctor_name} at {date_slot}."}


def doctor_update_schedule(
    doctor_name: str,
    password: str,
    date_slot: str,
    is_available: bool,
) -> dict[str, Any]:
    _ready()

    verified, message = _verify_doctor(doctor_name, password)
    if not verified:
        return {"success": False, "message": message}

    try:
        slot = _store_slot(date_slot)
    except Exception:
        return {"success": False, "message": f"Invalid date_slot format: {date_slot}"}

    doctor = _normalize_text(doctor_name)
    with _connect() as conn:
        row = _find_slot(conn, doctor, slot)
        if row is None:
            return {"success": False, "message": f"No slot found for {doctor_name} at {date_slot}."}
        if _normalize_patient(row["patient_to_attend"]):
            return {
                "success": False,
                "message": "Cannot update a slot that already has a patient booking.",
            }
        conn.execute(
            """
            UPDATE slots
            SET is_available = ?,
                patient_to_attend = '',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (int(bool(is_available)), row["id"]),
        )

    status = "available" if is_available else "blocked/unavailable"
    return {
        "success": True,
        "message": f"Schedule updated for {doctor_name} at {date_slot}. Slot is now {status}.",
    }
