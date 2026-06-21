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
- Store appointment data in CSV or SQLite using one active storage backend switch.

## Architecture

The system uses a LangGraph workflow with a supervisor agent that routes each user message to the correct specialist agent. A `load_global_features` node loads persistent feature flags at the start of every request.

```text
User
   │
   ▼
Supervisor ── intent classification and routing
   │
   ├── Info Agent ───────── queries about slots, doctors, and appointments
   ├── Booking Agent ────── collects details and books appointments
   ├── Cancellation Agent ─ cancels booked appointments
   ├── Rescheduling Agent ─ moves appointments to new available slots
   ├── Doctor Agent ─────── manages doctor schedule (requires doctor login)
   └── Admin Agent ──────── controls features globally, can perform patient/doctor actions
```

### Agent Responsibilities

| Agent | Responsibility |
| --- | --- |
| Supervisor | Detects intent and routes to the correct agent. |
| Info Agent | Answers availability, doctor, and appointment lookup queries. |
| Booking Agent | Collects patient ID, doctor, specialization, and date/time, then books the appointment. |
| Cancellation Agent | Finds booked appointments and cancels them after confirmation. |
| Rescheduling Agent | Moves an existing appointment to a new available slot. |
| Doctor Agent | Manages doctor's own schedule after login (add availability, block slots, update schedule). |
| Admin Agent | Global feature control, patient operations, and doctor schedule management. |

### Global Feature Control

Admin can enable/disable features that apply system-wide:

- Patient features: booking, cancellation, rescheduling, availability lookups
- Doctor features: add availability, block slot, update schedule
- Admin control features are protected (cannot be disabled)

Feature state is persisted in `feature_config.json` and reloaded on every graph run.

## Technology Stack

- Python 3.10+
- LangGraph
- LangChain
- Groq LLM through `langchain-groq`
- Pandas for CSV storage
- SQLite for optional persistent storage
- Pydantic for structured routing decisions
- `python-dotenv` for local environment configuration

## Project Structure

```text
Appointment-System-using-LangGraph/
├── main.py
├── app.py
├── feature_config.json
├── doctor_availability.csv
├── requirements.txt
├── data_/
│   ├── doctor_availability.csv
│   ├── doctor_availability1.csv
│   └── doctors.csv
├── dental_agent/
    ├── utils.py
    ├── storage/
    │   ├── repository.py
    │   └── sqlite_store.py
    ├── config/
    │   ├── settings.py
    │   └── features.py
    ├── models/
    │   └── state.py
    ├── tools/
    │   ├── csv_reader.py
    │   ├── csv_writer.py
    │   ├── csv_admin.py
    │   ├── csv_doctor.py
    │   ├── sqlite_reader.py
    │   ├── sqlite_writer.py
    │   ├── sqlite_admin.py
    │   ├── sqlite_doctor.py
    │   └── storage_factory.py
    ├── agents/
    │   ├── supervisor.py
    │   ├── info_agent.py
    │   ├── booking_agent.py
    │   ├── cancellation_agent.py
    │   ├── rescheduling_agent.py
    │   ├── doctor_agent.py
    │   └── admin_agent.py
    └── workflows/
        └── graph.py
```

Appointment data uses one active backend selected by `STORAGE_BACKEND`:

- `csv` uses `doctor_availability.csv`.
- `sqlite` uses `data/appointments.sqlite3`.

Global feature state is stored in `feature_config.json`.

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
STORAGE_BACKEND=csv
SYNC_CSV_SQLITE=false
```

`STORAGE_BACKEND` is the only active storage switch. Use either `csv` or `sqlite`, not both.

## Storage Backend Switch

The app supports two separate appointment storage modes. Only one mode is active at a time.

### CSV mode

Use CSV for simple local development and manual data inspection:

```env
STORAGE_BACKEND=csv
SYNC_CSV_SQLITE=false
```

In CSV mode:

- Appointment reads use `doctor_availability.csv`.
- Appointment writes update `doctor_availability.csv`.
- SQLite is not used.

### SQLite mode

Use SQLite for persistent local storage:

```env
STORAGE_BACKEND=sqlite
SYNC_CSV_SQLITE=false
```

In SQLite mode:

- Appointment reads use `data/appointments.sqlite3`.
- Appointment writes update `data/appointments.sqlite3`.
- CSV is not modified.

If you are switching from CSV to SQLite for the first time and want to import the existing CSV data once, temporarily set:

```env
SYNC_CSV_SQLITE=true
```

After the SQLite database is populated, set it back to `false` so SQLite remains the only active write target.

Changing `STORAGE_BACKEND` requires restarting the CLI or Streamlit app because tools are selected when the graph starts.

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

## Feature Control

Admin users can control features globally. Login as admin first, then use:

```text
admin_user
Admin password? ********
```

Available feature control commands:

- **List features**: "Show all features" or "What features can be controlled?"
- **Disable patient booking**: "Disable booking appointments"
- **Enable patient booking**: "Enable booking appointments"
- **Disable availability lookup**: "Disable checking availability"
- **Disable doctor schedule management**: "Disable adding doctor availability"

When a feature is disabled, patients cannot use related functions. Admin control features are protected and cannot be disabled to prevent lockout.

Feature state persists in `feature_config.json` and applies across all sessions.

## Supported Specializations

- `general_dentist` - routine checkups and cleanings
- `oral_surgeon` - oral surgeries
- `orthodontist` - braces and alignment
- `cosmetic_dentist` - smile design
- `prosthodontist` - dental prosthetics
- `pediatric_dentist` - children's dentistry
- `emergency_dentist` - urgent care

## Doctor Login

Doctors can log in to manage their own schedules:

```text
login as doctor Emily Johnson
```

After login, doctors can add availability and block slots. Doctor login provides `doctor_doctor_name` permission flags.

## Admin Login

Admin users have full system access:

```text
admin_user
Admin password? ********
```

Admin login provides `admin_has_permission` flags enabling all operations.

## Data Model

### Appointment Data (`doctor_availability.csv`)

CSV is active only when `STORAGE_BACKEND=csv`.

| Field | Description |
| --- | --- |
| `date_slot` | Appointment date and time in `M/D/YYYY H:MM` format. |
| `specialization` | Dental specialization. |
| `doctor_name` | Doctor name. |
| `is_available` | `TRUE` for open slots and `FALSE` for booked slots. |
| `patient_to_attend` | Patient ID for booked slots. Empty for available slots. |

### SQLite Data (`data/appointments.sqlite3`)

SQLite is active only when `STORAGE_BACKEND=sqlite`.

| Table | Description |
| --- | --- |
| `slots` | Stores doctor availability slots, booking state, and patient ID. |

The SQLite schema is created automatically in `dental_agent/storage/sqlite_store.py`.

### Global Features (`feature_config.json`)

| Field | Description |
| --- | --- |
| `features` | Dict of feature names to enabled/disabled status. |
| Keys include: `check_availability`, `book_appointment`, `cancel_appointment`, `reschedule_appointment`, `doctor_add_availability`, `doctor_block_slot`, `doctor_update_schedule` |

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

### Storage backend switch

If the app appears to ignore `STORAGE_BACKEND`, restart the CLI or Streamlit app after editing `.env`. The backend is selected when the graph starts.

Use only one value:

```env
STORAGE_BACKEND=csv
```

or:

```env
STORAGE_BACKEND=sqlite
```

### CSV date errors

Do not manually change `date_slot` values unless they follow `M/D/YYYY H:MM` format.
