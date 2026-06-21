# Features Manual

This file explains how the Dental Appointment System works from `main.py`, how patient, doctor, and admin flows are routed, how to use each feature, and what kind of output to expect.

---

## 1. Start the App

Run from the project root:

```powershell
python main.py
```

Exit with:

```text
quit
exit
bye
```

`main.py` receives the user input, adds it to the LangGraph message history, and streams the agent response.

---

## 2. Main Flow From `main.py`

```text
User input
   ↓
main.py
   ↓
dental_graph.stream(...)
   ↓
load_global_features node
   ↓
supervisor agent
   ↓
patient / doctor / admin agent
   ↓
tool node, if needed
   ↓
storage backend read/write, if needed
   ↓
final response
```

Routing priority:

```text
1. If admin is logged in, route to admin_agent.
2. Else if doctor is logged in, route to doctor_agent.
3. Else supervisor routes based on intent:
   - availability/query → info_agent
   - book → booking_agent
   - cancel → cancellation_agent
   - reschedule → rescheduling_agent
   - doctor login/schedule → doctor_agent
   - admin login/feature control → admin_agent
```

---

## 3. Important Files

| Area | File |
|---|---|
| CLI entry point | `main.py` |
| LangGraph workflow | `dental_agent/workflows/graph.py` |
| Supervisor routing | `dental_agent/agents/supervisor.py` |
| Patient info tools | `dental_agent/tools/storage_factory.py` selects CSV or SQLite reader tools |
| Patient write tools | `dental_agent/tools/storage_factory.py` selects CSV or SQLite writer tools |
| Doctor tools | `dental_agent/tools/storage_factory.py` selects CSV or SQLite doctor tools |
| Admin tools | `dental_agent/tools/storage_factory.py` selects CSV or SQLite admin tools |
| Feature control | `dental_agent/config/features.py` |
| Persistent feature flags | `feature_config.json` |
| CSV appointment data | `doctor_availability.csv` |
| SQLite appointment data | `data/appointments.sqlite3` |

---

## 4. Storage Backend and Data Format

The active appointment backend is selected by `STORAGE_BACKEND` in `.env`.

```text
STORAGE_BACKEND=csv
```

uses:

```text
doctor_availability.csv
```

```text
STORAGE_BACKEND=sqlite
```

uses:

```text
data/appointments.sqlite3
```

Only one backend is active at a time. Changing the backend requires restarting the CLI or Streamlit app.

CSV required columns:

```csv
date_slot,specialization,doctor_name,is_available,patient_to_attend
```

Date/time format:

```text
M/D/YYYY H:MM
```

Example:

```text
7/8/2026 9:00
```

Slot meaning:

| `is_available` | `patient_to_attend` | Meaning |
|---:|---|---|
| `TRUE` | empty | Slot is open |
| `FALSE` | patient ID | Slot is booked |
| `FALSE` | empty | Slot is blocked/unavailable |

---

## 5. Default Credentials

| Role | Login | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Superadmin | `superadmin` | `superadmin123` |
| Doctors | any valid doctor name | `doctor123` |

Valid doctor names are defined in `dental_agent/config/settings.py`.

---

# Patient Features

Patient mode is the default mode. If no doctor or admin session is active, normal appointment requests go to patient agents.

---

## 6. Patient Flow

```text
Patient input
   ↓
supervisor classifies intent
   ↓
info_agent / booking_agent / cancellation_agent / rescheduling_agent
   ↓
feature check
   ↓
storage backend read/write tool
   ↓
final answer
```

---

## 7. View Available Slots

Feature name:

```text
view_available_slots
```

Input examples:

```text
Show available slots
Show available slots for an orthodontist
Show Emily Johnson's available schedule
Show available slots for Emily Johnson from 7/8/2026 to 7/10/2026
```

Expected output:

```text
Here are the available slots for Emily Johnson from 7/8/2026 to 7/10/2026:

1. 7/8/2026 9:00 - orthodontist
2. 7/9/2026 10:00 - orthodontist
3. 7/10/2026 14:30 - orthodontist
```

