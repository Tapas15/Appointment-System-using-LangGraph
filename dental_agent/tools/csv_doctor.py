import re
import time

import pandas as pd
from langchain_core.tools import tool

from dental_agent.config.settings import CSV_PATH, DOCTOR_PASSWORDS
from dental_agent.utils import format_date_slot


def _load_df() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip()

    df["is_available"] = df["is_available"].astype(str).str.upper() == "TRUE"

    df["date_slot"] = pd.to_datetime(
        df["date_slot"],
        format="mixed",
        dayfirst=False,
    )

    df["doctor_name"] = df["doctor_name"].str.lower().str.strip()
    df["specialization"] = df["specialization"].str.lower().str.strip()

    df["patient_to_attend"] = (
        df["patient_to_attend"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )

    return df


def _save_df(df: pd.DataFrame) -> None:
    out = df.copy()

    out["date_slot"] = out["date_slot"].map(format_date_slot)

    out["is_available"] = out["is_available"].astype(bool).map({True: "TRUE", False: "FALSE"})

    out["patient_to_attend"] = (
        out["patient_to_attend"]
        .fillna("")
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
    )

    out.to_csv(CSV_PATH, index=False)


def _verify_doctor(doctor_name: str, password: str) -> tuple[bool, str]:
    doctor = doctor_name.lower().strip()

    if doctor not in DOCTOR_PASSWORDS:
        return False, "Doctor not found."

    if DOCTOR_PASSWORDS[doctor] != password:
        return False, "Invalid doctor password."

    return True, "Authenticated"



@tool
def doctor_login(doctor_name: str, password: str) -> dict:
    """
    Verify doctor credentials and start a doctor session.

    This tool does not modify the CSV. It only confirms that the provided
    doctor name and password are valid.
    """
    verified, message = _verify_doctor(doctor_name, password)

    if not verified:
        return {
            "success": False,
            "authenticated": False,
            "message": message,
        }

    return {
        "success": True,
        "authenticated": True,
        "doctor_name": doctor_name.lower().strip(),
        "doctor_session_started_at": time.time(),
        "last_doctor_activity_at": time.time(),
        "message": f"Logged in as {doctor_name.lower().strip()}.",
    }
def _slot_mask(df: pd.DataFrame, doctor_name: str, date_slot: str) -> tuple[pd.Series, str | None]:
    doctor = doctor_name.lower().strip()

    try:
        target_dt = pd.to_datetime(date_slot, format="mixed", dayfirst=False)
    except Exception:
        return pd.Series(False, index=df.index), f"Invalid date_slot format: {date_slot}"

    mask = (
        (df["doctor_name"] == doctor)
        & (df["date_slot"] == target_dt)
    )

    return mask, None


def _parse_date_value(date_value: str) -> pd.Timestamp:
    text = str(date_value).strip()
    if not text:
        raise ValueError(f"Invalid date format: {date_value}")

    text = re.sub(r"\b(\d+)\s+(st|nd|rd|th)\b", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d+)(st|nd|rd|th)\b", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+the\s+", " ", text, flags=re.IGNORECASE)
    text = text.replace(",", " ")
    text = re.sub(r"\s+", " ", text).strip()

    current_year = pd.Timestamp.today().year
    candidates = [
        text,
        f"{text} {current_year}",
        f"{current_year} {text}",
    ]

    for candidate in candidates:
        try:
            return pd.to_datetime(candidate, format="mixed", dayfirst=False)
        except Exception:
            continue

    raise ValueError(f"Invalid date format: {date_value}")


def _parse_time(time_value: str) -> pd.Timestamp:
    text = str(time_value).strip().lower().replace(".", "")
    text = re.sub(r"\s+", " ", text)

    if re.fullmatch(r"\d{1,2}", text):
        text = f"{text}:00"

    try:
        return pd.to_datetime(f"2000-01-01 {text}", format="mixed")
    except Exception as exc:
        raise ValueError(f"Invalid time format: {time_value}") from exc


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    unique_values = []

    for value in values:
        text = str(value).strip()
        if not text:
            continue

        key = text.lower()
        if key not in seen:
            seen.add(key)
            unique_values.append(text)

    return unique_values


