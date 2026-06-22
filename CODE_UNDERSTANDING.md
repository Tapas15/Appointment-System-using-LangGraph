# Dental Appointment System - Architecture and Feature Understanding

## 1. Project Overview

This project is a **Dental Appointment Management System** built with **LangGraph**, **LangChain**, **Groq**, **Pandas**, and optional **Streamlit**.

The system provides a multi-agent conversational assistant for:

- Patients: availability lookup, booking, cancellation, rescheduling, and appointment checks.
- Doctors: login and schedule management.
- Admins: global feature control, patient operations, and doctor schedule management.

The active runtime implementation uses the LangGraph workflow in:

```text
dental_agent/workflows/graph.py
```

The older React-agent implementation in:

```text
dental_agent/agent.py
```

is no longer used by `main.py` or `app.py`.

---

## 2. High-Level Architecture

```text
User Input
   ↓
main.py or app.py or telegram_bot.py
   ↓
LangGraph workflow
   ↓
load_global_features
   ↓
supervisor
   ↓
specialized agent
   ↓
tool node, if needed
   ↓
final response
   ↓
storage backend read/write, if needed
   ↓
final response
```

The graph starts by loading global feature flags, then the supervisor routes the request to the correct agent.

```text
START
  ↓
load_global_features
  ↓
supervisor
  ↓
info_agent / booking_agent / cancellation_agent / rescheduling_agent / doctor_agent / admin_agent
  ↓
tools
  ↓
agent final response
  ↓
END
```

---

## 3. Main Entry Points

### CLI

File:

```text
main.py
```

Run:

```powershell
.\myenv\Scripts\python.exe main.py
```

Exit commands:

```text
quit
exit
bye
```

The CLI streams final responses using:

```python
dental_graph.stream(...)
```

Current behavior:

- Final answer chunks stream to the terminal.
- Tool calls execute internally.
- Intermediate tool progress messages are not displayed yet.

---

### Streamlit Web App

File:

```text
app.py
```

Run:

```powershell
.\myenv\Scripts\python.exe -m streamlit run app.py
```

The Streamlit app uses the same LangGraph workflow as the CLI.

Current note:

```text
Streamlit must be installed in the virtual environment before this app can run.
```

---

## 4. Project Structure

```text
Appointment-System-using-LangGraph/
├── main.py
├── app.py
├── telegram_bot.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
├── CODE_UNDERSTANDING.md
├── feature_config.json
├── doctor_availability.csv
├── data_/
│   ├── doctors.csv
│   ├── doctor_availability.csv
│   └── doctor_availability1.csv
├── myenv/
└── dental_agent/
    ├── agent.py
    ├── utils.py
    ├── config/
    │   ├── settings.py
    │   ├── runtime.py
    │   └── features.py
    ├── models/
    │   └── state.py
    ├── workflows/
    │   └── graph.py
    ├── agents/
    │   ├── supervisor.py
    │   ├── info_agent.py
    │   ├── booking_agent.py
    │   ├── cancellation_agent.py
    │   ├── rescheduling_agent.py
    │   ├── doctor_agent.py
    │   └── admin_agent.py
    ├── tools/
    │   ├── csv_reader.py
    │   ├── csv_writer.py
    │   ├── csv_doctor.py
    │   ├── csv_admin.py
    │   ├── sqlite_reader.py
    │   ├── sqlite_writer.py
    │   ├── sqlite_admin.py
    │   ├── sqlite_doctor.py
    │   └── storage_factory.py
    └── storage/
        ├── repository.py
        └── sqlite_store.py
```

---

## 5. Configuration

### `dental_agent/config/settings.py`

Main configuration file.

Important values:

```python
BASE_DIR
CSV_PATH
DB_PATH
GROQ_API_KEY
MODEL_NAME
TEMPERATURE
STORAGE_BACKEND
SYNC_CSV_SQLITE
TELEGRAM_BOT_TOKEN
VALID_SPECIALIZATIONS
ADMIN_USERS
VALID_DOCTORS
DOCTOR_PASSWORDS
DATE_FORMAT
```

Active appointment data backend:

```text
STORAGE_BACKEND=csv uses doctor_availability.csv
STORAGE_BACKEND=sqlite uses data/appointments.sqlite3
```

Only one storage backend is active at runtime. Changing `STORAGE_BACKEND` requires restarting the CLI or Streamlit app.

