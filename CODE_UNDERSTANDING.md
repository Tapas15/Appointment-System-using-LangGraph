# Dental Appointment System - Code Understanding

## Project Overview

This is a **Dental Appointment Management System** built using **LangGraph** and **LangChain**. The system provides an AI-powered assistant that helps patients with booking, cancelling, and rescheduling dental appointments through natural language conversation.

---

## Architecture

### High-Level Flow

```
User Input → Supervisor Agent → Specialized Agent → Tools → CSV Database
                ↑                                                    ↓
                └────────────────── Response ─────────────────────────┘
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| `main.py` | Entry point | CLI interface for user interaction |
| `agent.py` | Core agent | Creates the LangGraph React agent |
| `supervisor.py` | Routing | Routes requests to appropriate specialized agents |
| `booking_agent.py` | Booking | Handles new appointment bookings |
| `cancellation_agent.py` | Cancellation | Handles appointment cancellations |
| `rescheduling_agent.py` | Rescheduling | Handles appointment rescheduling |
| `info_agent.py` | Information | Provides doctor/specialization info |
| `csv_reader.py` | Read tools | Reads appointment data from CSV |
| `csv_writer.py` | Write tools | Writes/updates appointment data |
| `graph.py` | Workflow | Defines the LangGraph workflow |
| `state.py` | State model | Defines the application state |

---

## Data Flow

### 1. User Input Processing
```
User message → Supervisor → Intent Classification → Route to Agent
```

### 2. Agent Execution
```
Agent → Tools (CSV read/write) → LLM → Response
```

### 3. State Management
The system uses a shared state object that flows through the graph:
- `messages`: Conversation history
- `current_agent`: Active agent name
- `next_agent`: Next agent to route to
- `patient_name`, `doctor_name`, `date`, `time`: Appointment details

---

## Key Files Explained

### [`main.py`](Dental-Appointment-System-using-LangGraph/main.py)
- Entry point of the application
- Provides a command-line interface
- Handles user input and displays responses
- Manages the conversation loop

### [`dental_agent/agent.py`](Dental-Appointment-System-using-LangGraph/dental_agent/agent.py)
- Creates the main LangGraph React agent
- Uses `ChatGroq` (or `ChatXAI`) as the LLM
- Defines the system prompt with booking rules
- Implements a pre-model hook for message sanitization

### [`dental_agent/agents/supervisor.py`](Dental-Appointment-System-using-LangGraph/dental_agent/agents/supervisor.py)
- Routes user requests to appropriate specialized agents
- Classifies intent: booking, cancellation, rescheduling, or info
- Uses LLM to make routing decisions

### [`dental_agent/tools/csv_reader.py`](Dental-Appointment-System-using-LangGraph/dental_agent/tools/csv_reader.py)
**Key Functions:**
- `get_available_slots()`: Returns available appointment slots
- `get_patient_appointments()`: Gets appointments for a patient
- `check_slot_availability()`: Checks if a slot is free
- `list_doctors_by_specialization()`: Lists doctors by specialty

### [`dental_agent/tools/csv_writer.py`](Dental-Appointment-System-using-LangGraph/dental_agent/tools/csv_writer.py)
**Key Functions:**
- `book_appointment()`: Books a new appointment
- `cancel_appointment()`: Cancels an existing appointment
- `reschedule_appointment()`: Reschedules an appointment

### [`dental_agent/workflows/graph.py`](Dental-Appointment-System-using-LangGraph/dental_agent/workflows/graph.py)
- Defines the LangGraph workflow
- Connects all agents and tools
- Manages state transitions

---

## State Model

```python
# dental_agent/models/state.py
class DentalState:
    messages: List[Message]      # Conversation history
    current_agent: str           # Current active agent
    next_agent: str              # Next agent to route to
    patient_name: str            # Patient name
    doctor_name: str             # Doctor name
    date: str                    # Appointment date
    time: str                    # Appointment time
    specialization: str            # Doctor specialization
