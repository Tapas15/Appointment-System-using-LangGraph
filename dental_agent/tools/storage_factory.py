from dental_agent.storage.repository import get_active_backend
from dental_agent.tools.csv_admin import (
    admin_disable_doctor_features,
    admin_disable_feature,
    admin_disable_patient_features,
    admin_enable_doctor_features,
    admin_enable_feature,
    admin_enable_patient_features,
    admin_list_features,
    admin_login,
)
from dental_agent.tools.csv_doctor import (
    doctor_add_availability as csv_doctor_add_availability,
    doctor_add_availability_bulk as csv_doctor_add_availability_bulk,
    doctor_block_time_slot as csv_doctor_block_time_slot,
    doctor_login as csv_doctor_login,
    doctor_update_schedule as csv_doctor_update_schedule,
)
from dental_agent.tools.csv_reader import (
    check_slot_availability as csv_check_slot_availability,
    get_available_doctors_by_date as csv_get_available_doctors_by_date,
    get_available_slots as csv_get_available_slots,
    get_available_slots_range as csv_get_available_slots_range,
    get_patient_appointments as csv_get_patient_appointments,
    get_specialty_summary as csv_get_specialty_summary,
    get_total_available_doctors as csv_get_total_available_doctors,
    list_doctors_by_specialization as csv_list_doctors_by_specialization,
)
from dental_agent.tools.csv_writer import (
    book_appointment as csv_book_appointment,
    cancel_appointment as csv_cancel_appointment,
    reschedule_appointment as csv_reschedule_appointment,
)
from dental_agent.tools.sqlite_admin import (
    admin_disable_doctor_features as sqlite_admin_disable_doctor_features,
    admin_disable_feature as sqlite_admin_disable_feature,
    admin_disable_patient_features as sqlite_admin_disable_patient_features,
    admin_enable_doctor_features as sqlite_admin_enable_doctor_features,
    admin_enable_feature as sqlite_admin_enable_feature,
    admin_enable_patient_features as sqlite_admin_enable_patient_features,
    admin_list_features as sqlite_admin_list_features,
    admin_login as sqlite_admin_login,
)
from dental_agent.tools.sqlite_doctor import (
    doctor_add_availability as sqlite_doctor_add_availability,
    doctor_add_availability_bulk as sqlite_doctor_add_availability_bulk,
    doctor_block_time_slot as sqlite_doctor_block_time_slot,
    doctor_login as sqlite_doctor_login,
    doctor_update_schedule as sqlite_doctor_update_schedule,
)
from dental_agent.tools.sqlite_reader import (
    check_slot_availability as sqlite_check_slot_availability,
    get_available_doctors_by_date as sqlite_get_available_doctors_by_date,
    get_available_slots as sqlite_get_available_slots,
    get_available_slots_range as sqlite_get_available_slots_range,
    get_patient_appointments as sqlite_get_patient_appointments,
    get_specialty_summary as sqlite_get_specialty_summary,
    get_total_available_doctors as sqlite_get_total_available_doctors,
    list_doctors_by_specialization as sqlite_list_doctors_by_specialization,
)
from dental_agent.tools.sqlite_writer import (
    book_appointment as sqlite_book_appointment,
    cancel_appointment as sqlite_cancel_appointment,
    reschedule_appointment as sqlite_reschedule_appointment,
)


def _backend() -> str:
    return get_active_backend()


def build_info_tools():
    if _backend() == "sqlite":
        return [
            sqlite_get_available_slots,
            sqlite_get_available_slots_range,
            sqlite_get_specialty_summary,
            sqlite_get_total_available_doctors,
            sqlite_get_available_doctors_by_date,
            sqlite_list_doctors_by_specialization,
            sqlite_check_slot_availability,
            sqlite_get_patient_appointments,
        ]

    return [
        csv_get_available_slots,
        csv_get_available_slots_range,
        csv_get_specialty_summary,
        csv_get_total_available_doctors,
        csv_get_available_doctors_by_date,
        csv_list_doctors_by_specialization,
        csv_check_slot_availability,
        csv_get_patient_appointments,
    ]


