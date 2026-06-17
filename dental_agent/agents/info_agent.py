from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from langgraph.prebuilt import ToolNode
from dental_agent.config.settings import get_chat_groq
from dental_agent.config.runtime import get_graph_settings
from dental_agent.models.state import AppointmentState
from dental_agent.tools.csv_reader import (
    get_available_slots,
    get_patient_appointments,
    check_slot_availability,
    list_doctors_by_specialization,
    get_available_doctors_by_date,
    get_available_slots_range,
    get_specialty_summary,
    get_total_available_doctors,
)
from dental_agent.utils import sanitize_messages

INFO_TOOLS = [
    get_available_slots,
    get_available_slots_range,
    get_specialty_summary,
    get_total_available_doctors,
    get_available_doctors_by_date,
    list_doctors_by_specialization,
    check_slot_availability,
    get_patient_appointments,
]

INFO_SYSTEM = """You are the Information Agent for a dental appointment system.

Your role is to answer queries about doctor availability, schedules, and appointment status.

## Available Tools
- get_available_slots(specialization, doctor_name, date_filter) — find open slots
- get_available_slots_range(start_date, end_date, specialization, doctor_name, limit) — find open slots across a date range
- get_specialty_summary(date_filter) — show total specialties, available doctors, and available slots
- get_total_available_doctors(date_filter, specialization) — show total available doctors and slots
- get_patient_appointments(patient_id) — look up a patient's bookings
- check_slot_availability(doctor_name, date_slot) — verify a specific slot
- list_doctors_by_specialization(specialization) — list doctors in a specialty
- get_available_doctors_by_date(date_filter) — doctors with available slots on a date

## Guidelines
1. Use tools to fetch real data. Never invent slot times or doctor names.
2. If the user has not provided enough parameters, ask a focused clarifying question.
3. Present results in a clear, friendly, numbered list or table.
4. Valid specializations: general_dentist, oral_surgeon, orthodontist, cosmetic_dentist, prosthodontist, pediatric_dentist, emergency_dentist.
5. Handle natural language queries:
   - "Show Emily Johnson's available schedule" → call get_available_slots(doctor_name="emily johnson")
   - "Show Emily Johnson's availability from 7/8/2026 to 7/10/2026" → call get_available_slots_range(start_date="7/8/2026", end_date="7/10/2026", doctor_name="emily johnson")
   - "Which doctors are cosmetic_dentists?" → call list_doctors_by_specialization(specialization="cosmetic_dentist")
   - "Show general_dentist slots on 7/8/2026" → call get_available_slots(specialization="general_dentist", date_filter="7/8/2026")
   - "Which doctors are available on 7/8/2026?" → call get_available_doctors_by_date(date_filter="7/8/2026")
   - "Show total specialties" → call get_specialty_summary()
   - "Show total doctors available on 7/8/2026" → call get_total_available_doctors(date_filter="7/8/2026")
6. Do not reveal patient_to_attend values for other patients.
7. Do not handle doctor schedule management requests such as adding availability, blocking slots, or updating schedules.

## Date Format
All dates follow M/D/YYYY H:MM format (e.g., 5/10/2026 9:00).
"""

INFO_PROMPT = ChatPromptTemplate.from_messages([
    ("system", INFO_SYSTEM),
    ("placeholder", "{messages}"),
])

info_tool_node = ToolNode(tools=INFO_TOOLS)


def info_agent_node(state: AppointmentState) -> dict:
    settings = get_graph_settings()
    llm = get_chat_groq(
        api_key=settings["api_key"],
        model_name=settings["model_name"],
        temperature=settings["temperature"],
    ).bind_tools(INFO_TOOLS)

    chain = INFO_PROMPT | llm
    response = chain.invoke({"messages": sanitize_messages(state["messages"])})
    return {
        "messages": [response],
        "final_response": response.content if not response.tool_calls else None,
    }
