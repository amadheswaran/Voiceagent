#!/usr/bin/env python3
"""
Multi-Channel Integration for AI Voice Agent
Support for WhatsApp, SMS, Telegram, and other messaging platforms
"""

import json
import requests
import datetime
from typing import Dict, List, Optional
from flask import Flask, request, jsonify
from database import DatabaseManager
from call_text_agent import CallTextAgent, MessageType

class MultiChannelManager:
    def __init__(self, db_path: str = "voiceagent.db"):
        self.db = DatabaseManager(db_path)
        self.agent = CallTextAgent(db_path)
        self.config = self.load_config()
        self.channels = {}

        # Initialize available channels
        self.setup_channels()

    def load_config(self) -> Dict:
        """Load multi-channel configuration"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                return config.get('multi_channel_settings', {
                    'whatsapp': {
                        'enabled': False,
                        'provider': 'twilio',  # or 'whatsapp_business_api'
                        'account_sid': '',
                        'auth_token': '',
                        'phone_number': '',
                        'webhook_verify_token': ''
                    },
                    'sms': {
                        'enabled': False,
                        'provider': 'twilio',
                        'account_sid': '',
                        'auth_token': '',
                        'phone_number': ''
                    },
                    'telegram': {
                        'enabled': False,
                        'bot_token': '',
                        'webhook_url': ''
                    },
                    'messenger': {
                        'enabled': False,
                        'page_access_token': '',
                        'verify_token': '',
                        'app_secret': ''
                    },
                    'webchat': {
                        'enabled': True,
                        'embed_code_available': True
                    }
                })
        except FileNotFoundError:
            return {
                'whatsapp': {'enabled': False},
                'sms': {'enabled': False},
                'telegram': {'enabled': False},
                'messenger': {'enabled': False},
                'webchat': {'enabled': True}
            }

    def setup_channels(self):
        """Initialize enabled channels"""
        if self.config['whatsapp']['enabled']:
            self.channels['whatsapp'] = WhatsAppChannel(self.config['whatsapp'])

        if self.config['sms']['enabled']:
            self.channels['sms'] = SMSChannel(self.config['sms'])

        if self.config['telegram']['enabled']:
            self.channels['telegram'] = TelegramChannel(self.config['telegram'])

        if self.config['messenger']['enabled']:
            self.channels['messenger'] = MessengerChannel(self.config['messenger'])

        if self.config['webchat']['enabled']:
            self.channels['webchat'] = WebChatChannel(self.config['webchat'])

        print(f"✅ Initialized {len(self.channels)} communication channels")

    def process_message(self, channel: str, sender_id: str, message: str, message_data: Dict = None) -> str:
        """Process incoming message from any channel"""
        try:
            # Normalize sender ID (add channel prefix)
            normalized_sender = f"{channel}:{sender_id}"

            # Process through AI agent
            response = self.agent.process_message(normalized_sender, message, MessageType.TEXT)

            # Log the interaction
            self.log_multi_channel_interaction(channel, sender_id, message, response)

            return response

        except Exception as e:
            print(f"Error processing {channel} message: {e}")
            return "I'm sorry, I'm having trouble processing your message right now. Please try again."

    def send_message(self, channel: str, recipient_id: str, message: str) -> bool:
        """Send message through specific channel"""
        try:
            if channel in self.channels:
                return self.channels[channel].send_message(recipient_id, message)
            else:
                print(f"Channel {channel} not available")
                return False

        except Exception as e:
            print(f"Error sending message via {channel}: {e}")
            return False

    def broadcast_message(self, message: str, channels: List[str] = None, user_filter: Dict = None) -> Dict:
        """Broadcast message to multiple channels"""
        if channels is None:
            channels = list(self.channels.keys())

        results = {}

        try:
            # Get users to broadcast to
            users = self.get_broadcast_recipients(user_filter)

            for channel in channels:
                if channel in self.channels:
                    channel_results = []

                    # Filter users by channel
                    channel_users = [user for user in users if user['phone'].startswith(f"{channel}:")]

                    for user in channel_users:
                        # Extract actual ID (remove channel prefix)
                        recipient_id = user['phone'].replace(f"{channel}:", "")
                        success = self.send_message(channel, recipient_id, message)
                        channel_results.append({
                            'recipient_id': recipient_id,
                            'success': success
                        })

                    results[channel] = {
                        'attempted': len(channel_results),
                        'successful': len([r for r in channel_results if r['success']]),
                        'details': channel_results
                    }

            return results

        except Exception as e:
            print(f"Error broadcasting message: {e}")
            return {'error': str(e)}

    def get_broadcast_recipients(self, user_filter: Dict = None) -> List[Dict]:
        """Get users for broadcast based on filter criteria"""
        try:
            # Get all users
            all_users = []

            # This would be implemented with actual user query from database
            # For now, return empty list
            return all_users

        except Exception as e:
            print(f"Error getting broadcast recipients: {e}")
            return []

    def log_multi_channel_interaction(self, channel: str, sender_id: str, message: str, response: str):
        """Log interaction with channel information"""
        try:
            # Save with channel info in the session data
            session_data = {
                'channel': channel,
                'original_sender_id': sender_id,
                'timestamp': datetime.datetime.now().isoformat()
            }

            # You could extend the database to store channel info
            self.db.save_chat_message(
                f"{channel}:{sender_id}",
                message,
                response,
                json.dumps(session_data)
            )

        except Exception as e:
            print(f"Error logging interaction: {e}")

    def get_channel_stats(self) -> Dict:
        """Get statistics for all channels"""
        stats = {}

        try:
            for channel_name, channel in self.channels.items():
                if hasattr(channel, 'get_stats'):
                    stats[channel_name] = channel.get_stats()
                else:
                    stats[channel_name] = {'enabled': True, 'status': 'active'}

            # Add overall stats
            stats['summary'] = {
                'total_channels': len(self.channels),
                'active_channels': len([c for c in self.channels.values() if getattr(c, 'is_active', True)]),
                'total_conversations': self.get_total_conversations()
            }

            return stats

        except Exception as e:
            print(f"Error getting channel stats: {e}")
            return {'error': str(e)}

    def get_total_conversations(self) -> int:
        """Get total number of conversations across all channels"""
        try:
            # Query database for unique users across all channels
            chat_history = self.db.get_chat_history('', 1000)  # Get recent history
            unique_users = set(msg['user_phone'] for msg in chat_history)
            return len(unique_users)

        except Exception:
            return 0

class BaseChannel:
    """Base class for all communication channels"""

    def __init__(self, config: Dict):
        self.config = config
        self.is_active = True

    def send_message(self, recipient_id: str, message: str) -> bool:
        """Send message to recipient"""
        raise NotImplementedError

    def get_stats(self) -> Dict:
        """Get channel statistics"""
        return {'enabled': True, 'status': 'active'}

class WhatsAppChannel(BaseChannel):
    """WhatsApp Business API integration"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.setup_whatsapp()

    def setup_whatsapp(self):
        """Setup WhatsApp connection"""
        try:
            if self.config.get('provider') == 'twilio':
                self.setup_twilio_whatsapp()
            else:
                self.setup_whatsapp_business_api()

        except Exception as e:
            print(f"Error setting up WhatsApp: {e}")
            self.is_active = False

    def setup_twilio_whatsapp(self):
        """Setup Twilio WhatsApp"""
        try:
            from twilio.rest import Client

            account_sid = self.config.get('account_sid')
            auth_token = self.config.get('auth_token')

            if account_sid and auth_token:
                self.client = Client(account_sid, auth_token)
                self.from_number = f"whatsapp:{self.config.get('phone_number')}"
                print("✅ Twilio WhatsApp initialized")
            else:
                print("❌ Twilio credentials missing")
                self.is_active = False

        except ImportError:
            print("❌ Twilio library not installed. Run: pip install twilio")
            self.is_active = False

    def setup_whatsapp_business_api(self):
        """Setup WhatsApp Business API"""
        print("🔧 WhatsApp Business API setup needed")
        # Implementation for direct WhatsApp Business API

    def send_message(self, recipient_id: str, message: str) -> bool:
        """Send WhatsApp message"""
        try:
            if not self.is_active:
                return False

            # Format recipient number
            to_number = f"whatsapp:{recipient_id}" if not recipient_id.startswith('whatsapp:') else recipient_id

            # Send via Twilio
            if hasattr(self, 'client'):
                message_obj = self.client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=to_number
                )
                print(f"✅ WhatsApp message sent: {message_obj.sid}")
                return True

            return False

        except Exception as e:
            print(f"❌ Error sending WhatsApp message: {e}")
            return False

    def get_stats(self) -> Dict:
        """Get WhatsApp channel statistics"""
        return {
            'channel': 'whatsapp',
            'provider': self.config.get('provider'),
            'active': self.is_active,
            'phone_number': self.config.get('phone_number'),
            'features': ['text', 'media', 'templates']
        }

