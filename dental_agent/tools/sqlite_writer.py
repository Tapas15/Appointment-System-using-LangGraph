from langchain_core.tools import tool

from dental_agent.storage.sqlite_store import (
    book_appointment as sqlite_book_appointment,
    cancel_appointment as sqlite_cancel_appointment,
    reschedule_appointment as sqlite_reschedule_appointment,
)


@tool
def book_appointment(patient_id: str, doctor_name: str, date_slot: str) -> dict:
    """
    Book an appointment: mark slot as unavailable and assign patient_id.

    Args:
        patient_id: Numeric patient ID string, e.g. '1000082'.
        doctor_name: Doctor name (case-insensitive), e.g. 'emily johnson'.
        date_slot: Slot in M/D/YYYY H:MM format, e.g. '5/10/2026 9:00'.

    Returns:
        Dict with keys: success (bool), message (str).
    """
    return sqlite_book_appointment(
        patient_id=patient_id,
        doctor_name=doctor_name,
        date_slot=date_slot,
    )


@tool
def cancel_appointment(patient_id: str, date_slot: str) -> dict:
    """
    Cancel an appointment: mark slot available and clear patient_id.

    Args:
        patient_id: Patient whose appointment to cancel.
        date_slot: Slot in M/D/YYYY H:MM format to cancel.

    Returns:
        Dict with keys: success (bool), message (str).
    """
    return sqlite_cancel_appointment(patient_id=patient_id, date_slot=date_slot)


@tool
def reschedule_appointment(
    patient_id: str,
    current_date_slot: str,
    new_date_slot: str,
    doctor_name: str,
) -> dict:
    """
    Reschedule by cancelling the old slot and booking a new one atomically.

    Args:
        patient_id: Patient whose appointment to reschedule.
        current_date_slot: Existing booked slot to vacate (M/D/YYYY H:MM).
        new_date_slot: Desired new slot (M/D/YYYY H:MM).
        doctor_name: Doctor name (must match the booking's doctor).

    Returns:
        Dict with keys: success (bool), message (str).
    """
    return sqlite_reschedule_appointment(
        patient_id=patient_id,
        current_date_slot=current_date_slot,
        new_date_slot=new_date_slot,
        doctor_name=doctor_name,
    )
