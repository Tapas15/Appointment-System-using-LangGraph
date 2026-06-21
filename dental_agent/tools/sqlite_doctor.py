from langchain_core.tools import tool

from dental_agent.storage.sqlite_store import (
    doctor_add_availability as sqlite_doctor_add_availability,
    doctor_add_availability_bulk as sqlite_doctor_add_availability_bulk,
    doctor_block_time_slot as sqlite_doctor_block_time_slot,
    doctor_login as sqlite_doctor_login,
    doctor_update_schedule as sqlite_doctor_update_schedule,
)


@tool
def doctor_login(doctor_name: str, password: str) -> dict:
    """Verify doctor credentials and start a doctor session in SQLite."""
    return sqlite_doctor_login(doctor_name=doctor_name, password=password)


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
    return sqlite_doctor_add_availability(
        doctor_name=doctor_name,
        password=password,
        date_slot=date_slot,
        specialization=specialization,
    )


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
    Doctor adds or restores availability for multiple dates and times in SQLite.
    """
    return sqlite_doctor_add_availability_bulk(
        doctor_name=doctor_name,
        password=password,
        dates=dates,
        start_time=start_time,
        end_time=end_time,
        specialization=specialization,
        interval_minutes=interval_minutes,
    )


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
    return sqlite_doctor_block_time_slot(
        doctor_name=doctor_name,
        password=password,
        date_slot=date_slot,
    )


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
    return sqlite_doctor_update_schedule(
        doctor_name=doctor_name,
        password=password,
        date_slot=date_slot,
        is_available=is_available,
    )