Default admin:

```text
admin / admin123
```

Configured superadmin:

```text
superadmin / superadmin123
```

Default doctor password:

```text
doctor123
```

Supported specializations:

```text
general_dentist
oral_surgeon
orthodontist
cosmetic_dentist
prosthodontist
pediatric_dentist
emergency_dentist
```

---

### `dental_agent/config/runtime.py`

Runtime graph settings used by Streamlit:

```python
GRAPH_API_KEY
GRAPH_MODEL_NAME
GRAPH_TEMPERATURE
```

---

### `dental_agent/config/features.py`

Defines and manages global feature control.

It contains:

```python
PATIENT_FEATURES
DOCTOR_FEATURES
ADMIN_CONTROL_FEATURES
PROTECTED_FEATURES
ALL_FEATURES
FEATURE_ALIASES
```

It also provides helpers:

```python
load_global_features()
save_global_features()
feature_category()
feature_for_request()
is_global_feature_enabled()
disabled_global_feature_for_request()
```

---

### `feature_config.json`

Persistent global feature configuration.

Default state:

```text
All patient, doctor, and admin control features are enabled.
```

Protected admin features cannot be disabled:

```text
admin_list_features
admin_enable_feature
admin_disable_feature
```

This prevents admin lockout.

---

## 6. Data Storage

### Active Appointment CSV

File:

```text
doctor_availability.csv
```

Columns:

```text
date_slot
specialization
doctor_name
is_available
patient_to_attend
```

Example:

```csv
date_slot,specialization,doctor_name,is_available,patient_to_attend
7/8/2026 8:00,general_dentist,john doe,FALSE,9776865125
7/8/2026 8:30,general_dentist,john doe,TRUE,
```

Date format:

```text
M/D/YYYY H:MM
```

Example:

```text
7/8/2026 9:00
```

Meaning of `is_available`:

```text
TRUE  = slot is available
FALSE = slot is booked or blocked
```

Meaning of `patient_to_attend`:

```text
Empty = available or doctor-blocked slot
Value = patient ID for a booked slot
```

---

### Legacy Data Folder

Folder:

```text
data_/
```

Contains older/raw datasets:

```text
data_/doctors.csv
data_/doctor_availability.csv
data_/doctor_availability1.csv
```

These are not used by the active graph.

---

## 7. LangGraph Workflow

File:

```text
dental_agent/workflows/graph.py
```

### Nodes

```text
load_global_features
supervisor
info_agent
info_tools
booking_agent
booking_tools
cancellation_agent
cancellation_tools
rescheduling_agent
rescheduling_tools
doctor_agent
doctor_tools
admin_agent
admin_tools
```

### Routing Priority

```text
1. If admin_session_role == admin:
   route to admin_agent

2. Else if session_role == doctor:
   route to doctor_agent

3. Else route based on supervisor intent:
   info_agent
   booking_agent
   cancellation_agent
   rescheduling_agent
   doctor_agent
   admin_agent
   end
```

### Tool Loop

Each specialized agent can call tools.

If the last AI message has tool calls:

```text
agent → tool node → agent
```

If the agent has no more tool calls:

```text
agent → END
```

---

## 8. State Model

File:

```text
dental_agent/models/state.py
```

State type:

```python
AppointmentState
```

Important state fields:

```text
messages
intent
next_agent
session_role
authenticated_doctor
doctor_session_started_at
last_doctor_activity_at
admin_session_role
authenticated_admin
admin_session_started_at
last_admin_activity_at
admin_patient_features_enabled
admin_doctor_features_enabled
admin_enabled_features
global_patient_features_enabled
global_doctor_features_enabled
global_enabled_features
patient_id
requested_specialization
requested_doctor
requested_date_slot
current_date_slot
new_date_slot
available_slots
operation_success
operation_message
final_response
```

The most important new fields are:

```text
global_enabled_features
global_patient_features_enabled
global_doctor_features_enabled
```

These allow admin feature changes to affect patient and doctor modes globally.

---

## 9. Agents

### 9.1 Supervisor Agent

File:

```text
dental_agent/agents/supervisor.py
```

Purpose:

```text
Classify user intent and route to the correct specialized agent.
```

Intent types:

```text
get_info
book
cancel
reschedule
doctor
admin
unknown
end
```

Routing examples:

```text
Show available slots → info_agent
Book appointment → booking_agent
Cancel appointment → cancellation_agent
Reschedule appointment → rescheduling_agent
I am doctor → doctor_agent
I am admin → admin_agent
bye → end
```

---

### 9.2 Info Agent

File:

```text
dental_agent/agents/info_agent.py
```

Purpose:

```text
Answer patient-facing availability and appointment lookup queries.
```

Patient features used:

```text
view_available_slots
view_slots_by_specialization
view_slots_by_doctor
view_slots_by_date
view_slots_by_date_range
view_available_doctors_by_date
view_doctors_by_specialization
view_availability_summary
check_slot_availability
view_patient_appointments
```

Tools:

```text
get_available_slots
get_available_slots_range
get_specialty_summary
get_total_available_doctors
get_available_doctors_by_date
list_doctors_by_specialization
check_slot_availability
get_patient_appointments
```

Example patient commands:

```text
Show available slots for an orthodontist
Show general_dentist slots on 7/8/2026
Which doctors are available on 7/8/2026?
Which doctors are cosmetic_dentists?
Show Emily Johnson's available schedule
Show Emily Johnson's availability from 7/8/2026 to 7/10/2026
Show total specialties
Show total doctors available on 7/8/2026
What appointments does patient 1000082 have?
Check if Emily Johnson is available on 7/8/2026 9:00
```

If a patient feature is globally disabled:

```text
This feature is disabled globally by admin: feature_name
```

---

### 9.3 Booking Agent

File:

```text
dental_agent/agents/booking_agent.py
```

Purpose:

```text
Book new patient appointments.
```

Feature:

```text
book_appointment
```

Tools:

```text
get_available_slots
check_slot_availability
book_appointment
```

Example commands:

```text
Book patient 1000082 with Emily Johnson on 7/8/2026 9:00
Book an appointment for patient 1000048 with Jane Smith on 7/9/2026 10:00
```

Booking flow:

```text
1. Check slot availability.
2. If available, book appointment.
3. If unavailable, suggest alternatives.
```

If disabled globally:

```text
This feature is disabled globally by admin: book_appointment
```

---

### 9.4 Cancellation Agent

File:

```text
dental_agent/agents/cancellation_agent.py
```

Purpose:

```text
Cancel existing patient appointments.
```

Feature:

```text
cancel_appointment
```

Tools:

```text
get_patient_appointments
cancel_appointment
```

Example commands:

```text
Cancel appointment for patient 1000082 at 7/8/2026 9:00
Cancel my appointment for patient 1000082
What appointments does patient 1000082 have?
```

Cancellation flow:

```text
1. Find patient appointment.
2. Confirm cancellation.
3. Cancel appointment.
```

If disabled globally:

```text
This feature is disabled globally by admin: cancel_appointment
```

---

### 9.5 Rescheduling Agent

File:

```text
dental_agent/agents/rescheduling_agent.py
```

Purpose:

```text
Move an existing patient appointment to a new available slot.
```

Feature:

```text
reschedule_appointment
```

Tools:

```text
get_patient_appointments
get_available_slots
reschedule_appointment
```

Example commands:

```text
Reschedule patient 1000082 from 7/8/2026 9:00 to 7/9/2026 10:00
Reschedule my appointment with Emily Johnson to 7/9/2026 10:00
```

Rescheduling flow:

```text
1. Find existing appointment.
2. Check new slot availability.
3. Move appointment.
4. Confirm old slot → new slot.
```

If disabled globally:

```text
This feature is disabled globally by admin: reschedule_appointment
```

---

### 9.6 Doctor Agent

File:

```text
dental_agent/agents/doctor_agent.py
```

Purpose:

```text
Allow authenticated doctors to manage their own schedule.
```

Doctor features:

```text
doctor_add_availability
doctor_block_slot
doctor_update_schedule
```

Tools:

```text
doctor_login
doctor_add_availability
doctor_block_time_slot
doctor_update_schedule
```

Doctor login:

```text
I am doctor
```

Default doctor password:

```text
doctor123
```

Example doctor commands:

```text
I am doctor
Block Emily Johnson slot on 7/9/2026 9:00 with password doctor123
Add availability for Emily Johnson on 7/10/2026 10:00 specialization general_dentist with password doctor123
Update Emily Johnson schedule on 7/10/2026 10:00 to unavailable with password doctor123
Restore availability for Emily Johnson on 7/10/2026 10:00 with password doctor123
Logout
```

