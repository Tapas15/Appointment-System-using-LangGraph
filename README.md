---
title: Dental Appointment
sdk: docker
pinned: false
---

# Dental Appointment Management System

A conversational dental appointment management system built with LangGraph and Groq. The application uses a multi-agent graph to route patient requests to specialized agents for availability lookup, booking, cancellation, and rescheduling.

## Features

- Search available appointment slots by specialization, doctor, or date.
- List doctors by specialization or by available slots on a date.
- Book appointments only after checking slot availability.
- Cancel booked appointments.
- Reschedule appointments to available slots with the same doctor.
- Keep appointment data in a CSV file for simple local development.

## Architecture

The system uses a LangGraph workflow with a supervisor agent that routes each user message to the correct specialist agent.

```text
User
  │
  ▼
Supervisor ── intent classification and routing
  │
  ├── Info Agent ───────── queries about slots, doctors, and appointments
  ├── Booking Agent ────── collects details and books appointments
  ├── Cancellation Agent ─ cancels booked appointments
  └── Rescheduling Agent ─ moves appointments to new available slots
```

### Agent Responsibilities

| Agent | Responsibility |
| --- | --- |
| Supervisor | Detects intent and routes to the correct agent. |
| Info Agent | Answers availability, doctor, and appointment lookup queries. |
| Booking Agent | Collects patient ID, doctor, specialization, and date/time, then books the appointment. |
| Cancellation Agent | Finds booked appointments and cancels them after confirmation. |
| Rescheduling Agent | Moves an existing appointment to a new available slot. |

## Technology Stack

- Python 3.10+
- LangGraph
- LangChain
- Groq LLM through `langchain-groq`
- Pandas for CSV-based data handling
- Pydantic for structured routing decisions
- `python-dotenv` for local environment configuration

## Project Structure

```text
Appointment-System-using-LangGraph/
├── main.py
├── doctor_availability.csv
├── requirements.txt
├── data_/
│   ├── doctor_availability.csv
│   ├── doctor_availability1.csv
│   └── doctors.csv
└── dental_agent/
    ├── agent.py
    ├── utils.py
    ├── agents/
    │   ├── supervisor.py
    │   ├── info_agent.py
    │   ├── booking_agent.py
    │   ├── cancellation_agent.py
    │   └── rescheduling_agent.py
    ├── config/
    │   └── settings.py
    ├── models/
    │   └── state.py
    ├── tools/
    │   ├── csv_reader.py
    │   └── csv_writer.py
    └── workflows/
        └── graph.py
```

The active appointment data file is `doctor_availability.csv` in the project root.

## Installation

### 1. Clone and open the project

```bash
cd Appointment-System-using-LangGraph
```

### 2. Create and activate a virtual environment

Windows:

```bash
python -m venv myenv
myenv\Scripts\activate
```

macOS/Linux:

```bash
python -m venv myenv
source myenv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root. Do not commit this file.

```env
GROQ_API_KEY=your_groq_api_key_here
MODEL_NAME=openai/gpt-oss-120b
TEMPERATURE=0
```

## Usage

Start the CLI:

```bash
python main.py
```

Type `quit`, `exit`, or `bye` to stop the application.

## Example Commands

Show available orthodontist slots:

```text
Show available slots for an orthodontist
```

Show slots for a doctor on a specific date:

```text
Show Emily Johnson's available schedule
```

Show general dentist slots on a date:

```text
Show general_dentist slots on 7/8/2026
```

List doctors by specialization:

```text
Which doctors are cosmetic_dentists?
```

Book an appointment:

```text
Book patient 1000082 with Emily Johnson on 5/10/2026 9:00
```

Cancel an appointment:

```text
Cancel appointment for patient 1000082 at 5/10/2026 9:00
```

Reschedule an appointment:

```text
Reschedule patient 1000082 from 5/10/2026 9:00 to 5/12/2026 10:00
```

Check a patient's appointments:

```text
What appointments does patient 1000048 have?
```

## Supported Specializations

- `general_dentist`
- `oral_surgeon`
- `orthodontist`
- `cosmetic_dentist`
- `prosthodontist`
- `pediatric_dentist`
- `emergency_dentist`

## Data Model

Appointment data is stored in `doctor_availability.csv`.

| Field | Description |
| --- | --- |
| `date_slot` | Appointment date and time in `M/D/YYYY H:MM` format. |
| `specialization` | Dental specialization. |
| `doctor_name` | Doctor name. |
| `is_available` | `TRUE` for open slots and `FALSE` for booked slots. |
| `patient_to_attend` | Patient ID for booked slots. Empty for available slots. |

## Booking Rules

- The booking agent checks availability before creating an appointment.
- A slot must be available before it can be booked.
- Cancellation requires a patient ID and exact appointment time.
- Rescheduling requires the existing appointment, new date/time, and doctor name.
- Date and time values should use `M/D/YYYY H:MM`, for example `5/10/2026 9:00`.

## Git Ignore Rules

The repository ignores these local files and generated files:

- `.env`
- `myenv/`
- `__pycache__/`
- `*.pyc`

Do not commit API keys, virtual environments, or Python cache files.

## Troubleshooting

### Missing API key

If the app fails with an API key error, add this to `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### Missing package

If Python reports `ModuleNotFoundError: No module named 'langchain_xai'`, reinstall dependencies:

```bash
pip install -r requirements.txt
```

### CSV date errors

Do not manually change `date_slot` values unless they follow `M/D/YYYY H:MM` format.
