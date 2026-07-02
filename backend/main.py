import os
from datetime import date, timedelta
from agents import Agent, Runner, function_tool
from agents.extensions.memory.sqlalchemy_session import SQLAlchemySession
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY or not DATABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and DATABASE_URL must be set."
    )

app = FastAPI(title="Appointment Booking AI Agent")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


def save_appointment(customer_name: str, appointment_date: str, appointment_time: str):
    """Save an appointment to Supabase."""

    response = (
        supabase.table("appointments")
        .insert(
            {
                "customer_name": customer_name,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
            }
        )
        .execute()
    )

    print("Supabase response:", response)

    return response

def get_booked_appointments():
    """Retrieve all booked appointments from Supabase."""

    response = (
        supabase.table("appointments")
        .select("*")
        .execute()
    )

    return response.data

def build_available_slots():
    times = ["09:00", "10:30", "14:00", "15:30"]
    slots = []
    current_day = date.today()

    while len(slots) < 12:
        current_day += timedelta(days=1)

        if current_day.weekday() >= 5:
            continue

        for appointment_time in times:
            slots.append(
                {
                    "date": current_day.isoformat(),
                    "time": appointment_time,
                }
            )

    return slots


@function_tool
def check_available_slots() -> str:
    """Check which appointment slots are still available."""
    available_slots = build_available_slots()
    booked_appointments = get_booked_appointments()

    booked_pairs = [
        (appointment["appointment_date"], appointment["appointment_time"])
        for appointment in booked_appointments
    ]

    open_slots = [
        slot
        for slot in available_slots
        if (slot["date"], slot["time"]) not in booked_pairs
    ]

    if not open_slots:
        return "There are no available appointment slots right now."

    slot_text = ", ".join(
        f"{slot['date']} at {slot['time']}" for slot in open_slots[:8]
    )

    return f"Available slots: {slot_text}"


@function_tool
def book_appointment(customer_name: str, appointment_date: str, appointment_time: str) -> str:
    """Book an appointment using the customer's name, date, and time."""
    available_slots = build_available_slots()

    is_valid_slot = any(
        slot["date"] == appointment_date and slot["time"] == appointment_time
        for slot in available_slots
    )

    if not is_valid_slot:
        return "That slot is not available. Please ask me to show available slots."

    booked_appointments = get_booked_appointments()

    for appointment in booked_appointments:
        same_date = appointment["appointment_date"] == appointment_date
        same_time = appointment["appointment_time"] == appointment_time

        if same_date and same_time:
            return f"Sorry, {appointment_date} at {appointment_time} is already booked."

    save_appointment(
        customer_name,
        appointment_date,
        appointment_time,
    )

    return f"Booked appointment for {customer_name} on {appointment_date} at {appointment_time}."


@function_tool
def list_booked_appointments() -> str:
    """List all currently booked appointments."""

    booked_appointments = get_booked_appointments()

    if not booked_appointments:
        return "There are no booked appointments yet."

    appointment_text = "; ".join(
        f"{appointment['customer_name']} on {appointment['appointment_date']} at {appointment['appointment_time']}"
        for appointment in booked_appointments
    )

    return f"Booked appointments: {appointment_text}"


session = SQLAlchemySession.from_url(
    session_id="default",
    url=DATABASE_URL,
    create_tables=True,
)

booking_agent = Agent(
    name="Appointment Booking Assistant",
    instructions=(
        "You are a friendly appointment booking assistant. "
        "Help the user check available slots, book appointments, and list booked appointments. "
        "Before booking, collect the customer's name, appointment date, and appointment time. "
        "Use the tools whenever the user asks about availability or bookings."
    ),
    tools=[
        check_available_slots,
        book_appointment,
        list_booked_appointments,
    ],
)


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "message": "Appointment Booking AI Agent API is running.",
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        result = await Runner.run(booking_agent, request.message, session=session)
        return ChatResponse(reply=result.final_output)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))