class SMSChannel(BaseChannel):
    """SMS integration via Twilio"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.setup_sms()

    def setup_sms(self):
        """Setup SMS connection"""
        try:
            from twilio.rest import Client

            account_sid = self.config.get('account_sid')
            auth_token = self.config.get('auth_token')

            if account_sid and auth_token:
                self.client = Client(account_sid, auth_token)
                self.from_number = self.config.get('phone_number')
                print("✅ SMS channel initialized")
            else:
                print("❌ SMS credentials missing")
                self.is_active = False

        except ImportError:
            print("❌ Twilio library not installed")
            self.is_active = False

    def send_message(self, recipient_id: str, message: str) -> bool:
        """Send SMS message"""
        try:
            if not self.is_active:
                return False

            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=recipient_id
            )
            print(f"✅ SMS sent: {message_obj.sid}")
            return True

        except Exception as e:
            print(f"❌ Error sending SMS: {e}")
            return False

class TelegramChannel(BaseChannel):
    """Telegram Bot integration"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.bot_token = config.get('bot_token')
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_message(self, recipient_id: str, message: str) -> bool:
        """Send Telegram message"""
        try:
            if not self.bot_token:
                return False

            payload = {
                'chat_id': recipient_id,
                'text': message,
                'parse_mode': 'Markdown'
            }

            response = requests.post(f"{self.api_url}/sendMessage", json=payload)

            if response.status_code == 200:
                print(f"✅ Telegram message sent to {recipient_id}")
                return True
            else:
                print(f"❌ Telegram API error: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error sending Telegram message: {e}")
            return False

