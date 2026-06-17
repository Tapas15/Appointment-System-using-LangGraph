from typing import TypedDict, Annotated, Literal, Optional, List
from langchain_core.messages import BaseMessage
import operator

IntentType = Literal[
    "get_info",
    "book",
    "cancel",
    "reschedule",
    "doctor",
    "admin",
    "unknown",
    "end",
]

RouteTarget = Literal[
    "info_agent",
    "booking_agent",
    "cancellation_agent",
    "rescheduling_agent",
    "doctor_agent",
    "admin_agent",
    "end",
]


class AppointmentState(TypedDict):
    # Conversation history â€” appended by each node, never replaced
    messages: Annotated[List[BaseMessage], operator.add]

    # Supervisor routing
    intent: Optional[IntentType]
    next_agent: Optional[RouteTarget]

    # Session role for mixed patient/doctor/admin chat
    session_role: Optional[Literal["patient", "doctor"]]
    authenticated_doctor: Optional[str]
    authenticated_doctor_password: Optional[str]
    doctor_session_started_at: Optional[float]
    last_doctor_activity_at: Optional[float]

    # Admin session role and feature controls
    admin_session_role: Optional[Literal["admin", "non_admin"]]
    authenticated_admin: Optional[str]
    authenticated_admin_password: Optional[str]
    admin_session_started_at: Optional[float]
    last_admin_activity_at: Optional[float]
    admin_patient_features_enabled: Optional[bool]
    admin_doctor_features_enabled: Optional[bool]
    admin_enabled_features: Optional[dict[str, bool]]

    # User-supplied booking parameters
    patient_id: Optional[str]
    requested_specialization: Optional[str]
    requested_doctor: Optional[str]
    requested_date_slot: Optional[str]

    # Rescheduling: old slot + new desired slot
    current_date_slot: Optional[str]
    new_date_slot: Optional[str]

    # Tool execution results
    available_slots: Optional[List[dict]]
    operation_success: Optional[bool]
    operation_message: Optional[str]

    # Final response assembled by the active agent
    final_response: Optional[str]
