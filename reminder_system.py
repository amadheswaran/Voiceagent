#!/usr/bin/env python3
"""
Automated Reminder System for AI Voice Agent
Sends reminders via SMS, email, or webhook notifications
"""

import schedule
import time
import datetime
import threading
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from database import DatabaseManager

class ReminderSystem:
    def __init__(self, db_path: str = "voiceagent.db"):
        self.db = DatabaseManager(db_path)
        self.running = False
        self.thread = None
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Load reminder configuration"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                return config.get('reminder_settings', {
                    'email_enabled': False,
                    'sms_enabled': False,
                    'webhook_enabled': False,
                    'reminder_hours': [24, 2],  # Hours before appointment
                    'business_hours': {'start': 9, 'end': 18}
                })
        except FileNotFoundError:
            return {
                'email_enabled': False,
                'sms_enabled': False,
                'webhook_enabled': False,
                'reminder_hours': [24, 2],
                'business_hours': {'start': 9, 'end': 18}
            }

    def start(self):
        """Start the reminder system"""
        if self.running:
            return

        self.running = True

        # Schedule reminder checks
        schedule.every(30).minutes.do(self.check_and_send_reminders)
        schedule.every().day.at("09:00").do(self.send_daily_reminders)

        # Start background thread
        self.thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.thread.start()

        print("📅 Reminder system started successfully")

    def stop(self):
        """Stop the reminder system"""
        self.running = False
        schedule.clear()
        print("📅 Reminder system stopped")

    def run_scheduler(self):
        """Background scheduler runner"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def check_and_send_reminders(self):
        """Check for appointments that need reminders"""
        try:
            # Get appointments for the next 48 hours that need reminders
            appointments = self.get_appointments_needing_reminders()

            for appointment in appointments:
                self.send_reminder(appointment)

        except Exception as e:
            print(f"Error checking reminders: {e}")

    def get_appointments_needing_reminders(self) -> List[Dict]:
        """Get appointments that need reminders sent"""
        now = datetime.datetime.now()
        appointments_to_remind = []

        # Get all pending appointments
        appointments = self.db.get_appointments(status='pending')

        for appointment in appointments:
            if appointment['reminder_sent']:
                continue

            # Parse appointment datetime
            try:
                apt_datetime = datetime.datetime.strptime(
                    f"{appointment['date']} {self.convert_time_to_24h(appointment['time'])}",
                    "%Y-%m-%d %H:%M"
                )

                # Check if we should send a reminder
                hours_until = (apt_datetime - now).total_seconds() / 3600

                # Send reminder if within configured hours and not sent yet
                for reminder_hour in self.config['reminder_hours']:
                    if abs(hours_until - reminder_hour) < 0.5:  # Within 30 minutes of target
                        appointments_to_remind.append(appointment)
                        break

            except ValueError as e:
                print(f"Error parsing appointment time: {e}")
                continue

        return appointments_to_remind

    def convert_time_to_24h(self, time_str: str) -> str:
        """Convert 12-hour time to 24-hour format"""
        try:
            dt = datetime.datetime.strptime(time_str, "%I:%M %p")
            return dt.strftime("%H:%M")
        except ValueError:
            # Already in 24h format or invalid
            return time_str

    def send_reminder(self, appointment: Dict):
        """Send reminder for an appointment"""
        try:
            user = self.db.get_user(appointment['user_phone'])

            # Create reminder message
            message = self.create_reminder_message(appointment)

            # Send via configured channels
            sent = False

            if self.config.get('sms_enabled') and appointment['user_phone']:
                if self.send_sms_reminder(appointment['user_phone'], message):
                    sent = True

            if self.config.get('email_enabled') and user and user.email:
                if self.send_email_reminder(user.email, message, appointment):
                    sent = True

            if self.config.get('webhook_enabled'):
                if self.send_webhook_reminder(appointment, message):
                    sent = True

            # Mark reminder as sent if any method succeeded
            if sent:
                self.db.mark_reminder_sent(appointment['id'])
                print(f"✅ Reminder sent for appointment {appointment['id']}")
            else:
                print(f"❌ Failed to send reminder for appointment {appointment['id']}")

        except Exception as e:
            print(f"Error sending reminder: {e}")

    def create_reminder_message(self, appointment: Dict) -> str:
        """Create reminder message text"""
        # Calculate time until appointment
        now = datetime.datetime.now()
        apt_date = datetime.datetime.strptime(appointment['date'], "%Y-%m-%d").date()

        if apt_date == now.date():
            time_phrase = "today"
        elif apt_date == (now.date() + datetime.timedelta(days=1)):
            time_phrase = "tomorrow"
        else:
            time_phrase = f"on {apt_date.strftime('%B %d')}"

        message = f"""
🔔 Appointment Reminder

Hi {appointment['name']}!

This is a friendly reminder about your upcoming appointment:

📅 Date: {time_phrase}
🕐 Time: {appointment['time']}
💇 Service: {appointment['service']}
📍 Location: Style Studio, 123 Main Street

If you need to reschedule or cancel, please contact us at least 24 hours in advance.

