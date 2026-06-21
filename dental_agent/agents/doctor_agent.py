import re
import time
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import ToolNode

from dental_agent.config.features import (
    disabled_global_feature_for_request,
    load_global_features,
)
from dental_agent.config.settings import get_chat_groq
from dental_agent.config.runtime import get_graph_settings
from dental_agent.models.state import AppointmentState
from dental_agent.tools.storage_factory import build_doctor_tools
from dental_agent.utils import sanitize_messages

DOCTOR_SESSION_TIMEOUT_SECONDS = 15 * 60

DOCTOR_TOOLS = build_doctor_tools()

DOCTOR_SYSTEM = f"""You are the Doctor Agent for a dental appointment system.

Your job is to help an authenticated doctor manage their own schedule.

Session rules:
- The supervisor routes to this agent when the user wants doctor mode, doctor login, doctor logout, add availability, block slots, or update schedule.
- Doctor session timeout is {DOCTOR_SESSION_TIMEOUT_SECONDS} seconds.
- If the user says logout, log out, sign out, or exit doctor mode, return these state updates:
  session_role = "patient"
  authenticated_doctor = None
  authenticated_doctor_password = None
  doctor_session_started_at = None
  last_doctor_activity_at = None
  Then tell the user they are back in patient mode.
- If the doctor session has expired due to inactivity, return the same logout state updates and tell the user the session expired.
- If the user is not authenticated, ask for doctor name and password before calling doctor tools.
- If the user provides both doctor name and password, call doctor_login first.
- If doctor_login succeeds, return these state updates:
  session_role = "doctor"
  authenticated_doctor = the doctor name
  authenticated_doctor_password = the password used for login
  doctor_session_started_at = current Unix timestamp
  last_doctor_activity_at = current Unix timestamp
  Then confirm that the doctor is logged in.
- If doctor_login fails, tell the user they are not authorized and do not update the session.
- If session_role is "doctor" and authenticated_doctor is already set, do NOT call doctor_login again. Use the existing authenticated_doctor and authenticated_doctor_password for doctor tools.
- Once logged in, keep using authenticated_doctor and authenticated_doctor_password for doctor tools.
- Do not reveal or repeat doctor passwords.

Doctor work allowed after login:
- Add or restore availability for one slot
- Add or restore availability for multiple dates and times in one request
- Block time slots
- Update unbooked schedule slots
- Answer questions about the doctor's own schedule management

Patient work is not allowed while logged in as a doctor:
- Do not book patient appointments.
- Do not cancel patient appointments.
- Do not reschedule patient appointments.
- Do not show general patient availability as a doctor-mode response.
- If the logged-in doctor asks for patient work, tell them to log out first.

Schedule rules:
- Available slot: is_available = TRUE and patient_to_attend is empty.
- Patient booked slot: is_available = FALSE and patient_to_attend has a patient ID.
- Doctor blocked slot: is_available = FALSE and patient_to_attend is empty.
- For bulk availability, create hourly slots by default unless the user asks for another interval.
- If the user gives multiple dates and a time range, call doctor_add_availability_bulk.
- Never change a slot that already has a patient booking.
"""

DOCTOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", DOCTOR_SYSTEM + "\n\nCurrent session context:\n{session_context}"),
    ("placeholder", "{messages}"),
])

doctor_tool_node = ToolNode(tools=DOCTOR_TOOLS)


