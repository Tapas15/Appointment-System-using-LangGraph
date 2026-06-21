from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from langgraph.prebuilt import ToolNode
from dental_agent.config.features import load_global_features
from dental_agent.config.settings import get_chat_groq
from dental_agent.config.runtime import get_graph_settings
from dental_agent.models.state import AppointmentState
from dental_agent.tools.storage_factory import build_rescheduling_tools
from dental_agent.utils import sanitize_messages

RESCHEDULE_TOOLS = build_rescheduling_tools()

RESCHEDULE_SYSTEM = """You are the Rescheduling Agent for a dental appointment management system.

Your ONLY job is to move an existing appointment to a new time slot.

## Workflow
1. Collect REQUIRED information:
   - patient_id         : numeric patient ID
   - current_date_slot  : the existing appointment to move (M/D/YYYY H:MM)
   - new_date_slot      : the desired new slot (M/D/YYYY H:MM)
   - doctor_name        : doctor name (from the existing booking)

2. If the patient does not know their current slot, call get_patient_appointments(patient_id)
   to list their bookings, then ask which one to reschedule.

3. If the patient does not know the desired new slot, call get_available_slots(doctor_name=...)
   to show options with the same doctor, then let them pick.

4. Call reschedule_appointment(patient_id, current_date_slot, new_date_slot, doctor_name).

5. Confirm the reschedule: old slot → new slot, doctor name.

## Rules
- The new slot is with the SAME doctor by default unless the user explicitly requests a different one.
- If the user wants a different doctor, ask for the new doctor's name and check availability.
- Always show clear confirmation of what changed (old → new).
- If reschedule fails (slot taken, not found), explain why and offer alternatives.

## Date Format
M/D/YYYY H:MM (e.g., 5/10/2026 9:00)
"""

RESCHEDULE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", RESCHEDULE_SYSTEM),
    ("placeholder", "{messages}"),
])

rescheduling_tool_node = ToolNode(tools=RESCHEDULE_TOOLS)


def rescheduling_agent_node(state: AppointmentState) -> dict:
    global_features = state.get("global_enabled_features") or load_global_features()
    if not global_features.get("reschedule_appointment", True):
        message = "This feature is disabled globally by admin: reschedule_appointment"
        return {
            "messages": [AIMessage(content=message)],
            "final_response": message,
        }

    settings = get_graph_settings()
    llm = get_chat_groq(
        api_key=settings["api_key"],
        model_name=settings["model_name"],
        temperature=settings["temperature"],
    ).bind_tools(RESCHEDULE_TOOLS)

    chain = RESCHEDULE_PROMPT | llm
    response = chain.invoke({"messages": sanitize_messages(state["messages"])})
    return {
        "messages": [response],
        "final_response": response.content if not response.tool_calls else None,
    }