If no slots exist:

```text
No available slots found for the requested criteria.
```

If the feature is disabled:

```text
This feature is disabled globally by admin: view_available_slots
```

---

## 8. View Slots by Specialization

Feature name:

```text
view_slots_by_specialization
```

Input examples:

```text
Show general_dentist slots on 7/8/2026
Show orthodontist slots
Which slots are available for cosmetic_dentist?
```

Expected output:

```text
Available general_dentist slots on 7/8/2026:

1. 7/8/2026 8:30 - John Doe
2. 7/8/2026 11:00 - Sarah Wilson
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

## 9. View Slots by Doctor

Feature name:

```text
view_slots_by_doctor
```

Input examples:

```text
Show Emily Johnson's available schedule
Show John Doe slots
What slots does Sarah Wilson have?
```

Expected output:

```text
Emily Johnson has these available slots:

1. 7/8/2026 9:00
2. 7/9/2026 10:00
3. 7/10/2026 14:30
```

---

## 10. View Slots by Date

Feature name:

```text
view_slots_by_date
```

Input examples:

```text
Show slots on 7/8/2026
Which doctors are available on 7/8/2026?
Show available slots for 7/9/2026
```

Expected output:

```text
Available slots on 7/8/2026:

1. 7/8/2026 8:00 - John Doe - general_dentist
2. 7/8/2026 9:00 - Emily Johnson - orthodontist
3. 7/8/2026 10:30 - Jane Smith - cosmetic_dentist
```

---

## 11. View Slots by Date Range

Feature name:

```text
view_slots_by_date_range
```

Input examples:

```text
Show slots from 7/8/2026 to 7/10/2026
Show Emily Johnson availability from 7/8/2026 to 7/10/2026
Show orthodontist slots between 7/8/2026 and 7/12/2026
```

Expected output:

```text
Available slots from 7/8/2026 to 7/10/2026:

1. 7/8/2026 9:00 - Emily Johnson - orthodontist
2. 7/9/2026 10:00 - Emily Johnson - orthodontist
3. 7/10/2026 14:30 - Emily Johnson - orthodontist
```

---

## 12. View Available Doctors by Date

Feature name:

```text
view_available_doctors_by_date
```

Input examples:

```text
Which doctors are available on 7/8/2026?
Show doctors available on 7/9/2026
Who is available next Monday?
```

Expected output:

```text
Doctors available on 7/8/2026:

1. John Doe - general_dentist - 3 slots
2. Emily Johnson - orthodontist - 2 slots
3. Jane Smith - cosmetic_dentist - 1 slot
```

---

## 13. View Doctors by Specialization

Feature name:

```text
view_doctors_by_specialization
```

Input examples:

```text
Which doctors are cosmetic_dentists?
List orthodontists
Show doctors for oral_surgeon
```

Expected output:

```text
Cosmetic dentists:

1. Jane Smith
2. Michael Green
```

---

## 14. View Availability Summary

Feature name:

```text
view_availability_summary
```

Input examples:

```text
Show total specialties
Show total doctors available on 7/8/2026
Show availability summary
```

Expected output:

```text
Availability summary for 7/8/2026:

- Specializations: 3
- Available doctors: 5
- Available slots: 12
```

---

## 15. Check One Slot Availability

Feature name:

```text
check_slot_availability
```

Input examples:

```text
Check if Emily Johnson is available on 7/8/2026 9:00
Is John Doe available at 7/8/2026 8:30?
```

Expected output if available:

```text
Emily Johnson is available on 7/8/2026 9:00.
```

Expected output if booked:

```text
Emily Johnson is not available on 7/8/2026 9:00. That slot is already booked.
```

Expected output if not found:

```text
No slot found for Emily Johnson on 7/8/2026 9:00.
```

---

## 16. View Patient Appointments

Feature name:

```text
view_patient_appointments
```

Input examples:

```text
What appointments does patient 1000082 have?
Show appointments for patient 1000048
```

Expected output:

```text
Appointments for patient 1000082:

1. 7/8/2026 9:00 - Emily Johnson - orthodontist
2. 7/10/2026 14:30 - Jane Smith - cosmetic_dentist
```

If none:

```text
No appointments found for patient 1000082.
```

---

## 17. Book Appointment

Feature name:

```text
book_appointment
```

Input examples:

```text
Book patient 1000082 with Emily Johnson on 7/8/2026 9:00
Book an appointment for patient 1000048 with Jane Smith on 7/9/2026 10:00
```

Required information:

```text
patient_id
doctor_name
date_slot
```

Expected output if successful:

```text
Appointment booked for patient 1000082 with Emily Johnson on 7/8/2026 9:00.
```

Expected output if slot is already taken:

```text
Slot is already booked. I can show available alternatives for Emily Johnson.
```

Expected output if missing information:

```text
Please provide the patient ID, doctor name, and appointment date/time.
```

Storage change:

```text
is_available becomes FALSE
patient_to_attend becomes the patient ID
```

---

## 18. Cancel Appointment

Feature name:

```text
cancel_appointment
```

Input examples:

```text
Cancel appointment for patient 1000082 at 7/8/2026 9:00
Cancel my appointment for patient 1000082
```

Required information:

```text
patient_id
date_slot
```

Expected flow:

```text
User: Cancel appointment for patient 1000082 at 7/8/2026 9:00
Agent: Are you sure you want to cancel the appointment at 7/8/2026 9:00? (yes/no)
User: yes
Agent: Appointment at 7/8/2026 9:00 for patient 1000082 has been cancelled.
```

Storage change:

```text
is_available becomes TRUE
patient_to_attend becomes empty
```

If no appointment found:

```text
No booked appointment found for patient 1000082 at 7/8/2026 9:00.
```

---

## 19. Reschedule Appointment

Feature name:

```text
reschedule_appointment
```

Input examples:

```text
Reschedule patient 1000082 from 7/8/2026 9:00 to 7/9/2026 10:00
Move patient 1000048 from 7/8/2026 9:00 to 7/10/2026 14:30 with Jane Smith
```

Required information:

```text
patient_id
current_date_slot
new_date_slot
doctor_name
```

Expected output if successful:

```text
Appointment for patient 1000082 rescheduled from 7/8/2026 9:00 to 7/9/2026 10:00 with Emily Johnson.
```

Storage change:

```text
Old slot becomes available and patient_to_attend is cleared.
New slot becomes unavailable and patient_to_attend is set to the patient ID.
```

If new slot is taken:

```text
Slot 7/9/2026 10:00 is already taken.
```

---

# Doctor Features

Doctor mode starts after doctor login. Doctor mode is only for managing the doctor's own schedule.

Important rule:

```text
While logged in as doctor, patient booking/cancel/reschedule actions are blocked until doctor logout.
```

---

## 20. Doctor Flow

```text
Doctor says "I am doctor"
   ↓
supervisor routes to doctor_agent
   ↓
doctor_agent asks for name/password if needed
   ↓
doctor_login verifies credentials
   ↓
session_role becomes doctor
   ↓
doctor can manage schedule
   ↓