class MessengerChannel(BaseChannel):
    """Facebook Messenger integration"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.page_access_token = config.get('page_access_token')
        self.api_url = "https://graph.facebook.com/v18.0/me/messages"

    def send_message(self, recipient_id: str, message: str) -> bool:
        """Send Facebook Messenger message"""
        try:
            if not self.page_access_token:
                return False

            payload = {
                'recipient': {'id': recipient_id},
                'message': {'text': message}
            }

            headers = {
                'Content-Type': 'application/json'
            }

            params = {
                'access_token': self.page_access_token
            }

            response = requests.post(self.api_url, json=payload, headers=headers, params=params)

            if response.status_code == 200:
                print(f"✅ Messenger message sent to {recipient_id}")
                return True
            else:
                print(f"❌ Messenger API error: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error sending Messenger message: {e}")
            return False

class WebChatChannel(BaseChannel):
    """Web chat channel (our existing chat widget)"""

    def __init__(self, config: Dict):
        super().__init__(config)

    def send_message(self, recipient_id: str, message: str) -> bool:
        """Send web chat message (via WebSocket or similar)"""
        # This would integrate with WebSocket for real-time delivery
        print(f"📱 Web chat message to {recipient_id}: {message}")
        return True

    def get_embed_code(self) -> str:
        """Generate embed code for websites"""
        return """
