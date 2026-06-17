import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root
CSV_PATH = str(BASE_DIR / "doctor_availability.csv")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-oss-120b")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))

VALID_SPECIALIZATIONS = [
    "general_dentist",
    "oral_surgeon",
    "orthodontist",
    "cosmetic_dentist",
    "prosthodontist",
    "pediatric_dentist",
    "emergency_dentist",
]

ADMIN_USERS = {
    "admin": os.getenv("ADMIN_PASSWORD", "admin123"),
    "superadmin": os.getenv("SUPERADMIN_PASSWORD", "superadmin123"),
}

VALID_DOCTORS = [
    "john doe",
    "emily johnson",
    "sarah wilson",
    "jane smith",
    "michael green",
    "robert martinez",
    "lisa brown",
    "susan davis",
    "daniel miller",
    "kevin anderson",
]

DEFAULT_DOCTOR_PASSWORD = os.getenv("DEFAULT_DOCTOR_PASSWORD", "doctor123")
DOCTOR_PASSWORDS = {
    doctor_name.lower(): DEFAULT_DOCTOR_PASSWORD
    for doctor_name in VALID_DOCTORS
}

DATE_FORMAT = "%m/%d/%Y %H:%M"


def get_chat_groq(
    api_key: str | None = None,
    model_name: str | None = None,
    temperature: float | None = None,
):
    from langchain_groq import ChatGroq

    return ChatGroq(
        api_key=api_key or GROQ_API_KEY,
        model=model_name or MODEL_NAME,
        temperature=TEMPERATURE if temperature is None else temperature,
    )
