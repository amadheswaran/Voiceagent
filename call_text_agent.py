#!/usr/bin/env python3
"""
Simple Call/Text Agent with Predefined Q&A and Appointment Booking
This agent handles incoming messages and calls with automated responses.
"""

import datetime
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from database import DatabaseManager, Appointment as DBAppointment

class MessageType(Enum):
    TEXT = "text"
    CALL = "call"

class ConversationState(Enum):
    GREETING = "greeting"
    FAQ = "faq"
    BOOKING = "booking"
    CONFIRMATION = "confirmation"
    COMPLETED = "completed"

@dataclass
class Appointment:
    date: str
    time: str
    name: str
    phone: str
    service: str
    status: str = "pending"
    id: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = f"apt_{hash(f'{self.name}{self.phone}{self.date}{self.time}')}"

@dataclass
class UserSession:
    phone_number: str
    state: ConversationState = ConversationState.GREETING
    context: Dict = None
    last_message_time: datetime.datetime = None
    
    def __post_init__(self):
        if not self.context:
            self.context = {}
        if not self.last_message_time:
            self.last_message_time = datetime.datetime.now()

class CallTextAgent:
    def __init__(self, db_path: str = "voiceagent.db"):
        self.sessions: Dict[str, UserSession] = {}
        self.db = DatabaseManager(db_path)
        self.faq_database = self._load_faq()
        self.available_slots = self._generate_available_slots()

        # Initialize database with available slots
        self.db.initialize_available_slots(self.available_slots)
        
    def _load_faq(self) -> Dict[str, str]:
        """Load predefined FAQ responses"""
        return {
            "hours": "We are open Monday-Friday 9AM-6PM, Saturday 10AM-4PM. Closed Sundays.",
            "location": "We're located at 123 Main Street, Downtown. Free parking available.",
            "services": "We offer haircuts, styling, coloring, treatments, and special event styling.",
            "prices": "Haircuts start at $30, styling from $25, coloring from $60. Call for detailed pricing.",
            "cancellation": "Please give us 24 hours notice for cancellations to avoid fees.",
            "walk-ins": "We accept walk-ins but recommend booking ahead to guarantee your preferred time.",
            "payment": "We accept cash, credit cards, and digital payments (Venmo, PayPal, etc.).",
            "first-time": "First-time clients get 10% off! Please arrive 15 minutes early for consultation."
        }
    
    def _generate_available_slots(self) -> Dict[str, List[str]]:
        """Generate available appointment slots for the next 7 days"""
        slots = {}
        today = datetime.date.today()
        
        for i in range(1, 8):  # Next 7 days
            date = today + datetime.timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # Skip Sundays (day 6)
            if date.weekday() == 6:
                continue
                
            # Generate time slots
            if date.weekday() == 5:  # Saturday
                time_slots = ["10:00 AM", "11:00 AM", "12:00 PM", "1:00 PM", "2:00 PM", "3:00 PM"]
            else:  # Monday-Friday
                time_slots = ["9:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", 
                             "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM"]
            
            slots[date_str] = time_slots
        
        return slots
    
    def process_message(self, phone_number: str, message: str, message_type: MessageType = MessageType.TEXT) -> str:
        """Main method to process incoming messages"""
        # Create or update user in database
        user = self.db.get_user(phone_number)
        if not user:
            self.db.create_or_update_user(phone_number)
        else:
            self.db.update_user_activity(phone_number)

        # Get or create user session
        if phone_number not in self.sessions:
            self.sessions[phone_number] = UserSession(phone_number=phone_number)

        session = self.sessions[phone_number]
        session.last_message_time = datetime.datetime.now()
        
        # Route to appropriate handler based on state
        response = ""
        if session.state == ConversationState.GREETING:
            response = self._handle_greeting(session, message)
        elif session.state == ConversationState.FAQ:
            response = self._handle_faq(session, message)
        elif session.state == ConversationState.BOOKING:
            response = self._handle_booking(session, message)
        elif session.state == ConversationState.CONFIRMATION:
            response = self._handle_confirmation(session, message)
        else:
            response = self._handle_greeting(session, message)

        # Save chat message to database
        self.db.save_chat_message(phone_number, message, response, session.phone_number)

        return response
    
    def _handle_greeting(self, session: UserSession, message: str) -> str:
        """Handle initial greeting and route to appropriate service"""
        message_lower = message.lower()
        
        greeting = "Hello! Welcome to Style Studio. I'm your virtual assistant. How can I help you today?\n\n"
        options = "I can help you with:\n1️⃣ Book an appointment\n2️⃣ Answer questions about our services\n3️⃣ Hours and location info\n\nJust type 'book', 'questions', or 'info' to get started!"
        
        # Check for booking intent
        if any(word in message_lower for word in ['book', 'appointment', 'schedule']):
            session.state = ConversationState.BOOKING
            return self._start_booking(session)
        
        # Check for FAQ intent
        elif any(word in message_lower for word in ['question', 'info', 'hours', 'location', 'price', 'service']):
            session.state = ConversationState.FAQ
            return self._show_faq_menu()
        
        # Default greeting
        return greeting + options
    
    def _handle_faq(self, session: UserSession, message: str) -> str:
        """Handle FAQ questions"""
        message_lower = message.lower()
        
        # Check if user wants to book after FAQ
        if any(word in message_lower for word in ['book', 'appointment', 'schedule']):
            session.state = ConversationState.BOOKING
            return self._start_booking(session)
        
        # Search for FAQ matches
        for key, answer in self.faq_database.items():
            if key in message_lower:
                response = f"📋 {answer}\n\n"
                response += "Need anything else? Type 'book' for appointments, or ask another question!"
                return response
        
        # If no specific match, show menu
        return self._show_faq_menu()
    
    def _show_faq_menu(self) -> str:
        """Show FAQ menu options"""
        menu = "❓ What would you like to know?\n\n"
        menu += "• Type 'hours' - Business hours\n"
        menu += "• Type 'location' - Address and parking\n"
        menu += "• Type 'services' - What we offer\n"
        menu += "• Type 'prices' - Pricing information\n"
        menu += "• Type 'cancellation' - Cancellation policy\n"
        menu += "• Type 'payment' - Payment options\n"
        menu += "• Type 'first-time' - New client info\n\n"
        menu += "Or type 'book' to schedule an appointment!"
        return menu
    
    def _start_booking(self, session: UserSession) -> str:
        """Start the booking process"""
        session.context = {'booking_step': 'name'}
        return "📅 Great! I'll help you book an appointment.\n\nFirst, what's your name?"
    
    def _handle_booking(self, session: UserSession, message: str) -> str:
        """Handle the booking conversation flow"""
        step = session.context.get('booking_step', 'name')
        
        if step == 'name':
            session.context['name'] = message.strip()
            session.context['booking_step'] = 'service'
            return f"Nice to meet you, {message.strip()}! What service are you interested in?\n\n• Haircut\n• Styling\n• Coloring\n• Treatment\n• Special Event"
        
        elif step == 'service':
            session.context['service'] = message.strip()
            session.context['booking_step'] = 'date'
            return self._show_available_dates()
        
        elif step == 'date':
            if message.strip() in self.available_slots:
                session.context['date'] = message.strip()
                session.context['booking_step'] = 'time'
                return self._show_available_times(message.strip())
            else:
                return "Please select a valid date from the options above."
        
        elif step == 'time':
            selected_date = session.context['date']
            if message.strip() in self.available_slots[selected_date]:
                session.context['time'] = message.strip()
                session.state = ConversationState.CONFIRMATION
                return self._show_booking_confirmation(session)
            else:
                return "Please select a valid time from the available options."
        
        return "I didn't understand. Let me restart the booking process."
    
    def _show_available_dates(self) -> str:
        """Show available dates for booking with smart suggestions"""
        response = "📅 Please select a date:\n\n"

        # Show next 5 available dates
        available_dates = []
        today = datetime.date.today()

        for i in range(1, 15):  # Check next 14 days
            check_date = today + datetime.timedelta(days=i)
            date_str = check_date.strftime("%Y-%m-%d")

            # Skip Sundays
            if check_date.weekday() == 6:
                continue

            # Check if date has availability
            if date_str in self.available_slots and self.available_slots[date_str]:
                available_dates.append(date_str)

            if len(available_dates) >= 5:
                break

        for date_str in available_dates:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%A, %B %d")

            # Show number of available slots
            slot_count = len(self.available_slots.get(date_str, []))
            slots_text = f"({slot_count} slots available)"

            response += f"• {date_str} ({formatted_date}) {slots_text}\n"

        response += "\nJust type the date (YYYY-MM-DD format) you prefer."
        return response
    
    def _show_available_times(self, date: str) -> str:
        """Show available times for selected date"""
        times = self.available_slots.get(date, [])
        
        response = f"🕐 Available times for {date}:\n\n"
        for time in times:
            response += f"• {time}\n"
        
        response += "\nPlease type your preferred time."
        return response
    
    def _show_booking_confirmation(self, session: UserSession) -> str:
        """Show booking confirmation details"""
        context = session.context
        
        confirmation = "📋 Please confirm your appointment:\n\n"
        confirmation += f"👤 Name: {context['name']}\n"
        confirmation += f"📞 Phone: {session.phone_number}\n"
        confirmation += f"💇 Service: {context['service']}\n"
        confirmation += f"📅 Date: {context['date']}\n"
        confirmation += f"🕐 Time: {context['time']}\n\n"
        confirmation += "Type 'YES' to confirm or 'NO' to cancel."
        
        return confirmation
    
    def _handle_confirmation(self, session: UserSession, message: str) -> str:
        """Handle appointment confirmation"""
        message_lower = message.lower().strip()
        
        if message_lower in ['yes', 'y', 'confirm', 'ok']:
            # Create appointment
            appointment = DBAppointment(
                id=f"apt_{hash(f'{session.context["name"]}{session.phone_number}{session.context["date"]}{session.context["time"]}')}",
                user_phone=session.phone_number,
                name=session.context['name'],
                service=session.context['service'],
                date=session.context['date'],
                time=session.context['time'],
                created_at=datetime.datetime.now().isoformat()
            )

            # Save to database
            success = self.db.create_appointment(appointment)
            if not success:
                return "Sorry, that time slot is no longer available. Please try booking again."

            # Update user info in database if we have a name
            if session.context.get('name'):
                self.db.create_or_update_user(session.phone_number, session.context['name'])

            # Book the slot
            self.db.book_slot(appointment.date, appointment.time)

            # Remove the time slot from available slots cache
            if appointment.date in self.available_slots:
                if appointment.time in self.available_slots[appointment.date]:
                    self.available_slots[appointment.date].remove(appointment.time)
            
            session.state = ConversationState.COMPLETED
            
            response = "✅ Your appointment is confirmed!\n\n"
            response += f"📋 Confirmation ID: {appointment.id}\n"
            response += f"📅 {appointment.date} at {appointment.time}\n"
            response += f"💇 {appointment.service} for {appointment.name}\n\n"
            response += "We'll send you a reminder 24 hours before your appointment. "
            response += "If you need to cancel or reschedule, please call us with 24 hours notice.\n\n"
            response += "Thank you for choosing Style Studio! 💫"
            
            return response
        
        elif message_lower in ['no', 'n', 'cancel']:
            session.state = ConversationState.GREETING
            session.context = {}
            return "No problem! Your appointment was not booked. Feel free to start over anytime. How else can I help you?"
        
        else:
            return "Please type 'YES' to confirm your appointment or 'NO' to cancel."
    
    def get_appointments(self, phone_number: str = None) -> List[Dict]:
        """Get appointments, optionally filtered by phone number"""
        return self.db.get_appointments(phone_number)
    
    def cancel_appointment(self, appointment_id: str) -> bool:
        """Cancel an appointment by ID"""
        # Get appointment details first
        appointments = self.db.get_appointments()
        appointment = next((apt for apt in appointments if apt['id'] == appointment_id), None)

        if appointment and self.db.cancel_appointment(appointment_id):
            # Release the slot
            self.db.release_slot(appointment['date'], appointment['time'])

            # Add the time slot back to available slots cache
            if appointment['date'] in self.available_slots:
                if appointment['time'] not in self.available_slots[appointment['date']]:
                    self.available_slots[appointment['date']].append(appointment['time'])
                    self.available_slots[appointment['date']].sort()
            return True
        return False

    def get_chat_history(self, phone_number: str, limit: int = 50) -> List[Dict]:
        """Get chat history for user"""
        return self.db.get_chat_history(phone_number, limit)

    def get_user_stats(self) -> Dict:
        """Get user statistics"""
        return self.db.get_user_stats()

# Example usage and testing
def main():
    """Test the agent with sample conversations"""
    agent = CallTextAgent()
    
    print("=== Call/Text Agent Demo ===\n")
    
    # Simulate conversation
    test_conversations = [
        ("555-0123", "Hi there!"),
        ("555-0123", "book"),
        ("555-0123", "John Smith"),
        ("555-0123", "Haircut"),
        ("555-0123", "2024-01-15"),
        ("555-0123", "2:00 PM"),
        ("555-0123", "yes"),
    ]
    
    for phone, message in test_conversations:
        print(f"User ({phone}): {message}")
        response = agent.process_message(phone, message)
        print(f"Agent: {response}\n")
        print("-" * 50 + "\n")
    
    # Show booked appointments
    print("=== Booked Appointments ===")
    appointments = agent.get_appointments()
    for apt in appointments:
        print(f"ID: {apt['id']}")
        print(f"Name: {apt['name']} ({apt['phone']})")
        print(f"Service: {apt['service']}")
        print(f"Date/Time: {apt['date']} at {apt['time']}")
        print(f"Status: {apt['status']}\n")

if __name__ == "__main__":
    main()
