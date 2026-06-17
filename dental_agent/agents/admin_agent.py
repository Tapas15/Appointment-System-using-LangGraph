import json
import time

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import ToolNode

from dental_agent.config.runtime import get_graph_settings
from dental_agent.config.settings import get_chat_groq
from dental_agent.models.state import AppointmentState
from dental_agent.tools.csv_admin import (
    ADMIN_FEATURE_DEFINITIONS,
    admin_add_availability,
    admin_block_time_slot,
    admin_disable_doctor_features,
    admin_disable_feature,
    admin_disable_patient_features,
    admin_enable_doctor_features,
    admin_enable_feature,
    admin_enable_patient_features,
    admin_list_features,
    admin_login,
    admin_update_schedule,
)
from dental_agent.tools.csv_reader import (
    check_slot_availability,
    get_available_doctors_by_date,
    get_available_slots,
    get_available_slots_range,
    get_patient_appointments,
    get_specialty_summary,
    get_total_available_doctors,
    list_doctors_by_specialization,
)
from dental_agent.tools.csv_writer import (
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
)
from dental_agent.utils import sanitize_messages

ADMIN_SESSION_TIMEOUT_SECONDS = 15 * 60

ADMIN_TOOLS = [
    admin_login,
    admin_enable_patient_features,
    admin_disable_patient_features,
    admin_enable_doctor_features,
    admin_disable_doctor_features,
    admin_enable_feature,
    admin_disable_feature,
    admin_list_features,
]

PATIENT_ADMIN_TOOLS = [
    get_available_slots,
    get_available_slots_range,
    get_specialty_summary,
    get_total_available_doctors,
    get_available_doctors_by_date,
    list_doctors_by_specialization,
    check_slot_availability,
    get_patient_appointments,
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
]

DOCTOR_ADMIN_TOOLS = [
    admin_add_availability,
    admin_block_time_slot,
    admin_update_schedule,
]

ADMIN_SYSTEM = """You are the Admin Agent for a dental appointment management system.

You operate under the supervisor and support both patient-facing appointment work and doctor schedule-management work when those features are enabled.

Rules:
- Admin must login first with admin_user_id and password.
- After successful admin login, all individual admin features are enabled by default.
- Admin can enable or disable each individual feature by exact feature name.
- Admin can list admin-controlled features with admin_list_features.
- If a requested feature is disabled, do not perform that action.
- Admin can do patient work only when the exact patient feature is enabled.
- Admin can do doctor schedule-management work only when the exact doctor feature is enabled.
- Do not reveal admin passwords.
- If a required parameter is missing, ask one focused clarifying question.
- Use the available tools for real data and changes. Never invent slots, doctors, or appointment results.
"""

ADMIN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", ADMIN_SYSTEM + "\n\nCurrent admin context:\n{admin_context}"),
    ("placeholder", "{messages}"),
])

admin_tool_node = ToolNode(tools=ADMIN_TOOLS + PATIENT_ADMIN_TOOLS + DOCTOR_ADMIN_TOOLS)