logout returns to patient mode
```

---

## 21. Doctor Login

Feature name:

```text
doctor login/session
```

Input:

```text
I am doctor
```

Expected output if password is needed:

```text
Please provide your doctor name and password.
```

Input with password:

```text
I am doctor Emily Johnson, password doctor123
```

Expected output if login succeeds:

```text
Logged in as Emily Johnson.
```

Expected output if password is wrong:

```text
You are not authorized.
```

State after login:

```text
session_role = doctor
authenticated_doctor = emily johnson
```

---

## 22. Add or Restore Doctor Availability

Feature name:

```text
doctor_add_availability
```

Input examples:

```text
Add availability for Emily Johnson on 7/10/2026 10:00 specialization general_dentist with password doctor123
Restore availability for Emily Johnson on 7/10/2026 10:00 with password doctor123
```

If doctor is already logged in:

```text
Add availability for Emily Johnson on 7/10/2026 10:00 specialization general_dentist
```

Expected output if slot does not exist and specialization is provided:

```text
Availability added/restored for Emily Johnson at 7/10/2026 10:00.
```

Expected output if slot exists and is not booked:

```text
Availability added/restored for Emily Johnson at 7/10/2026 10:00.
```

Expected output if slot already has a patient:

```text
Cannot change availability for a slot that already has a patient booking.
```

Expected output if creating a new slot without specialization:

```text
Specialization is required when creating a new slot.
```

Storage change:

```text
is_available becomes TRUE
patient_to_attend becomes empty
```

---

## 23. Add or Restore Doctor Availability in Bulk

Feature name:

```text
doctor_add_availability_bulk
```

Admin feature gate:

```text
doctor_add_availability
```

Input examples:

```text
Add availability for Emily Johnson on June 9, June 10, and June 11 from 9am to 4pm with password doctor123
Add my availability from 9:00 to 16:00 on 6/9/2026 and 6/10/2026
Add availability for Emily Johnson on 6/9/2026 and 6/10/2026 every 30 minutes from 9am to 12pm with password doctor123
```

Structured tool input:

```json
{
  "doctor_name": "emily johnson",
  "password": "doctor123",
  "dates": ["6/9/2026", "6/10/2026", "6/11/2026"],
  "start_time": "9am",
  "end_time": "4pm",
  "specialization": "general_dentist",
  "interval_minutes": 60
}
```

Expected output if successful:

```text
Availability added/restored for Emily Johnson across 3 date(s) from 9am to 4pm every 60 minute(s). Changed 24 slot(s).
```

Expected output if some slots already have patients:

```text
Availability added/restored for Emily Johnson across 3 date(s) from 9am to 4pm every 60 minute(s). Changed 23 slot(s).
```

The response also returns skipped slots, for example:

```text
6/10/2026 12:00: already has a patient booking.
```

Expected output if creating new slots without specialization:

```text
No availability slots were added or restored.
```

Storage change:

```text
For each generated slot:
- Existing unbooked slot: is_available becomes TRUE and patient_to_attend becomes empty.
- Existing booked slot: skipped without changes.
- Missing slot: created with is_available TRUE, patient_to_attend empty, and the provided specialization.
```

---

## 24. Block Doctor Time Slot

Feature name:

```text
doctor_block_slot
```

Input examples:

```text
Block Emily Johnson slot on 7/9/2026 9:00 with password doctor123
Block my slot on 7/9/2026 9:00
```

Expected output if successful:

```text
Slot blocked for Emily Johnson at 7/9/2026 9:00.
```

Expected output if slot is already unavailable:

```text
Slot is already unavailable.
```

Expected output if no slot exists:

```text
No slot found for Emily Johnson at 7/9/2026 9:00.
```

Storage change:

```text
is_available becomes FALSE
patient_to_attend becomes empty
```

---

## 24. Update Doctor Schedule

Feature name:

```text
doctor_update_schedule
```

Input examples:

```text
Update Emily Johnson schedule on 7/10/2026 10:00 to unavailable with password doctor123
Update Emily Johnson schedule on 7/10/2026 10:00 to available with password doctor123
Set my 7/10/2026 10:00 slot to available
```

Expected output if successful:

```text
Schedule updated for Emily Johnson at 7/10/2026 10:00. Slot is now blocked/unavailable.
```

or:

```text
Schedule updated for Emily Johnson at 7/10/2026 10:00. Slot is now available.
```

Expected output if slot has a patient:

```text
Cannot update a slot that already has a patient booking.
```

---

## 25. Doctor Logout

Input:

```text
logout
log out
doctor logout
exit doctor mode
```

Expected output:

```text
Logged out. You are back in patient mode.
```

State after logout:

```text
session_role = patient
authenticated_doctor = None
```

---

## 26. Doctor Requests Patient Work

If doctor is logged in and asks patient work:

```text
Show available slots
Book patient 1000082 with Emily Johnson on 7/8/2026 9:00
```

Expected output:

```text
You are currently in doctor mode. Type logout to return to patient mode and check patient availability.
```

Doctor mode cannot:

```text
book patient appointments
cancel patient appointments
reschedule patient appointments
show general patient availability
```

---

# Admin Features

Admin mode has highest routing priority. Once admin is logged in, all messages are routed to `admin_agent`.

---

## 27. Admin Flow

```text
Admin login
   ↓
