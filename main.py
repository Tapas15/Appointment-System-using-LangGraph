"""
Dental Appointment System — powered by LangGraph + Groq
"""

from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage, AIMessageChunk
from dental_agent.workflows.graph import dental_graph

BANNER = """
╔══════════════════════════════════════════════════════════╗
║         Dental Appointment Management System             ║
║         Powered by LangGraph + Groq                       ║
╚══════════════════════════════════════════════════════════╝
Available commands:
  • Show available slots for an orthodontist
  • Show general_dentist slots on 7/8/2026
  • Which doctors are available on 7/8/2026?
  • Which doctors are cosmetic_dentists?
  • Show Emily Johnson's available schedule
  • Book patient 1000082 with Emily Johnson on 5/10/2026 9:00
  • Cancel appointment for patient 1000082 at 5/10/2026 9:00
  • Reschedule patient 1000082 from 5/10/2026 9:00 to 5/12/2026 10:00
  • Doctor login: I am doctor
  • Doctor: block John Doe slot on 5/10/2026 9:00 with password doctor123
  • Admin login: admin login user_id admin password admin123
  • Admin: list features
  • Admin: enable feature book_appointment
  • Admin: disable feature cancel_appointment
  • Admin: disable feature doctor_block_slot
  • Admin: book patient 1000082 with Emily Johnson on 5/10/2026 9:00
  • Admin: block John Doe slot on 5/10/2026 9:00
  • Admin logout: logout
  • What appointments does patient 1000048 have?

Type 'quit' to exit.
"""


def run():
    print(BANNER)
    history = []
    state_snapshot = {"messages": history}

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        normalized = user_input.lower()

        if normalized in {"quit", "exit", "bye"}:
            print("Goodbye!")
            break


        history.append(HumanMessage(content=user_input))

        print("\nAgent: ", end="", flush=True)
        final_messages = None

        try:
            for event_type, data in dental_graph.stream(
                state_snapshot,
                stream_mode=["messages", "values"],
                config={"recursion_limit": 20},
            ):
                if event_type == "messages":
                    chunk, meta = data
                    if (
                        isinstance(chunk, AIMessageChunk)
                        and chunk.content
                        and not getattr(chunk, "tool_calls", None)
                    ):
                        print(chunk.content, end="", flush=True)
                elif event_type == "values":
                    final_messages = data.get("messages", [])
                    state_snapshot = data
        except Exception as exc:
            print(f"\nError: {exc}")
            history.pop()
            continue

        print()
        if final_messages:
            state_snapshot["messages"] = final_messages
            history = final_messages


if __name__ == "__main__":
    run()
