from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from langgraph.prebuilt import ToolNode
from dental_agent.config.features import load_global_features
from dental_agent.config.settings import get_chat_groq
from dental_agent.config.runtime import get_graph_settings
from dental_agent.models.state import AppointmentState
from dental_agent.tools.storage_factory import build_cancellation_tools
from dental_agent.utils import sanitize_messages

CANCEL_TOOLS = build_cancellation_tools()

CANCEL_SYSTEM = """You are the Cancellation Agent for a dental appointment management system.

Your ONLY job is to cancel existing appointments.

## Workflow
1. Collect REQUIRED information:
   - patient_id  : numeric patient ID
   - date_slot   : the specific slot to cancel in M/D/YYYY H:MM format

2. If the patient does not know the exact slot, call get_patient_appointments(patient_id)
   to list their bookings, then ask which one to cancel.

3. Confirm with the user before proceeding:
   "Are you sure you want to cancel the appointment at {{date_slot}} with {{doctor_name}}? (yes/no)"

4. On user confirmation, call cancel_appointment(patient_id, date_slot).

5. Inform the user of the outcome.

## Rules
- Always confirm before cancelling — ask "yes/no" explicitly.
- If the patient has no appointments, inform them kindly.
- Do NOT cancel if the patient_id does not match the booking.
- If the user already confirmed in their message (e.g. "yes, cancel it"), skip asking again.

## Date Format
M/D/YYYY H:MM (e.g., 5/8/2026 8:30)
"""

CANCEL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", CANCEL_SYSTEM),
    ("placeholder", "{messages}"),
])

cancellation_tool_node = ToolNode(tools=CANCEL_TOOLS)


def cancellation_agent_node(state: AppointmentState) -> dict:
    global_features = state.get("global_enabled_features") or load_global_features()
    if not global_features.get("cancel_appointment", True):
        message = "This feature is disabled globally by admin: cancel_appointment"
        return {
            "messages": [AIMessage(content=message)],
            "final_response": message,
        }

    settings = get_graph_settings()
    llm = get_chat_groq(
        api_key=settings["api_key"],
        model_name=settings["model_name"],
        temperature=settings["temperature"],
    ).bind_tools(CANCEL_TOOLS)

    chain = CANCEL_PROMPT | llm
    response = chain.invoke({"messages": sanitize_messages(state["messages"])})
    return {
        "messages": [response],
        "final_response": response.content if not response.tool_calls else None,
    }


