import os
import json
import datetime
import smtplib
from email.mime.text import MIMEText
import logging
from langchain_core.tools import tool

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Path to the appointments JSON file
APPOINTMENTS_FILE = "appointments.json"

# Function to load appointments from JSON
def load_appointments():
    """Load appointments from the JSON file."""
    if os.path.exists(APPOINTMENTS_FILE):
        with open(APPOINTMENTS_FILE, "r") as file:
            return json.load(file)
    return []

# Function to save appointments to JSON
def save_appointments(appointments):
    """Save appointments to the JSON file."""
    with open(APPOINTMENTS_FILE, "w") as file:
        json.dump(appointments, file, indent=4, default=str)

# Initialize appointments list
APPOINTMENTS = load_appointments()

# Function to send email notifications
def send_email_notification(to_email, subject, message):
    """Send an email notification."""
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    from_email = os.getenv("EMAIL")  # Your email
    password = os.getenv("EMAIL_PASSWORD")  # Email password

    if not from_email or not password:
        logging.error("EMAIL or EMAIL_PASSWORD environment variables are not set.")
        raise ValueError("EMAIL or EMAIL_PASSWORD environment variables are not set.")

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            logging.info("Connecting to SMTP server...")
            server.starttls()
            server.login(from_email, password)
            server.send_message(msg)
            logging.info(f"Email sent to {to_email} with subject: {subject}")
    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {e}")
        raise

# Tool to get the next available appointment
@tool
def get_next_available_appointment():
    """Returns the next available appointment."""
    current_time = datetime.datetime.now()
    while True:
        available_time = current_time + datetime.timedelta(minutes=(30 - current_time.minute % 30))
        if not any(datetime.datetime.fromisoformat(appt["time"]) == available_time for appt in APPOINTMENTS):
            logging.info(f"Next available appointment: {available_time}")
            return f"One appointment available at {available_time}"
        current_time += datetime.timedelta(minutes=30)

# Tool to book an appointment
@tool
def book_appointment(appointment_year: int, appointment_month: int, appointment_day: int,
                     appointment_hour: int, appointment_minute: int, appointment_name: str):
    """Book an appointment at the specified time."""
    time = datetime.datetime(appointment_year, appointment_month, appointment_day, 
                             appointment_hour, appointment_minute)
                             
    # Check for conflicting appointments
    for appointment in APPOINTMENTS:
        if datetime.datetime.fromisoformat(appointment["time"]) == time:
            logging.warning(f"Attempt to book already booked slot: {time}")
            return f"Appointment at {time} is already booked"
    
    # Add the appointment
    new_appointment = {"time": time.isoformat(), "name": appointment_name}
    APPOINTMENTS.append(new_appointment)
    save_appointments(APPOINTMENTS)  # Save to JSON file
    logging.info(f"Appointment booked: {time} with {appointment_name}")
    
    # Send notifications
    subject = "Appointment Confirmation"
    message = f"Your appointment with {appointment_name} is booked for {time}."
    
    try:
        user_email = "user@example.com"  # Replace with dynamic user email retrieval
        send_email_notification(user_email, subject, message)
        logging.info(f"Confirmation email sent to user: {user_email}")
    except Exception as e:
        logging.error(f"Failed to send email notifications: {e}")
        return f"Appointment booked, but email notification failed: {e}"
    
    return f"Appointment booked for {time}."

# Tool to cancel an appointment
@tool
def cancel_appointment(appointment_year: int, appointment_month: int, appointment_day: int,
                       appointment_hour: int, appointment_minute: int):
    """Cancel an appointment at the specified time."""
    time = datetime.datetime(appointment_year, appointment_month, appointment_day,
                             appointment_hour, appointment_minute)
    for appointment in APPOINTMENTS:
        if datetime.datetime.fromisoformat(appointment["time"]) == time:
            APPOINTMENTS.remove(appointment)
            save_appointments(APPOINTMENTS)  # Save to JSON file
            logging.info(f"Appointment canceled: {time}")
            
            # Notify user
            subject = "Appointment Cancellation"
            message = f"Your appointment on {time} has been canceled."
            
            try:
                user_email = "user@example.com"  # Replace with dynamic user email retrieval
                send_email_notification(user_email, subject, message)
                logging.info(f"Cancellation email sent to user: {user_email}")
            except Exception as e:
                logging.error(f"Failed to send cancellation email notifications: {e}")
                return f"Appointment canceled, but email notification failed: {e}"
            
            return f"Appointment at {time} cancelled"
    
    logging.warning(f"No appointment found to cancel at: {time}")
    return f"No appointment found at {time}"