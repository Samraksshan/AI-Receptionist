import os
import json
import hashlib
import datetime
import streamlit as st
from dotenv import load_dotenv
from tools import send_email_notification

# Load environment variables
load_dotenv()

# File paths
USER_DATABASE_FILE = "user_data.json"
DOCTORS_DATABASE_FILE = "doctors.json"
APPOINTMENTS_DATABASE_FILE = "appointments.json"
DISEASE_SPECIALTIES_FILE = "disease_specialties.json"

# Password handling
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# User database management
def load_user_database():
    """Load the user database."""
    if os.path.exists(USER_DATABASE_FILE):
        with open(USER_DATABASE_FILE, "r") as file:
            return json.load(file)
    return {}

def save_user_database(data):
    """Save the user database."""
    with open(USER_DATABASE_FILE, "w") as file:
        json.dump(data, file, indent=4)

# Doctors database management
def load_doctors_database():
    """Load the doctors' database."""
    if os.path.exists(DOCTORS_DATABASE_FILE):
        with open(DOCTORS_DATABASE_FILE, "r") as file:
            return json.load(file)
    return []

def save_doctors_database(data):
    """Save the doctors' database."""
    with open(DOCTORS_DATABASE_FILE, "w") as file:
        json.dump(data, file, indent=4)

# Appointment database management
def load_appointments_database():
    """Load the appointments database."""
    if os.path.exists(APPOINTMENTS_DATABASE_FILE):
        with open(APPOINTMENTS_DATABASE_FILE, "r") as file:
            return json.load(file)
    return []

def save_appointments_database(data):
    """Save the appointments database."""
    with open(APPOINTMENTS_DATABASE_FILE, "w") as file:
        json.dump(data, file, indent=4)

# Disease specialties management
def load_disease_specialties():
    """Load the disease specialties mapping."""
    if os.path.exists(DISEASE_SPECIALTIES_FILE):
        with open(DISEASE_SPECIALTIES_FILE, "r") as file:
            return json.load(file)
    return {}

# Initializing databases
USER_DATABASE = load_user_database()
DOCTORS_DATABASE = load_doctors_database()
APPOINTMENTS_DATABASE = load_appointments_database()
DISEASE_SPECIALTIES = load_disease_specialties()

# User authentication and registration
def authenticate_user(email, password):
    """Authenticate a user."""
    if email in USER_DATABASE:
        return USER_DATABASE[email]["password"] == hash_password(password)
    return False

def register_user(email, password):
    """Register a new user."""
    if email in USER_DATABASE:
        return False, "User already exists."
    USER_DATABASE[email] = {"password": hash_password(password)}
    save_user_database(USER_DATABASE)
    return True, "User registered successfully."

# Appointment management
def suggest_appointment_time():
    """Suggest the next available time for an appointment."""
    current_time = datetime.datetime.now()
    suggested_time = current_time + datetime.timedelta(hours=1)  # Next hour
    return suggested_time

def check_doctor_availability(doctor_name, appointment_time):
    """Check if the doctor is available at the given time for a half-hour slot."""
    # Check if any appointment overlaps with the selected half-hour time
    start_time = appointment_time
    end_time = appointment_time + datetime.timedelta(minutes=30)
    
    for appointment in APPOINTMENTS_DATABASE:
        # Convert the stored appointment time back into a datetime object
        appt_time = datetime.datetime.fromisoformat(appointment["time"])
        appt_end_time = appt_time + datetime.timedelta(minutes=30)
        
        # Check for overlap: if the appointment times overlap with the new time slot
        if appointment["doctor"] == doctor_name and (
            (start_time < appt_end_time and start_time >= appt_time) or 
            (end_time > appt_time and end_time <= appt_end_time)
        ):
            return False  # Doctor is not available for the entire half-hour slot
    return True

def book_appointment(user_email, doctor_name, disease, appointment_time):
    """Book an appointment."""
    if not check_doctor_availability(doctor_name, appointment_time):
        st.error(f"Sorry, {doctor_name} is not available at this time. Please choose another time.")
        return
    
    APPOINTMENTS_DATABASE.append({
        "user": user_email,
        "doctor": doctor_name,
        "disease": disease,
        "time": appointment_time.isoformat(),
    })
    save_appointments_database(APPOINTMENTS_DATABASE)
    st.success(
        f"Appointment with {doctor_name} for '{disease}' booked on "
        f"{appointment_time.strftime('%Y-%m-%d %H:%M')}."
    )
    send_email_notification(
        user_email,
        "Appointment Confirmation",
        f"Your appointment with {doctor_name} for {disease} is confirmed on "
        f"{appointment_time.strftime('%Y-%m-%d %H:%M')}."
    )

# Helper function: Get doctors by disease
def get_doctors_by_disease(disease):
    """Retrieve doctors based on the disease (specialty)."""
    specialty = DISEASE_SPECIALTIES.get(disease.lower())
    if not specialty:
        return []
    return [doctor for doctor in DOCTORS_DATABASE if doctor["specialty"] == specialty]

# App state
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""

# Display UI
if not st.session_state["authenticated"]:
    st.title("Doctor Appointment Booking System")
    st.subheader("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate_user(email, password):
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = email
            st.success("Logged in successfully.")
        else:
            st.error("Invalid email or password.")
    
    st.subheader("Register")
    new_email = st.text_input("New Email")
    new_password = st.text_input("New Password", type="password")
    if st.button("Register"):
        success, message = register_user(new_email, new_password)
        if success:
            st.success(message)
        else:
            st.error(message)

else:
    st.title(f"Welcome {st.session_state['user_email']}")
    st.subheader("Book an Appointment")
    disease = st.text_input("Enter disease (e.g., fever, cold, etc.)")
    doctors = get_doctors_by_disease(disease)
    
    if doctors:
        doctor_names = [doctor["name"] for doctor in doctors]
        doctor_name = st.selectbox("Choose a doctor", doctor_names)
        suggested_time = suggest_appointment_time()

        # Allow the user to modify the suggested appointment time
        st.write("Suggested Appointment Time")
        suggested_date = suggested_time.date()
        suggested_time_input = suggested_time.time()
        
        # User input for modifying time
        date = st.date_input("Appointment Date", value=suggested_date)
        time = st.time_input("Appointment Time", value=suggested_time_input)

        # Combine date and time to form the complete datetime object
        user_time = datetime.datetime.combine(date, time)

        # Debugging: Display the selected date and time
        st.write(f"Selected Time: {user_time}")

        if st.button("Book Appointment"):
            book_appointment(st.session_state["user_email"], doctor_name, disease, user_time)
    else:
        st.warning(f"No doctors found for '{disease}'")