Doctor restrictions:

```text
Doctor mode cannot book patient appointments.
Doctor mode cannot cancel patient appointments.
Doctor mode cannot reschedule patient appointments.
Doctor mode cannot show general patient availability.
```

If a doctor feature is globally disabled:

```text
This feature is disabled globally by admin: doctor_block_slot
```

---

### 9.7 Admin Agent

File:

```text
dental_agent/agents/admin_agent.py
```

Purpose:

```text
Allow admin login, global feature control, patient operations, and doctor schedule management.
```

Admin login:

```text
I am a admin, here is my password admin123
```

Admin control features:

```text
admin_list_features
admin_enable_feature
admin_disable_feature
```

Admin patient/doctor feature grouping tools:

```text
admin_enable_patient_features
admin_disable_patient_features
admin_enable_doctor_features
admin_disable_doctor_features
```

Patient/admin operation features:

```text
view_available_slots
view_slots_by_specialization
view_slots_by_doctor
view_slots_by_date
view_slots_by_date_range
view_available_doctors_by_date
view_doctors_by_specialization
view_availability_summary
check_slot_availability
view_patient_appointments
book_appointment
cancel_appointment
reschedule_appointment
```

Doctor/admin operation features:

```text
doctor_add_availability
doctor_block_slot
doctor_update_schedule
```

Admin examples:

```text
I am a admin, here is my password admin123
Admin: list features
Admin: disable feature book_appointment
Admin: enable feature book_appointment
Admin: disable patient features
Admin: enable patient features
Admin: disable doctor features
Admin: enable doctor features
Admin: disable feature doctor_block_slot
Admin: enable feature doctor_block_slot
Admin: book patient 1000082 with Emily Johnson on 7/8/2026 9:00
Admin: block Emily Johnson slot on 7/9/2026 9:00
Admin: add availability for Emily Johnson on 7/10/2026 10:00 specialization general_dentist
Admin: update Emily Johnson schedule on 7/10/2026 10:00 to unavailable
Admin logout
```

Protected features:

```text
admin_list_features
admin_enable_feature
admin_disable_feature
```

These are forced to stay enabled to avoid admin lockout.

---

## 10. Global Feature Control

### Current behavior

Admin feature changes are global.

When admin disables a patient feature:

```text
Patient mode is blocked.
Admin patient operation is blocked.
Doctor mode is not affected.
```

When admin disables a doctor feature:

```text
Doctor mode is blocked.
Admin doctor-management operation is blocked.
Patient mode is not affected.
```

Example:

```text
Admin: disable feature book_appointment
```

Then patient booking is blocked:

```text
This feature is disabled globally by admin: book_appointment
```

Example:

```text
Admin: disable feature doctor_block_slot
```

Then doctor slot blocking is blocked:

```text
This feature is disabled globally by admin: doctor_block_slot
```

### Global feature files

Definition file:

```text
dental_agent/config/features.py
```

Persistent config:

```text
feature_config.json
```

Graph loader:

```text
dental_agent/workflows/graph.py
```

State fields:

```text
global_enabled_features
global_patient_features_enabled
global_doctor_features_enabled
```

Admin updater:

```text
dental_agent/agents/admin_agent.py
```

---

## 11. Tools

### `dental_agent/tools/csv_reader.py`

CSV-mode patient/admin read tools.

Functions:

```text
get_available_slots
get_patient_appointments
check_slot_availability
list_doctors_by_specialization
get_available_doctors_by_date
get_available_slots_range
get_specialty_summary
get_total_available_doctors
```

Used when `STORAGE_BACKEND=csv` by:

```text
info_agent
booking_agent
rescheduling_agent
admin_agent
```

---

### `dental_agent/tools/csv_writer.py`

CSV-mode patient/admin write tools.

Functions:

```text
book_appointment
cancel_appointment
reschedule_appointment
```

Used when `STORAGE_BACKEND=csv` by:

```text
booking_agent
cancellation_agent
rescheduling_agent
admin_agent
```

These tools update:

```text
doctor_availability.csv
```

---

### `dental_agent/tools/csv_doctor.py`

CSV-mode doctor tools.

Functions:

```text
doctor_login
doctor_add_availability
doctor_block_time_slot
doctor_update_schedule
```