```

---

## Agent Types

### 1. Booking Agent
- **Purpose**: Book new appointments
- **Process**:
  1. Check slot availability
  2. If available, book the appointment
  3. If not, suggest alternatives

### 2. Cancellation Agent
- **Purpose**: Cancel existing appointments
- **Process**:
  1. Find the appointment
  2. Confirm cancellation with user
  3. Execute cancellation

### 3. Rescheduling Agent
- **Purpose**: Reschedule appointments
- **Process**:
  1. Find the existing appointment
  2. Check new slot availability
  3. Update the appointment

### 4. Info Agent
- **Purpose**: Provide information
- **Process**:
  1. List doctors by specialization
  2. Show available slots
  3. Provide doctor information

---

## Tools

### Read Tools (csv_reader.py)
| Tool | Description |
|------|-------------|
| `get_available_slots` | Get all available slots for a doctor/date |
| `get_patient_appointments` | Get all appointments for a patient |
| `check_slot_availability` | Check if a specific slot is available |
| `list_doctors_by_specialization` | List doctors for a specialization |

### Write Tools (csv_writer.py)
| Tool | Description |
|------|-------------|
| `book_appointment` | Book a new appointment |
| `cancel_appointment` | Cancel an existing appointment |
| `reschedule_appointment` | Reschedule an appointment |

---

## Configuration

### [`dental_agent/config/settings.py`](Dental-Appointment-System-using-LangGraph/dental_agent/config/settings.py)

| Setting | Description |
|---------|-------------|
| `GROQ_API_KEY` | API key for Groq LLM |
| `MODEL_NAME` | LLM model name (default: llama-3.3-70b-versatile) |
| `TEMPERATURE` | LLM temperature (default: 0) |
| `CSV_PATH` | Path to the CSV database |
| `VALID_SPECIALIZATIONS` | List of valid dental specializations |
| `VALID_DOCTORS` | List of valid doctor names |
| `DATE_FORMAT` | Date format for appointments |

---

## Data Storage

The system uses a CSV file (`doctor_availability.csv`) as the database with columns:
- `patient_name`: Patient's name
- `doctor_name`: Doctor's name
- `date`: Appointment date
- `time`: Appointment time
- `specialization`: Doctor's specialization

---

## Key Design Patterns

### 1. Supervisor Pattern
The supervisor agent routes requests to specialized agents based on intent classification.

### 2. Tool-Based Architecture
Each agent has access to specific tools for reading and writing appointment data.

### 3. State Management
LangGraph manages state across agent transitions, preserving conversation context.

### 4. Pre-Model Hook
Sanitizes messages before sending to the LLM to handle edge cases.

---

## Interview Talking Points

### Why LangGraph?
- **State Management**: Built-in state handling across agent transitions
- **Flexibility**: Easy to add new agents and workflows
- **Debugging**: Visual graph representation for debugging

### Why CSV instead of a database?
- **Simplicity**: No database setup required
- **Portability**: Easy to share and version control
- **Suitable for demo**: Adequate for small-scale applications

### How to extend?
1. Add new agent in `dental_agent/agents/`
2. Add new tools in `dental_agent/tools/`
3. Update supervisor routing logic
4. Add new state fields in `state.py`

### Error Handling
- Slot availability is checked before booking
- User confirmation before cancellations
- Graceful handling of missing information

---

## Technology Comparison: Agent Frameworks

### Why LangGraph? (What this project uses)

| Feature | LangGraph |
|---------|----------|
| **State Management** | Built-in state handling across agent transitions |
| **Flexibility** | Easy to add new agents and workflows |
| **Debugging** | Visual graph representation for debugging |
| **Control Flow** | Fine-grained control over agent routing |
| **Use Case** | Complex multi-agent workflows with state |

### Framework Comparison

| Framework | Best For | Pros | Cons |
|-----------|----------|------|------|
| **LangGraph** | Multi-agent workflows with state | State management, debugging, flexible routing | More complex setup |
| **AutoGen** | Conversational AI, multi-agent chat | Easy to set up, good for chat-based agents | Less control over state |
| **CrewAI** | Role-based agent teams | Simple role definitions, good for team workflows | Less flexible than LangGraph |
| **DeepAgents** | Research-focused agents | Good for research tasks | Limited documentation |
| **SmolAgents** | Lightweight agents | Simple, minimal dependencies | Less feature-rich |
| **LlamaIndex** | RAG and data indexing | Excellent for data retrieval | Not primarily for agent workflows |
| **LangChain** | General LLM applications | Mature ecosystem, many integrations | Can be verbose |

### When to Choose Each

- **LangGraph**: When you need complex state management and multi-agent coordination
- **AutoGen**: For conversational AI and simple agent interactions
- **CrewAI**: For role-based team simulations
- **LlamaIndex**: For RAG applications and data indexing
- **LangChain**: For general LLM application development

### This Project's Choice: LangGraph

This project uses **LangGraph** because:
1. It needs to manage state across multiple agent types (booking, cancellation, rescheduling)
2. The supervisor pattern requires fine-grained control over routing
3. State persistence is important for conversation context
4. Debugging capabilities help with complex workflows