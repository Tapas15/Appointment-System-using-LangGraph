import time

import pandas as pd
from langchain_core.tools import tool

from dental_agent.config.features import load_global_features
from dental_agent.config.settings import ADMIN_USERS, CSV_PATH
from dental_agent.utils import format_date_slot


ADMIN_FEATURE_DEFINITIONS = {
    "view_available_slots": "View available appointment slots",
    "view_slots_by_specialization": "View slots by specialization",
    "view_slots_by_doctor": "View slots by doctor",
    "view_slots_by_date": "View slots by date",
    "view_slots_by_date_range": "View slots by date range",
    "view_available_doctors_by_date": "View available doctors by date",
    "view_doctors_by_specialization": "View doctors by specialization",
    "view_availability_summary": "View total specialties, doctors, and slots summary",
    "check_slot_availability": "Check one specific doctor slot",
    "view_patient_appointments": "View patient appointments",
    "book_appointment": "Book appointment",
    "cancel_appointment": "Cancel appointment",
    "reschedule_appointment": "Reschedule appointment",
    "doctor_add_availability": "Add or restore doctor availability",
    "doctor_block_slot": "Block doctor time slot",
    "doctor_update_schedule": "Update doctor schedule availability",
    "admin_list_features": "List admin-controlled features",
    "admin_enable_feature": "Enable one admin-controlled feature",
    "admin_disable_feature": "Disable one admin-controlled feature",
}

ADMIN_FEATURE_NAMES = tuple(ADMIN_FEATURE_DEFINITIONS.keys())


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


def _verify_admin(admin_user_id: str, password: str) -> tuple[bool, str]:
    admin = admin_user_id.lower().strip()

    if admin not in ADMIN_USERS:
        return False, "Admin user not found."

    if ADMIN_USERS[admin] != password:
        return False, "Invalid admin password."

    return True, "Authenticated"


def _slot_mask(
    df: pd.DataFrame,
    doctor_name: str,
    date_slot: str,
) -> tuple[pd.Series, str | None]:
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


def _all_features_enabled() -> dict[str, bool]:
    return {feature_name: True for feature_name in ADMIN_FEATURE_NAMES}


@tool
def admin_login(admin_user_id: str, password: str) -> dict:
    """
    Verify admin credentials and start an admin session.
    """
    verified, message = _verify_admin(admin_user_id, password)

    if not verified:
        return {
            "success": False,
            "authenticated": False,
            "message": message,
        }

    admin = admin_user_id.lower().strip()
    now = time.time()

    return {
        "success": True,
        "authenticated": True,
        "admin_user_id": admin,
        "admin_session_started_at": now,
        "last_admin_activity_at": now,
        "admin_patient_features_enabled": True,
        "admin_doctor_features_enabled": True,
        "admin_enabled_features": _all_features_enabled(),
        "global_enabled_features": load_global_features(),
        "global_patient_features_enabled": True,
        "global_doctor_features_enabled": True,
        "message": f"Admin logged in as {admin}. All individual admin features are enabled by default.",
    }


@tool
def admin_enable_patient_features() -> dict:
    """
    Enable patient features for the current admin session.
    """
    return {
        "success": True,
        "admin_patient_features_enabled": True,
        "message": "Patient features enabled.",
    }


@tool
def admin_disable_patient_features() -> dict:
    """
    Disable patient features for the current admin session.
    """
    return {
        "success": True,
        "admin_patient_features_enabled": False,
        "message": "Patient features disabled.",
    }


@tool
def admin_enable_doctor_features() -> dict:
    """
    Enable doctor features for the current admin session.
    """
    return {
        "success": True,
        "admin_doctor_features_enabled": True,
        "message": "Doctor features enabled.",
    }


@tool
def admin_disable_doctor_features() -> dict:
    """
    Disable doctor features for the current admin session.
    """
    return {
        "success": True,
        "admin_doctor_features_enabled": False,
        "message": "Doctor features disabled.",
    }


@tool
def admin_enable_feature(feature_name: str) -> dict:
    """
    Enable one individual admin-controlled feature.
    """
    feature = feature_name.strip()

    if feature not in ADMIN_FEATURE_DEFINITIONS:
        return {
            "success": False,
            "message": f"Unknown feature: {feature}",
        }

    return {
        "success": True,
        "feature_name": feature,
        "enabled": True,
        "message": f"Feature '{feature}' enabled.",
    }


@tool
def admin_disable_feature(feature_name: str) -> dict:
    """
    Disable one individual admin-controlled feature.
    """
    feature = feature_name.strip()

    if feature not in ADMIN_FEATURE_DEFINITIONS:
        return {
            "success": False,
            "message": f"Unknown feature: {feature}",
        }

    return {
        "success": True,
        "feature_name": feature,
        "enabled": False,
        "message": f"Feature '{feature}' disabled.",
    }


@tool
def admin_list_features() -> list:
    """
    List all admin-controlled features.
    """
    return [
        {
            "feature_name": feature_name,
            "description": description,
        }
        for feature_name, description in ADMIN_FEATURE_DEFINITIONS.items()
    ]


@tool
def admin_add_availability(
    doctor_name: str,
    date_slot: str,
    specialization: str = "",
) -> dict:
    """
    Admin adds or restores availability for a doctor's slot without doctor password.
    """
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
def admin_block_time_slot(
    doctor_name: str,
    date_slot: str,
) -> dict:
    """
    Admin blocks a doctor's available time slot without doctor password.
    """
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
def admin_update_schedule(
    doctor_name: str,
    date_slot: str,
    is_available: bool,
) -> dict:
    """
    Admin updates a doctor's schedule availability without doctor password.
    """
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