def _last_message_text(state: AppointmentState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return ""
    return str(getattr(messages[-1], "content", ""))


def _admin_context(state: AppointmentState) -> str:
    role = state.get("admin_session_role") or "non_admin"
    admin = state.get("authenticated_admin") or "None"
    patient_features = bool(state.get("admin_patient_features_enabled"))
    doctor_features = bool(state.get("admin_doctor_features_enabled"))
    started_at = state.get("admin_session_started_at") or "None"
    last_activity = state.get("last_admin_activity_at") or "None"
    enabled_features = ", ".join(sorted(
        feature_name
        for feature_name, enabled in (state.get("admin_enabled_features") or {}).items()
        if enabled
    )) or "None"

    return (
        f"admin_session_role: {role}\n"
        f"authenticated_admin: {admin}\n"
        f"admin_patient_features_enabled: {patient_features}\n"
        f"admin_doctor_features_enabled: {doctor_features}\n"
        f"enabled_features: {enabled_features}\n"
        f"admin_session_started_at: {started_at}\n"
        f"last_admin_activity_at: {last_activity}\n"
        f"admin_session_timeout_seconds: {ADMIN_SESSION_TIMEOUT_SECONDS}"
    )


def _reset_admin_session(message: str) -> dict:
    return {
        "messages": [AIMessage(content=message)],
        "admin_session_role": "non_admin",
        "authenticated_admin": None,
        "authenticated_admin_password": None,
        "admin_session_started_at": None,
        "last_admin_activity_at": None,
        "admin_patient_features_enabled": False,
        "admin_doctor_features_enabled": False,
        "admin_enabled_features": {},
        "final_response": message,
    }


def _is_logout_request(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in {
        "logout",
        "log out",
        "admin logout",
        "admin log out",
        "sign out",
        "exit admin mode",
    }


def _is_admin_session_expired(state: AppointmentState) -> bool:
    if state.get("admin_session_role") != "admin":
        return False

    last_activity = state.get("last_admin_activity_at")
    if not last_activity:
        return False

    return (time.time() - float(last_activity)) > ADMIN_SESSION_TIMEOUT_SECONDS


def _is_feature_toggle_request(text: str) -> bool:
    normalized = text.strip().lower()
    return any(
        phrase in normalized
        for phrase in [
            "enable patient features",
            "disable patient features",
            "enable doctor features",
            "disable doctor features",
            "enable feature",
            "disable feature",
            "list features",
            "admin login",
            "login as admin",
        ]
    )


def _is_patient_work(text: str) -> bool:
    if _is_feature_toggle_request(text):
        return False

    normalized = text.strip().lower()
    patient_phrases = [
        "show slots",
        "available slots",
        "show availability",
        "check availability",
        "which doctors are available",
        "list doctors",
        "total doctors",
        "total specialties",
        "patient appointment",
        "what appointments",
        "book ",
        "cancel ",
        "reschedule ",
        "cancel appointment",
        "reschedule appointment",
    ]
    return any(phrase in normalized for phrase in patient_phrases)


def _is_doctor_work(text: str) -> bool:
    if _is_feature_toggle_request(text):
        return False

    normalized = text.strip().lower()
    doctor_phrases = [
        "add availability",
        "restore availability",
        "block slot",
        "block time",
        "update schedule",
        "doctor schedule",
        "doctor features",
    ]
    return any(phrase in normalized for phrase in doctor_phrases)


FEATURE_ALIASES = {
    "show slots": "view_available_slots",
    "available slots": "view_available_slots",
    "show availability": "view_available_slots",
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
    "which doctors": "view_available_doctors_by_date",
    "doctors by specialization": "view_doctors_by_specialization",
    "specialization doctors": "view_doctors_by_specialization",
    "total doctors": "view_availability_summary",
    "total specialties": "view_availability_summary",
    "summary": "view_availability_summary",
    "check slot": "check_slot_availability",
    "slot availability": "check_slot_availability",
    "patient appointments": "view_patient_appointments",
    "what appointments": "view_patient_appointments",
    "book ": "book_appointment",
    "booking": "book_appointment",
    "cancel ": "cancel_appointment",
    "cancellation": "cancel_appointment",
    "reschedule ": "reschedule_appointment",
    "add availability": "doctor_add_availability",
    "restore availability": "doctor_add_availability",
    "block ": "doctor_block_slot",
    "block slot": "doctor_block_slot",
    "block time": "doctor_block_slot",
    "update schedule": "doctor_update_schedule",
    "doctor schedule": "doctor_update_schedule",
}


def _required_feature_for_request(text: str) -> str | None:
    normalized = text.strip().lower()

    for alias, feature_name in FEATURE_ALIASES.items():
        if alias in normalized:
            return feature_name

    return None


def _feature_enabled(state: AppointmentState, feature_name: str) -> bool:
    features = state.get("admin_enabled_features") or {}
    return bool(features.get(feature_name, False))


def _set_feature_state(state: AppointmentState, feature_name: str, enabled: bool) -> dict:
    features = dict(state.get("admin_enabled_features") or {})
    features[feature_name] = enabled

    patient_features = {
        "view_available_slots",
        "view_slots_by_specialization",
        "view_slots_by_doctor",
        "view_slots_by_date",
        "view_slots_by_date_range",
        "view_available_doctors_by_date",
        "view_doctors_by_specialization",
        "view_availability_summary",
        "check_slot_availability",
        "view_patient_appointments",
        "book_appointment",
        "cancel_appointment",
        "reschedule_appointment",
    }
    doctor_features = {
        "doctor_add_availability",
        "doctor_block_slot",
        "doctor_update_schedule",
    }

    return {
        "admin_enabled_features": features,
        "admin_patient_features_enabled": any(features.get(feature, False) for feature in patient_features),
        "admin_doctor_features_enabled": any(features.get(feature, False) for feature in doctor_features),
        "last_admin_activity_at": time.time(),
    }


def _parse_tool_content(content) -> dict | None:
    if isinstance(content, dict):
        return content

    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    return None


def _last_tool_message(state: AppointmentState) -> ToolMessage | None:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, ToolMessage):
            return message
    return None


def _tool_result_state_update(state: AppointmentState) -> dict:
    tool_message = _last_tool_message(state)
    if not tool_message:
        return {}

    result = _parse_tool_content(tool_message.content)
    if not result or not result.get("success"):
        return {}

    if tool_message.name == admin_login.name:
        now = time.time()
        admin_id = result.get("admin_user_id")
        enabled_features = result.get("admin_enabled_features") or {}
        return {
            "admin_session_role": "admin",
            "authenticated_admin": admin_id,
            "authenticated_admin_password": None,
            "admin_session_started_at": result.get("admin_session_started_at", now),
            "last_admin_activity_at": result.get("last_admin_activity_at", now),
            "admin_patient_features_enabled": bool(result.get("admin_patient_features_enabled", True)),
            "admin_doctor_features_enabled": bool(result.get("admin_doctor_features_enabled", True)),
            "admin_enabled_features": enabled_features,
        }

    if tool_message.name == admin_enable_patient_features.name:
        features = {
            feature_name: True
            for feature_name in ADMIN_FEATURE_DEFINITIONS
            if feature_name != "admin_list_features"
        }
        return {
            **_set_feature_state(state, "view_available_slots", True),
            **{
                feature_name: True
                for feature_name in [
                    "view_slots_by_specialization",
                    "view_slots_by_doctor",
                    "view_slots_by_date",
                    "view_slots_by_date_range",
                    "view_available_doctors_by_date",
                    "view_doctors_by_specialization",
                    "view_availability_summary",
                    "check_slot_availability",
                    "view_patient_appointments",
                    "book_appointment",
                    "cancel_appointment",
                    "reschedule_appointment",
                ]
            },
            "admin_patient_features_enabled": True,
            "message": result.get("message"),
        }

    if tool_message.name == admin_disable_patient_features.name:
        features = dict(state.get("admin_enabled_features") or {})
        for feature_name in [
            "view_available_slots",
            "view_slots_by_specialization",
            "view_slots_by_doctor",
            "view_slots_by_date",
            "view_slots_by_date_range",
            "view_available_doctors_by_date",
            "view_doctors_by_specialization",
            "view_availability_summary",
            "check_slot_availability",
            "view_patient_appointments",
            "book_appointment",
            "cancel_appointment",
            "reschedule_appointment",
        ]:
            features[feature_name] = False
        return {
            **_set_feature_state(state, "view_available_slots", False),
            **{
                feature_name: False
                for feature_name in [
                    "view_slots_by_specialization",
                    "view_slots_by_doctor",
                    "view_slots_by_date",
                    "view_slots_by_date_range",
                    "view_available_doctors_by_date",
                    "view_doctors_by_specialization",
                    "view_availability_summary",
                    "check_slot_availability",
                    "view_patient_appointments",
                    "book_appointment",
                    "cancel_appointment",
                    "reschedule_appointment",
                ]
            },
            "admin_patient_features_enabled": False,
            "message": result.get("message"),
        }

    if tool_message.name == admin_enable_doctor_features.name:
        return {
            **_set_feature_state(state, "doctor_add_availability", True),
            **{
                "doctor_block_slot": True,
                "doctor_update_schedule": True,
            },
            "admin_doctor_features_enabled": True,
            "message": result.get("message"),
        }

    if tool_message.name == admin_disable_doctor_features.name:
        return {
            **_set_feature_state(state, "doctor_add_availability", False),
            **{
                "doctor_block_slot": False,
                "doctor_update_schedule": False,
            },
            "admin_doctor_features_enabled": False,
            "message": result.get("message"),
        }

    if tool_message.name == admin_enable_feature.name:
        feature_name = result.get("feature_name")
        if feature_name in ADMIN_FEATURE_DEFINITIONS:
            return {
                **_set_feature_state(state, feature_name, True),
                "message": result.get("message"),
            }

    if tool_message.name == admin_disable_feature.name:
        feature_name = result.get("feature_name")
        if feature_name in ADMIN_FEATURE_DEFINITIONS:
            return {
                **_set_feature_state(state, feature_name, False),
                "message": result.get("message"),
            }

    return {}


def _admin_tools_for_state(state: AppointmentState) -> list:
    features = state.get("admin_enabled_features") or {}
    tools = [admin_login]

    if features.get("admin_list_features", False):
        tools.append(admin_list_features)
    if features.get("admin_enable_feature", False):
        tools.extend([
            admin_enable_patient_features,
            admin_enable_doctor_features,
            admin_enable_feature,
        ])
    if features.get("admin_disable_feature", False):
        tools.extend([
            admin_disable_patient_features,
            admin_disable_doctor_features,
            admin_disable_feature,
        ])

    if state.get("admin_session_role") != "admin":
        return tools

    if features.get("view_available_slots") or features.get("view_slots_by_specialization") or features.get("view_slots_by_doctor") or features.get("view_slots_by_date"):
        tools.append(get_available_slots)

    if features.get("view_slots_by_date_range"):
        tools.append(get_available_slots_range)

    if features.get("view_availability_summary"):
        tools.extend([
            get_specialty_summary,
            get_total_available_doctors,
        ])

    if features.get("view_available_doctors_by_date"):
        tools.append(get_available_doctors_by_date)

    if features.get("view_doctors_by_specialization"):
        tools.append(list_doctors_by_specialization)

    if features.get("check_slot_availability") or features.get("book_appointment") or features.get("reschedule_appointment"):
        tools.append(check_slot_availability)

    if features.get("view_patient_appointments") or features.get("cancel_appointment") or features.get("reschedule_appointment"):
        tools.append(get_patient_appointments)

    if features.get("book_appointment"):
        tools.append(book_appointment)

    if features.get("cancel_appointment"):
        tools.append(cancel_appointment)

    if features.get("reschedule_appointment"):
        tools.append(reschedule_appointment)

    if features.get("doctor_add_availability"):
        tools.append(admin_add_availability)

    if features.get("doctor_block_slot"):
        tools.append(admin_block_time_slot)

    if features.get("doctor_update_schedule"):
        tools.append(admin_update_schedule)

    return tools


def admin_agent_node(state: AppointmentState) -> dict:
    text = _last_message_text(state)

    if _is_logout_request(text):
        return _reset_admin_session("Admin logged out. You are back in non-admin mode.")

    if _is_admin_session_expired(state):
        return _reset_admin_session("Admin session expired due to 15 minutes of inactivity.")

    pending_tool_update = _tool_result_state_update(state)
    if pending_tool_update:
        state = {**state, **pending_tool_update}

    if (
        state.get("admin_session_role") != "admin"
        and "admin login" not in text.lower()
        and "login as admin" not in text.lower()
    ):
        message = "Please login first with admin_user_id and password."
        return {
            "messages": [AIMessage(content=message)],
            "final_response": message,
        }

    required_feature = _required_feature_for_request(text)
    if (
        state.get("admin_session_role") == "admin"
        and required_feature
        and not _feature_enabled(state, required_feature)
    ):
        message = f"This feature is disabled: {required_feature}"
        return {
            "messages": [AIMessage(content=message)],
            "last_admin_activity_at": time.time(),
            "final_response": message,
        }

    settings = get_graph_settings()
    llm = get_chat_groq(
        api_key=settings["api_key"],
        model_name=settings["model_name"],
        temperature=settings["temperature"],
    ).bind_tools(_admin_tools_for_state(state))

    chain = ADMIN_PROMPT | llm
    response = chain.invoke({
        "messages": sanitize_messages(state["messages"]),
        "admin_context": _admin_context(state),
    })

    update = {
        "messages": [response],
        "final_response": response.content if not response.tool_calls else None,
        "last_admin_activity_at": time.time(),
    }

    if pending_tool_update:
        update.update(pending_tool_update)

    return update
