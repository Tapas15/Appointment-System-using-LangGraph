import json
from pathlib import Path
from typing import Literal

from dental_agent.config.settings import BASE_DIR

FeatureCategory = Literal["patient", "doctor", "admin", "unknown"]

FEATURE_CONFIG_PATH = Path(BASE_DIR) / "feature_config.json"

PATIENT_FEATURES = {
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
}

DOCTOR_FEATURES = {
    "doctor_add_availability": "Add or restore doctor availability",
    "doctor_block_slot": "Block doctor time slot",
    "doctor_update_schedule": "Update doctor schedule availability",
}

ADMIN_CONTROL_FEATURES = {
    "admin_list_features": "List admin-controlled features",
    "admin_enable_feature": "Enable one admin-controlled feature",
    "admin_disable_feature": "Disable one admin-controlled feature",
}

PROTECTED_FEATURES = set(ADMIN_CONTROL_FEATURES)
ALL_FEATURES = tuple(PATIENT_FEATURES) + tuple(DOCTOR_FEATURES) + tuple(ADMIN_CONTROL_FEATURES)

FEATURE_ALIASES = {
    "show available slots": "view_available_slots",
    "show slots": "view_available_slots",
    "available slots": "view_available_slots",
    "available schedule": "view_available_slots",
    "show availability": "view_available_slots",
    "check availability": "view_available_slots",
    "slots by specialization": "view_slots_by_specialization",
    "specialization slots": "view_slots_by_specialization",
    "slots by doctor": "view_slots_by_doctor",
    "doctor slots": "view_slots_by_doctor",
    "slots by date": "view_slots_by_date",
    "date slots": "view_slots_by_date",
    "date range": "view_slots_by_date_range",
    "from ": "view_slots_by_date_range",
    " to ": "view_slots_by_date_range",
    "available doctors": "view_available_doctors_by_date",
    "which doctors are available": "view_available_doctors_by_date",
    "which doctors are": "view_doctors_by_specialization",
    "doctors by specialization": "view_doctors_by_specialization",
    "specialization doctors": "view_doctors_by_specialization",
    "show total": "view_availability_summary",
    "total doctors": "view_availability_summary",
    "total specialties": "view_availability_summary",
    "availability summary": "view_availability_summary",
    "check slot": "check_slot_availability",
    "slot availability": "check_slot_availability",
    "patient appointments": "view_patient_appointments",
    "what appointments": "view_patient_appointments",
    "book ": "book_appointment",
    "booking": "book_appointment",
    "cancel ": "cancel_appointment",
    "cancellation": "cancel_appointment",
    "reschedule ": "reschedule_appointment",
    "rescheduling": "reschedule_appointment",
    "add availability": "doctor_add_availability",
    "restore availability": "doctor_add_availability",
    "my availability": "doctor_add_availability",
    "block slot": "doctor_block_slot",
    "block time": "doctor_block_slot",
    "block ": "doctor_block_slot",
    "update schedule": "doctor_update_schedule",
    "change schedule": "doctor_update_schedule",
    "doctor schedule": "doctor_update_schedule",
    "my schedule": "doctor_update_schedule",
}


def default_global_features() -> dict[str, bool]:
    return {feature_name: True for feature_name in ALL_FEATURES}


def _normalize_features(features: dict | None) -> dict[str, bool]:
    normalized = default_global_features()
    if not features:
        return normalized

    for feature_name, enabled in features.items():
        if feature_name in ALL_FEATURES and feature_name not in PROTECTED_FEATURES:
            normalized[feature_name] = bool(enabled)

    for feature_name in PROTECTED_FEATURES:
        normalized[feature_name] = True

    return normalized


def load_global_features() -> dict[str, bool]:
    if not FEATURE_CONFIG_PATH.exists():
        features = default_global_features()
        save_global_features(features)
        return features

    try:
        with FEATURE_CONFIG_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return default_global_features()

    features = _normalize_features(data if isinstance(data, dict) else {})
    if features != _normalize_features(data if isinstance(data, dict) else {}):
        save_global_features(features)

    return features


def save_global_features(features: dict[str, bool]) -> None:
    normalized = _normalize_features(features)
    FEATURE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = FEATURE_CONFIG_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(normalized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(FEATURE_CONFIG_PATH)


def feature_category(feature_name: str | None) -> FeatureCategory:
    if feature_name in PATIENT_FEATURES:
        return "patient"
    if feature_name in DOCTOR_FEATURES:
        return "doctor"
    if feature_name in ADMIN_CONTROL_FEATURES:
        return "admin"
    return "unknown"


def feature_for_request(text: str) -> str | None:
    normalized = text.strip().lower()
    if not normalized:
        return None

    for alias, feature_name in FEATURE_ALIASES.items():
        if alias in normalized:
            return feature_name

    return None


def is_global_feature_enabled(features: dict[str, bool] | None, feature_name: str | None) -> bool:
    if not feature_name:
        return True
    return bool((features or load_global_features()).get(feature_name, True))


def disabled_global_feature_for_request(
    state_features: dict[str, bool] | None,
    text: str,
    category: FeatureCategory | None = None,
) -> str | None:
    feature_name = feature_for_request(text)
    if not feature_name:
        return None

    if category and feature_category(feature_name) != category:
        return None

    features = state_features or load_global_features()
    if not is_global_feature_enabled(features, feature_name):
        return feature_name

    return None
