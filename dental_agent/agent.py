from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from dental_agent.config.settings import GROQ_API_KEY, MODEL_NAME, TEMPERATURE
from dental_agent.tools.storage_factory import (
    build_booking_tools,
    build_cancellation_tools,
    build_info_tools,
    build_rescheduling_tools,
)
from dental_agent.utils import sanitize_messages


def _dedupe_tools(tool_groups: list[list]) -> list:
    tools = []
    seen = set()
    for group in tool_groups:
        for tool in group:
            name = getattr(tool, "name", str(tool))
            if name in seen:
                continue
            tools.append(tool)
            seen.add(name)
    return tools


TOOLS = _dedupe_tools([
    build_info_tools(),
    build_booking_tools(),
    build_cancellation_tools(),
    build_rescheduling_tools(),
])

SYSTEM_PROMPT = """You are a helpful dental appointment assistant. You help patients with:

1. Checking available appointment slots and doctor information
2. Booking new appointments
3. Cancelling existing appointments
4. Rescheduling appointments

## Available Tools
- get_available_slots(specialization, doctor_name, date_filter) — find open slots
- get_patient_appointments(patient_id) — look up a patient's bookings
- check_slot_availability(doctor_name, date_slot) — verify a specific slot
- list_doctors_by_specialization(specialization) — list doctors in a specialty
- get_available_doctors_by_date(date_filter) — doctors with available slots on a date

## Available Specializations
general_dentist, oral_surgeon, orthodontist, cosmetic_dentist,
prosthodontist, pediatric_dentist, emergency_dentist

## Date Format
Always use M/D/YYYY H:MM format — e.g. 5/10/2026 9:00

## Booking Rules
- Always call check_slot_availability before booking to confirm the slot is free
- If a slot is taken, call get_available_slots to suggest alternatives
- Always confirm cancellations before executing them
- Ask for one missing detail at a time — don't overwhelm the user
"""


def _pre_model_hook(state: dict) -> dict:
    """
    Runs as a dedicated graph node before every LLM call in the react loop.

    This hook sanitizes all message types and prepends the system prompt,
    returning them via `llm_input_messages` so the stored state is never mutated.
    """
    sanitized = sanitize_messages(state["messages"])
    return {"llm_input_messages": [SystemMessage(content=SYSTEM_PROMPT)] + sanitized}


def create_dental_graph(api_key: str | None = None, model_name: str | None = None, temperature: float = TEMPERATURE):
    resolved_api_key = api_key or GROQ_API_KEY
    if not resolved_api_key:
        raise ValueError("GROQ_API_KEY is required. Add it in the Streamlit sidebar or Hugging Face Space secrets.")
    llm = ChatGroq(api_key=resolved_api_key, model=model_name or MODEL_NAME, temperature=temperature)
    return create_react_agent(model=llm, tools=TOOLS, pre_model_hook=_pre_model_hook)


dental_graph = create_dental_graph() if GROQ_API_KEY else None
