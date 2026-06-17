import pandas as pd
from langchain_core.tools import tool
from dental_agent.config.settings import CSV_PATH, DATE_FORMAT
from dental_agent.utils import format_date_slot


def _load_df() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip()
    df["is_available"] = df["is_available"].astype(str).str.upper() == "TRUE"
    df["date_slot"] = pd.to_datetime(df["date_slot"], format="mixed", dayfirst=False)
    df["doctor_name"] = df["doctor_name"].str.lower().str.strip()
    df["specialization"] = df["specialization"].str.lower().str.strip()
    df["patient_to_attend"] = (
        df["patient_to_attend"]
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)  # 1000082.0 → 1000082
    )
    return df


@tool
def get_available_slots(
    specialization: str = "",
    doctor_name: str = "",
    date_filter: str = "",
) -> list:
    """
    Return available (is_available=TRUE) appointment slots.

    Args:
        specialization: Filter by specialization, e.g. 'orthodontist'. Leave empty to skip.
        doctor_name: Filter by doctor name (case-insensitive), e.g. 'emily johnson'. Leave empty to skip.
        date_filter: Filter by date string M/D/YYYY, e.g. '5/10/2026'. Leave empty to skip.

    Returns:
        List of dicts with keys: date_slot, specialization, doctor_name.
        Returns at most 20 rows to keep response concise.
    """
    df = _load_df()
    mask = df["is_available"]

    if specialization:
        mask = mask & (df["specialization"] == specialization.lower().strip())
    if doctor_name:
        mask = mask & (df["doctor_name"] == doctor_name.lower().strip())
    if date_filter:
        try:
            target_date = pd.to_datetime(date_filter).date()
            mask = mask & (df["date_slot"].dt.date == target_date)
        except Exception:
            pass

    result = df[mask][["date_slot", "specialization", "doctor_name"]].copy()
    result["date_slot"] = result["date_slot"].map(format_date_slot)
    return result.head(20).to_dict(orient="records")


@tool
def get_patient_appointments(patient_id: str) -> list:
    """
    Return all booked appointments for a given patient ID.

    Args:
        patient_id: Numeric patient ID string, e.g. '1000082'.

    Returns:
        List of dicts with keys: date_slot, specialization, doctor_name, patient_to_attend.
    """
    df = _load_df()
    mask = df["patient_to_attend"] == str(patient_id).strip()
    result = df[mask][["date_slot", "specialization", "doctor_name", "patient_to_attend"]].copy()
    result["date_slot"] = result["date_slot"].map(format_date_slot)
    return result.to_dict(orient="records")


@tool
def check_slot_availability(doctor_name: str, date_slot: str) -> dict:
    """
    Check if a specific doctor slot is available.

    Args:
        doctor_name: Doctor name, e.g. 'emily johnson'.
        date_slot: Slot string in M/D/YYYY H:MM format, e.g. '5/10/2026 9:00'.

    Returns:
        Dict with keys: found (bool), is_available (bool), patient_to_attend (str).
    """
    df = _load_df()
    try:
        target_dt = pd.to_datetime(date_slot, format="mixed", dayfirst=False)
    except Exception:
        return {"found": False, "is_available": False, "patient_to_attend": ""}

    mask = (df["doctor_name"] == doctor_name.lower().strip()) & (df["date_slot"] == target_dt)
    rows = df[mask]

    if rows.empty:
        return {"found": False, "is_available": False, "patient_to_attend": ""}

    row = rows.iloc[0]
    return {
        "found": True,
        "is_available": bool(row["is_available"]),
        "patient_to_attend": row["patient_to_attend"],
    }


@tool
def list_doctors_by_specialization(specialization: str) -> list:
    """
    Return distinct doctor names for a given specialization.

    Args:
        specialization: e.g. 'orthodontist'.

    Returns:
        Sorted list of doctor name strings.
    """
    df = _load_df()
    mask = df["specialization"] == specialization.lower().strip()
    return sorted(df[mask]["doctor_name"].unique().tolist())