def build_booking_tools():
    if _backend() == "sqlite":
        return [
            sqlite_get_available_slots,
            sqlite_check_slot_availability,
            sqlite_book_appointment,
        ]

    return [
        csv_get_available_slots,
        csv_check_slot_availability,
        csv_book_appointment,
    ]


def build_cancellation_tools():
    if _backend() == "sqlite":
        return [
            sqlite_get_patient_appointments,
            sqlite_cancel_appointment,
        ]

    return [
        csv_get_patient_appointments,
        csv_cancel_appointment,
    ]


def build_rescheduling_tools():
    if _backend() == "sqlite":
        return [
            sqlite_get_patient_appointments,
            sqlite_get_available_slots,
            sqlite_reschedule_appointment,
        ]

    return [
        csv_get_patient_appointments,
        csv_get_available_slots,
        csv_reschedule_appointment,
    ]


def build_doctor_tools():
    if _backend() == "sqlite":
        return [
            sqlite_doctor_login,
            sqlite_doctor_add_availability,
            sqlite_doctor_add_availability_bulk,
            sqlite_doctor_block_time_slot,
            sqlite_doctor_update_schedule,
        ]

    return [
        csv_doctor_login,
        csv_doctor_add_availability,
        csv_doctor_add_availability_bulk,
        csv_doctor_block_time_slot,
        csv_doctor_update_schedule,
    ]


def get_admin_feature_tools():
    if _backend() == "sqlite":
        return [
            sqlite_admin_login,
            sqlite_admin_enable_patient_features,
            sqlite_admin_disable_patient_features,
            sqlite_admin_enable_doctor_features,
            sqlite_admin_disable_doctor_features,
            sqlite_admin_enable_feature,
            sqlite_admin_disable_feature,
            sqlite_admin_list_features,
        ]

    return [
        admin_login,
        admin_enable_patient_features,
        admin_disable_patient_features,
        admin_enable_doctor_features,
        admin_disable_doctor_features,
        admin_enable_feature,
        admin_disable_feature,
        admin_list_features,
    ]


def get_admin_operation_tool_map():
    if _backend() == "sqlite":
        from dental_agent.tools.sqlite_admin import (
            admin_add_availability as sqlite_admin_add_availability,
            admin_block_time_slot as sqlite_admin_block_time_slot,
            admin_update_schedule as sqlite_admin_update_schedule,
        )

        return {
            "view_available_slots": sqlite_get_available_slots,
            "view_slots_by_date_range": sqlite_get_available_slots_range,
            "view_availability_summary": sqlite_get_specialty_summary,
            "view_availability_summary_total": sqlite_get_total_available_doctors,
            "view_available_doctors_by_date": sqlite_get_available_doctors_by_date,
            "view_doctors_by_specialization": sqlite_list_doctors_by_specialization,
            "check_slot_availability": sqlite_check_slot_availability,
            "view_patient_appointments": sqlite_get_patient_appointments,
            "book_appointment": sqlite_book_appointment,
            "cancel_appointment": sqlite_cancel_appointment,
            "reschedule_appointment": sqlite_reschedule_appointment,
            "doctor_add_availability": sqlite_admin_add_availability,
            "doctor_block_slot": sqlite_admin_block_time_slot,
            "doctor_update_schedule": sqlite_admin_update_schedule,
        }

    from dental_agent.tools.csv_admin import (
        admin_add_availability,
        admin_block_time_slot,
        admin_update_schedule,
    )

    return {
        "view_available_slots": csv_get_available_slots,
        "view_slots_by_date_range": csv_get_available_slots_range,
        "view_availability_summary": csv_get_specialty_summary,
        "view_availability_summary_total": csv_get_total_available_doctors,
        "view_available_doctors_by_date": csv_get_available_doctors_by_date,
        "view_doctors_by_specialization": csv_list_doctors_by_specialization,
        "check_slot_availability": csv_check_slot_availability,
        "view_patient_appointments": csv_get_patient_appointments,
        "book_appointment": csv_book_appointment,
        "cancel_appointment": csv_cancel_appointment,
        "reschedule_appointment": csv_reschedule_appointment,
        "doctor_add_availability": admin_add_availability,
        "doctor_block_slot": admin_block_time_slot,
        "doctor_update_schedule": admin_update_schedule,
    }