def _last_message_text(state: AppointmentState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return ""
    return str(getattr(messages[-1], "content", ""))


def _disabled_global_doctor_feature(state: AppointmentState) -> str | None:
    text = _last_message_text(state)
    normalized = text.strip().lower()

    if _is_logout_request(text):
        return None
    if normalized in {"i am doctor", "doctor login", "login", "log in"}:
        return None
    if state.get("session_role") == "doctor" and _is_patient_availability_request(text):
        return None

    return disabled_global_feature_for_request(
        state.get("global_enabled_features") or load_global_features(),
        text,
        "doctor",
    )




def _reset_doctor_session(message: str) -> dict:
    return {
        "messages": [AIMessage(content=message)],
        "session_role": "patient",
        "authenticated_doctor": None,
        "authenticated_doctor_password": None,
        "doctor_session_started_at": None,
        "last_doctor_activity_at": None,
        "final_response": message,
    }


def _session_context(state: AppointmentState) -> str:
    session_role = state.get("session_role") or "patient"
    authenticated_doctor = state.get("authenticated_doctor") or "None"
    password_status = "set" if state.get("authenticated_doctor_password") else "not set"
    started_at = state.get("doctor_session_started_at") or "None"
    last_activity_at = state.get("last_doctor_activity_at") or "None"
    return (
        f"session_role: {session_role}\n"
        f"authenticated_doctor: {authenticated_doctor}\n"
        f"authenticated_doctor_password: {password_status}\n"
        f"doctor_session_started_at: {started_at}\n"
        f"last_doctor_activity_at: {last_activity_at}\n"
        f"doctor_session_timeout_seconds: {DOCTOR_SESSION_TIMEOUT_SECONDS}"
    )




def _is_patient_availability_request(text: str) -> bool:
    normalized = text.strip().lower()
    if not normalized:
        return False

    doctor_management_phrases = [
        "add availability",
        "restore availability",
        "block slot",
        "block time",
        "update schedule",
        "change schedule",
        "doctor schedule",
        "my schedule",
        "my availability",
    ]
    if any(phrase in normalized for phrase in doctor_management_phrases):
        return False

    patient_availability_phrases = [
        "check availability",
        "available slots",
        "availability for",
        "date range",
        "which doctors are available",
        "show slots",
        "show availability",
        "patient availability",
        "appointment slots",
        "open slots",
    ]
    if any(phrase in normalized for phrase in patient_availability_phrases):
        return True

    date_only_patterns = [
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
        r"\b(jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b",
        r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b",
        r"\b(today|tomorrow|next week|this week|weekend)\b",
    ]
    if any(re.search(pattern, normalized) for pattern in date_only_patterns):
        return True

    return False

def _is_logout_request(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in {
        "logout",
        "log out",
        "doctor logout",
        "doctor log out",
        "sign out",
        "exit doctor mode",
        "logout doctor mode",
    }


def _is_doctor_session_expired(state: AppointmentState) -> bool:
    if state.get("session_role") != "doctor":
        return False

    last_activity = state.get("last_doctor_activity_at")
    if not last_activity:
        return False

    return (time.time() - float(last_activity)) > DOCTOR_SESSION_TIMEOUT_SECONDS


def _has_unavailable_tool_call(response) -> bool:
    allowed_tool_names = {tool.name for tool in DOCTOR_TOOLS}
    for tool_call in getattr(response, "tool_calls", []) or []:
        if tool_call.get("name") not in allowed_tool_names:
            return True
    return False


def doctor_agent_node(state: AppointmentState) -> dict:
    if _is_logout_request(_last_message_text(state)):
        return _reset_doctor_session("Logged out. You are back in patient mode.")

    if _is_doctor_session_expired(state):
        return _reset_doctor_session(
            "Your doctor session expired due to 15 minutes of inactivity. You are back in patient mode."
        )


    if state.get("session_role") == "doctor" and _is_patient_availability_request(_last_message_text(state)):
        message = "You are currently in doctor mode. Type logout to return to patient mode and check patient availability."
        return {
            "messages": [AIMessage(content=message)],
            "last_doctor_activity_at": time.time(),
            "final_response": message,
        }

    disabled_feature = _disabled_global_doctor_feature(state)
    if disabled_feature:
        message = f"This feature is disabled globally by admin: {disabled_feature}"
        return {
            "messages": [AIMessage(content=message)],
            "last_doctor_activity_at": time.time(),
            "final_response": message,
        }

    settings = get_graph_settings()
    llm = get_chat_groq(
        api_key=settings["api_key"],
        model_name=settings["model_name"],
        temperature=settings["temperature"],
    ).bind_tools(DOCTOR_TOOLS)

    chain = DOCTOR_PROMPT | llm

    if state.get("session_role") == "doctor" and state.get("authenticated_doctor"):
        normalized = _last_message_text(state).strip().lower()
        if normalized in {"i am doctor", "doctor login", "login", "log in"}:
            doctor_name = state.get("authenticated_doctor")
            message = f"Already logged in as {doctor_name}."
            return {
                "messages": [AIMessage(content=message)],
                "last_doctor_activity_at": time.time(),
                "final_response": message,
            }

    response = chain.invoke({
        "messages": sanitize_messages(state["messages"]),
        "session_context": _session_context(state),
    })

    if _has_unavailable_tool_call(response):
        message = "You are currently in doctor mode. Type logout to return to patient mode and check patient availability."
        return {
            "messages": [AIMessage(content=message)],
            "last_doctor_activity_at": time.time(),
            "final_response": message,
        }

    update = {
        "messages": [response],
        "final_response": response.content if not response.tool_calls else None,
    }

    if state.get("session_role") == "doctor" and state.get("authenticated_doctor"):
        update["last_doctor_activity_at"] = time.time()

    return update

