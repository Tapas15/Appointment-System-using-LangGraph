import json
import re
import time

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import ToolNode

from dental_agent.config.features import (
    DOCTOR_FEATURES,
    PATIENT_FEATURES,
    PROTECTED_FEATURES,
    feature_category,
    load_global_features,
    save_global_features,
)
from dental_agent.config.runtime import get_graph_settings
from dental_agent.config.settings import get_chat_groq
from dental_agent.models.state import AppointmentState
from dental_agent.tools.storage_factory import (
    get_admin_feature_tools,
    get_admin_operation_tool_map,
)
from dental_agent.utils import sanitize_messages

ADMIN_SESSION_TIMEOUT_SECONDS = 15 * 60

ADMIN_SYSTEM = """You are the Admin Agent for a dental appointment management system.

You operate under the supervisor and support both patient-facing appointment work and doctor schedule-management work when those features are enabled.

Rules:
- Admin must login first with admin_user_id and password.
- After successful admin login, all individual admin features are enabled by default.
- Admin can enable or disable each individual feature by exact feature name.
- Feature changes apply globally to patient, doctor, and admin modes.
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

admin_tool_node = ToolNode(tools=get_admin_feature_tools() + list(get_admin_operation_tool_map().values()))


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
    global_patient_features = bool(state.get("global_patient_features_enabled"))
    global_doctor_features = bool(state.get("global_doctor_features_enabled"))
    started_at = state.get("admin_session_started_at") or "None"
    last_activity = state.get("last_admin_activity_at") or "None"
    enabled_features = ", ".join(sorted(
        feature_name
        for feature_name, enabled in (state.get("admin_enabled_features") or {}).items()
        if enabled
    )) or "None"
    global_enabled_features = ", ".join(sorted(
        feature_name
        for feature_name, enabled in (state.get("global_enabled_features") or {}).items()
        if enabled
    )) or "None"

    return (
        f"admin_session_role: {role}\n"
        f"authenticated_admin: {admin}\n"
        f"admin_patient_features_enabled: {patient_features}\n"
        f"admin_doctor_features_enabled: {doctor_features}\n"
        f"global_patient_features_enabled: {global_patient_features}\n"
        f"global_doctor_features_enabled: {global_doctor_features}\n"
        f"enabled_features: {enabled_features}\n"
        f"global_enabled_features: {global_enabled_features}\n"
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


def _is_simple_admin_login_request(text: str) -> bool:
    normalized = text.strip().lower()
    return any(
        phrase in normalized
        for phrase in [
            "i am admin",
            "i am a admin",
            "im admin",
            "im a admin",
            "i am the admin",
            "login as admin",
            "admin login",
        ]
    )


def _extract_admin_password(text: str) -> str | None:
    normalized = text.strip().lower()
    patterns = [
        r"password\s+is\s+([^\s.]+)",
        r"password\s*:?\s*([^\s.]+)",
        r"my\s+password\s+is\s+([^\s.]+)",
        r"here\s+is\s+my\s+password\s+([^\s.]+)",
        r"admin\s+password\s+([^\s.]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return match.group(1)

    return None


def _admin_login_tool_call(password: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": admin_login.name,
                "args": {
                    "admin_user_id": "admin",
                    "password": password,
                },
                "id": "call_admin_login",
                "type": "tool_call",
            }
        ],
    )


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
            "i am admin",
            "i am a admin",
            "im admin",
            "im a admin",
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


def _global_feature_enabled(state: AppointmentState, feature_name: str) -> bool:
    features = state.get("global_enabled_features") or load_global_features()
    return bool(features.get(feature_name, True))


def _admin_action_allowed(state: AppointmentState, feature_name: str) -> bool:
    return _feature_enabled(state, feature_name) and _global_feature_enabled(state, feature_name)


def _feature_state_updates(features: dict[str, bool]) -> dict:
    return {
        "admin_enabled_features": features,
        "admin_patient_features_enabled": any(features.get(feature, False) for feature in PATIENT_FEATURES),
        "admin_doctor_features_enabled": any(features.get(feature, False) for feature in DOCTOR_FEATURES),
        "global_enabled_features": features,
        "global_patient_features_enabled": any(features.get(feature, False) for feature in PATIENT_FEATURES),
        "global_doctor_features_enabled": any(features.get(feature, False) for feature in DOCTOR_FEATURES),
        "last_admin_activity_at": time.time(),
    }


def _set_feature_state(state: AppointmentState, feature_name: str, enabled: bool) -> dict:
    features = dict(state.get("admin_enabled_features") or load_global_features())
    features[feature_name] = enabled

    global_features = dict(state.get("global_enabled_features") or load_global_features())
    global_features[feature_name] = enabled

    try:
        save_global_features(global_features)
    except OSError as exc:
        return {
            "messages": [AIMessage(content=f"Could not save global feature settings: {exc}")],
            "last_admin_activity_at": time.time(),
        }

    return {
        **_feature_state_updates(features),
        "global_enabled_features": global_features,
        "global_patient_features_enabled": any(global_features.get(feature, False) for feature in PATIENT_FEATURES),
        "global_doctor_features_enabled": any(global_features.get(feature, False) for feature in DOCTOR_FEATURES),
    }


def _set_category_feature_state(state: AppointmentState, category: str, enabled: bool) -> dict:
    features = dict(state.get("admin_enabled_features") or load_global_features())
    global_features = dict(state.get("global_enabled_features") or load_global_features())

    category_features = PATIENT_FEATURES if category == "patient" else DOCTOR_FEATURES
    for feature_name in category_features:
        features[feature_name] = enabled
        global_features[feature_name] = enabled

    try:
        save_global_features(global_features)
    except OSError as exc:
        return {
            "messages": [AIMessage(content=f"Could not save global feature settings: {exc}")],
            "last_admin_activity_at": time.time(),
        }

    return {
        **_feature_state_updates(features),
        "global_enabled_features": global_features,
        "global_patient_features_enabled": any(global_features.get(feature, False) for feature in PATIENT_FEATURES),
        "global_doctor_features_enabled": any(global_features.get(feature, False) for feature in DOCTOR_FEATURES),
    }


def _protected_feature_message(feature_name: str) -> str:
    if feature_category(feature_name) == "admin":
        return "Admin control features cannot be disabled."
    return f"Unknown feature: {feature_name}"


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
        global_features = result.get("global_enabled_features") or load_global_features()
        return {
            "admin_session_role": "admin",
            "authenticated_admin": admin_id,
            "authenticated_admin_password": None,
            "admin_session_started_at": result.get("admin_session_started_at", now),
            "last_admin_activity_at": result.get("last_admin_activity_at", now),
            "admin_patient_features_enabled": bool(result.get("admin_patient_features_enabled", True)),
            "admin_doctor_features_enabled": bool(result.get("admin_doctor_features_enabled", True)),
            "admin_enabled_features": enabled_features,
            "global_patient_features_enabled": any(global_features.get(feature, False) for feature in PATIENT_FEATURES),
            "global_doctor_features_enabled": any(global_features.get(feature, False) for feature in DOCTOR_FEATURES),
            "global_enabled_features": global_features,
        }

    if tool_message.name == admin_enable_patient_features.name:
        return {
            **_set_category_feature_state(state, "patient", True),
            "message": result.get("message"),
        }

    if tool_message.name == admin_disable_patient_features.name:
        return {
            **_set_category_feature_state(state, "patient", False),
            "message": result.get("message"),
        }

    if tool_message.name == admin_enable_doctor_features.name:
        return {
            **_set_category_feature_state(state, "doctor", True),
            "message": result.get("message"),
        }

    if tool_message.name == admin_disable_doctor_features.name:
        return {
            **_set_category_feature_state(state, "doctor", False),
            "message": result.get("message"),
        }

    if tool_message.name == admin_enable_feature.name:
        feature_name = result.get("feature_name")
        if feature_name in ADMIN_FEATURE_DEFINITIONS:
            if feature_name in PROTECTED_FEATURES:
                return {
                    "messages": [AIMessage(content="Admin control features cannot be disabled.")],
                    "last_admin_activity_at": time.time(),
                }
            return {
                **_set_feature_state(state, feature_name, True),
                "message": result.get("message"),
            }

    if tool_message.name == admin_disable_feature.name:
        feature_name = result.get("feature_name")
        if feature_name in ADMIN_FEATURE_DEFINITIONS:
            if feature_name in PROTECTED_FEATURES:
                return {
                    "messages": [AIMessage(content="Admin control features cannot be disabled.")],
                    "last_admin_activity_at": time.time(),
                }
            return {
                **_set_feature_state(state, feature_name, False),
                "message": result.get("message"),
            }

    return {}


def _admin_tools_for_state(state: AppointmentState) -> list:
    features = state.get("admin_enabled_features") or {}
    tools = list(get_admin_feature_tools())
    operation_tools = get_admin_operation_tool_map()

    if state.get("admin_session_role") != "admin":
        return tools

    if features.get("view_available_slots") or features.get("view_slots_by_specialization") or features.get("view_slots_by_doctor") or features.get("view_slots_by_date"):
        tools.append(operation_tools["view_available_slots"])

    if features.get("view_slots_by_date_range"):
        tools.append(operation_tools["view_slots_by_date_range"])

    if features.get("view_availability_summary"):
        tools.append(operation_tools["view_availability_summary"])
        tools.append(operation_tools["view_availability_summary_total"])

    if features.get("view_available_doctors_by_date"):
        tools.append(operation_tools["view_available_doctors_by_date"])

    if features.get("view_doctors_by_specialization"):
        tools.append(operation_tools["view_doctors_by_specialization"])

    if features.get("check_slot_availability") or features.get("book_appointment") or features.get("reschedule_appointment"):
        tools.append(operation_tools["check_slot_availability"])

    if features.get("view_patient_appointments") or features.get("cancel_appointment") or features.get("reschedule_appointment"):
        tools.append(operation_tools["view_patient_appointments"])

    if features.get("book_appointment"):
        tools.append(operation_tools["book_appointment"])

    if features.get("cancel_appointment"):
        tools.append(operation_tools["cancel_appointment"])

    if features.get("reschedule_appointment"):
        tools.append(operation_tools["reschedule_appointment"])

    if features.get("doctor_add_availability"):
        tools.append(operation_tools["doctor_add_availability"])

    if features.get("doctor_block_slot"):
        tools.append(operation_tools["doctor_block_slot"])

    if features.get("doctor_update_schedule"):
        tools.append(operation_tools["doctor_update_schedule"])

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

    if state.get("admin_session_role") != "admin" and _is_simple_admin_login_request(text):
        password = _extract_admin_password(text)
        if not password:
            message = "Please provide your admin password, for example: I am a admin, here is my password admin123"
            return {
                "messages": [AIMessage(content=message)],
                "final_response": message,
            }

        return {
            "messages": [_admin_login_tool_call(password)],
            "final_response": None,
        }

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
        and not _admin_action_allowed(state, required_feature)
    ):
        if not _global_feature_enabled(state, required_feature):
            message = f"This feature is disabled globally by admin: {required_feature}"
        else:
            message = f"This feature is disabled for admin: {required_feature}"
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





