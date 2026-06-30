import os
from datetime import date, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app = FastAPI(title="Appointment Booking AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


booked_appointments = []


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


def check_available_slots():
    available_slots = build_available_slots()

    booked_pairs = [
        (appointment["date"], appointment["time"])
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


def book_appointment(customer_name, appointment_date, appointment_time):
    available_slots = build_available_slots()

    is_valid_slot = any(
        slot["date"] == appointment_date and slot["time"] == appointment_time
        for slot in available_slots
    )

    if not is_valid_slot:
        return "That slot is not available. Please ask me to show available slots."

    for appointment in booked_appointments:
        same_date = appointment["date"] == appointment_date
        same_time = appointment["time"] == appointment_time

        if same_date and same_time:
            return f"Sorry, {appointment_date} at {appointment_time} is already booked."

    booked_appointments.append(
        {
            "customer_name": customer_name,
            "date": appointment_date,
            "time": appointment_time,
        }
    )

    return f"Booked appointment for {customer_name} on {appointment_date} at {appointment_time}."


def list_booked_appointments():
    if not booked_appointments:
        return "There are no booked appointments yet."

    appointment_text = "; ".join(
        f"{appointment['customer_name']} on {appointment['date']} at {appointment['time']}"
        for appointment in booked_appointments
    )

    return f"Booked appointments: {appointment_text}"


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

    message = request.message.lower()

    if "available" in message or "slot" in message:
        reply = check_available_slots()
    elif "booked" in message or "appointments" in message:
        reply = list_booked_appointments()
    else:
        reply = (
            "Booking logic is working. Ask me for available slots. "
            "The AI Agent will understand natural booking requests in the next step."
        )

    return ChatResponse(reply=reply)