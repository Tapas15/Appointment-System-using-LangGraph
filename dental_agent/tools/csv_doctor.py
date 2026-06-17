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

    out["is_available"] = out["is_available"].map({
        True: "TRUE",
        False: "FALSE",
    })

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

