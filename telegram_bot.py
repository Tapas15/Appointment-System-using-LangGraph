import asyncio
import os
import sys
import logging
import time
import hashlib
import re
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessageChunk, HumanMessage
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from dental_agent.storage.repository import get_active_backend
from dental_agent.workflows.graph import dental_graph

# Configure LangSmith tracing for token usage/debugging
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "dental-bot"

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

SESSIONS: dict[int, dict] = {}
MESSAGE_CACHE: dict[str, str] = {}

TOKEN_LOG_FILE = "token_usage.log"


def log_token_usage(chat_id: int, user_message: str, total_tokens: int, latency_ms: int) -> None:
    timestamp = datetime.utcnow().isoformat()
    with open(TOKEN_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} chat_id={chat_id} tokens={total_tokens} latency={latency_ms} msg={repr(user_message[:50])}\n")

INTENTS = {
    "book_appointment": ["book", "appointment", "schedule", "dentist"],
    "clinic_address": ["address", "location", "where", "clinic"],
    "doctor_list": ["doctor", "dentist", "available"],
    "timing": ["time", "open", "close", "hours"],
    "cancel_appointment": ["cancel", "reschedule", "change appointment"],
}

INTENT_REPLIES = {
    "book_appointment": "Sure, please tell me your preferred date and time.",
    "clinic_address": "Our clinic is located at Example Road, City.",
    "doctor_list": "Available doctors are Dr. A, Dr. B, and Dr. C.",
    "timing": "We are open Monday to Saturday, 10 AM to 8 PM.",
    "cancel_appointment": "Please share your appointment date and phone number.",
}

SESSIONS: dict[int, dict] = {}


def normalize_content(content) -> str:
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


def normalize_message_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def make_cache_key(text: str) -> str:
    normalized = normalize_message_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def detect_intent(text: str) -> str | None:
    normalized = normalize_message_text(text)
    for intent, keywords in INTENTS.items():
        if any(keyword in normalized for keyword in keywords):
            return intent
    return None


def get_session(chat_id: int) -> dict:
    if chat_id not in SESSIONS:
        SESSIONS[chat_id] = {"messages": []}
    return SESSIONS[chat_id]


async def stream_agent_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    state = get_session(chat_id)
    user_message = state["messages"][-1].content if state["messages"] else ""

    # Check exact cache
    cache_key = make_cache_key(user_message)
    if cache_key in MESSAGE_CACHE:
        reply = MESSAGE_CACHE[cache_key]
        await update.message.reply_text(reply)
        return

    # Check intent routing
    intent = detect_intent(user_message)
    if intent and intent in INTENT_REPLIES:
        reply = INTENT_REPLIES[intent]
        await update.message.reply_text(reply)
        MESSAGE_CACHE[cache_key] = reply
        return

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    full_response = ""
    final_messages = None
    start_time = time.time()

    try:
        async for event_type, data in dental_graph.astream(
            state,
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
                    text = normalize_content(chunk.content)
                    if text:
                        full_response += text
                        await update.message.reply_text(text)
            elif event_type == "values":
                final_messages = data.get("messages", [])
                state = data
                usage = data.get("usage")
                if usage:
                    total_tokens = usage.get("total_tokens", 0)
                    log_token_usage(chat_id, user_message, total_tokens, 0)

        if final_messages:
            state["messages"] = final_messages
            SESSIONS[chat_id] = state

        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "Response sent chat_id=%s latency=%sms",
            chat_id,
            latency_ms,
        )

        if not full_response:
            await update.message.reply_text("No response generated.")
        else:
            MESSAGE_CACHE[cache_key] = full_response

    except Exception as exc:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.exception("LangGraph failed chat_id=%s latency=%sms", chat_id, latency_ms)
        await update.message.reply_text(f"Error: {exc}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Dental Appointment Bot is ready.\n\n"
        "Ask about slots, doctors, booking, cancellation, rescheduling, "
        "doctor login, or admin login."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Commands:\n"
        "/start - Show welcome message\n"
        "/reset - Clear this chat history\n"
        "/backend - Show active storage backend\n"
        "/help - Show this help\n\n"
        "Examples:\n"
        "Show available orthodontist slots\n"
        "Book patient 1000082 with Emily Johnson on 5/10/2026 9:00\n"
        "I am doctor\n"
        "I am a admin, here is my password admin123"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    SESSIONS[chat_id] = {"messages": []}
    await update.message.reply_text("Chat history cleared.")


async def backend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Active storage backend: {get_active_backend()}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if not text:
        return

    state = get_session(update.effective_chat.id)
    state["messages"].append(HumanMessage(content=text))

    await stream_agent_response(update, context)


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is missing. Add it to .env.")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("clear", reset))
    application.add_handler(CommandHandler("backend", backend))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