<div id="ai-chat-widget"></div>
<script>
    (function() {
        var script = document.createElement('script');
        script.src = 'http://localhost:8000/static/chat-widget.js';
        script.async = true;
        document.head.appendChild(script);
    })();
</script>
        """

# Flask routes for webhooks
def create_webhook_routes(app: Flask, multi_channel: MultiChannelManager):
    """Create webhook routes for different channels"""

    @app.route('/webhook/whatsapp', methods=['GET', 'POST'])
    def whatsapp_webhook():
        """WhatsApp webhook handler"""
        if request.method == 'GET':
            # Webhook verification
            verify_token = request.args.get('hub.verify_token')
            if verify_token == multi_channel.config['whatsapp'].get('webhook_verify_token'):
                return request.args.get('hub.challenge')
            return 'Invalid verification token', 403

        elif request.method == 'POST':
            # Handle incoming message
            try:
                data = request.get_json()

                # Extract message data (Twilio format)
                from_number = data.get('From', '').replace('whatsapp:', '')
                message_body = data.get('Body', '')

                if from_number and message_body:
                    response = multi_channel.process_message('whatsapp', from_number, message_body)

                    # Send response back
                    multi_channel.send_message('whatsapp', from_number, response)

                return '', 200

            except Exception as e:
                print(f"WhatsApp webhook error: {e}")
                return '', 500

    @app.route('/webhook/telegram', methods=['POST'])
    def telegram_webhook():
        """Telegram webhook handler"""
        try:
            data = request.get_json()

            if 'message' in data:
                message = data['message']
                chat_id = message['chat']['id']
                text = message.get('text', '')

                if text:
                    response = multi_channel.process_message('telegram', str(chat_id), text)
                    multi_channel.send_message('telegram', str(chat_id), response)

            return '', 200

        except Exception as e:
            print(f"Telegram webhook error: {e}")
            return '', 500

    @app.route('/webhook/messenger', methods=['GET', 'POST'])
    def messenger_webhook():
        """Facebook Messenger webhook handler"""
        if request.method == 'GET':
            # Webhook verification
            verify_token = request.args.get('hub.verify_token')
            if verify_token == multi_channel.config['messenger'].get('verify_token'):
                return request.args.get('hub.challenge')
            return 'Invalid verification token', 403

        elif request.method == 'POST':
            try:
                data = request.get_json()

                if 'entry' in data:
                    for entry in data['entry']:
                        for messaging_event in entry.get('messaging', []):
                            if 'message' in messaging_event:
                                sender_id = messaging_event['sender']['id']
                                message_text = messaging_event['message'].get('text', '')

                                if message_text:
                                    response = multi_channel.process_message('messenger', sender_id, message_text)
                                    multi_channel.send_message('messenger', sender_id, response)

                return '', 200

            except Exception as e:
                print(f"Messenger webhook error: {e}")
                return '', 500

def setup_instructions():
    """Print setup instructions for multi-channel integration"""
    instructions = """
📱 Multi-Channel Integration Setup

🟢 **WhatsApp (via Twilio)**
1. Sign up at twilio.com
2. Get WhatsApp-enabled phone number
3. Configure webhook: /webhook/whatsapp
4. Add credentials to config.json

🟢 **SMS (via Twilio)**
1. Use same Twilio account
2. Get SMS-enabled phone number
3. Add credentials to config.json

🟢 **Telegram**
1. Create bot with @BotFather
2. Get bot token
3. Set webhook: https://api.telegram.org/bot<TOKEN>/setWebhook?url=<YOUR_URL>/webhook/telegram

🟢 **Facebook Messenger**
1. Create Facebook App
2. Set up Messenger integration
3. Configure webhook: /webhook/messenger
4. Get page access token

🟢 **Configuration Example:**
{
  "multi_channel_settings": {
    "whatsapp": {
      "enabled": true,
      "provider": "twilio",
      "account_sid": "your_account_sid",
      "auth_token": "your_auth_token",
      "phone_number": "+1234567890"
    }
  }
}
    """
    print(instructions)

if __name__ == "__main__":
    setup_instructions()