def _build_bulk_slots(
    dates: list[str],
    start_time: str,
    end_time: str,
    interval_minutes: int,
) -> tuple[list[str], str | None]:
    if interval_minutes <= 0:
        return [], "interval_minutes must be greater than 0."

    if interval_minutes > 1440:
        return [], "interval_minutes must be 1440 or less."

    try:
        start_dt = _parse_time(start_time)
        end_dt = _parse_time(end_time)
    except ValueError as exc:
        return [], str(exc)

    if end_dt < start_dt:
        return [], "end_time must be the same as or later than start_time."

    unique_dates = _unique_preserve_order(dates)
    if not unique_dates:
        return [], "At least one date is required."

    slots = []

    try:
        for date_value in unique_dates:
            date_dt = _parse_date_value(date_value).normalize()
            day_start = date_dt + (start_dt - pd.Timestamp("2000-01-01"))
            day_end = date_dt + (end_dt - pd.Timestamp("2000-01-01"))

            for slot_dt in pd.date_range(
                start=day_start,
                end=day_end,
                freq=f"{interval_minutes}min",
            ):
                slots.append(format_date_slot(slot_dt))
    except Exception as exc:
        return [], f"Invalid date format: {exc}"

    return _unique_preserve_order(slots), None


@tool
def doctor_add_availability(
    doctor_name: str,
    password: str,
    date_slot: str,
    specialization: str = "",
) -> dict:
    """
    Doctor adds or restores availability for their own slot.

    Existing columns only:
    - is_available = TRUE
    - patient_to_attend = empty
    """
    verified, message = _verify_doctor(doctor_name, password)

    if not verified:
        return {
            "success": False,
            "message": message,
        }

    df = _load_df()
    mask, error = _slot_mask(df, doctor_name, date_slot)

    if error:
        return {
            "success": False,
            "message": error,
        }

    doctor = doctor_name.lower().strip()

    if df[mask].empty:
        if not specialization:
            return {
                "success": False,
                "message": "Specialization is required when creating a new slot.",
            }

        try:
            target_dt = pd.to_datetime(date_slot, format="mixed", dayfirst=False)
        except Exception:
            return {
                "success": False,
                "message": f"Invalid date_slot format: {date_slot}",
            }

        new_row = {
            "date_slot": format_date_slot(target_dt),
            "specialization": specialization.lower().strip(),
            "doctor_name": doctor,
            "is_available": "TRUE",
            "patient_to_attend": "",
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    else:
        row = df.loc[mask].iloc[0]

        if str(row["patient_to_attend"]).strip() != "":
            return {
                "success": False,
                "message": "Cannot change availability for a slot that already has a patient booking.",
            }

        df.loc[mask, "is_available"] = True
        df.loc[mask, "patient_to_attend"] = ""

    _save_df(df)

    return {
        "success": True,
        "message": f"Availability added/restored for {doctor_name} at {date_slot}.",
    }


@tool
def doctor_add_availability_bulk(
    doctor_name: str,
    password: str,
    dates: list[str],
    start_time: str,
    end_time: str,
    specialization: str = "",
    interval_minutes: int = 60,
) -> dict:
    """
    Doctor adds or restores availability for multiple dates and times.

    Use this when the doctor wants to add availability across a date range or
    multiple dates, for example:
    - dates: ["6/9/2026", "6/10/2026", "6/11/2026"]
    - start_time: "9am"
    - end_time: "4pm"
    - interval_minutes: 60

    This creates hourly slots from 9am through 4pm on each provided date.
    """
    verified, message = _verify_doctor(doctor_name, password)

    if not verified:
        return {
            "success": False,
            "message": message,
        }

    slots, error = _build_bulk_slots(
        dates=dates,
        start_time=start_time,
        end_time=end_time,
        interval_minutes=interval_minutes,
    )

    if error:
        return {
            "success": False,
            "message": error,
        }

    df = _load_df()
    doctor = doctor_name.lower().strip()

    created_slots = []
    restored_slots = []
    skipped_slots = []

    for slot in slots:
        mask, slot_error = _slot_mask(df, doctor, slot)

        if slot_error:
            skipped_slots.append(f"{slot}: {slot_error}")
            continue

        rows = df[mask]

        if rows.empty:
            if not specialization:
                skipped_slots.append(
                    f"{slot}: specialization is required when creating a new slot."
                )
                continue

            try:
                target_dt = pd.to_datetime(slot, format="mixed", dayfirst=False)
            except Exception as exc:
                skipped_slots.append(f"{slot}: invalid date_slot format ({exc})")
                continue

            new_row = {
                "date_slot": format_date_slot(target_dt),
                "specialization": specialization.lower().strip(),
                "doctor_name": doctor,
                "is_available": "TRUE",
                "patient_to_attend": "",
            }

            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            created_slots.append(slot)
            continue

        row = rows.iloc[0]

        if str(row["patient_to_attend"]).strip() != "":
            skipped_slots.append(
                f"{slot}: already has a patient booking."
            )
            continue

        df.loc[mask, "is_available"] = True
        df.loc[mask, "patient_to_attend"] = ""
        restored_slots.append(slot)

    if not created_slots and not restored_slots:
        return {
            "success": False,
            "message": "No availability slots were added or restored.",
            "skipped_slots": skipped_slots,
        }

    _save_df(df)

    changed_count = len(created_slots) + len(restored_slots)
    message = (
        f"Availability added/restored for {doctor_name} across {len(_unique_preserve_order(dates))} "
        f"date(s) from {start_time} to {end_time} every {interval_minutes} minute(s). "
        f"Changed {changed_count} slot(s)."
    )

    return {
        "success": True,
        "message": message,
        "total_requested_slots": len(slots),
        "created_slots": created_slots,
        "restored_slots": restored_slots,
        "skipped_slots": skipped_slots,
    }


@tool
def doctor_block_time_slot(
    doctor_name: str,
    password: str,
    date_slot: str,
) -> dict:
    """
    Doctor blocks their own available time slot.

    Existing columns only:
    - is_available = FALSE
    - patient_to_attend = empty
    """
    verified, message = _verify_doctor(doctor_name, password)

    if not verified:
        return {
            "success": False,
            "message": message,
        }

    df = _load_df()
    mask, error = _slot_mask(df, doctor_name, date_slot)

    if error:
        return {
            "success": False,
            "message": error,
        }

    rows = df[mask]

    if rows.empty:
        return {
            "success": False,
            "message": f"No slot found for {doctor_name} at {date_slot}.",
        }

    row = rows.iloc[0]

    if not row["is_available"]:
        return {
            "success": False,
            "message": "Slot is already unavailable.",
        }

    df.loc[mask, "is_available"] = False
    df.loc[mask, "patient_to_attend"] = ""

    _save_df(df)

    return {
        "success": True,
        "message": f"Slot blocked for {doctor_name} at {date_slot}.",
    }


@tool
def doctor_update_schedule(
    doctor_name: str,
    password: str,
    date_slot: str,
    is_available: bool,
) -> dict:
    """
    Doctor updates their own schedule.

    Existing columns only:
    - if is_available=True:
        is_available = TRUE
        patient_to_attend = empty

    - if is_available=False:
        is_available = FALSE
        patient_to_attend = empty
    """
    verified, message = _verify_doctor(doctor_name, password)

    if not verified:
        return {
            "success": False,
            "message": message,
        }

    df = _load_df()
    mask, error = _slot_mask(df, doctor_name, date_slot)

    if error:
        return {
            "success": False,
            "message": error,
        }

    rows = df[mask]

    if rows.empty:
        return {
            "success": False,
            "message": f"No slot found for {doctor_name} at {date_slot}.",
        }

    row = rows.iloc[0]

    if str(row["patient_to_attend"]).strip() != "":
        return {
            "success": False,
            "message": "Cannot update a slot that already has a patient booking.",
        }

    df.loc[mask, "is_available"] = bool(is_available)
    df.loc[mask, "patient_to_attend"] = "" 

    _save_df(df)

    status = "available" if is_available else "blocked/unavailable"

    return {
        "success": True,
        "message": f"Schedule updated for {doctor_name} at {date_slot}. Slot is now {status}.",
    }