Used when `STORAGE_BACKEND=csv` by:

```text
doctor_agent
```

These tools update:

```text
doctor_availability.csv
```

---

### `dental_agent/tools/csv_admin.py`

Admin tools.

Functions:

```text
admin_login
admin_enable_patient_features
admin_disable_patient_features
admin_enable_doctor_features
admin_disable_doctor_features
admin_enable_feature
admin_disable_feature
admin_list_features
admin_add_availability
admin_block_time_slot
admin_update_schedule
```

Admin schedule-management tools update the active backend through `storage_factory.py`; in CSV mode this updates `doctor_availability.csv`.

---

### SQLite support

Files:

```text
dental_agent/storage/repository.py
dental_agent/storage/sqlite_store.py
dental_agent/tools/sqlite_reader.py
dental_agent/tools/sqlite_writer.py
dental_agent/tools/sqlite_doctor.py
dental_agent/tools/sqlite_admin.py
dental_agent/tools/storage_factory.py
```

Current status:

```text
Active when STORAGE_BACKEND=sqlite.
```

Backend selection:

```text
storage_factory.py chooses CSV tools when STORAGE_BACKEND=csv.
storage_factory.py chooses SQLite tools when STORAGE_BACKEND=sqlite.
```

SQLite data path:

```text
data/appointments.sqlite3
```

SQLite migration:

```text
SYNC_CSV_SQLITE=true imports existing CSV rows into SQLite once.
SYNC_CSV_SQLITE=false keeps SQLite as the only active write target.
```

---

## 12. Message Sanitization

File:

```text
dental_agent/utils.py
```

Purpose:

```text
Sanitize LangChain messages before sending them to Groq.
```

Important behavior:

```text
Empty message content is replaced with a single space.
```

This avoids Groq API errors for empty/null content.

Also includes:

```python
format_date_slot()
```

Used to normalize CSV date values.

---

## 13. User Flows

### Patient flow

```text
Patient asks availability question
   ↓
supervisor routes to info_agent
   ↓
info_agent checks global patient feature
   ↓
info_agent calls read tools
   ↓
info_agent returns answer
```

```text
Patient asks to book
   ↓
supervisor routes to booking_agent
   ↓
booking_agent checks global book_appointment feature
   ↓
booking_agent checks slot availability
   ↓
booking_agent books slot
   ↓
active storage is updated
```

```text
Patient asks to cancel
   ↓
supervisor routes to cancellation_agent
   ↓
cancellation_agent checks global cancel_appointment feature
   ↓
cancellation_agent confirms and cancels
   ↓
active storage is updated
```

```text
Patient asks to reschedule
   ↓
supervisor routes to rescheduling_agent
   ↓
rescheduling_agent checks global reschedule_appointment feature
   ↓
rescheduling_agent checks old and new slots
   ↓
active storage is updated
```

---

### Doctor flow

```text
Doctor says "I am doctor"
   ↓
supervisor routes to doctor_agent
   ↓
doctor_agent asks for doctor name/password if needed
   ↓
doctor_login verifies credentials
   ↓
session_role becomes doctor
   ↓
doctor can manage their own schedule
```

Doctor schedule actions:

```text
add availability
block slot
update schedule
logout
```

Doctor actions are blocked if the matching global doctor feature is disabled.

---

### Admin flow

```text
Admin says "I am a admin, here is my password admin123"
   ↓
supervisor routes to admin_agent
   ↓
admin_login verifies credentials
   ↓
admin_session_role becomes admin
   ↓
admin can list, enable, or disable features
   ↓
feature_config.json is updated
   ↓
patient and doctor modes obey the new global feature state
```

Admin can also perform:

```text
patient appointment operations
doctor schedule-management operations
```

when the relevant features are enabled.

---

## 14. Feature Matrix

