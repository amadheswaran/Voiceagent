#!/usr/bin/env python3
"""
Database Integration for AI Voice Agent
SQLite database for persistent data storage
"""

import sqlite3
import datetime
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class User:
    phone: str
    name: str = ""
    email: str = ""
    preferences: str = ""  # JSON string
    created_at: str = ""
    last_active: str = ""

@dataclass
class Appointment:
    id: str
    user_phone: str
    name: str
    service: str
    date: str
    time: str
    status: str = "pending"  # pending, confirmed, cancelled, completed
    notes: str = ""
    created_at: str = ""
    reminder_sent: bool = False

@dataclass
class ChatMessage:
    id: int
    user_phone: str
    message: str
    response: str
    timestamp: str
    session_id: str = ""

class DatabaseManager:
    def __init__(self, db_path: str = "voiceagent.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    phone TEXT PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    preferences TEXT,
                    created_at TEXT,
                    last_active TEXT
                )
            ''')

            # Appointments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS appointments (
                    id TEXT PRIMARY KEY,
                    user_phone TEXT,
                    name TEXT,
                    service TEXT,
                    date TEXT,
                    time TEXT,
                    status TEXT DEFAULT 'pending',
                    notes TEXT,
                    created_at TEXT,
                    reminder_sent INTEGER DEFAULT 0,
                    FOREIGN KEY (user_phone) REFERENCES users (phone)
                )
            ''')

            # Chat messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_phone TEXT,
                    message TEXT,
                    response TEXT,
                    timestamp TEXT,
                    session_id TEXT,
                    FOREIGN KEY (user_phone) REFERENCES users (phone)
                )
            ''')

            # Available slots table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS available_slots (
                    date TEXT,
                    time TEXT,
                    is_available INTEGER DEFAULT 1,
                    PRIMARY KEY (date, time)
                )
            ''')

            # Business settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS business_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            conn.commit()

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    # User management
    def create_or_update_user(self, phone: str, name: str = "", email: str = "", preferences: Dict = None) -> User:
        """Create or update user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            now = datetime.datetime.now().isoformat()
            prefs_json = json.dumps(preferences or {})

            cursor.execute('''
                INSERT OR REPLACE INTO users
                (phone, name, email, preferences, created_at, last_active)
                VALUES (?, ?, ?, ?,
                    COALESCE((SELECT created_at FROM users WHERE phone = ?), ?),
                    ?)
            ''', (phone, name, email, prefs_json, phone, now, now))

            conn.commit()

            return User(
                phone=phone,
                name=name,
                email=email,
                preferences=prefs_json,
                created_at=now,
                last_active=now
            )

    def get_user(self, phone: str) -> Optional[User]:
        """Get user by phone"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
            row = cursor.fetchone()

            if row:
                return User(
                    phone=row[0],
                    name=row[1] or "",
                    email=row[2] or "",
                    preferences=row[3] or "{}",
                    created_at=row[4] or "",
                    last_active=row[5] or ""
                )
            return None

    def update_user_activity(self, phone: str):
        """Update user's last activity"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET last_active = ? WHERE phone = ?
            ''', (datetime.datetime.now().isoformat(), phone))
            conn.commit()

    # Appointment management
    def create_appointment(self, appointment: Appointment) -> bool:
        """Create new appointment"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Check if slot is available
                cursor.execute('''
                    SELECT COUNT(*) FROM appointments
                    WHERE date = ? AND time = ? AND status != 'cancelled'
                ''', (appointment.date, appointment.time))

                if cursor.fetchone()[0] > 0:
                    return False  # Slot already taken

                cursor.execute('''
                    INSERT INTO appointments
                    (id, user_phone, name, service, date, time, status, notes, created_at, reminder_sent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    appointment.id,
                    appointment.user_phone,
                    appointment.name,
                    appointment.service,
                    appointment.date,
                    appointment.time,
                    appointment.status,
                    appointment.notes,
                    appointment.created_at or datetime.datetime.now().isoformat(),
                    appointment.reminder_sent
                ))

                conn.commit()
                return True

        except sqlite3.Error as e:
            print(f"Database error creating appointment: {e}")
            return False

    def get_appointments(self, user_phone: str = None, status: str = None) -> List[Dict]:
        """Get appointments with optional filters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = 'SELECT * FROM appointments WHERE 1=1'
            params = []

            if user_phone:
                query += ' AND user_phone = ?'
                params.append(user_phone)

            if status:
                query += ' AND status = ?'
                params.append(status)

            query += ' ORDER BY date, time'

            cursor.execute(query, params)
            rows = cursor.fetchall()

            appointments = []
            for row in rows:
                appointments.append({
                    'id': row[0],
                    'user_phone': row[1],
                    'name': row[2],
                    'service': row[3],
                    'date': row[4],
                    'time': row[5],
                    'status': row[6],
                    'notes': row[7],
                    'created_at': row[8],
                    'reminder_sent': bool(row[9])
                })

            return appointments

    def get_appointments_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get appointments within a specific date range"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = '''
                    SELECT * FROM appointments
                    WHERE date BETWEEN ? AND ?
                    ORDER BY date, time
                '''

                cursor.execute(query, (start_date, end_date))
                rows = cursor.fetchall()

                appointments = []
                for row in rows:
                    appointments.append({
                        'id': row[0],
                        'user_phone': row[1],
                        'name': row[2],
                        'service': row[3],
                        'date': row[4],
                        'time': row[5],
                        'status': row[6],
                        'notes': row[7],
                        'created_at': row[8],
                        'reminder_sent': bool(row[9])
                    })

                return appointments

        except sqlite3.Error as e:
            print(f"Database error in get_appointments_by_date_range: {e}")
            return []

    def update_appointment_status(self, appointment_id: str, status: str) -> bool:
        """Update appointment status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE appointments SET status = ? WHERE id = ?
                ''', (status, appointment_id))

                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.Error as e:
            print(f"Database error updating appointment: {e}")
            return False

    def cancel_appointment(self, appointment_id: str) -> bool:
        """Cancel appointment"""
        return self.update_appointment_status(appointment_id, 'cancelled')

    def get_appointments_for_reminders(self) -> List[Dict]:
        """Get appointments that need reminders"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get appointments for tomorrow that haven't had reminders sent
            tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

            cursor.execute('''
                SELECT * FROM appointments
                WHERE date = ? AND status = 'pending' AND reminder_sent = 0
            ''', (tomorrow,))

            rows = cursor.fetchall()

            appointments = []
            for row in rows:
                appointments.append({
                    'id': row[0],
                    'user_phone': row[1],
                    'name': row[2],
                    'service': row[3],
                    'date': row[4],
                    'time': row[5],
                    'status': row[6],
                    'notes': row[7],
                    'created_at': row[8],
                    'reminder_sent': bool(row[9])
                })

            return appointments

    def mark_reminder_sent(self, appointment_id: str) -> bool:
        """Mark reminder as sent for appointment"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE appointments SET reminder_sent = 1 WHERE id = ?
                ''', (appointment_id,))

                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.Error as e:
            print(f"Database error marking reminder: {e}")
            return False

    # Chat history
    def save_chat_message(self, user_phone: str, message: str, response: str, session_id: str = "") -> bool:
        """Save chat message and response"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO chat_messages
                    (user_phone, message, response, timestamp, session_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    user_phone,
                    message,
                    response,
                    datetime.datetime.now().isoformat(),
                    session_id
                ))

                conn.commit()
                return True

        except sqlite3.Error as e:
            print(f"Database error saving chat message: {e}")
            return False

    def get_chat_history(self, user_phone: str, limit: int = 50) -> List[Dict]:
        """Get chat history for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM chat_messages
                WHERE user_phone = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (user_phone, limit))

            rows = cursor.fetchall()

            messages = []
            for row in rows:
                messages.append({
                    'id': row[0],
                    'user_phone': row[1],
                    'message': row[2],
                    'response': row[3],
                    'timestamp': row[4],
                    'session_id': row[5]
                })

            return list(reversed(messages))  # Return chronological order

    # Available slots management
    def initialize_available_slots(self, slots: Dict[str, List[str]]):
        """Initialize available time slots"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            for date, times in slots.items():
                for time in times:
                    cursor.execute('''
                        INSERT OR IGNORE INTO available_slots (date, time, is_available)
                        VALUES (?, ?, 1)
                    ''', (date, time))

            conn.commit()

    def get_available_slots(self) -> Dict[str, List[str]]:
        """Get available time slots"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT date, time FROM available_slots
                WHERE is_available = 1
                ORDER BY date, time
            ''')

            rows = cursor.fetchall()

            slots = {}
            for date, time in rows:
                if date not in slots:
                    slots[date] = []
                slots[date].append(time)

            return slots

    def book_slot(self, date: str, time: str) -> bool:
        """Mark slot as booked"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE available_slots SET is_available = 0
                    WHERE date = ? AND time = ?
                ''', (date, time))

                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.Error as e:
            print(f"Database error booking slot: {e}")
            return False

    def release_slot(self, date: str, time: str) -> bool:
        """Mark slot as available"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE available_slots SET is_available = 1
                    WHERE date = ? AND time = ?
                ''', (date, time))

                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.Error as e:
            print(f"Database error releasing slot: {e}")
            return False

    # Business settings
    def get_setting(self, key: str, default: str = None) -> str:
        """Get business setting"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM business_settings WHERE key = ?', (key,))
            row = cursor.fetchone()

            return row[0] if row else default

    def set_setting(self, key: str, value: str) -> bool:
        """Set business setting"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO business_settings (key, value)
                    VALUES (?, ?)
                ''', (key, value))

                conn.commit()
                return True

        except sqlite3.Error as e:
            print(f"Database error setting value: {e}")
            return False

    # Analytics and reporting
    def get_user_stats(self) -> Dict:
        """Get user statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Total users
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]

            # Active users (last 7 days)
            week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
            cursor.execute('SELECT COUNT(*) FROM users WHERE last_active > ?', (week_ago,))
            active_users = cursor.fetchone()[0]

            # Total appointments
            cursor.execute('SELECT COUNT(*) FROM appointments')
            total_appointments = cursor.fetchone()[0]

            # Pending appointments
            cursor.execute('SELECT COUNT(*) FROM appointments WHERE status = "pending"')
            pending_appointments = cursor.fetchone()[0]

            return {
                'total_users': total_users,
                'active_users': active_users,
                'total_appointments': total_appointments,
                'pending_appointments': pending_appointments
            }

    def close(self):
        """Close database connection (if needed)"""
        # SQLite connections are automatically closed when using context managers
        pass

# Example usage and testing
def test_database():
    """Test database functionality"""
    db = DatabaseManager("test_voiceagent.db")

    # Test user creation
    user = db.create_or_update_user("555-1234", "John Doe", "john@example.com", {"voice_enabled": True})
    print(f"Created user: {user}")

    # Test appointment creation
    appointment = Appointment(
        id="test-123",
        user_phone="555-1234",
        name="John Doe",
        service="Haircut",
        date="2024-01-15",
        time="2:00 PM",
        created_at=datetime.datetime.now().isoformat()
    )

    success = db.create_appointment(appointment)
    print(f"Appointment created: {success}")

    # Test getting appointments
    appointments = db.get_appointments("555-1234")
    print(f"User appointments: {appointments}")

    # Test chat history
    db.save_chat_message("555-1234", "Hello", "Hi there!", "session-1")
    history = db.get_chat_history("555-1234")
    print(f"Chat history: {history}")

    # Test stats
    stats = db.get_user_stats()
    print(f"Stats: {stats}")

if __name__ == "__main__":
    test_database()
