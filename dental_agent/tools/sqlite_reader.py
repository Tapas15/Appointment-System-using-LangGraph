from langchain_core.tools import tool

from dental_agent.storage.sqlite_store import (
    check_slot_availability as sqlite_check_slot_availability,
    get_available_doctors_by_date as sqlite_get_available_doctors_by_date,
    get_available_slots as sqlite_get_available_slots,
    get_available_slots_range as sqlite_get_available_slots_range,
    get_patient_appointments as sqlite_get_patient_appointments,
    get_specialty_summary as sqlite_get_specialty_summary,
    get_total_available_doctors as sqlite_get_total_available_doctors,
    list_all_specializations_and_doctors as sqlite_list_all_specializations_and_doctors,
    list_doctors_by_specialization as sqlite_list_doctors_by_specialization,
)


@tool
def get_available_slots(
    specialization: str = "",
    doctor_name: str = "",
    date_filter: str = "",
) -> list:
    """
    Return available appointment slots from SQLite.
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
    """
    return sqlite_get_patient_appointments(patient_id=patient_id)


@tool
def check_slot_availability(doctor_name: str, date_slot: str) -> dict:
    """
    Check if a specific doctor slot is available.
    """
    return sqlite_check_slot_availability(doctor_name=doctor_name, date_slot=date_slot)


@tool
def list_doctors_by_specialization(specialization: str) -> list:
    """
    Return distinct doctor names for a given specialization.
    """
    return sqlite_list_doctors_by_specialization(specialization=specialization)


@tool
def list_all_specializations_and_doctors() -> list:
    """
    Return every stored specialization with its doctor names.
    """
    return sqlite_list_all_specializations_and_doctors()


@tool
def get_available_doctors_by_date(date_filter: str) -> list:
    """
    Return doctors who have at least one available slot on a given date.
    """
    return sqlite_get_available_doctors_by_date(date_filter=date_filter)


@tool
def get_available_slots_range(
    start_date: str = "",
    end_date: str = "",
    specialization: str = "",
    doctor_name: str = "",
    limit: int = 50,
) -> list:
    """
    Return available slots across a date range from SQLite.
    """
    return sqlite_get_available_slots_range(
        start_date=start_date,
        end_date=end_date,
        specialization=specialization,
        doctor_name=doctor_name,
        limit=limit,
    )


@tool
def get_specialty_summary(date_filter: str = "") -> list:
    """
    Return specialty availability summary from SQLite.
    """
    return sqlite_get_specialty_summary(date_filter=date_filter)


@tool
def get_total_available_doctors(
    date_filter: str = "",
    specialization: str = "",
) -> dict:
    """
    Return total availability counts from SQLite.
    """
    return sqlite_get_total_available_doctors(
        date_filter=date_filter,
        specialization=specialization,
    )
