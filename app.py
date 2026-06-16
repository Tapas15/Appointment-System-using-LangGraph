import os

import streamlit as st
from langchain_core.messages import AIMessageChunk, HumanMessage

from dental_agent.config.runtime import configure_graph
from dental_agent.workflows.graph import dental_graph

st.set_page_config(page_title="Dental Appointment Chat", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: #0b0f19;
        color: #e6edf3;
    }
    .stChatMessage,
    .stChatInputContainer textarea,
    .stTextInput input {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }
    .stChatMessage {
        background: #111827;
        border: 1px solid #263244;
        border-radius: 12px;
        padding: 10px 14px;
    }
    .stChatInputContainer {
        border: 1px solid #30363d;
        border-radius: 12px;
        background: #0d1117;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Dental Appointment Chat")
st.caption("Chat with the same LangGraph dental agent used in the terminal.")

with st.sidebar:
    st.header("Model settings")
    api_key_input = st.text_input(
        "Groq API key",
        value=os.getenv("GROQ_API_KEY", ""),
        type="password",
        help="The key is used only in this Streamlit session.",
    )
    model_input = st.text_input("Model", value=os.getenv("MODEL_NAME", "openai/gpt-oss-120b"))

    if st.button("Apply settings", type="primary"):
        st.session_state["api_key"] = api_key_input
        st.session_state["model"] = model_input
        st.session_state["history"] = []
        st.session_state["ui_messages"] = []
        st.rerun()

    if st.button("Clear chat"):
        st.session_state["history"] = []
        st.session_state["ui_messages"] = []
        st.rerun()

if "api_key" not in st.session_state:
    st.session_state["api_key"] = api_key_input
if "model" not in st.session_state:
    st.session_state["model"] = model_input
if "history" not in st.session_state:
    st.session_state["history"] = []
if "ui_messages" not in st.session_state:
    st.session_state["ui_messages"] = []


def normalize_content(content):
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if "text" in item:
                    parts.append(str(item["text"]))
                elif "content" in item:
                    parts.append(str(item["content"]))
        return "".join(parts)
    return str(content)


for message in st.session_state["ui_messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask about available slots, doctors, booking, cancellation, rescheduling, or doctor schedule updates.")

if prompt:
    if not st.session_state["api_key"]:
        st.error("Enter a Groq API key in the sidebar.")
        st.stop()
    if not st.session_state["model"]:
        st.error("Enter a model name in the sidebar.")
        st.stop()

    st.session_state["ui_messages"].append({"role": "user", "content": prompt})
    st.session_state["history"].append(HumanMessage(content=prompt))

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_box = st.empty()
        full_response = ""
        final_messages = None
        configure_graph(
            api_key=st.session_state["api_key"],
            model_name=st.session_state["model"],
            temperature=0,
        )
        graph = dental_graph

        try:
            for event_type, data in graph.stream(
                {"messages": st.session_state["history"]},
                stream_mode=["messages", "values"],
                config={"recursion_limit": 20},
            ):
                if event_type == "messages":
                    chunk, _ = data
                    if (
                        isinstance(chunk, AIMessageChunk)
                        and chunk.content
                        and not getattr(chunk, "tool_calls", None)
                    ):
                        content = normalize_content(chunk.content)
                        if content:
                            full_response += content
                            response_box.markdown(full_response + "▌")
                elif event_type == "values":
                    final_messages = data.get("messages", [])

            response_box.markdown(full_response)

            if final_messages:
                st.session_state["history"] = final_messages
            if full_response:
                st.session_state["ui_messages"].append(
                    {"role": "assistant", "content": full_response}
                )
        except Exception as exc:
            response_box.markdown(f"**Error:** `{exc}`")
            if st.session_state["history"]:
                st.session_state["history"].pop()