supervisor routes to admin_agent
   ↓
admin_login verifies credentials
   ↓
admin_session_role becomes admin
   ↓
admin can list/enable/disable features
   ↓
admin can perform patient operations
   ↓
admin can perform doctor schedule operations
   ↓
admin logout returns to non-admin mode
```

---

## 28. Admin Login

Input examples:

```text
I am a admin, here is my password admin123
I am admin, password admin123
login as admin admin123
```

Expected output if login succeeds:

```text
Admin logged in as admin. All individual admin features are enabled by default.
```

Expected output if password is missing:

```text
Please provide your admin password, for example: I am a admin, here is my password admin123
```

Expected output if password is wrong:

```text
Invalid admin password.
```

State after login:

```text
admin_session_role = admin
authenticated_admin = admin
```

---

## 29. Admin List Features

Feature name:

```text
admin_list_features
```

Input:

```text
Admin: list features
Show all features
What features can be controlled?
```

Expected output:

```text
Admin-controlled features:

1. view_available_slots - View available appointment slots
2. view_slots_by_specialization - View slots by specialization
3. view_slots_by_doctor - View slots by doctor
4. view_slots_by_date - View slots by date
5. view_slots_by_date_range - View slots by date range
6. view_available_doctors_by_date - View available doctors by date
7. view_doctors_by_specialization - View doctors by specialization
8. view_availability_summary - View total specialties, doctors, and slots summary
9. check_slot_availability - Check one specific doctor slot
10. view_patient_appointments - View patient appointments
11. book_appointment - Book appointment
12. cancel_appointment - Cancel appointment
13. reschedule_appointment - Reschedule appointment
14. doctor_add_availability - Add or restore doctor availability
15. doctor_block_slot - Block doctor time slot
16. doctor_update_schedule - Update doctor schedule availability
17. admin_list_features - List admin-controlled features
18. admin_enable_feature - Enable one admin-controlled feature
19. admin_disable_feature - Disable one admin-controlled feature
```

Protected features:

```text
admin_list_features
admin_enable_feature
admin_disable_feature
```

These cannot be disabled.

---

## 30. Disable One Feature

Feature name:

```text
admin_disable_feature
```

Input:

```text
Admin: disable feature book_appointment
Admin: disable feature doctor_block_slot
```

Expected output:

```text
Feature 'book_appointment' disabled.
```

Persistent file changed:

```text
feature_config.json
```

Effect:

```text
The disabled feature is blocked globally for patient, doctor, and admin modes.
```

Example after disabling booking:

```text
User: Book patient 1000082 with Emily Johnson on 7/8/2026 9:00
Agent: This feature is disabled globally by admin: book_appointment
```

---

## 31. Enable One Feature

Feature name:

```text
admin_enable_feature
```

Input:

```text
Admin: enable feature book_appointment
Admin: enable feature doctor_block_slot
```

Expected output:

```text
Feature 'book_appointment' enabled.
```

Effect:

```text
The feature becomes usable again globally, if the feature name is valid.
```

If feature is unknown:

```text
Unknown feature: fake_feature_name
```

If feature is protected admin control feature:

```text
Admin control features cannot be disabled.
```

---

## 32. Disable All Patient Features

Feature name:

```text
admin_disable_patient_features
```

Input:

```text
Admin: disable patient features
```

Expected output:

```text
Patient features disabled.
```

Patient features affected:

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

Example after disabling patient features:

```text
User: Show available slots
Agent: This feature is disabled globally by admin: view_available_slots
```

---

## 33. Enable All Patient Features

Feature name:

```text
admin_enable_patient_features
```

Input:

```text
Admin: enable patient features
```

Expected output:

```text
Patient features enabled.
```

Effect:

```text
All patient features become enabled globally.
```

---

## 34. Disable All Doctor Features

Feature name:

```text
admin_disable_doctor_features
```

Input:

```text
Admin: disable doctor features
```

Expected output:

```text
Doctor features disabled.
```

Doctor features affected:

```text
doctor_add_availability
doctor_block_slot
doctor_update_schedule
```

Example after disabling doctor features:

```text
Doctor: Block my slot on 7/9/2026 9:00
Agent: This feature is disabled globally by admin: doctor_block_slot
```

---

## 35. Enable All Doctor Features

Feature name:

```text
admin_enable_doctor_features
```

Input:

```text
Admin: enable doctor features
```

Expected output:

```text
Doctor features enabled.
```

Effect:

```text
All doctor features become enabled globally.
```

---

## 36. Admin View Availability

Admin can view patient-facing availability if the matching feature is enabled.

Input examples:

```text
Admin: show available slots
Admin: show orthodontist slots on 7/8/2026
Admin: show Emily Johnson availability from 7/8/2026 to 7/10/2026
```

Expected output:

```text
Available slots:

1. 7/8/2026 9:00 - Emily Johnson - orthodontist
2. 7/8/2026 10:30 - Jane Smith - cosmetic_dentist
```

If feature disabled:

```text
This feature is disabled for admin: view_available_slots
```

---

## 37. Admin Book Appointment

Feature name:

```text
book_appointment
```

Input:

```text
Admin: book patient 1000082 with Emily Johnson on 7/8/2026 9:00
```

Expected output if successful:

```text
Appointment booked for patient 1000082 with Emily Johnson on 7/8/2026 9:00.
```

Storage change:

```text
is_available becomes FALSE
patient_to_attend becomes 1000082
```

If disabled:

```text
This feature is disabled for admin: book_appointment
```

---

## 38. Admin Cancel Appointment

Feature name:

```text
cancel_appointment
```

Input:

```text
Admin: cancel appointment for patient 1000082 at 7/8/2026 9:00
```

Expected output if successful:

```text
Appointment at 7/8/2026 9:00 for patient 1000082 has been cancelled.
```

Storage change:

```text
is_available becomes TRUE
patient_to_attend becomes empty
```

If disabled:

```text
This feature is disabled for admin: cancel_appointment
```

---

## 39. Admin Reschedule Appointment

Feature name:

```text
reschedule_appointment
```

Input:

```text
Admin: reschedule patient 1000082 from 7/8/2026 9:00 to 7/9/2026 10:00
```

Expected output if successful:

```text
Appointment for patient 1000082 rescheduled from 7/8/2026 9:00 to 7/9/2026 10:00 with Emily Johnson.
```

Storage change:

```text
Old slot becomes available.
New slot becomes booked for the same patient.
```

If disabled:

```text
This feature is disabled for admin: reschedule_appointment
```

---

## 40. Admin Add Doctor Availability

Feature name:

```text
doctor_add_availability
```

Input:

```text
Admin: add availability for Emily Johnson on 7/10/2026 10:00 specialization general_dentist
Admin: restore availability for John Doe on 7/10/2026 10:00
```

Expected output:

```text
Availability added/restored for Emily Johnson at 7/10/2026 10:00.
```

Storage change:

```text
is_available becomes TRUE
patient_to_attend becomes empty
```

If disabled:

```text
This feature is disabled for admin: doctor_add_availability
```

---

## 41. Admin Block Doctor Slot

Feature name:

```text
doctor_block_slot
```

Input:

```text
Admin: block Emily Johnson slot on 7/9/2026 9:00
Admin: block John Doe slot on 7/8/2026 8:30
```

Expected output:

```text
Slot blocked for Emily Johnson at 7/9/2026 9:00.
```

Storage change:

```text
is_available becomes FALSE
patient_to_attend becomes empty
```

If disabled:

```text
This feature is disabled for admin: doctor_block_slot
```

---

## 42. Admin Update Doctor Schedule

Feature name:

```text
doctor_update_schedule
```

Input:

```text
Admin: update Emily Johnson schedule on 7/10/2026 10:00 to unavailable
Admin: update John Doe schedule on 7/10/2026 10:00 to available
```

Expected output:

```text
Schedule updated for Emily Johnson at 7/10/2026 10:00. Slot is now blocked/unavailable.
```

or:

```text
Schedule updated for John Doe at 7/10/2026 10:00. Slot is now available.
```

If disabled:

```text
This feature is disabled for admin: doctor_update_schedule
```

---

## 43. Admin Logout

Input:

```text
Admin logout
admin log out
exit admin mode
```

Expected output:

```text
Admin logged out. You are back in non-admin mode.
```

State after logout:

```text
admin_session_role = non_admin
authenticated_admin = None
```

---

# Feature Matrix

| Feature | Patient | Doctor | Admin |
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

# How Feature Control Works

Feature flags are loaded at the start of every graph run:

```text
load_global_features → supervisor → agent
```

Persistent file:

```text
feature_config.json
```

Example:

```json
{
  "book_appointment": true,
  "doctor_block_slot": true,
  "view_available_slots": true
}
```

If admin disables a feature, the file is updated and the feature is blocked globally.

Example:

```text
Admin: disable feature book_appointment
```

Then:

```text
Patient: Book patient 1000082 with Emily Johnson on 7/8/2026 9:00
Agent: This feature is disabled globally by admin: book_appointment
```

To restore:

```text
Admin: enable feature book_appointment
```

---

# How to Write a New Feature

To add a new feature correctly, update these places.

## 44. Add Feature Definition

Edit:

```text
dental_agent/config/features.py
```

Add the feature to the correct category:

```python
PATIENT_FEATURES = {
    "new_patient_feature": "Description",
}
```

or:

```python
DOCTOR_FEATURES = {
    "new_doctor_feature": "Description",
}
```

or:

```python
ADMIN_CONTROL_FEATURES = {
    "new_admin_control_feature": "Description",
}
```

If admin should control it, add it to `ADMIN_FEATURE_DEFINITIONS` in:

```text
dental_agent/tools/csv_admin.py
```

---

## 45. Add Tool Logic

If the feature reads data, add the CSV tool in:

```text
dental_agent/tools/csv_reader.py
```

and the matching SQLite tool in:

```text
dental_agent/storage/sqlite_store.py
dental_agent/tools/sqlite_reader.py
```

If the feature writes data, add the CSV tool in:

```text
dental_agent/tools/csv_writer.py
```

and the matching SQLite tool in:

```text
dental_agent/storage/sqlite_store.py
dental_agent/tools/sqlite_writer.py
```

If the feature is doctor schedule management, add the CSV tool in:

```text
dental_agent/tools/csv_doctor.py
```

and the matching SQLite tool in:

```text
dental_agent/storage/sqlite_store.py
dental_agent/tools/sqlite_doctor.py
```

If the feature is admin-controlled, add CSV admin behavior in:

```text
dental_agent/tools/csv_admin.py
```

and SQLite admin behavior in:

```text
dental_agent/tools/sqlite_admin.py
```

Then expose the tool through `dental_agent/tools/storage_factory.py`.

---

## 46. Add Agent Support

Edit the correct agent file:

| Feature type | Agent file |
|---|---|
| Patient info | `dental_agent/agents/info_agent.py` |
| Booking | `dental_agent/agents/booking_agent.py` |
| Cancellation | `dental_agent/agents/cancellation_agent.py` |
| Rescheduling | `dental_agent/agents/rescheduling_agent.py` |
| Doctor | `dental_agent/agents/doctor_agent.py` |
| Admin | `dental_agent/agents/admin_agent.py` |

Add feature checks like:

```python
if not global_features.get("new_feature", True):
    return {
        "messages": [AIMessage(content="This feature is disabled globally by admin: new_feature")],
        "final_response": "This feature is disabled globally by admin: new_feature",
    }
