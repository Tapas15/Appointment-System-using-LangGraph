from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import ToolNode

from dental_agent.config.settings import get_chat_groq
from dental_agent.config.runtime import get_graph_settings
from dental_agent.models.state import AppointmentState
from dental_agent.tools.csv_doctor import (
    doctor_add_availability,
    doctor_block_time_slot,
    doctor_update_schedule,
)
from dental_agent.utils import sanitize_messages

DOCTOR_TOOLS = [
    doctor_add_availability,
    doctor_block_time_slot,
    doctor_update_schedule,
]

DOCTOR_SYSTEM = """You are the Doctor Agent.

Your ONLY job is to help authenticated doctors manage their own availability.

You can:
1. Add availability
2. Update schedule
3. Block time slots

Doctor authentication rules:
- Before calling any doctor tool, ask for the doctor name and password if they are missing.
- Verify the doctor name and password through the doctor tool arguments.
- Do not call doctor tools until the user provides both doctor name and password.
- A doctor can only update slots where doctor_name matches the authenticated doctor.

Schedule rules:
- Available slot: is_available = TRUE and patient_to_attend is empty.
- Patient booked slot: is_available = FALSE and patient_to_attend has a patient ID.
- Doctor blocked slot: is_available = FALSE and patient_to_attend is empty.
- Never change a slot that already has a patient booking.
- Never reveal or repeat doctor passwords.
- If authentication fails, stop and tell the user they are not authorized.

Do not handle patient booking, cancellation, or rescheduling. Route those requests back to the supervisor by giving a normal assistant response.
"""

DOCTOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", DOCTOR_SYSTEM),
    ("placeholder", "{messages}"),
])

doctor_tool_node = ToolNode(tools=DOCTOR_TOOLS)


def doctor_agent_node(state: AppointmentState) -> dict:
    settings = get_graph_settings()
    llm = get_chat_groq(
        api_key=settings["api_key"],
        model_name=settings["model_name"],
        temperature=settings["temperature"],
    ).bind_tools(DOCTOR_TOOLS)

    chain = DOCTOR_PROMPT | llm
    response = chain.invoke({"messages": sanitize_messages(state["messages"])})

    return {
        "messages": [response],
        "final_response": response.content if not response.tool_calls else None,
    }
