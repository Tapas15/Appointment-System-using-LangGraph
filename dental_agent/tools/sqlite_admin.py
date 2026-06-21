from langchain_core.tools import tool

from dental_agent.storage.sqlite_store import (
    admin_add_availability as sqlite_admin_add_availability,
    admin_block_time_slot as sqlite_admin_block_time_slot,
    admin_update_schedule as sqlite_admin_update_schedule,
)
from dental_agent.tools.csv_admin import (
    admin_disable_doctor_features as csv_admin_disable_doctor_features,
    admin_disable_feature as csv_admin_disable_feature,
    admin_disable_patient_features as csv_admin_disable_patient_features,
    admin_enable_doctor_features as csv_admin_enable_doctor_features,
    admin_enable_feature as csv_admin_enable_feature,
    admin_enable_patient_features as csv_admin_enable_patient_features,
    admin_list_features as csv_admin_list_features,
    admin_login as csv_admin_login,
)


@tool
def admin_login(admin_user_id: str, password: str) -> dict:
    """Verify admin credentials and start an admin session."""
    return csv_admin_login(admin_user_id=admin_user_id, password=password)


@tool
def admin_enable_patient_features() -> dict:
    """Enable patient features for the current admin session."""
    return csv_admin_enable_patient_features()


@tool
def admin_disable_patient_features() -> dict:
    """Disable patient features for the current admin session."""
    return csv_admin_disable_patient_features()


@tool
def admin_enable_doctor_features() -> dict:
    """Enable doctor features for the current admin session."""
    return csv_admin_enable_doctor_features()


@tool
def admin_disable_doctor_features() -> dict:
    """Disable doctor features for the current admin session."""
    return csv_admin_disable_doctor_features()


@tool
def admin_enable_feature(feature_name: str) -> dict:
    """Enable one individual admin-controlled feature."""
    return csv_admin_enable_feature(feature_name=feature_name)


@tool
def admin_disable_feature(feature_name: str) -> dict:
    """Disable one individual admin-controlled feature."""
    return csv_admin_disable_feature(feature_name=feature_name)


@tool
def admin_list_features() -> list:
    """List all admin-controlled features."""
    return csv_admin_list_features()


@tool
def admin_add_availability(doctor_name: str, date_slot: str, specialization: str = "") -> dict:
    """Admin adds or restores a doctor's availability slot in SQLite."""
    return sqlite_admin_add_availability(
        doctor_name=doctor_name,
        date_slot=date_slot,
        specialization=specialization,
    )


@tool
def admin_block_time_slot(doctor_name: str, date_slot: str) -> dict:
    """Admin blocks a doctor's available time slot in SQLite."""
    return sqlite_admin_block_time_slot(doctor_name=doctor_name, date_slot=date_slot)


@tool
def admin_update_schedule(doctor_name: str, date_slot: str, is_available: bool) -> dict:
    """Admin updates a doctor's schedule availability in SQLite."""
    return sqlite_admin_update_schedule(
        doctor_name=doctor_name,
        date_slot=date_slot,
        is_available=is_available,
    )
