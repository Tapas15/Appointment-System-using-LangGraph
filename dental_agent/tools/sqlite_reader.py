from langchain_core.tools import tool

from dental_agent.storage.sqlite_store import (
    check_slot_availability as sqlite_check_slot_availability,
    get_available_doctors_by_date as sqlite_get_available_doctors_by_date,
    get_available_slots as sqlite_get_available_slots,
    get_patient_appointments as sqlite_get_patient_appointments,
    list_doctors_by_specialization as sqlite_list_doctors_by_specialization,
    list_all_specializations_and_doctors as sqlite_list_all_specializations_and_doctors,
)


@tool
def get_available_slots(
    specialization: str = "",
    doctor_name: str = "",
    date_filter: str = "",
) -> list:
    """
    Return available appointment slots from SQLite.

    Args:
        specialization: Filter by specialization, e.g. 'orthodontist'. Leave empty to skip.
        doctor_name: Filter by doctor name (case-insensitive), e.g. 'emily johnson'. Leave empty to skip.
        date_filter: Filter by date string M/D/YYYY, e.g. '5/10/2026'. Leave empty to skip.

    Returns:
        List of dicts with keys: date_slot, specialization, doctor_name.
        Returns at most 20 rows to keep response concise.
    """
    return sqlite_get_available_slots(
        specialization=specialization,
        doctor_name=doctor_name,
        date_filter=date_filter,
    )


@tool
def get_patient_appointments(patient_id: str) -> list:
    """
    Return all booked appointments for a given patient ID.

    Args:
        patient_id: Numeric patient ID string, e.g. '1000082'.

    Returns:
        List of dicts with keys: date_slot, specialization, doctor_name, patient_to_attend.
    """
    return sqlite_get_patient_appointments(patient_id=patient_id)


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
    return sqlite_check_slot_availability(doctor_name=doctor_name, date_slot=date_slot)


@tool
def list_doctors_by_specialization(specialization: str) -> list:
    """
    Return distinct doctor names for a given specialization.

    Args:
        specialization: e.g. 'orthodontist'.

    Returns:
        Sorted list of doctor name strings.
    """
    return sqlite_list_doctors_by_specialization(specialization=specialization)


@tool
def list_all_specializations_and_doctors() -> list:
    """
    Return every stored specialization with its doctor names.

    Use this when the user asks for all specialties, all specialty doctors,
    or a full list of specialties and doctors.

    Returns:
        List of dicts with keys: specialization, doctors.
    """
    return sqlite_list_all_specializations_and_doctors()


@tool
def get_available_doctors_by_date(date_filter: str) -> list:
    """
    Return doctors who have at least one available slot on a given date.

    Args:
        date_filter: Date string M/D/YYYY, e.g. '7/8/2026'.

    Returns:
        List of dicts with keys: doctor_name, specialization, available_count.
    """
    return sqlite_get_available_doctors_by_date(date_filter=date_filter)
