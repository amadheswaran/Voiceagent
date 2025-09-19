#!/usr/bin/env python3
"""
Google Calendar Integration for AI Voice Agent
Sync appointments with Google Calendar and check availability
"""

import datetime
import json
import os
from typing import Dict, List, Optional, Tuple
from database import DatabaseManager

# Google Calendar imports (install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib)
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False
    print("⚠️  Google Calendar libraries not installed. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

class CalendarIntegration:
    def __init__(self, db_path: str = "voiceagent.db"):
        self.db = DatabaseManager(db_path)
        self.calendar_service = None
        self.calendar_id = None
        self.scopes = ['https://www.googleapis.com/auth/calendar']
        self.credentials_file = 'credentials.json'
        self.token_file = 'token.json'

        # Load configuration
        self.config = self.load_config()

        if GOOGLE_CALENDAR_AVAILABLE:
            self.initialize_calendar()

    def load_config(self) -> Dict:
        """Load calendar configuration"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                return config.get('calendar_settings', {
                    'enabled': False,
                    'calendar_id': 'primary',
                    'sync_direction': 'both',  # 'to_calendar', 'from_calendar', 'both'
                    'auto_sync': True,
                    'conflict_detection': True,
                    'business_calendar_id': None
                })
        except FileNotFoundError:
            return {
                'enabled': False,
                'calendar_id': 'primary',
                'sync_direction': 'both',
                'auto_sync': True,
                'conflict_detection': True
            }

    def initialize_calendar(self):
        """Initialize Google Calendar service"""
        if not GOOGLE_CALENDAR_AVAILABLE:
            print("❌ Google Calendar integration not available")
            return False

        try:
            creds = None

            # Load existing token
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)

            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        print(f"❌ {self.credentials_file} not found. Please download from Google Cloud Console.")
                        return False

                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.scopes)
                    creds = flow.run_local_server(port=0)

                # Save the credentials for the next run
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())

            self.calendar_service = build('calendar', 'v3', credentials=creds)
            self.calendar_id = self.config.get('calendar_id', 'primary')

            print("✅ Google Calendar integration initialized")
            return True

        except Exception as e:
            print(f"❌ Failed to initialize Google Calendar: {e}")
            return False

    def is_enabled(self) -> bool:
        """Check if calendar integration is enabled and working"""
        return (GOOGLE_CALENDAR_AVAILABLE and
                self.calendar_service is not None and
                self.config.get('enabled', False))

    def create_calendar_event(self, appointment: Dict) -> Optional[str]:
        """Create an event in Google Calendar"""
        if not self.is_enabled():
            return None

        try:
            # Parse appointment date and time
            start_datetime = self.parse_appointment_datetime(
                appointment['date'],
                appointment['time']
            )

            # Estimate duration based on service (could be in config)
            duration_minutes = self.get_service_duration(appointment['service'])
            end_datetime = start_datetime + datetime.timedelta(minutes=duration_minutes)

            # Create event object
            event = {
                'summary': f"{appointment['service']} - {appointment['name']}",
                'description': f"""
Appointment Details:
• Client: {appointment['name']}
• Phone: {appointment['user_phone']}
• Service: {appointment['service']}
• Booked via: AI Voice Agent
• Appointment ID: {appointment['id']}
                """.strip(),
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'America/New_York',  # Configure based on business location
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'America/New_York',
                },
                'attendees': [
                    {'email': appointment.get('email', '')},
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 24 hours
                        {'method': 'popup', 'minutes': 120},      # 2 hours
                    ],
                },
                'colorId': '9',  # Blue color for appointments
            }

            # Insert event
            created_event = self.calendar_service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()

            print(f"✅ Calendar event created: {created_event['id']}")

            # Store calendar event ID in database
            self.db.db.execute('''
                UPDATE appointments
                SET notes = COALESCE(notes, '') || ' [Calendar ID: ' || ? || ']'
                WHERE id = ?
            ''', (created_event['id'], appointment['id']))

            return created_event['id']

        except Exception as e:
            print(f"❌ Failed to create calendar event: {e}")
            return None

    def update_calendar_event(self, appointment: Dict, calendar_event_id: str) -> bool:
        """Update an existing calendar event"""
        if not self.is_enabled():
            return False

        try:
            # Get existing event
            event = self.calendar_service.events().get(
                calendarId=self.calendar_id,
                eventId=calendar_event_id
            ).execute()

            # Update event details
            start_datetime = self.parse_appointment_datetime(
                appointment['date'],
                appointment['time']
            )
            duration_minutes = self.get_service_duration(appointment['service'])
            end_datetime = start_datetime + datetime.timedelta(minutes=duration_minutes)

            event.update({
                'summary': f"{appointment['service']} - {appointment['name']}",
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'America/New_York',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'America/New_York',
                },
            })

            # Update the event
            updated_event = self.calendar_service.events().update(
                calendarId=self.calendar_id,
                eventId=calendar_event_id,
                body=event
            ).execute()

            print(f"✅ Calendar event updated: {calendar_event_id}")
            return True

        except Exception as e:
            print(f"❌ Failed to update calendar event: {e}")
            return False

    def delete_calendar_event(self, calendar_event_id: str) -> bool:
        """Delete a calendar event"""
        if not self.is_enabled():
            return False

        try:
            self.calendar_service.events().delete(
                calendarId=self.calendar_id,
                eventId=calendar_event_id
            ).execute()

            print(f"✅ Calendar event deleted: {calendar_event_id}")
            return True

        except Exception as e:
            print(f"❌ Failed to delete calendar event: {e}")
            return False

    def check_availability(self, date: str, time: str, duration_minutes: int = 60) -> bool:
        """Check if a time slot is available in Google Calendar"""
        if not self.is_enabled():
            return True  # Assume available if calendar not connected

        try:
            start_datetime = self.parse_appointment_datetime(date, time)
            end_datetime = start_datetime + datetime.timedelta(minutes=duration_minutes)

            # Query calendar for existing events
            events_result = self.calendar_service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_datetime.isoformat() + 'Z',
                timeMax=end_datetime.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            # Check for conflicts
            for event in events:
                if 'dateTime' in event['start']:
                    event_start = datetime.datetime.fromisoformat(
                        event['start']['dateTime'].replace('Z', '+00:00')
                    )
                    event_end = datetime.datetime.fromisoformat(
                        event['end']['dateTime'].replace('Z', '+00:00')
                    )

                    # Check for overlap
                    if (start_datetime < event_end and end_datetime > event_start):
                        print(f"⚠️  Conflict detected with: {event.get('summary', 'Unknown event')}")
                        return False

            return True

        except Exception as e:
            print(f"❌ Error checking availability: {e}")
            return True  # Assume available on error

    def sync_appointments_to_calendar(self) -> int:
        """Sync all appointments from database to Google Calendar"""
        if not self.is_enabled():
            return 0

        synced_count = 0
        appointments = self.db.get_appointments(status='pending')

        for appointment in appointments:
            # Check if already synced
            if '[Calendar ID:' not in appointment.get('notes', ''):
                calendar_event_id = self.create_calendar_event(appointment)
                if calendar_event_id:
                    synced_count += 1

        print(f"✅ Synced {synced_count} appointments to calendar")
        return synced_count

    def sync_calendar_to_appointments(self) -> int:
        """Sync calendar events to local database (import external bookings)"""
        if not self.is_enabled():
            return 0

        try:
            # Get events from calendar for next 30 days
            now = datetime.datetime.utcnow()
            end_time = now + datetime.timedelta(days=30)

            events_result = self.calendar_service.events().list(
                calendarId=self.calendar_id,
                timeMin=now.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            imported_count = 0

            for event in events:
                if self.is_external_appointment(event):
                    if self.import_calendar_event(event):
                        imported_count += 1

            print(f"✅ Imported {imported_count} external appointments")
            return imported_count

        except Exception as e:
            print(f"❌ Error syncing from calendar: {e}")
            return 0

    def is_external_appointment(self, event: Dict) -> bool:
        """Check if calendar event is an external appointment (not created by our system)"""
        description = event.get('description', '')
        return 'AI Voice Agent' not in description

    def import_calendar_event(self, event: Dict) -> bool:
        """Import a calendar event as an appointment"""
        try:
            start_datetime = datetime.datetime.fromisoformat(
                event['start']['dateTime'].replace('Z', '+00:00')
            )

            # Create appointment record
            appointment_data = {
                'id': f"cal_{event['id'][:8]}",
                'user_phone': 'calendar-import',
                'name': event.get('summary', 'Calendar Import'),
                'service': 'External Booking',
                'date': start_datetime.strftime('%Y-%m-%d'),
                'time': start_datetime.strftime('%I:%M %p'),
                'status': 'confirmed',
                'notes': f"Imported from calendar. Original ID: {event['id']}",
                'created_at': datetime.datetime.now().isoformat()
            }

            from database import Appointment as DBAppointment
            appointment = DBAppointment(**appointment_data)

            return self.db.create_appointment(appointment)

        except Exception as e:
            print(f"❌ Error importing calendar event: {e}")
            return False

    def get_busy_times(self, date: str) -> List[Tuple[str, str]]:
        """Get busy times for a specific date from calendar"""
        if not self.is_enabled():
            return []

        try:
            start_of_day = datetime.datetime.strptime(date, '%Y-%m-%d')
            end_of_day = start_of_day + datetime.timedelta(days=1)

            events_result = self.calendar_service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            busy_times = []

            for event in events:
                if 'dateTime' in event['start']:
                    start_time = datetime.datetime.fromisoformat(
                        event['start']['dateTime'].replace('Z', '+00:00')
                    )
                    end_time = datetime.datetime.fromisoformat(
                        event['end']['dateTime'].replace('Z', '+00:00')
                    )

                    busy_times.append((
                        start_time.strftime('%I:%M %p'),
                        end_time.strftime('%I:%M %p')
                    ))

            return busy_times

        except Exception as e:
            print(f"❌ Error getting busy times: {e}")
            return []

    def parse_appointment_datetime(self, date: str, time: str) -> datetime.datetime:
        """Parse appointment date and time into datetime object"""
        try:
            # Convert 12-hour to 24-hour format if needed
            if 'AM' in time or 'PM' in time:
                time_obj = datetime.datetime.strptime(time, '%I:%M %p').time()
            else:
                time_obj = datetime.datetime.strptime(time, '%H:%M').time()

            date_obj = datetime.datetime.strptime(date, '%Y-%m-%d').date()

            return datetime.datetime.combine(date_obj, time_obj)

        except ValueError as e:
            print(f"❌ Error parsing datetime: {e}")
            # Return a default time if parsing fails
            return datetime.datetime.now()

    def get_service_duration(self, service: str) -> int:
        """Get estimated duration for a service in minutes"""
        durations = {
            'Haircut': 45,
            'Styling': 30,
            'Coloring': 120,
            'Treatment': 60,
            'Special Event': 90
        }
        return durations.get(service, 60)  # Default 60 minutes

    def get_calendar_stats(self) -> Dict:
        """Get calendar integration statistics"""
        try:
            stats = {
                'enabled': self.is_enabled(),
                'calendar_id': self.calendar_id,
                'sync_direction': self.config.get('sync_direction', 'both'),
                'auto_sync': self.config.get('auto_sync', True)
            }

            if self.is_enabled():
                # Get recent events count
                now = datetime.datetime.utcnow()
                week_ago = now - datetime.timedelta(days=7)

                events_result = self.calendar_service.events().list(
                    calendarId=self.calendar_id,
                    timeMin=week_ago.isoformat() + 'Z',
                    timeMax=now.isoformat() + 'Z',
                    singleEvents=True
                ).execute()

                stats['events_last_week'] = len(events_result.get('items', []))

            return stats

        except Exception as e:
            print(f"❌ Error getting calendar stats: {e}")
            return {'enabled': False, 'error': str(e)}

# Example setup instructions
def setup_instructions():
    """Print setup instructions for Google Calendar integration"""
    instructions = """
📅 Google Calendar Integration Setup

1. **Create Google Cloud Project:**
   - Go to https://console.cloud.google.com/
   - Create new project or select existing one
   - Enable Google Calendar API

2. **Create Credentials:**
   - Go to "Credentials" in Google Cloud Console
   - Create "OAuth 2.0 Client ID" for "Desktop application"
   - Download JSON file and save as 'credentials.json'

3. **Install Dependencies:**
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

4. **Configure in config.json:**
   "calendar_settings": {
     "enabled": true,
     "calendar_id": "primary",
     "sync_direction": "both",
     "auto_sync": true,
     "conflict_detection": true
   }

5. **First Run:**
   - Run the app, it will open browser for authentication
   - Grant calendar access permissions
   - token.json will be created automatically

🎉 Your calendar integration will be ready!
    """
    print(instructions)

if __name__ == "__main__":
    setup_instructions()