```

Add tools through the correct backend factory in `dental_agent/tools/storage_factory.py`; agents import tools from that factory.

---

## 47. Add Supervisor Routing

Edit:

```text
dental_agent/agents/supervisor.py
```

Add the intent type if needed:

```python
intent: Literal["get_info", "book", "cancel", "reschedule", "doctor", "admin", "new_intent", "unknown", "end"]
```

Update the supervisor prompt routing rules.

Then update the graph routing in:

```text
dental_agent/workflows/graph.py
```

---

## 48. Test the Feature

Test with:

```powershell
python main.py
```

For every new feature, test:

```text
normal success case
missing parameter case
invalid date/time case
disabled feature case
active storage data after write
admin disable/enable behavior
```

---

# Common Troubleshooting

## CSV Is Locked

This issue only affects CSV mode.

Affected operations:

```text
booking
cancellation
rescheduling
doctor schedule updates
admin schedule updates
```

Cause:

```text
Excel, OneDrive, antivirus, or another Python process has doctor_availability.csv open.
```

Fix:

```text
Close Excel.
Stop other Python processes.
Move project outside OneDrive/Documents.
Use SQLite for real concurrent usage.
```

---

## Doctor Cannot Do Patient Work

Expected behavior:

```text
Doctor mode blocks patient booking, cancellation, rescheduling, and general availability lookup.
```

Fix:

```text
Type logout to return to patient mode.
```

---

## Patient Cannot Use a Feature

Possible causes:

```text
Admin disabled the feature globally.
Supervisor routed to the wrong agent.
Required parameters are missing.
CSV is locked while using CSV mode.
SQLite database is missing or empty while using SQLite mode.
LLM did not call the correct tool.
```

Check:

```text
feature_config.json
main.py routing
agent feature checks
active storage backend and data
```

---

## Admin Cannot Disable Admin Control Features

Expected behavior:

```text
Admin control features cannot be disabled.
```

Reason:

```text
admin_list_features, admin_enable_feature, and admin_disable_feature are protected to avoid admin lockout.
```

---

# Quick Command Reference

## Patient

```text
Show available slots
Show general_dentist slots on 7/8/2026
Which doctors are cosmetic_dentists?
Show Emily Johnson's available schedule
Check if Emily Johnson is available on 7/8/2026 9:00
Book patient 1000082 with Emily Johnson on 7/8/2026 9:00
Cancel appointment for patient 1000082 at 7/8/2026 9:00
Reschedule patient 1000082 from 7/8/2026 9:00 to 7/9/2026 10:00
What appointments does patient 1000082 have?
```

## Doctor

```text
I am doctor
I am doctor Emily Johnson, password doctor123
Block my slot on 7/9/2026 9:00
Add availability for Emily Johnson on 7/10/2026 10:00 specialization general_dentist
Add availability for Emily Johnson on June 9, June 10, and June 11 from 9am to 4pm with password doctor123
Add my availability from 9:00 to 16:00 on 6/9/2026 and 6/10/2026
Update Emily Johnson schedule on 7/10/2026 10:00 to unavailable
Logout
```

## Admin

```text
I am a admin, here is my password admin123
Admin: list features
Admin: disable feature book_appointment
Admin: enable feature book_appointment
Admin: disable patient features
Admin: enable patient features
Admin: disable doctor features
Admin: enable doctor features
Admin: book patient 1000082 with Emily Johnson on 7/8/2026 9:00
Admin: cancel appointment for patient 1000082 at 7/8/2026 9:00
Admin: reschedule patient 1000082 from 7/8/2026 9:00 to 7/9/2026 10:00
Admin: block Emily Johnson slot on 7/9/2026 9:00
Admin: add availability for Emily Johnson on 7/10/2026 10:00 specialization general_dentist
Admin: update Emily Johnson schedule on 7/10/2026 10:00 to unavailable
Admin logout
```