| Feature | Patient Mode | Doctor Mode | Admin Mode |
|---|---:|---:|---:|
| `view_available_slots` | Yes | No | Yes |
| `view_slots_by_specialization` | Yes | No | Yes |
| `view_slots_by_doctor` | Yes | No | Yes |
| `view_slots_by_date` | Yes | No | Yes |
| `view_slots_by_date_range` | Yes | No | Yes |
| `view_available_doctors_by_date` | Yes | No | Yes |
| `view_doctors_by_specialization` | Yes | No | Yes |
| `view_availability_summary` | Yes | No | Yes |
| `check_slot_availability` | Yes | No | Yes |
| `view_patient_appointments` | Yes | No | Yes |
| `book_appointment` | Yes | No | Yes |
| `cancel_appointment` | Yes | No | Yes |
| `reschedule_appointment` | Yes | No | Yes |
| `doctor_add_availability` | No | Yes | Yes |
| `doctor_block_slot` | No | Yes | Yes |
| `doctor_update_schedule` | No | Yes | Yes |
| `admin_list_features` | No | No | Yes |
| `admin_enable_feature` | No | No | Yes |
| `admin_disable_feature` | No | No | Yes |

---

## 15. Current Known Limitations

### CSV file lock

Active file:

```text
doctor_availability.csv
```

If Excel, OneDrive, or another process locks the CSV, write operations fail:

```text
PermissionError: [Errno 13] Permission denied
```

Affected operations:

```text
booking
cancellation
rescheduling
doctor schedule updates
admin schedule updates
```

Recommended fixes:

```text
Close Excel or other process using the CSV.
Move the project outside OneDrive/Documents.
Replace CSV storage with SQLite or another database.
```

---

### Streamlit dependency

`requirements.txt` includes Streamlit, but the current virtual environment may not have it installed.

Fix:

```powershell
.\myenv\Scripts\python.exe -m pip install -r requirements.txt
```

---

### Tool-call progress visibility

The graph streams final answer chunks, but the UI does not currently show intermediate tool progress.

Current behavior:

```text
User asks → agent processes internally → final answer streams
```

Better behavior:

```text
User asks → checking message → tool progress → final answer
```

Files to update later:

```text
main.py
app.py
```

---

### `.env` API key exposure

The current `.env` appears to contain a real-looking Groq API key.

If the project is shared, rotate the key.

---

## 16. Design Patterns

### Supervisor pattern

The supervisor classifies intent and routes to the correct agent.

### Tool-based agents

Each agent has a focused tool set.

### Global feature control

Admin-controlled feature flags are persisted in `feature_config.json` and loaded at the start of every graph run.

### Stateful conversations

LangGraph state preserves:

```text
conversation history
doctor session
admin session
feature state
booking/rescheduling parameters
tool results
```

### Storage backend selection

The system supports one active storage backend:

```text
STORAGE_BACKEND=csv
STORAGE_BACKEND=sqlite
```

`storage_factory.py` returns the correct tool implementation for the active backend. CSV tools and SQLite tools have the same public tool names, so agent prompts do not need separate backend-specific instructions.

---

## 17. How to Extend

To add a new feature:

```text
1. Add the feature name to dental_agent/config/features.py.
2. Add it to feature_config.json or allow default creation.
3. Add admin enable/disable support if needed.
4. Add agent-level global feature checks.
5. Add tools if the feature needs data changes.
6. Update this document and README.md.
```

To add a new agent:

```text
1. Create file in dental_agent/agents/.
2. Define tools in dental_agent/tools/.
3. Add state fields if needed.
4. Register node in dental_agent/workflows/graph.py.
5. Update supervisor routing logic.
6. Add feature-control checks if admin should control it.
```

To switch storage backends:

```text
1. Set STORAGE_BACKEND=csv or STORAGE_BACKEND=sqlite in .env.
2. Restart the CLI or Streamlit app.
3. Optionally set SYNC_CSV_SQLITE=true once when migrating CSV data into a new SQLite database.
4. Set SYNC_CSV_SQLITE=false after migration so only the active backend is written.
```

---

## 18. Current Active Implementation Summary

Active entry points:

```text
main.py
app.py
telegram_bot.py
```

Active graph:

```text
dental_agent/workflows/graph.py
```

Active storage:

```text
Selected by STORAGE_BACKEND
```

Active global feature config:

```text
feature_config.json
```

Active roles:

```text
patient
doctor
admin
```

Current working capabilities:

```text
patient availability lookup
patient booking
patient cancellation
patient rescheduling
doctor login
doctor schedule management
admin login
admin global feature enable/disable
admin patient operations
admin doctor schedule management
persistent global feature flags
```

Current non-active/incomplete capabilities:

```text
visible tool-call progress messages
Streamlit app until dependencies are installed
CSV writes while doctor_availability.csv is locked by another process
```
