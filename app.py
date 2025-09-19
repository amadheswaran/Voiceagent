#!/usr/bin/env python3
"""
Flask Web Server for AI Chat Agent
Provides web API endpoints for the chat interface
"""

import json
import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from call_text_agent import CallTextAgent, MessageType
from reminder_system import ReminderSystem
from multi_channel import MultiChannelManager, create_webhook_routes
from admin_settings import AdminSettingsManager

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize the agent and systems
agent = CallTextAgent()
reminder_system = ReminderSystem()
multi_channel = MultiChannelManager()
admin_settings = AdminSettingsManager()

# Start reminder system
reminder_system.start()

# Setup multi-channel webhook routes
create_webhook_routes(app, multi_channel)

@app.route('/')
def home():
    """Serve the main chat interface"""
    return send_from_directory('.', 'chat_widget.html')

@app.route('/config.json')
def get_config():
    """Serve the configuration file"""
    return send_from_directory('.', 'config.json')

@app.route('/chat/quick-actions', methods=['GET'])
def get_quick_actions():
    """Get quick actions for chat interface"""
    try:
        settings = admin_settings.get_all_settings()
        faq_responses = settings.get('faq_responses', {})

        # Priority order for quick actions
        priority_actions = [
            {'key': 'booking', 'icon': '📅', 'label': 'Book Appointment', 'message': 'book appointment', 'always_show': True},
            {'key': 'hours', 'icon': '🕐', 'label': 'Hours', 'message': 'hours'},
            {'key': 'services', 'icon': '💇', 'label': 'Services', 'message': 'services'},
            {'key': 'prices', 'icon': '💰', 'label': 'Prices', 'message': 'prices'},
            {'key': 'location', 'icon': '📍', 'label': 'Location', 'message': 'location'},
            {'key': 'parking', 'icon': '🅿️', 'label': 'Parking', 'message': 'parking'},
            {'key': 'payment', 'icon': '💳', 'label': 'Payment', 'message': 'payment'},
            {'key': 'cancellation', 'icon': '❌', 'label': 'Cancellation', 'message': 'cancellation'}
        ]

        # Filter available quick actions
        available_actions = []
        for action in priority_actions:
            if action.get('always_show') or action['key'] in faq_responses:
                available_actions.append(action)
                if len(available_actions) >= 6:  # Limit to 6 actions
                    break

        return jsonify({
            'quick_actions': available_actions,
            'business_name': settings.get('business_info', {}).get('name', 'AI Assistant'),
            'welcome_message': settings.get('automated_responses', {}).get('greeting', ''),
            'ui_settings': settings.get('ui_settings', {})
        })

    except Exception as e:
        print(f"Error getting quick actions: {e}")
        return jsonify({'error': 'Failed to get quick actions'}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages from the web interface"""
    try:
        data = request.get_json()

        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400

        message = data['message']
        user_id = data.get('user_id', 'web-user')

        # Process message through the agent
        response = agent.process_message(user_id, message, MessageType.TEXT)

        return jsonify({
            'response': response,
            'user_id': user_id,
            'timestamp': agent.sessions[user_id].last_message_time.isoformat() if user_id in agent.sessions else None
        })

    except Exception as e:
        print(f"Error processing chat message: {e}")
        return jsonify({'error': 'Failed to process message'}), 500

@app.route('/appointments', methods=['GET'])
def get_appointments():
    """Get all appointments or appointments for a specific user"""
    try:
        user_id = request.args.get('user_id')
        appointments = agent.get_appointments(user_id)

        return jsonify({
            'appointments': appointments,
            'count': len(appointments)
        })

    except Exception as e:
        print(f"Error getting appointments: {e}")
        return jsonify({'error': 'Failed to get appointments'}), 500

@app.route('/appointments/<appointment_id>/cancel', methods=['POST'])
def cancel_appointment(appointment_id):
    """Cancel an appointment by ID"""
    try:
        success = agent.cancel_appointment(appointment_id)

        if success:
            return jsonify({'message': 'Appointment cancelled successfully'})
        else:
            return jsonify({'error': 'Appointment not found'}), 404

    except Exception as e:
        print(f"Error cancelling appointment: {e}")
        return jsonify({'error': 'Failed to cancel appointment'}), 500

@app.route('/available-slots', methods=['GET'])
def get_available_slots():
    """Get available appointment slots"""
    try:
        return jsonify({
            'available_slots': agent.available_slots
        })

    except Exception as e:
        print(f"Error getting available slots: {e}")
        return jsonify({'error': 'Failed to get available slots'}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Get system status and statistics"""
    try:
        stats = agent.get_user_stats()
        return jsonify({
            'status': 'online',
            'active_sessions': len(agent.sessions),
            'total_appointments': stats.get('total_appointments', 0),
            'pending_appointments': stats.get('pending_appointments', 0),
            'total_users': stats.get('total_users', 0),
            'active_users': stats.get('active_users', 0),
            'available_dates': len(agent.available_slots)
        })

    except Exception as e:
        print(f"Error getting status: {e}")
        return jsonify({'error': 'Failed to get status'}), 500

@app.route('/chat-history/<user_id>', methods=['GET'])
def get_chat_history(user_id):
    """Get chat history for a user"""
    try:
        limit = int(request.args.get('limit', 50))
        history = agent.get_chat_history(user_id, limit)

        return jsonify({
            'history': history,
            'count': len(history)
        })

    except Exception as e:
        print(f"Error getting chat history: {e}")
        return jsonify({'error': 'Failed to get chat history'}), 500

@app.route('/users/<user_id>', methods=['GET'])
def get_user_info(user_id):
    """Get user information"""
    try:
        user = agent.db.get_user(user_id)
        if user:
            return jsonify({
                'user': {
                    'phone': user.phone,
                    'name': user.name,
                    'email': user.email,
                    'preferences': json.loads(user.preferences) if user.preferences else {},
                    'created_at': user.created_at,
                    'last_active': user.last_active
                }
            })
        else:
            return jsonify({'error': 'User not found'}), 404

    except Exception as e:
        print(f"Error getting user info: {e}")
        return jsonify({'error': 'Failed to get user info'}), 500

@app.route('/reminders/stats', methods=['GET'])
def get_reminder_stats():
    """Get reminder system statistics"""
    try:
        stats = reminder_system.get_reminder_stats()
        return jsonify(stats)

    except Exception as e:
        print(f"Error getting reminder stats: {e}")
        return jsonify({'error': 'Failed to get reminder stats'}), 500

@app.route('/reminders/test/<appointment_id>', methods=['POST'])
def test_reminder(appointment_id):
    """Send a test reminder for an appointment"""
    try:
        success = reminder_system.send_test_reminder(appointment_id)

        if success:
            return jsonify({'message': 'Test reminder sent successfully'})
        else:
            return jsonify({'error': 'Failed to send test reminder'}), 400

    except Exception as e:
        print(f"Error sending test reminder: {e}")
        return jsonify({'error': 'Failed to send test reminder'}), 500

@app.route('/reminders/toggle', methods=['POST'])
def toggle_reminder_system():
    """Start or stop the reminder system"""
    try:
        if reminder_system.running:
            reminder_system.stop()
            status = 'stopped'
        else:
            reminder_system.start()
            status = 'started'

        return jsonify({
            'message': f'Reminder system {status}',
            'running': reminder_system.running
        })

    except Exception as e:
        print(f"Error toggling reminder system: {e}")
        return jsonify({'error': 'Failed to toggle reminder system'}), 500

@app.route('/channels/stats', methods=['GET'])
def get_channel_stats():
    """Get multi-channel statistics"""
    try:
        stats = multi_channel.get_channel_stats()
        return jsonify(stats)

    except Exception as e:
        print(f"Error getting channel stats: {e}")
        return jsonify({'error': 'Failed to get channel stats'}), 500

@app.route('/channels/send', methods=['POST'])
def send_channel_message():
    """Send message via specific channel"""
    try:
        data = request.get_json()
        channel = data.get('channel')
        recipient_id = data.get('recipient_id')
        message = data.get('message')

        if not all([channel, recipient_id, message]):
            return jsonify({'error': 'Missing required fields'}), 400

        success = multi_channel.send_message(channel, recipient_id, message)

        return jsonify({
            'success': success,
            'message': 'Message sent successfully' if success else 'Failed to send message'
        })

    except Exception as e:
        print(f"Error sending channel message: {e}")
        return jsonify({'error': 'Failed to send message'}), 500

@app.route('/channels/broadcast', methods=['POST'])
def broadcast_message():
    """Broadcast message to multiple channels"""
    try:
        data = request.get_json()
        message = data.get('message')
        channels = data.get('channels', [])
        user_filter = data.get('user_filter', {})

        if not message:
            return jsonify({'error': 'Message is required'}), 400

        results = multi_channel.broadcast_message(message, channels, user_filter)

        return jsonify({
            'results': results,
            'message': 'Broadcast completed'
        })

    except Exception as e:
        print(f"Error broadcasting message: {e}")
        return jsonify({'error': 'Failed to broadcast message'}), 500

# Admin Settings Routes
@app.route('/admin/settings')
def admin_settings_page():
    """Serve the admin settings interface"""
    return send_from_directory('.', 'admin_interface.html')

@app.route('/admin/settings/data', methods=['GET'])
def get_admin_settings():
    """Get all admin settings"""
    try:
        settings = admin_settings.get_all_settings()
        return jsonify(settings)
    except Exception as e:
        print(f"Error getting admin settings: {e}")
        return jsonify({'error': 'Failed to get admin settings'}), 500

@app.route('/admin/settings/business', methods=['POST'])
def update_business_info():
    """Update business information"""
    try:
        data = request.get_json()
        success = admin_settings.update_business_info(data)

        if success:
            return jsonify({'message': 'Business information updated successfully'})
        else:
            return jsonify({'error': 'Failed to update business information'}), 500
    except Exception as e:
        print(f"Error updating business info: {e}")
        return jsonify({'error': 'Failed to update business information'}), 500

@app.route('/admin/settings/hours', methods=['POST'])
def update_business_hours():
    """Update business hours"""
    try:
        data = request.get_json()
        success = admin_settings.update_business_hours(data)

        if success:
            return jsonify({'message': 'Business hours updated successfully'})
        else:
            return jsonify({'error': 'Failed to update business hours'}), 500
    except Exception as e:
        print(f"Error updating business hours: {e}")
        return jsonify({'error': 'Failed to update business hours'}), 500

@app.route('/admin/settings/services', methods=['POST'])
def update_services():
    """Update services"""
    try:
        data = request.get_json()

        # Clear existing services and add new ones
        admin_settings.config['services'] = data
        success = admin_settings.save_config()

        if success:
            return jsonify({'message': 'Services updated successfully'})
        else:
            return jsonify({'error': 'Failed to update services'}), 500
    except Exception as e:
        print(f"Error updating services: {e}")
        return jsonify({'error': 'Failed to update services'}), 500

@app.route('/admin/settings/faq', methods=['POST'])
def update_faq():
    """Update FAQ responses"""
    try:
        data = request.get_json()
        success = admin_settings.update_faq(data)

        if success:
            return jsonify({'message': 'FAQ updated successfully'})
        else:
            return jsonify({'error': 'Failed to update FAQ'}), 500
    except Exception as e:
        print(f"Error updating FAQ: {e}")
        return jsonify({'error': 'Failed to update FAQ'}), 500

@app.route('/admin/settings/calendar', methods=['POST'])
def update_calendar_settings():
    """Update calendar settings"""
    try:
        data = request.get_json()
        success = admin_settings.update_calendar_settings(data)

        if success:
            return jsonify({'message': 'Calendar settings updated successfully'})
        else:
            return jsonify({'error': 'Failed to update calendar settings'}), 500
    except Exception as e:
        print(f"Error updating calendar settings: {e}")
        return jsonify({'error': 'Failed to update calendar settings'}), 500

@app.route('/admin/settings/reminders', methods=['POST'])
def update_reminder_settings():
    """Update reminder settings"""
    try:
        data = request.get_json()
        success = admin_settings.update_reminder_settings(data)

        if success:
            return jsonify({'message': 'Reminder settings updated successfully'})
        else:
            return jsonify({'error': 'Failed to update reminder settings'}), 500
    except Exception as e:
        print(f"Error updating reminder settings: {e}")
        return jsonify({'error': 'Failed to update reminder settings'}), 500

@app.route('/admin/settings/channel/<channel>', methods=['POST'])
def update_channel_settings(channel):
    """Update multi-channel settings"""
    try:
        data = request.get_json()
        success = admin_settings.update_channel_settings(channel, data)

        if success:
            return jsonify({'message': f'{channel.title()} settings updated successfully'})
        else:
            return jsonify({'error': f'Failed to update {channel} settings'}), 500
    except Exception as e:
        print(f"Error updating {channel} settings: {e}")
        return jsonify({'error': f'Failed to update {channel} settings'}), 500

@app.route('/admin/settings/voice', methods=['POST'])
def update_voice_settings():
    """Update voice settings"""
    try:
        data = request.get_json()
        success = admin_settings.update_voice_settings(data)

        if success:
            return jsonify({'message': 'Voice settings updated successfully'})
        else:
            return jsonify({'error': 'Failed to update voice settings'}), 500
    except Exception as e:
        print(f"Error updating voice settings: {e}")
        return jsonify({'error': 'Failed to update voice settings'}), 500

@app.route('/admin/settings/ui', methods=['POST'])
def update_ui_settings():
    """Update UI settings"""
    try:
        data = request.get_json()
        success = admin_settings.update_ui_settings(data)

        if success:
            return jsonify({'message': 'UI settings updated successfully'})
        else:
            return jsonify({'error': 'Failed to update UI settings'}), 500
    except Exception as e:
        print(f"Error updating UI settings: {e}")
        return jsonify({'error': 'Failed to update UI settings'}), 500

@app.route('/admin/settings/security', methods=['POST'])
def update_security_settings():
    """Update security settings"""
    try:
        data = request.get_json()
        success = admin_settings.update_security_settings(data)

        if success:
            return jsonify({'message': 'Security settings updated successfully'})
        else:
            return jsonify({'error': 'Failed to update security settings'}), 500
    except Exception as e:
        print(f"Error updating security settings: {e}")
        return jsonify({'error': 'Failed to update security settings'}), 500

@app.route('/admin/settings/industry-template', methods=['POST'])
def apply_industry_template():
    """Apply industry template"""
    try:
        data = request.get_json()
        industry = data.get('industry')

        if not industry:
            return jsonify({'error': 'Industry not specified'}), 400

        success = admin_settings.apply_industry_template(industry)

        if success:
            return jsonify({'message': f'{industry.title()} template applied successfully'})
        else:
            return jsonify({'error': 'Failed to apply industry template'}), 500
    except Exception as e:
        print(f"Error applying industry template: {e}")
        return jsonify({'error': 'Failed to apply industry template'}), 500

@app.route('/admin/settings/export', methods=['GET'])
def export_config():
    """Export configuration"""
    try:
        import tempfile

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(admin_settings.config, f, indent=2)
            temp_filename = f.name

        return send_from_directory(
            os.path.dirname(temp_filename),
            os.path.basename(temp_filename),
            as_attachment=True,
            download_name=f"ai_agent_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
    except Exception as e:
        print(f"Error exporting config: {e}")
        return jsonify({'error': 'Failed to export configuration'}), 500

@app.route('/admin/settings/import', methods=['POST'])
def import_config():
    """Import configuration"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if file and file.filename.endswith('.json'):
            import tempfile

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                file.save(f.name)
                success = admin_settings.import_config(f.name)

            if success:
                return jsonify({'message': 'Configuration imported successfully'})
            else:
                return jsonify({'error': 'Failed to import configuration - invalid format'}), 500
        else:
            return jsonify({'error': 'Invalid file format - must be JSON'}), 400
    except Exception as e:
        print(f"Error importing config: {e}")
        return jsonify({'error': 'Failed to import configuration'}), 500

@app.route('/admin/settings/stats', methods=['GET'])
def get_config_stats():
    """Get configuration statistics"""
    try:
        stats = admin_settings.get_config_stats()
        return jsonify(stats)
    except Exception as e:
        print(f"Error getting config stats: {e}")
        return jsonify({'error': 'Failed to get configuration statistics'}), 500

# Additional Admin Settings Routes

@app.route('/admin/settings/responses', methods=['POST'])
def update_automated_responses():
    """Update automated responses"""
    try:
        data = request.get_json()

        # Update automated responses in config
        if 'automated_responses' not in admin_settings.config:
            admin_settings.config['automated_responses'] = {}

        admin_settings.config['automated_responses'].update(data)
        success = admin_settings.save_config()

        if success:
            return jsonify({'message': 'Automated responses updated successfully'})
        else:
            return jsonify({'error': 'Failed to update automated responses'}), 500
    except Exception as e:
        print(f"Error updating automated responses: {e}")
        return jsonify({'error': 'Failed to update automated responses'}), 500

@app.route('/admin/settings/channels', methods=['POST'])
def update_multi_channel_settings():
    """Update all multi-channel settings"""
    try:
        data = request.get_json()

        # Update multi-channel settings
        if 'multi_channel_settings' not in admin_settings.config:
            admin_settings.config['multi_channel_settings'] = {}

        admin_settings.config['multi_channel_settings'].update(data)
        success = admin_settings.save_config()

        if success:
            return jsonify({'message': 'Channel settings updated successfully'})
        else:
            return jsonify({'error': 'Failed to update channel settings'}), 500
    except Exception as e:
        print(f"Error updating channel settings: {e}")
        return jsonify({'error': 'Failed to update channel settings'}), 500

@app.route('/admin/settings/analytics', methods=['POST'])
def update_analytics_settings():
    """Update analytics settings"""
    try:
        data = request.get_json()

        # Update analytics settings
        if 'analytics_settings' not in admin_settings.config:
            admin_settings.config['analytics_settings'] = {}

        admin_settings.config['analytics_settings'].update(data)
        success = admin_settings.save_config()

        if success:
            return jsonify({'message': 'Analytics settings updated successfully'})
        else:
            return jsonify({'error': 'Failed to update analytics settings'}), 500
    except Exception as e:
        print(f"Error updating analytics settings: {e}")
        return jsonify({'error': 'Failed to update analytics settings'}), 500

# Test endpoints for validating configurations

@app.route('/admin/settings/calendar/test', methods=['POST'])
def test_calendar_connection():
    """Test Google Calendar connection"""
    try:
        # Import calendar integration and test
        from calendar_integration import CalendarIntegration
        calendar = CalendarIntegration()

        # Try to get calendar info
        result = calendar.get_calendar_info()

        if result:
            return jsonify({'message': 'Calendar connection successful', 'calendar_info': result})
        else:
            return jsonify({'error': 'Calendar connection failed'}), 400
    except Exception as e:
        print(f"Error testing calendar: {e}")
        return jsonify({'error': f'Calendar test failed: {str(e)}'}), 500

@app.route('/admin/settings/email/test', methods=['POST'])
def test_email_settings():
    """Test email configuration"""
    try:
        # Get email settings from config
        email_settings = admin_settings.config.get('reminder_settings', {})

        if not email_settings.get('email_enabled'):
            return jsonify({'error': 'Email reminders not enabled'}), 400

        # Import and test email
        from reminder_system import ReminderSystem
        test_reminder = ReminderSystem()

        # Send test email
        success = test_reminder.send_test_email(email_settings.get('admin_email', 'test@example.com'))

        if success:
            return jsonify({'message': 'Test email sent successfully'})
        else:
            return jsonify({'error': 'Email test failed'}), 400
    except Exception as e:
        print(f"Error testing email: {e}")
        return jsonify({'error': f'Email test failed: {str(e)}'}), 500

@app.route('/admin/settings/channels/test', methods=['POST'])
def test_channel_connections():
    """Test multi-channel connections"""
    try:
        channel_settings = admin_settings.config.get('multi_channel_settings', {})
        results = {}

        # Test WhatsApp (Twilio)
        if channel_settings.get('whatsapp', {}).get('enabled'):
            try:
                from twilio.rest import Client
                account_sid = channel_settings['whatsapp'].get('account_sid')
                auth_token = channel_settings['whatsapp'].get('auth_token')

                if account_sid and auth_token:
                    client = Client(account_sid, auth_token)
                    # Test by getting account info
                    account = client.api.accounts(account_sid).fetch()
                    results['whatsapp'] = {'status': 'success', 'message': 'Connection successful'}
                else:
                    results['whatsapp'] = {'status': 'error', 'message': 'Missing credentials'}
            except Exception as e:
                results['whatsapp'] = {'status': 'error', 'message': str(e)}

        # Test Telegram
        if channel_settings.get('telegram', {}).get('enabled'):
            try:
                import requests
                bot_token = channel_settings['telegram'].get('bot_token')

                if bot_token:
                    response = requests.get(f'https://api.telegram.org/bot{bot_token}/getMe')
                    if response.status_code == 200:
                        results['telegram'] = {'status': 'success', 'message': 'Bot connection successful'}
                    else:
                        results['telegram'] = {'status': 'error', 'message': 'Invalid bot token'}
                else:
                    results['telegram'] = {'status': 'error', 'message': 'Missing bot token'}
            except Exception as e:
                results['telegram'] = {'status': 'error', 'message': str(e)}

        return jsonify({'results': results})
    except Exception as e:
        print(f"Error testing channels: {e}")
        return jsonify({'error': f'Channel test failed: {str(e)}'}), 500

@app.route('/admin/analytics/export', methods=['GET'])
def export_analytics_data():
    """Export analytics data as CSV"""
    try:
        import csv
        import tempfile

        # Get analytics data from database
        stats = agent.get_user_stats()
        appointments = agent.get_appointments()

        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)

            # Write headers
            writer.writerow(['Metric', 'Value'])

            # Write statistics
            for key, value in stats.items():
                writer.writerow([key, value])

            # Add appointment data
            writer.writerow([''])
            writer.writerow(['Appointment ID', 'User', 'Service', 'Date', 'Time', 'Status'])

            for apt in appointments:
                writer.writerow([
                    apt.get('id', ''),
                    apt.get('name', ''),
                    apt.get('service', ''),
                    apt.get('date', ''),
                    apt.get('time', ''),
                    apt.get('status', '')
                ])

            temp_filename = f.name

        return send_from_directory(
            os.path.dirname(temp_filename),
            os.path.basename(temp_filename),
            as_attachment=True,
            download_name=f"analytics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
    except Exception as e:
        print(f"Error exporting analytics: {e}")
        return jsonify({'error': 'Failed to export analytics data'}), 500

@app.route('/admin/settings/backup', methods=['POST'])
def create_config_backup():
    """Create a backup of current configuration"""
    try:
        backup_filename = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = os.path.join('.', backup_filename)

        # Create backup
        with open(backup_path, 'w') as f:
            json.dump(admin_settings.config, f, indent=2)

        return jsonify({
            'message': 'Configuration backup created successfully',
            'filename': backup_filename
        })
    except Exception as e:
        print(f"Error creating backup: {e}")
        return jsonify({'error': 'Failed to create backup'}), 500

@app.route('/admin/settings/restore', methods=['POST'])
def restore_config_backup():
    """Restore configuration from backup"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No backup file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if file and file.filename.endswith('.json'):
            # Read and validate backup file
            backup_data = json.load(file)

            if admin_settings.validate_config(backup_data):
                # Create current backup before restore
                current_backup = f"config_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(current_backup, 'w') as f:
                    json.dump(admin_settings.config, f, indent=2)

                # Restore configuration
                admin_settings.config = backup_data
                success = admin_settings.save_config()

                if success:
                    return jsonify({
                        'message': 'Configuration restored successfully',
                        'backup_created': current_backup
                    })
                else:
                    return jsonify({'error': 'Failed to save restored configuration'}), 500
            else:
                return jsonify({'error': 'Invalid backup file format'}), 400
        else:
            return jsonify({'error': 'Invalid file format - must be JSON'}), 400
    except Exception as e:
        print(f"Error restoring backup: {e}")
        return jsonify({'error': 'Failed to restore configuration'}), 500

# Appointment Management Routes

@app.route('/appointments/<appointment_id>/status', methods=['POST'])
def update_appointment_status(appointment_id):
    """Update appointment status"""
    try:
        data = request.get_json()
        new_status = data.get('status')

        if not new_status:
            return jsonify({'error': 'Status is required'}), 400

        # Valid statuses
        valid_statuses = ['confirmed', 'completed', 'cancelled', 'no-show']
        if new_status not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400

        # Update appointment status in database
        success = agent.db.update_appointment_status(appointment_id, new_status)

        if success:
            return jsonify({'message': 'Appointment status updated successfully'})
        else:
            return jsonify({'error': 'Appointment not found'}), 404

    except Exception as e:
        print(f"Error updating appointment status: {e}")
        return jsonify({'error': 'Failed to update appointment status'}), 500

@app.route('/appointments/walk-in', methods=['POST'])
def add_walk_in_appointment():
    """Add walk-in appointment directly to database"""
    try:
        data = request.get_json()

        name = data.get('name')
        phone = data.get('phone')
        service = data.get('service')
        date = data.get('date')
        time = data.get('time')
        notes = data.get('notes', 'Walk-in customer')

        if not all([name, phone, service, date, time]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Create user if doesn't exist
        user = agent.db.create_or_update_user(phone, name)

        # Create appointment
        from database import Appointment
        appointment_id = f"walk-in-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        appointment = Appointment(
            id=appointment_id,
            user_phone=phone,
            name=name,
            service=service,
            date=date,
            time=time,
            status='confirmed',
            notes=notes,
            created_at=datetime.now().isoformat()
        )

        success = agent.db.create_appointment(appointment)

        if success:
            return jsonify({
                'message': 'Walk-in appointment created successfully',
                'appointment_id': appointment_id
            })
        else:
            return jsonify({'error': 'Failed to create appointment - slot may be taken'}), 400

    except Exception as e:
        print(f"Error creating walk-in appointment: {e}")
        return jsonify({'error': 'Failed to create walk-in appointment'}), 500

@app.route('/appointments/<appointment_id>/notes', methods=['POST'])
def update_appointment_notes(appointment_id):
    """Update appointment notes"""
    try:
        data = request.get_json()
        notes = data.get('notes', '')

        # Get current appointment
        appointments = agent.db.get_appointments()
        appointment = next((apt for apt in appointments if apt['id'] == appointment_id), None)

        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404

        # Update notes in database
        with agent.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE appointments SET notes = ? WHERE id = ?
            ''', (notes, appointment_id))
            conn.commit()

            if cursor.rowcount > 0:
                return jsonify({'message': 'Notes updated successfully'})
            else:
                return jsonify({'error': 'Failed to update notes'}), 500

    except Exception as e:
        print(f"Error updating appointment notes: {e}")
        return jsonify({'error': 'Failed to update notes'}), 500

@app.route('/appointments/<appointment_id>/reschedule', methods=['POST'])
def reschedule_appointment(appointment_id):
    """Reschedule an appointment to a new date and time"""
    try:
        data = request.get_json()
        new_date = data.get('date')
        new_time = data.get('time')

        if not new_date or not new_time:
            return jsonify({'error': 'New date and time are required'}), 400

        # Get current appointment
        appointments = agent.db.get_appointments()
        appointment = next((apt for apt in appointments if apt['id'] == appointment_id), None)

        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404

        # Check if the new slot is available
        with agent.db.get_connection() as conn:
            cursor = conn.cursor()

            # Check for conflicts (excluding the current appointment)
            cursor.execute('''
                SELECT COUNT(*) FROM appointments
                WHERE date = ? AND time = ? AND status != 'cancelled' AND id != ?
            ''', (new_date, new_time, appointment_id))

            if cursor.fetchone()[0] > 0:
                return jsonify({'error': 'The selected time slot is already booked'}), 400

            # Update the appointment
            cursor.execute('''
                UPDATE appointments
                SET date = ?, time = ?, notes = ?
                WHERE id = ?
            ''', (new_date, new_time,
                  f"{appointment['notes'] or ''} [Rescheduled from {appointment['date']} {appointment['time']}]".strip(),
                  appointment_id))

            conn.commit()

            if cursor.rowcount > 0:
                return jsonify({
                    'message': 'Appointment rescheduled successfully',
                    'new_date': new_date,
                    'new_time': new_time
                })
            else:
                return jsonify({'error': 'Failed to reschedule appointment'}), 500

    except Exception as e:
        print(f"Error rescheduling appointment: {e}")
        return jsonify({'error': 'Failed to reschedule appointment'}), 500

@app.route('/admin/appointments/export', methods=['GET'])
def export_appointments():
    """Export appointments to CSV"""
    try:
        import csv
        import tempfile

        # Get all appointments
        appointments = agent.get_appointments()

        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)

            # Write headers
            writer.writerow([
                'ID', 'Name', 'Phone', 'Email', 'Service', 'Date', 'Time',
                'Status', 'Notes', 'Created At', 'Updated At'
            ])

            # Write appointment data
            for apt in appointments:
                writer.writerow([
                    apt.get('id', ''),
                    apt.get('name', ''),
                    apt.get('phone', ''),
                    apt.get('email', ''),
                    apt.get('service', ''),
                    apt.get('date', ''),
                    apt.get('time', ''),
                    apt.get('status', 'confirmed'),
                    apt.get('notes', ''),
                    apt.get('created_at', ''),
                    apt.get('updated_at', '')
                ])

            temp_filename = f.name

        return send_from_directory(
            os.path.dirname(temp_filename),
            os.path.basename(temp_filename),
            as_attachment=True,
            download_name=f"appointments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
    except Exception as e:
        print(f"Error exporting appointments: {e}")
        return jsonify({'error': 'Failed to export appointments'}), 500

# Reports Routes

@app.route('/admin/reports', methods=['GET'])
def get_reports():
    """Get appointment reports with date range filtering"""
    try:
        start_date = request.args.get('start')
        end_date = request.args.get('end')

        # Get filtered appointments
        appointments = agent.db.get_appointments_by_date_range(start_date, end_date) if start_date and end_date else agent.get_appointments()

        # Calculate statistics
        total_appointments = len(appointments)
        completed_appointments = len([apt for apt in appointments if apt.get('status') == 'completed'])
        cancelled_appointments = len([apt for apt in appointments if apt.get('status') == 'cancelled'])
        no_show_appointments = len([apt for apt in appointments if apt.get('status') == 'no-show'])
        confirmed_appointments = total_appointments - completed_appointments - cancelled_appointments - no_show_appointments

        completion_rate = round((completed_appointments / total_appointments * 100) if total_appointments > 0 else 0, 1)

        # Calculate revenue (assuming service prices from config)
        services_config = admin_settings.config.get('services', [])
        service_prices = {service['name']: service.get('price', '$0') for service in services_config}

        total_revenue = 0
        for apt in appointments:
            if apt.get('status') == 'completed':
                service_name = apt.get('service', '')
                price_str = service_prices.get(service_name, '$0')
                # Extract number from price string (e.g., "$30+" -> 30)
                try:
                    price = float(''.join(filter(str.isdigit, price_str)))
                    total_revenue += price
                except:
                    pass

        # Services breakdown
        services_breakdown = {}
        for apt in appointments:
            service = apt.get('service', 'Unknown')
            if service not in services_breakdown:
                services_breakdown[service] = {'count': 0, 'revenue': 0}

            services_breakdown[service]['count'] += 1

            if apt.get('status') == 'completed':
                price_str = service_prices.get(service, '$0')
                try:
                    price = float(''.join(filter(str.isdigit, price_str)))
                    services_breakdown[service]['revenue'] += price
                except:
                    pass

        # Convert to list for frontend
        services_list = [
            {
                'name': name,
                'count': data['count'],
                'revenue': data['revenue']
            }
            for name, data in services_breakdown.items()
        ]

        # Peak hours analysis
        hour_counts = {}
        for apt in appointments:
            time_str = apt.get('time', '')
            if time_str:
                try:
                    # Extract hour from time string
                    hour = int(time_str.split(':')[0])
                    if hour not in hour_counts:
                        hour_counts[hour] = 0
                    hour_counts[hour] += 1
                except:
                    pass

        # Convert to list and determine peak hours
        peak_hours = []
        max_count = max(hour_counts.values()) if hour_counts else 0

        for hour in range(8, 19):  # 8 AM to 6 PM
            count = hour_counts.get(hour, 0)
            time_str = f"{hour:02d}:00"
            if hour >= 12:
                time_str += " PM" if hour > 12 else " PM"
                if hour > 12:
                    time_str = f"{hour-12:02d}:00 PM"
            else:
                time_str += " AM"

            peak_hours.append({
                'time': time_str,
                'count': count,
                'isPeak': count == max_count and max_count > 0
            })

        return jsonify({
            'total_appointments': total_appointments,
            'completed_appointments': completed_appointments,
            'cancelled_appointments': cancelled_appointments,
            'no_show_appointments': no_show_appointments,
            'confirmed_appointments': confirmed_appointments,
            'completion_rate': completion_rate,
            'total_revenue': total_revenue,
            'services_breakdown': services_list,
            'peak_hours': peak_hours,
            'date_range': {
                'start': start_date,
                'end': end_date
            }
        })

    except Exception as e:
        print(f"Error getting reports: {e}")
        return jsonify({'error': 'Failed to get reports'}), 500

@app.route('/admin/reports/export', methods=['GET'])
def export_report():
    """Export report as PDF"""
    try:
        start_date = request.args.get('start')
        end_date = request.args.get('end')

        # Get report data (reuse the reports endpoint logic)
        reports_response = get_reports()
        report_data = json.loads(reports_response.get_data())

        # Create a simple text report (in a real app, you'd use a PDF library)
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(f"APPOINTMENT REPORT\n")
            f.write(f"Date Range: {start_date} to {end_date}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write(f"SUMMARY STATISTICS\n")
            f.write(f"Total Appointments: {report_data['total_appointments']}\n")
            f.write(f"Completed: {report_data['completed_appointments']}\n")
            f.write(f"Cancelled: {report_data['cancelled_appointments']}\n")
            f.write(f"No Shows: {report_data['no_show_appointments']}\n")
            f.write(f"Completion Rate: {report_data['completion_rate']}%\n")
            f.write(f"Total Revenue: ${report_data['total_revenue']}\n\n")

            f.write(f"SERVICES BREAKDOWN\n")
            for service in report_data['services_breakdown']:
                f.write(f"{service['name']}: {service['count']} appointments, ${service['revenue']} revenue\n")

            f.write(f"\nPEAK HOURS\n")
            for hour in report_data['peak_hours']:
                if hour['isPeak']:
                    f.write(f"Peak: {hour['time']} ({hour['count']} appointments)\n")

            temp_filename = f.name

        return send_from_directory(
            os.path.dirname(temp_filename),
            os.path.basename(temp_filename),
            as_attachment=True,
            download_name=f"report_{start_date}_to_{end_date}.txt"
        )
    except Exception as e:
        print(f"Error exporting report: {e}")
        return jsonify({'error': 'Failed to export report'}), 500

@app.route('/admin')
def admin_dashboard():
    """Comprehensive Daily Operations Dashboard for Store/Shop Admin"""
    return send_from_directory('.', 'admin_dashboard.html')

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'

    print(f"🤖 AI Chat Agent Server Starting...")
    print(f"📱 Chat Interface: http://localhost:{port}")
    print(f"📊 Admin Dashboard: http://localhost:{port}/admin")
    print(f"🔧 Debug Mode: {debug}")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
