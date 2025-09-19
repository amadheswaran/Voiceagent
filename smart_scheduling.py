#!/usr/bin/env python3
"""
Smart Scheduling System for AI Voice Agent
Intelligent appointment scheduling with conflict detection and optimization
"""

import datetime
import json
from typing import Dict, List, Optional, Tuple, Set
from database import DatabaseManager
from calendar_integration import CalendarIntegration

class SmartScheduler:
    def __init__(self, db_path: str = "voiceagent.db"):
        self.db = DatabaseManager(db_path)
        self.calendar = CalendarIntegration(db_path)
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Load scheduling configuration"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                return config.get('scheduling_settings', {
                    'buffer_minutes': 15,  # Buffer between appointments
                    'max_daily_appointments': 8,
                    'lunch_break': {'start': '12:00', 'end': '13:00'},
                    'preferred_slots': ['9:00 AM', '10:00 AM', '2:00 PM', '3:00 PM'],
                    'avoid_slots': ['12:00 PM'],  # Lunch time
                    'auto_suggest_alternatives': True,
                    'optimize_schedule': True
                })
        except FileNotFoundError:
            return {
                'buffer_minutes': 15,
                'max_daily_appointments': 8,
                'lunch_break': {'start': '12:00', 'end': '13:00'},
                'preferred_slots': ['9:00 AM', '10:00 AM', '2:00 PM', '3:00 PM'],
                'avoid_slots': ['12:00 PM'],
                'auto_suggest_alternatives': True,
                'optimize_schedule': True
            }

    def check_appointment_conflicts(self, date: str, time: str, service: str, exclude_id: str = None) -> Dict:
        """Comprehensive conflict detection"""
        conflicts = {
            'has_conflict': False,
            'conflict_type': None,
            'details': [],
            'suggestions': []
        }

        try:
            # 1. Check database conflicts
            db_conflicts = self.check_database_conflicts(date, time, exclude_id)
            if db_conflicts:
                conflicts['has_conflict'] = True
                conflicts['conflict_type'] = 'existing_appointment'
                conflicts['details'].extend(db_conflicts)

            # 2. Check calendar conflicts
            if self.calendar.is_enabled():
                duration = self.get_service_duration(service)
                if not self.calendar.check_availability(date, time, duration):
                    conflicts['has_conflict'] = True
                    conflicts['conflict_type'] = 'calendar_conflict'
                    conflicts['details'].append('Conflicts with calendar event')

            # 3. Check business rules
            business_conflicts = self.check_business_rules(date, time, service)
            if business_conflicts:
                conflicts['has_conflict'] = True
                conflicts['conflict_type'] = 'business_rule'
                conflicts['details'].extend(business_conflicts)

            # 4. Generate suggestions if conflicts exist
            if conflicts['has_conflict'] and self.config['auto_suggest_alternatives']:
                conflicts['suggestions'] = self.suggest_alternative_times(date, service)

            return conflicts

        except Exception as e:
            print(f"Error checking conflicts: {e}")
            return {'has_conflict': False, 'error': str(e)}

    def check_database_conflicts(self, date: str, time: str, exclude_id: str = None) -> List[str]:
        """Check for conflicts in existing appointments"""
        conflicts = []

        try:
            appointments = self.db.get_appointments()

            for apt in appointments:
                if apt['id'] == exclude_id:
                    continue

                if apt['date'] == date and apt['status'] in ['pending', 'confirmed']:
                    # Check for exact time match
                    if apt['time'] == time:
                        conflicts.append(f"Exact time conflict with {apt['name']} ({apt['service']})")

                    # Check for buffer time conflicts
                    elif self.times_too_close(apt['time'], time):
                        conflicts.append(f"Too close to appointment with {apt['name']} at {apt['time']}")

            return conflicts

        except Exception as e:
            print(f"Error checking database conflicts: {e}")
            return []

    def check_business_rules(self, date: str, time: str, service: str) -> List[str]:
        """Check business rules and constraints"""
        violations = []

        try:
            # 1. Check if it's a business day
            date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
            if date_obj.weekday() == 6:  # Sunday
                violations.append("We are closed on Sundays")

            # 2. Check business hours
            time_obj = self.parse_time(time)
            business_hours = self.get_business_hours(date_obj.strftime('%A').lower())

            if not self.is_within_business_hours(time_obj, business_hours):
                violations.append(f"Outside business hours ({business_hours['open']} - {business_hours['close']})")

            # 3. Check lunch break
            if self.is_during_lunch_break(time):
                violations.append("During lunch break (12:00 PM - 1:00 PM)")

            # 4. Check daily appointment limit
            daily_count = len([apt for apt in self.db.get_appointments()
                             if apt['date'] == date and apt['status'] in ['pending', 'confirmed']])

            if daily_count >= self.config['max_daily_appointments']:
                violations.append(f"Daily appointment limit reached ({self.config['max_daily_appointments']})")

            # 5. Check service-specific rules
            service_violations = self.check_service_rules(service, time, date)
            violations.extend(service_violations)

            return violations

        except Exception as e:
            print(f"Error checking business rules: {e}")
            return []

    def suggest_alternative_times(self, date: str, service: str, count: int = 3) -> List[Dict]:
        """Suggest alternative appointment times"""
        suggestions = []

        try:
            # Get available slots for the day
            available_slots = self.get_available_slots(date)

            # If no slots available today, check next few days
            if not available_slots:
                for i in range(1, 8):  # Check next 7 days
                    next_date = (datetime.datetime.strptime(date, '%Y-%m-%d') +
                               datetime.timedelta(days=i)).strftime('%Y-%m-%d')

                    next_day_slots = self.get_available_slots(next_date)
                    if next_day_slots:
                        for slot in next_day_slots[:count]:
                            suggestions.append({
                                'date': next_date,
                                'time': slot,
                                'reason': f'Available {self.get_day_name(next_date)}',
                                'priority': 'alternative_day'
                            })
                        break

            else:
                # Prioritize preferred slots
                preferred_slots = [slot for slot in available_slots
                                 if slot in self.config['preferred_slots']]

                # Add preferred slots first
                for slot in preferred_slots[:count]:
                    suggestions.append({
                        'date': date,
                        'time': slot,
                        'reason': 'Preferred time slot',
                        'priority': 'preferred'
                    })

                # Fill remaining with other available slots
                remaining_count = count - len(suggestions)
                other_slots = [slot for slot in available_slots
                             if slot not in preferred_slots]

                for slot in other_slots[:remaining_count]:
                    suggestions.append({
                        'date': date,
                        'time': slot,
                        'reason': 'Available time slot',
                        'priority': 'available'
                    })

            return suggestions

        except Exception as e:
            print(f"Error suggesting alternatives: {e}")
            return []

    def get_available_slots(self, date: str) -> List[str]:
        """Get all available time slots for a date"""
        try:
            # Get business hours for the day
            date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
            day_name = date_obj.strftime('%A').lower()
            business_hours = self.get_business_hours(day_name)

            if not business_hours['open']:
                return []  # Closed day

            # Generate all possible slots
            all_slots = self.generate_time_slots(business_hours)

            # Filter out unavailable slots
            available_slots = []

            for slot in all_slots:
                conflicts = self.check_appointment_conflicts(date, slot, 'Haircut')  # Default service for checking
                if not conflicts['has_conflict']:
                    available_slots.append(slot)

            return available_slots

        except Exception as e:
            print(f"Error getting available slots: {e}")
            return []

    def generate_time_slots(self, business_hours: Dict, interval_minutes: int = 60) -> List[str]:
        """Generate time slots based on business hours"""
        slots = []

        try:
            start_time = datetime.datetime.strptime(business_hours['open'], '%I:%M %p').time()
            end_time = datetime.datetime.strptime(business_hours['close'], '%I:%M %p').time()

            current_time = datetime.datetime.combine(datetime.date.today(), start_time)
            end_datetime = datetime.datetime.combine(datetime.date.today(), end_time)

            while current_time < end_datetime:
                time_str = current_time.strftime('%I:%M %p')

                # Skip lunch break
                if not self.is_during_lunch_break(time_str):
                    slots.append(time_str)

                current_time += datetime.timedelta(minutes=interval_minutes)

            return slots

        except Exception as e:
            print(f"Error generating time slots: {e}")
            return []

    def optimize_daily_schedule(self, date: str) -> Dict:
        """Optimize the schedule for a given day"""
        try:
            appointments = [apt for apt in self.db.get_appointments()
                          if apt['date'] == date and apt['status'] in ['pending', 'confirmed']]

            if not appointments:
                return {'optimized': False, 'reason': 'No appointments to optimize'}

            # Sort appointments by time
            appointments.sort(key=lambda x: self.parse_time(x['time']))

            optimization_report = {
                'optimized': False,
                'current_schedule': appointments,
                'suggestions': [],
                'gaps': [],
                'efficiency_score': 0
            }

            # Identify gaps between appointments
            gaps = self.find_schedule_gaps(appointments)
            optimization_report['gaps'] = gaps

            # Calculate efficiency score
            efficiency_score = self.calculate_schedule_efficiency(appointments)
            optimization_report['efficiency_score'] = efficiency_score

            # Generate optimization suggestions
            if efficiency_score < 80:  # If efficiency is low
                suggestions = self.generate_optimization_suggestions(appointments, gaps)
                optimization_report['suggestions'] = suggestions
                optimization_report['optimized'] = len(suggestions) > 0

            return optimization_report

        except Exception as e:
            print(f"Error optimizing schedule: {e}")
            return {'optimized': False, 'error': str(e)}

    def find_schedule_gaps(self, appointments: List[Dict]) -> List[Dict]:
        """Find gaps in the schedule"""
        gaps = []

        try:
            for i in range(len(appointments) - 1):
                current_apt = appointments[i]
                next_apt = appointments[i + 1]

                current_end = self.add_service_duration(current_apt['time'], current_apt['service'])
                next_start = self.parse_time(next_apt['time'])

                gap_minutes = (next_start.hour * 60 + next_start.minute) - (current_end.hour * 60 + current_end.minute)

                if gap_minutes > self.config['buffer_minutes'] * 2:  # Significant gap
                    gaps.append({
                        'start_time': current_end.strftime('%I:%M %p'),
                        'end_time': next_apt['time'],
                        'duration_minutes': gap_minutes,
                        'type': 'between_appointments'
                    })

            return gaps

        except Exception as e:
            print(f"Error finding gaps: {e}")
            return []

    def calculate_schedule_efficiency(self, appointments: List[Dict]) -> float:
        """Calculate schedule efficiency score (0-100)"""
        try:
            if not appointments:
                return 100

            total_work_time = sum(self.get_service_duration(apt['service']) for apt in appointments)

            first_apt_time = self.parse_time(appointments[0]['time'])
            last_apt = appointments[-1]
            last_apt_end = self.add_service_duration(last_apt['time'], last_apt['service'])

            total_span_minutes = (last_apt_end.hour * 60 + last_apt_end.minute) - (first_apt_time.hour * 60 + first_apt_time.minute)

            if total_span_minutes == 0:
                return 100

            efficiency = (total_work_time / total_span_minutes) * 100
            return min(100, efficiency)

        except Exception as e:
            print(f"Error calculating efficiency: {e}")
            return 0

    def generate_optimization_suggestions(self, appointments: List[Dict], gaps: List[Dict]) -> List[str]:
        """Generate suggestions to optimize the schedule"""
        suggestions = []

        try:
            # Suggest filling large gaps
            for gap in gaps:
                if gap['duration_minutes'] >= 60:  # 1 hour or more
                    suggestions.append(f"Consider booking a {gap['duration_minutes']}-minute service between {gap['start_time']} and {gap['end_time']}")

            # Suggest grouping similar services
            services = [apt['service'] for apt in appointments]
            if len(set(services)) > 1:
                suggestions.append("Consider grouping similar services together for better workflow")

            # Suggest avoiding early/late appointments if possible
            first_time = self.parse_time(appointments[0]['time'])
            if first_time.hour < 10:
                suggestions.append("Consider starting appointments later for better work-life balance")

            return suggestions

        except Exception as e:
            print(f"Error generating suggestions: {e}")
            return []

    # Helper methods
    def times_too_close(self, time1: str, time2: str) -> bool:
        """Check if two times are too close (within buffer)"""
        try:
            t1 = self.parse_time(time1)
            t2 = self.parse_time(time2)

            diff_minutes = abs((t1.hour * 60 + t1.minute) - (t2.hour * 60 + t2.minute))
            return diff_minutes < self.config['buffer_minutes']

        except Exception:
            return False

    def parse_time(self, time_str: str) -> datetime.time:
        """Parse time string to time object"""
        try:
            if 'AM' in time_str or 'PM' in time_str:
                return datetime.datetime.strptime(time_str, '%I:%M %p').time()
            else:
                return datetime.datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            return datetime.time(9, 0)  # Default to 9 AM

    def get_business_hours(self, day: str) -> Dict:
        """Get business hours for a specific day"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                hours = config.get('business_hours', {})

                if day in hours and hours[day] != "Closed":
                    parts = hours[day].split(' - ')
                    return {'open': parts[0], 'close': parts[1]}
                else:
                    return {'open': None, 'close': None}

        except Exception:
            return {'open': '9:00 AM', 'close': '6:00 PM'}  # Default hours

    def is_within_business_hours(self, time_obj: datetime.time, business_hours: Dict) -> bool:
        """Check if time is within business hours"""
        if not business_hours['open']:
            return False

        try:
            open_time = datetime.datetime.strptime(business_hours['open'], '%I:%M %p').time()
            close_time = datetime.datetime.strptime(business_hours['close'], '%I:%M %p').time()

            return open_time <= time_obj <= close_time

        except Exception:
            return True

    def is_during_lunch_break(self, time: str) -> bool:
        """Check if time is during lunch break"""
        try:
            lunch = self.config['lunch_break']
            time_obj = self.parse_time(time)
            lunch_start = datetime.datetime.strptime(lunch['start'], '%H:%M').time()
            lunch_end = datetime.datetime.strptime(lunch['end'], '%H:%M').time()

            return lunch_start <= time_obj <= lunch_end

        except Exception:
            return False

    def get_service_duration(self, service: str) -> int:
        """Get service duration in minutes"""
        durations = {
            'Haircut': 45,
            'Styling': 30,
            'Coloring': 120,
            'Treatment': 60,
            'Special Event': 90
        }
        return durations.get(service, 60)

    def add_service_duration(self, time_str: str, service: str) -> datetime.time:
        """Add service duration to a time"""
        try:
            time_obj = self.parse_time(time_str)
            duration_minutes = self.get_service_duration(service)

            start_datetime = datetime.datetime.combine(datetime.date.today(), time_obj)
            end_datetime = start_datetime + datetime.timedelta(minutes=duration_minutes)

            return end_datetime.time()

        except Exception:
            return datetime.time(10, 0)  # Default fallback

    def check_service_rules(self, service: str, time: str, date: str) -> List[str]:
        """Check service-specific scheduling rules"""
        violations = []

        try:
            # Coloring services shouldn't be scheduled late in the day
            if service == 'Coloring':
                time_obj = self.parse_time(time)
                if time_obj.hour >= 15:  # After 3 PM
                    violations.append("Coloring services should be scheduled earlier in the day (before 3 PM)")

            # Special events need more preparation time
            if service == 'Special Event':
                date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                if (date_obj - datetime.datetime.now()).days < 3:
                    violations.append("Special event services require at least 3 days advance booking")

            return violations

        except Exception:
            return []

    def get_day_name(self, date: str) -> str:
        """Get day name from date string"""
        try:
            date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
            return date_obj.strftime('%A')
        except Exception:
            return 'Unknown'

    def get_smart_scheduling_stats(self) -> Dict:
        """Get smart scheduling statistics"""
        try:
            today = datetime.date.today().isoformat()
            appointments = self.db.get_appointments()

            # Calculate statistics
            total_appointments = len(appointments)
            today_appointments = len([apt for apt in appointments if apt['date'] == today])

            # Calculate average efficiency for recent days
            recent_dates = set(apt['date'] for apt in appointments
                             if apt['date'] >= (datetime.date.today() - datetime.timedelta(days=7)).isoformat())

            avg_efficiency = 0
            if recent_dates:
                efficiencies = []
                for date in recent_dates:
                    date_appointments = [apt for apt in appointments if apt['date'] == date]
                    if len(date_appointments) > 1:
                        efficiency = self.calculate_schedule_efficiency(date_appointments)
                        efficiencies.append(efficiency)

                if efficiencies:
                    avg_efficiency = sum(efficiencies) / len(efficiencies)

            return {
                'total_appointments': total_appointments,
                'today_appointments': today_appointments,
                'average_efficiency': round(avg_efficiency, 1),
                'calendar_integration': self.calendar.is_enabled(),
                'conflict_detection': True,
                'smart_suggestions': self.config['auto_suggest_alternatives']
            }

        except Exception as e:
            print(f"Error getting smart scheduling stats: {e}")
            return {}

# Example usage
def test_smart_scheduling():
    """Test smart scheduling functionality"""
    scheduler = SmartScheduler()

    # Test conflict detection
    conflicts = scheduler.check_appointment_conflicts('2024-01-15', '2:00 PM', 'Haircut')
    print(f"Conflicts: {conflicts}")

    # Test optimization
    optimization = scheduler.optimize_daily_schedule('2024-01-15')
    print(f"Optimization: {optimization}")

    # Test stats
    stats = scheduler.get_smart_scheduling_stats()
    print(f"Stats: {stats}")

if __name__ == "__main__":
    test_smart_scheduling()
