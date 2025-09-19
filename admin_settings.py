#!/usr/bin/env python3
"""
Admin Settings Manager for AI Voice Agent
Comprehensive configuration interface for all settings
"""

import json
import os
from typing import Dict, Any, List
from datetime import datetime

class AdminSettingsManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.get_default_config()

    def save_config(self) -> bool:
        """Save configuration to file"""
        try:
            # Create backup
            backup_file = f"{self.config_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if os.path.exists(self.config_file):
                os.rename(self.config_file, backup_file)

            # Save new config
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get_default_config(self) -> Dict:
        """Get default configuration template"""
        return {
            "business_info": {
                "name": "Your Business Name",
                "address": "Your Business Address",
                "phone": "Your Phone Number",
                "email": "your@email.com",
                "website": "https://yourbusiness.com",
                "timezone": "America/New_York",
                "currency": "USD",
                "industry": "general"
            },
            "business_hours": {
                "monday": "9:00 AM - 6:00 PM",
                "tuesday": "9:00 AM - 6:00 PM",
                "wednesday": "9:00 AM - 6:00 PM",
                "thursday": "9:00 AM - 6:00 PM",
                "friday": "9:00 AM - 6:00 PM",
                "saturday": "10:00 AM - 4:00 PM",
                "sunday": "Closed"
            },
            "services": [],
            "faq_responses": {},
            "appointment_settings": {
                "booking_window_days": 14,
                "cancellation_hours": 24,
                "reminder_hours": 24,
                "max_appointments_per_day": 8,
                "require_phone": True,
                "require_email": False,
                "auto_confirm": True
            },
            "automated_responses": {
                "greeting": "Hello! Welcome to {business_name}. I'm your virtual assistant. How can I help you today?",
                "booking_success": "✅ Your appointment is confirmed! We'll send you a reminder 24 hours before your appointment.",
                "booking_cancelled": "No problem! Your appointment was not booked. Feel free to start over anytime.",
                "outside_hours": "Thank you for contacting us! We're currently closed but will respond during business hours.",
                "error": "I'm sorry, I didn't understand that. Could you please rephrase your request?"
            },
            "voice_settings": {
                "enabled": True,
                "auto_speak_responses": False,
                "voice_rate": 0.9,
                "voice_pitch": 1.0,
                "voice_volume": 0.8,
                "language": "en-US"
            },
            "ui_settings": {
                "theme": "default",
                "primary_color": "#667eea",
                "secondary_color": "#764ba2",
                "logo_url": "",
                "favicon_url": "",
                "custom_css": ""
            },
            "security_settings": {
                "rate_limit_per_minute": 10,
                "max_session_duration": 3600,
                "require_verification": False,
                "blocked_countries": [],
                "admin_password": ""
            },
            "reminder_settings": {
                "email_enabled": False,
                "sms_enabled": False,
                "webhook_enabled": False,
                "reminder_hours": [24, 2],
                "business_hours": {"start": 9, "end": 18},
                "admin_phone": "",
                "admin_email": "",
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "email_user": "",
                "email_password": "",
                "webhook_url": ""
            },
            "calendar_settings": {
                "enabled": False,
                "calendar_id": "primary",
                "sync_direction": "both",
                "auto_sync": True,
                "conflict_detection": True,
                "business_calendar_id": None
            },
            "scheduling_settings": {
                "buffer_minutes": 15,
                "max_daily_appointments": 8,
                "lunch_break": {"start": "12:00", "end": "13:00"},
                "preferred_slots": ["9:00 AM", "10:00 AM", "2:00 PM", "3:00 PM"],
                "avoid_slots": ["12:00 PM"],
                "auto_suggest_alternatives": True,
                "optimize_schedule": True
            },
            "multi_channel_settings": {
                "whatsapp": {
                    "enabled": False,
                    "provider": "twilio",
                    "account_sid": "",
                    "auth_token": "",
                    "phone_number": "",
                    "webhook_verify_token": ""
                },
                "sms": {
                    "enabled": False,
                    "provider": "twilio",
                    "account_sid": "",
                    "auth_token": "",
                    "phone_number": ""
                },
                "telegram": {
                    "enabled": False,
                    "bot_token": "",
                    "webhook_url": ""
                },
                "messenger": {
                    "enabled": False,
                    "page_access_token": "",
                    "verify_token": "",
                    "app_secret": ""
                },
                "webchat": {
                    "enabled": True,
                    "embed_code_available": True
                }
            },
            "analytics_settings": {
                "google_analytics_id": "",
                "track_conversations": True,
                "track_appointments": True,
                "data_retention_days": 365
            },
            "ai_settings": {
                "provider": "built-in",
                "openai_api_key": "",
                "claude_api_key": "",
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 150,
                "context_window": 10
            }
        }

    # Business Information Management
    def update_business_info(self, info: Dict) -> bool:
        """Update business information"""
        try:
            self.config["business_info"].update(info)
            return self.save_config()
        except Exception as e:
            print(f"Error updating business info: {e}")
            return False

    def update_business_hours(self, hours: Dict) -> bool:
        """Update business hours"""
        try:
            self.config["business_hours"].update(hours)
            return self.save_config()
        except Exception as e:
            print(f"Error updating business hours: {e}")
            return False

    # Services Management
    def add_service(self, service: Dict) -> bool:
        """Add a new service"""
        try:
            if "services" not in self.config:
                self.config["services"] = []

            # Validate required fields
            required_fields = ["name", "price", "duration"]
            if not all(field in service for field in required_fields):
                return False

            self.config["services"].append(service)
            return self.save_config()
        except Exception as e:
            print(f"Error adding service: {e}")
            return False

    def update_service(self, index: int, service: Dict) -> bool:
        """Update an existing service"""
        try:
            if 0 <= index < len(self.config["services"]):
                self.config["services"][index].update(service)
                return self.save_config()
            return False
        except Exception as e:
            print(f"Error updating service: {e}")
            return False

    def delete_service(self, index: int) -> bool:
        """Delete a service"""
        try:
            if 0 <= index < len(self.config["services"]):
                del self.config["services"][index]
                return self.save_config()
            return False
        except Exception as e:
            print(f"Error deleting service: {e}")
            return False

    # FAQ Management
    def update_faq(self, faq_data: Dict) -> bool:
        """Update FAQ responses"""
        try:
            self.config["faq_responses"].update(faq_data)
            return self.save_config()
        except Exception as e:
            print(f"Error updating FAQ: {e}")
            return False

    def add_faq_item(self, key: str, response: str) -> bool:
        """Add a new FAQ item"""
        try:
            self.config["faq_responses"][key] = response
            return self.save_config()
        except Exception as e:
            print(f"Error adding FAQ item: {e}")
            return False

    def delete_faq_item(self, key: str) -> bool:
        """Delete an FAQ item"""
        try:
            if key in self.config["faq_responses"]:
                del self.config["faq_responses"][key]
                return self.save_config()
            return False
        except Exception as e:
            print(f"Error deleting FAQ item: {e}")
            return False

    # Integration Settings
    def update_calendar_settings(self, settings: Dict) -> bool:
        """Update calendar integration settings"""
        try:
            self.config["calendar_settings"].update(settings)
            return self.save_config()
        except Exception as e:
            print(f"Error updating calendar settings: {e}")
            return False

    def update_reminder_settings(self, settings: Dict) -> bool:
        """Update reminder settings"""
        try:
            self.config["reminder_settings"].update(settings)
            return self.save_config()
        except Exception as e:
            print(f"Error updating reminder settings: {e}")
            return False

    def update_channel_settings(self, channel: str, settings: Dict) -> bool:
        """Update multi-channel settings"""
        try:
            if channel in self.config["multi_channel_settings"]:
                self.config["multi_channel_settings"][channel].update(settings)
                return self.save_config()
            return False
        except Exception as e:
            print(f"Error updating channel settings: {e}")
            return False

    def update_voice_settings(self, settings: Dict) -> bool:
        """Update voice settings"""
        try:
            if "voice_settings" not in self.config:
                self.config["voice_settings"] = {}
            self.config["voice_settings"].update(settings)
            return self.save_config()
        except Exception as e:
            print(f"Error updating voice settings: {e}")
            return False

    def update_ui_settings(self, settings: Dict) -> bool:
        """Update UI/theme settings"""
        try:
            if "ui_settings" not in self.config:
                self.config["ui_settings"] = {}
            self.config["ui_settings"].update(settings)
            return self.save_config()
        except Exception as e:
            print(f"Error updating UI settings: {e}")
            return False

    def update_security_settings(self, settings: Dict) -> bool:
        """Update security settings"""
        try:
            if "security_settings" not in self.config:
                self.config["security_settings"] = {}
            self.config["security_settings"].update(settings)
            return self.save_config()
        except Exception as e:
            print(f"Error updating security settings: {e}")
            return False

    def update_ai_settings(self, settings: Dict) -> bool:
        """Update AI provider settings"""
        try:
            if "ai_settings" not in self.config:
                self.config["ai_settings"] = {}
            self.config["ai_settings"].update(settings)
            return self.save_config()
        except Exception as e:
            print(f"Error updating AI settings: {e}")
            return False

    # Validation Methods
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def validate_phone(self, phone: str) -> bool:
        """Validate phone number format"""
        import re
        # Simple validation for international phone numbers
        pattern = r'^\+?[\d\s\-\(\)]{10,}$'
        return re.match(pattern, phone) is not None

    def validate_url(self, url: str) -> bool:
        """Validate URL format"""
        import re
        pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
        return re.match(pattern, url) is not None

    def validate_time_format(self, time_str: str) -> bool:
        """Validate time format (H:MM AM/PM)"""
        import re
        pattern = r'^(1[0-2]|0?[1-9]):([0-5][0-9]) (AM|PM)$'
        return re.match(pattern, time_str) is not None

    # Configuration Templates for Different Industries
    def get_industry_template(self, industry: str) -> Dict:
        """Get configuration template for specific industry"""
        templates = {
            "salon": {
                "services": [
                    {"name": "Haircut", "price": "$30+", "duration": "45 minutes"},
                    {"name": "Styling", "price": "$25+", "duration": "30 minutes"},
                    {"name": "Coloring", "price": "$60+", "duration": "2 hours"}
                ],
                "faq_responses": {
                    "parking": "Free parking is available in the lot behind our building.",
                    "products": "We use premium salon products including professional brands.",
                    "first-time": "First-time clients get 10% off! Please arrive 15 minutes early."
                }
            },
            "medical": {
                "services": [
                    {"name": "Consultation", "price": "$150", "duration": "30 minutes"},
                    {"name": "Check-up", "price": "$100", "duration": "20 minutes"},
                    {"name": "Follow-up", "price": "$75", "duration": "15 minutes"}
                ],
                "appointment_settings": {
                    "cancellation_hours": 48,
                    "require_insurance": True
                },
                "faq_responses": {
                    "insurance": "We accept most major insurance plans. Please bring your insurance card.",
                    "preparation": "Please arrive 15 minutes early for paperwork."
                }
            },
            "dental": {
                "services": [
                    {"name": "Cleaning", "price": "$80", "duration": "60 minutes"},
                    {"name": "Examination", "price": "$150", "duration": "30 minutes"},
                    {"name": "Filling", "price": "$200+", "duration": "45 minutes"}
                ],
                "faq_responses": {
                    "insurance": "We work with most dental insurance plans.",
                    "payment": "We accept cash, cards, and offer payment plans."
                }
            },
            "spa": {
                "services": [
                    {"name": "Massage", "price": "$80+", "duration": "60 minutes"},
                    {"name": "Facial", "price": "$70+", "duration": "60 minutes"},
                    {"name": "Manicure", "price": "$35", "duration": "45 minutes"}
                ],
                "faq_responses": {
                    "preparation": "Please arrive 10 minutes early to relax and prepare.",
                    "packages": "We offer spa packages with multiple services at discounted rates."
                }
            },
            "fitness": {
                "services": [
                    {"name": "Personal Training", "price": "$60", "duration": "60 minutes"},
                    {"name": "Group Class", "price": "$20", "duration": "45 minutes"},
                    {"name": "Consultation", "price": "$Free", "duration": "30 minutes"}
                ],
                "faq_responses": {
                    "equipment": "All equipment is provided. Just bring water and a towel.",
                    "membership": "We offer flexible membership options with no long-term contracts."
                }
            },
            "restaurant": {
                "services": [
                    {"name": "Dinner Reservation", "price": "Free", "duration": "90 minutes"},
                    {"name": "Private Event", "price": "Custom", "duration": "3 hours"},
                    {"name": "Catering", "price": "Custom", "duration": "Variable"}
                ],
                "faq_responses": {
                    "menu": "Our menu features fresh, locally-sourced ingredients with seasonal specials.",
                    "dietary": "We accommodate vegetarian, vegan, and gluten-free dietary requirements."
                }
            }
        }

        return templates.get(industry, {})

    def apply_industry_template(self, industry: str) -> bool:
        """Apply industry-specific template to current config"""
        try:
            template = self.get_industry_template(industry)
            if template:
                # Merge template with current config
                for key, value in template.items():
                    if key in self.config:
                        if isinstance(value, dict):
                            self.config[key].update(value)
                        else:
                            self.config[key] = value
                    else:
                        self.config[key] = value

                # Update business info
                self.config["business_info"]["industry"] = industry
                return self.save_config()
            return False
        except Exception as e:
            print(f"Error applying industry template: {e}")
            return False

    # Configuration Export/Import
    def export_config(self, filename: str = None) -> str:
        """Export configuration to file"""
        if filename is None:
            filename = f"config_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(filename, 'w') as f:
                json.dump(self.config, f, indent=2)
            return filename
        except Exception as e:
            print(f"Error exporting config: {e}")
            return ""

    def import_config(self, filename: str) -> bool:
        """Import configuration from file"""
        try:
            with open(filename, 'r') as f:
                imported_config = json.load(f)

            # Validate imported config
            if self.validate_config(imported_config):
                self.config = imported_config
                return self.save_config()
            return False
        except Exception as e:
            print(f"Error importing config: {e}")
            return False

    def validate_config(self, config: Dict) -> bool:
        """Validate configuration structure"""
        required_sections = [
            "business_info", "business_hours", "services",
            "faq_responses", "appointment_settings"
        ]

        return all(section in config for section in required_sections)

    # Configuration Statistics
    def get_config_stats(self) -> Dict:
        """Get configuration statistics"""
        return {
            "total_services": len(self.config.get("services", [])),
            "total_faq_items": len(self.config.get("faq_responses", {})),
            "channels_enabled": sum(1 for channel in self.config.get("multi_channel_settings", {}).values()
                                  if isinstance(channel, dict) and channel.get("enabled", False)),
            "integrations_active": {
                "calendar": self.config.get("calendar_settings", {}).get("enabled", False),
                "reminders": any([
                    self.config.get("reminder_settings", {}).get("email_enabled", False),
                    self.config.get("reminder_settings", {}).get("sms_enabled", False)
                ]),
                "voice": self.config.get("voice_settings", {}).get("enabled", True)
            },
            "last_modified": datetime.fromtimestamp(os.path.getmtime(self.config_file)).isoformat() if os.path.exists(self.config_file) else None
        }

    # Get all settings organized by category
    def get_all_settings(self) -> Dict:
        """Get all settings organized by category for admin interface"""
        return {
            "business": {
                "info": self.config.get("business_info", {}),
                "hours": self.config.get("business_hours", {}),
                "services": self.config.get("services", []),
                "appointment_settings": self.config.get("appointment_settings", {})
            },
            "conversation": {
                "faq_responses": self.config.get("faq_responses", {}),
                "automated_responses": self.config.get("automated_responses", {}),
                "keywords": self.config.get("keywords", {}),
                "voice_settings": self.config.get("voice_settings", {})
            },
            "integrations": {
                "calendar": self.config.get("calendar_settings", {}),
                "reminders": self.config.get("reminder_settings", {}),
                "channels": self.config.get("multi_channel_settings", {}),
                "ai": self.config.get("ai_settings", {})
            },
            "appearance": {
                "ui": self.config.get("ui_settings", {}),
                "branding": {
                    "logo_url": self.config.get("ui_settings", {}).get("logo_url", ""),
                    "colors": {
                        "primary": self.config.get("ui_settings", {}).get("primary_color", "#667eea"),
                        "secondary": self.config.get("ui_settings", {}).get("secondary_color", "#764ba2")
                    }
                }
            },
            "security": {
                "settings": self.config.get("security_settings", {}),
                "rate_limiting": self.config.get("security_settings", {}).get("rate_limit_per_minute", 10)
            },
            "analytics": self.config.get("analytics_settings", {}),
            "advanced": {
                "scheduling": self.config.get("scheduling_settings", {}),
                "system": {
                    "timezone": self.config.get("business_info", {}).get("timezone", "America/New_York"),
                    "currency": self.config.get("business_info", {}).get("currency", "USD")
                }
            }
        }

# Example usage and testing
def test_admin_settings():
    """Test admin settings functionality"""
    admin = AdminSettingsManager()

    # Test business info update
    business_info = {
        "name": "Test Business",
        "phone": "+1234567890",
        "email": "test@business.com"
    }

    result = admin.update_business_info(business_info)
    print(f"Business info update: {result}")

    # Test service management
    service = {
        "name": "Test Service",
        "price": "$50",
        "duration": "30 minutes"
    }

    result = admin.add_service(service)
    print(f"Add service: {result}")

    # Test FAQ management
    result = admin.add_faq_item("test", "This is a test response")
    print(f"Add FAQ: {result}")

    # Get configuration stats
    stats = admin.get_config_stats()
    print(f"Config stats: {stats}")

if __name__ == "__main__":
    test_admin_settings()