@tool
def get_available_doctors_by_date(date_filter: str) -> list:
    """
    Return doctors who have at least one available slot on a given date.

    Args:
        date_filter: Date string M/D/YYYY, e.g. '7/8/2026'.

    Returns:
        List of dicts with keys: doctor_name, specialization, available_count.
    """
    df = _load_df()
    try:
        target_date = pd.to_datetime(date_filter).date()
    except Exception:
        return []

    available_mask = df["is_available"] & (df["date_slot"].dt.date == target_date)
    available_slots = df[available_mask]

    result = (
        available_slots.groupby(["doctor_name", "specialization"])
        .size()
        .reset_index(name="available_count")
    )
    return result.to_dict(orient="records")


@tool
def get_available_slots_range(
    start_date: str = "",
    end_date: str = "",
    specialization: str = "",
    doctor_name: str = "",
    limit: int = 50,
) -> list:
    """
    Return available slots within an optional patient-facing date range.

    Args:
        start_date: Optional start date M/D/YYYY, e.g. '7/8/2026'.
        end_date: Optional end date M/D/YYYY, e.g. '7/10/2026'.
        specialization: Optional filter by specialization.
        doctor_name: Optional filter by doctor name.
        limit: Maximum rows to return. Defaults to 50.

    Returns:
        List of dicts with keys: date_slot, specialization, doctor_name.
    """
    df = _load_df()
    mask = df["is_available"]

    try:
        if start_date:
            start = pd.to_datetime(start_date).date()
            mask = mask & (df["date_slot"].dt.date >= start)
        if end_date:
            end = pd.to_datetime(end_date).date()
            mask = mask & (df["date_slot"].dt.date <= end)
    except Exception:
        return []

    if specialization:
        mask = mask & (df["specialization"] == specialization.lower().strip())
    if doctor_name:
        mask = mask & (df["doctor_name"] == doctor_name.lower().strip())

    result = df[mask][["date_slot", "specialization", "doctor_name"]].copy()
    result = result.sort_values("date_slot")
    result["date_slot"] = result["date_slot"].map(format_date_slot)
    return result.head(limit).to_dict(orient="records")


@tool
def get_specialty_summary(date_filter: str = "") -> list:
    """
    Return a patient-facing summary of all specialties.

    Args:
        date_filter: Optional date string M/D/YYYY, e.g. '7/8/2026'.
                     Leave empty to search across all dates.

    Returns:
        List of dicts:
        - specialization
        - available_doctors
        - available_slots
    """
    df = _load_df()
    mask = df["is_available"]

    if date_filter:
        try:
            target_date = pd.to_datetime(date_filter).date()
            mask = mask & (df["date_slot"].dt.date == target_date)
        except Exception:
            return []

    summary = (
        df[mask]
        .groupby("specialization")
        .agg(
            available_doctors=("doctor_name", "nunique"),
            available_slots=("doctor_name", "size"),
        )
        .reset_index()
        .sort_values("specialization")
    )

    return summary.to_dict(orient="records")


@tool
def get_total_available_doctors(
    date_filter: str = "",
    specialization: str = "",
) -> dict:
    """
    Return total patient-facing availability counts.

    Args:
        date_filter: Optional date string M/D/YYYY, e.g. '7/8/2026'.
        specialization: Optional specialization filter, e.g. 'orthodontist'.

    Returns:
        Dict with:
        - total_specializations
        - total_doctors_available
        - total_available_slots
    """
    df = _load_df()
    mask = df["is_available"]

    if specialization:
        mask = mask & (df["specialization"] == specialization.lower().strip())

    if date_filter:
        try:
            target_date = pd.to_datetime(date_filter).date()
            mask = mask & (df["date_slot"].dt.date == target_date)
        except Exception:
            return {
                "date_filter": date_filter,
                "specialization": specialization,
                "total_specializations": 0,
                "total_doctors_available": 0,
                "total_available_slots": 0,
            }

    available = df[mask]

    return {
        "date_filter": date_filter,
        "specialization": specialization,
        "total_specializations": int(available["specialization"].nunique()),
        "total_doctors_available": int(available["doctor_name"].nunique()),
        "total_available_slots": int(len(available)),
    }