See you soon!
- Style Studio Team
        """.strip()

        return message

    def send_sms_reminder(self, phone: str, message: str) -> bool:
        """Send SMS reminder (integration placeholder)"""
        try:
            # This is where you'd integrate with Twilio, etc.
            # For now, we'll just log it
            print(f"📱 SMS Reminder to {phone}: {message[:50]}...")

            # Simulate successful send
            return True

        except Exception as e:
            print(f"Error sending SMS reminder: {e}")
            return False

    def send_email_reminder(self, email: str, message: str, appointment: Dict) -> bool:
        """Send email reminder"""
        try:
            # Email configuration (would be in config)
            smtp_server = self.config.get('smtp_server', 'smtp.gmail.com')
            smtp_port = self.config.get('smtp_port', 587)
            email_user = self.config.get('email_user', '')
            email_password = self.config.get('email_password', '')

            if not email_user or not email_password:
                print("Email credentials not configured")
                return False

            # Create email
            msg = MIMEMultipart()
            msg['From'] = email_user
            msg['To'] = email
            msg['Subject'] = f"Appointment Reminder - {appointment['date']} at {appointment['time']}"

            # Add HTML version
            html_message = message.replace('\n', '<br>')
            msg.attach(MIMEText(html_message, 'html'))

            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_user, email_password)
                server.send_message(msg)

            print(f"📧 Email reminder sent to {email}")
            return True

        except Exception as e:
            print(f"Error sending email reminder: {e}")
            return False

    def send_webhook_reminder(self, appointment: Dict, message: str) -> bool:
        """Send webhook reminder to external service"""
        try:
            webhook_url = self.config.get('webhook_url', '')

            if not webhook_url:
                return False

            payload = {
                'type': 'appointment_reminder',
                'appointment': appointment,
                'message': message,
                'timestamp': datetime.datetime.now().isoformat()
            }

            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                print(f"🔗 Webhook reminder sent for appointment {appointment['id']}")
                return True
            else:
                print(f"Webhook failed with status {response.status_code}")
                return False

        except Exception as e:
            print(f"Error sending webhook reminder: {e}")
            return False

    def send_daily_reminders(self):
        """Send daily summary of upcoming appointments"""
        try:
            tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
            appointments = self.db.get_appointments()

            # Filter for tomorrow's appointments
            tomorrow_appointments = [
                apt for apt in appointments
                if apt['date'] == tomorrow and apt['status'] == 'pending'
            ]

            if tomorrow_appointments:
                summary_message = self.create_daily_summary(tomorrow_appointments)

                # Send to business owner/admin
                admin_phone = self.config.get('admin_phone', '')
                admin_email = self.config.get('admin_email', '')

                if admin_phone:
                    self.send_sms_reminder(admin_phone, summary_message)

                if admin_email:
                    self.send_admin_email(admin_email, summary_message, tomorrow_appointments)

                print(f"📊 Daily summary sent: {len(tomorrow_appointments)} appointments tomorrow")

        except Exception as e:
            print(f"Error sending daily summary: {e}")

    def create_daily_summary(self, appointments: List[Dict]) -> str:
        """Create daily appointment summary"""
        message = f"""
📅 Daily Appointment Summary

Tomorrow's Schedule ({len(appointments)} appointments):

"""
        for apt in sorted(appointments, key=lambda x: x['time']):
            message += f"• {apt['time']} - {apt['name']} ({apt['service']})\n"

        message += f"\nHave a great day!\n- AI Assistant"
        return message

    def send_admin_email(self, email: str, message: str, appointments: List[Dict]):
        """Send admin email with appointment details"""
        try:
            # Create HTML table for appointments
            html_table = """
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f2f2f2;">
                    <th>Time</th>
                    <th>Name</th>
                    <th>Phone</th>
                    <th>Service</th>
                    <th>Status</th>
                </tr>
            """

            for apt in sorted(appointments, key=lambda x: x['time']):
                html_table += f"""
                <tr>
                    <td>{apt['time']}</td>
                    <td>{apt['name']}</td>
                    <td>{apt['user_phone']}</td>
                    <td>{apt['service']}</td>
                    <td>{apt['status']}</td>
                </tr>
                """

            html_table += "</table>"

            # Send detailed email (implementation would be similar to send_email_reminder)
            print(f"📧 Admin summary email prepared for {email}")

        except Exception as e:
            print(f"Error preparing admin email: {e}")

    def send_test_reminder(self, appointment_id: str) -> bool:
        """Send a test reminder for debugging"""
        try:
            appointments = self.db.get_appointments()
            appointment = next((apt for apt in appointments if apt['id'] == appointment_id), None)

            if not appointment:
                print(f"Appointment {appointment_id} not found")
                return False

            self.send_reminder(appointment)
            return True

        except Exception as e:
            print(f"Error sending test reminder: {e}")
            return False

    def get_reminder_stats(self) -> Dict:
        """Get reminder system statistics"""
        try:
            appointments = self.db.get_appointments()

            total_appointments = len(appointments)
            reminders_sent = len([apt for apt in appointments if apt['reminder_sent']])
            pending_reminders = len([
                apt for apt in appointments
                if not apt['reminder_sent'] and apt['status'] == 'pending'
            ])

            return {
                'total_appointments': total_appointments,
                'reminders_sent': reminders_sent,
                'pending_reminders': pending_reminders,
                'system_running': self.running
            }

        except Exception as e:
            print(f"Error getting reminder stats: {e}")
            return {}

# Example usage and testing
def test_reminder_system():
    """Test the reminder system"""
    reminder_system = ReminderSystem()

    print("Testing reminder system...")

    # Get stats
    stats = reminder_system.get_reminder_stats()
    print(f"Reminder stats: {stats}")

    # Start system
    reminder_system.start()

    # Wait a bit then stop
    time.sleep(2)
    reminder_system.stop()

if __name__ == "__main__":
    test_reminder_system()
