# AI Voice Agent - Chat Interface

## 📋 Overview

This is a complete AI voice agent system with a user-friendly chat interface for:
- ✨ **Simple Chat UI** - Clean, minimal "bit window" style interface
- 🤖 **AI Conversations** - Automated responses to common questions
- 📅 **Appointment Booking** - Full booking workflow with confirmations
- 📊 **Admin Dashboard** - Monitor appointments and system status
- 🔧 **Easy Setup** - One-click startup and configuration

## 🚀 Quick Start

### Option 1: One-Click Startup (Recommended)
```bash
python start.py
```
This will automatically:
- Install dependencies if needed
- Start the web server
- Open your browser to the chat interface

### Option 2: Manual Setup
1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Server**
   ```bash
   python app.py
   ```

3. **Open Chat Interface**
   - Visit: http://localhost:5000
   - Admin Dashboard: http://localhost:5000/admin

### Option 3: Test Backend Only
```bash
python call_text_agent.py
```

## 💬 Using the Chat Interface

1. **Open the chat** at http://localhost:5000
2. **Try these commands:**
   - "Hi" - Get started
   - "book appointment" - Start booking process
   - "hours" - Business hours
   - "services" - Available services
   - "prices" - Pricing information

3. **Quick Actions** - Use the blue buttons for common requests

## 🔌 Integration Options

### SMS Integration (Twilio)

```python
from flask import Flask, request
from twilio.rest import Client
from call_text_agent import CallTextAgent

app = Flask(__name__)
agent = CallTextAgent()
twilio_client = Client(account_sid, auth_token)

@app.route('/sms', methods=['POST'])
def handle_sms():
    from_number = request.form['From']
    message = request.form['Body']
    
    # Process through agent
    response = agent.process_message(from_number, message)
    
    # Send response back
    twilio_client.messages.create(
        body=response,
        from_=YOUR_TWILIO_NUMBER,
        to=from_number
    )
    
    return '', 204
```

### Voice Call Integration

```python
from twilio.twiml import VoiceResponse

@app.route('/voice', methods=['POST'])
def handle_voice():
    response = VoiceResponse()
    
    # Convert speech to text (using Twilio's speech recognition)
    response.gather(
        input='speech',
        action='/process_speech',
        speech_timeout='auto'
    )
    
    response.say("Hello! How can I help you today?")
    return str(response)

@app.route('/process_speech', methods=['POST'])
def process_speech():
    speech_result = request.form.get('SpeechResult', '')
    from_number = request.form['From']
    
    # Process through agent
    agent_response = agent.process_message(from_number, speech_result)
    
    # Convert back to speech
    response = VoiceResponse()
    response.say(agent_response)
    response.hangup()
    
    return str(response)
```

## 🛠️ Platform Integrations

### 1. Twilio (Recommended)
- **Features**: SMS, Voice, WhatsApp
- **Setup**: Sign up at twilio.com
- **Cost**: Pay per message/minute
- **Documentation**: [Twilio Python Quickstart](https://www.twilio.com/docs/sms/quickstart/python)

### 2. MessageBird
- **Features**: SMS, Voice, WhatsApp, Telegram
- **Setup**: Sign up at messagebird.com
- **Cost**: Pay per message
- **Documentation**: [MessageBird Python SDK](https://developers.messagebird.com/docs/sms-messaging)

### 3. Vonage (Nexmo)
- **Features**: SMS, Voice, WhatsApp
- **Setup**: Sign up at vonage.com
- **Documentation**: [Vonage Python SDK](https://developer.vonage.com/messaging/sms/code-snippets/send-an-sms/python)

### 4. AWS SNS
- **Features**: SMS only
- **Setup**: AWS Console
- **Cost**: Very low per message
- **Documentation**: [AWS SNS Python](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sns.html)

## 📱 WhatsApp Business API Integration

```python
# Using Twilio's WhatsApp Business API
@app.route('/whatsapp', methods=['POST'])
def handle_whatsapp():
    from_number = request.form['From'].replace('whatsapp:', '')
    message = request.form['Body']
    
    response = agent.process_message(from_number, message)
    
    twilio_client.messages.create(
        body=response,
        from_='whatsapp:+14155238886',  # Twilio Sandbox
        to=f'whatsapp:{from_number}'
    )
    
    return '', 204
```

## 🗄️ Database Integration

### SQLite (Simple)
```python
import sqlite3

def save_appointment(appointment):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO appointments 
        (id, name, phone, service, date, time, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        appointment.id,
        appointment.name,
        appointment.phone,
        appointment.service,
        appointment.date,
        appointment.time,
        appointment.status
    ))
    
    conn.commit()
    conn.close()
```

### PostgreSQL (Production)
```python
import psycopg2
from psycopg2.extras import RealDictCursor

def get_appointments():
    conn = psycopg2.connect(
        host="localhost",
        database="appointments",
        user="username",
        password="password"
    )
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM appointments ORDER BY date, time")
    appointments = cursor.fetchall()
    
    conn.close()
    return appointments
```

## 🔐 Security Best Practices

1. **Environment Variables**
   ```python
   import os
   TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
   TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
   ```

2. **Request Validation**
   ```python
   from twilio.request_validator import RequestValidator
   
   def validate_twilio_request():
       validator = RequestValidator(TWILIO_AUTH_TOKEN)
       return validator.validate(
           request.url,
           request.form,
           request.headers.get('X-Twilio-Signature', '')
       )
   ```

3. **Rate Limiting**
   ```python
   from flask_limiter import Limiter
   
   limiter = Limiter(
       app,
       key_func=lambda: request.form.get('From', 'anonymous'),
       default_limits=["10 per minute"]
   )
   ```

## 📊 Analytics Integration

### Google Analytics
```python
import requests

def track_conversation_event(phone_number, event_type):
    data = {
        'v': '1',  # Version
        'tid': 'UA-XXXXX-Y',  # Tracking ID
        'cid': hash(phone_number),  # Client ID
        't': 'event',  # Hit Type
        'ec': 'Agent',  # Event Category
        'ea': event_type,  # Event Action
    }
    
    requests.post('https://www.google-analytics.com/collect', data=data)
```

## 🚀 Deployment Options

### 1. Heroku (Easiest)
```bash
# Create requirements.txt
echo "flask==2.0.1" > requirements.txt
echo "twilio==7.16.0" >> requirements.txt

# Create Procfile
echo "web: python app.py" > Procfile

# Deploy
git init
git add .
git commit -m "Initial commit"
heroku create your-app-name
git push heroku main
```

### 2. AWS Lambda (Serverless)
```python
import json
import boto3
from call_text_agent import CallTextAgent

agent = CallTextAgent()

def lambda_handler(event, context):
    # Parse webhook data
    body = json.loads(event['body'])
    phone = body.get('From')
    message = body.get('Body')
    
    # Process message
    response = agent.process_message(phone, message)
    
    # Send SMS response via SNS
    sns = boto3.client('sns')
    sns.publish(
        PhoneNumber=phone,
        Message=response
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({'status': 'success'})
    }
```

### 3. Docker Container
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["python", "app.py"]
```

## 🔧 Customization Guide

### 1. Adding New FAQ Categories
Edit `config.json`:
```json
{
  "faq_responses": {
    "new_category": "Your custom response here",
    "existing_category": "Updated response"
  }
}
```

### 2. Custom Services
```json
{
  "services": [
    {
      "name": "New Service",
      "price": "$50+",
      "duration": "60 minutes"
    }
  ]
}
```

### 3. Multi-language Support
```python
def get_response_language(phone_number):
    # Detect or store user language preference
    return user_preferences.get(phone_number, 'en')

def translate_response(text, language):
    # Use Google Translate API or similar
    return translated_text
```

## 📞 Testing Your Setup

1. **Local Testing**: Use ngrok to expose localhost
2. **SMS Testing**: Send test messages to your number
3. **Voice Testing**: Call your Twilio number
4. **Load Testing**: Use tools like Apache Bench

## 🆘 Troubleshooting

### Common Issues:
- **Webhook not receiving**: Check URL and SSL certificate
- **Messages not sending**: Verify API credentials
- **Rate limiting**: Implement proper delays
- **Database errors**: Check connection strings

### Debug Mode:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Next Steps

1. Add payment integration (Stripe, PayPal)
2. Implement calendar sync (Google Calendar, Outlook)
3. Add customer feedback collection
4. Create admin dashboard
5. Implement AI-powered responses

## 🤝 Support

For questions or issues:
1. Check the troubleshooting section
2. Review platform documentation
3. Test with the web interface first
4. Monitor logs for error messages

Remember to test thoroughly before going live with customers!



requirements.txt

Flask==2.3.3
Flask-CORS==4.0.0
Flask-SocketIO==5.3.6
python-dotenv==1.0.0
schedule==1.2.0
requests==2.31.0
twilio==8.10.0
google-api-python-client==2.108.0
google-auth-httplib2==0.1.1
google-auth-oauthlib==1.1.0

=================
setup guide


# 🚀 AI Voice Agent - Complete Setup Guide

## 🎉 **What You've Built**

Your AI Voice Agent is now **enterprise-grade** with these powerful features:

### ✅ **Core Features**
- 🎤 **Voice Input/Output** - Speak to the agent, hear responses
- 💬 **Smart Chat Interface** - Clean, mobile-friendly design
- 📅 **Appointment Booking** - Full workflow with confirmations
- 💾 **Database Storage** - Persistent data, chat history, analytics
- 🔔 **Automated Reminders** - 24hr/2hr before appointments
- 🧠 **Smart Scheduling** - Conflict detection, alternative suggestions
- 📱 **Multi-Channel** - WhatsApp, SMS, Telegram, Messenger support
- 📊 **Admin Dashboard** - Real-time stats and management

---

## 🚀 **Quick Start (3 Steps)**

### 1. **Install Dependencies**
```bash
pip3 install -r requirements.txt
```

### 2. **Start the System**
```bash
python3 start.py
```

### 3. **Open Your Agent**
- 💬 **Chat Interface**: http://localhost:5000
- 📊 **Admin Dashboard**: http://localhost:5000/admin

**That's it!** Your agent is ready for customers.

---

## 🎯 **Basic Configuration**

Edit `config.json` to customize:

```json
{
  "business_info": {
    "name": "Your Business Name",
    "address": "Your Address",
    "phone": "Your Phone"
  },
  "services": [
    {
      "name": "Your Service",
      "price": "$50+",
      "duration": "60 minutes"
    }
  ]
}
```

---

## 📱 **Advanced Integrations**

### 🗓️ **Google Calendar Setup**

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project
   - Enable Google Calendar API

2. **Get Credentials**
   - Create OAuth 2.0 Client ID (Desktop app)
   - Download `credentials.json` to your project folder

3. **Configure**
   ```json
   "calendar_settings": {
     "enabled": true,
     "calendar_id": "primary",
     "sync_direction": "both"
   }
   ```

4. **First Run**
   - Agent will open browser for authentication
   - Grant calendar permissions
   - `token.json` created automatically

### 📱 **WhatsApp Integration**

1. **Get Twilio Account**
   - Sign up at [twilio.com](https://twilio.com)
   - Get WhatsApp-enabled phone number

2. **Configure Webhook**
   - Webhook URL: `https://yourdomain.com/webhook/whatsapp`
   - Verify Token: Set your own token

3. **Update Config**
   ```json
   "multi_channel_settings": {
     "whatsapp": {
       "enabled": true,
       "provider": "twilio",
       "account_sid": "your_sid",
       "auth_token": "your_token",
       "phone_number": "+1234567890"
     }
   }
   ```

### 📧 **Email Reminders**

1. **SMTP Setup**
   ```json
   "reminder_settings": {
     "email_enabled": true,
     "smtp_server": "smtp.gmail.com",
     "smtp_port": 587,
     "email_user": "your_email@gmail.com",
     "email_password": "your_app_password"
   }
   ```

2. **Gmail App Password**
   - Enable 2FA on Gmail
   - Generate App Password
   - Use App Password (not regular password)

---

## 🔧 **Production Deployment**

### 🌐 **Deploy on Heroku**

1. **Prepare Files**
   ```bash
   echo "web: python app.py" > Procfile
   echo "python-3.11.0" > runtime.txt
   ```

2. **Deploy**
   ```bash
   git init
   git add .
   git commit -m "Deploy AI Voice Agent"
   heroku create your-agent-name
   git push heroku main
   ```

3. **Set Environment Variables**
   ```bash
   heroku config:set PORT=8000
   heroku config:set TWILIO_ACCOUNT_SID=your_sid
   heroku config:set TWILIO_AUTH_TOKEN=your_token
   ```

### 🐳 **Docker Deployment**

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   EXPOSE 8000
   CMD ["python", "app.py"]
   ```

2. **Build & Run**
   ```bash
   docker build -t ai-voice-agent .
   docker run -p 8000:8000 ai-voice-agent
   ```

### ☁️ **AWS/DigitalOcean**

1. **Upload Files** to your server
2. **Install Python 3.11+**
3. **Run Setup**
   ```bash
   pip3 install -r requirements.txt
   python3 app.py
   ```

4. **Setup Nginx** (optional)
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
       }
   }
   ```

---

## 🔒 **Security Setup**

### 🛡️ **Basic Security**

1. **Environment Variables**
   ```bash
   export TWILIO_ACCOUNT_SID="your_sid"
   export TWILIO_AUTH_TOKEN="your_token"
   export DATABASE_URL="sqlite:///production.db"
   ```

2. **HTTPS/SSL** (Required for production)
   - Use Cloudflare, Let's Encrypt, or your hosting provider
   - Update webhook URLs to `https://`

3. **Rate Limiting**
   ```python
   # Already included in the code
   # Prevents spam and abuse
   ```

### 🔐 **Advanced Security**

1. **Webhook Validation**
   - Verify Twilio signatures
   - Check request origins
   - Validate tokens

2. **Database Security**
   - Use PostgreSQL for production
   - Enable database encryption
   - Regular backups

---

## 📊 **Analytics & Monitoring**

### 📈 **Built-in Analytics**
- User engagement metrics
- Appointment conversion rates
- Channel performance
- Peak usage times

### 🔍 **External Monitoring**

1. **Google Analytics**
   ```javascript
   // Add to your website
   gtag('event', 'chat_started', {
     'event_category': 'engagement',
     'event_label': 'ai_agent'
   });
   ```

2. **Error Tracking**
   - Sentry.io integration
   - Log monitoring
   - Uptime monitoring

---

## 🎨 **Customization**

### 🖌️ **Brand Your Interface**

1. **Colors & Styling**
   - Edit `chat_widget.html`
   - Update CSS variables
   - Add your logo

2. **Voice Settings**
   - Change voice parameters
   - Add language support
   - Custom wake words

### 🤖 **AI Responses**

1. **Custom FAQ**
   - Edit `config.json`
   - Add business-specific responses
   - Update service information

2. **Conversation Flow**
   - Modify `call_text_agent.py`
   - Add new conversation states
   - Custom validation rules

---

## 🚀 **Advanced Features**

### 💳 **Payment Integration**

```python
# Stripe integration example
@app.route('/process-payment', methods=['POST'])
def process_payment():
    # Payment processing logic
    # Integrate with Stripe/PayPal
    pass
```

### 🔗 **Webhook Integrations**

```python
# Custom webhook for CRM integration
@app.route('/webhook/crm', methods=['POST'])
def crm_webhook():
    # Send appointment data to CRM
    # Update customer records
    pass
```

### 📱 **Mobile App**

- React Native wrapper
- Push notifications
- Offline mode support

---

## 🆘 **Troubleshooting**

### ❌ **Common Issues**

**Server won't start:**
```bash
# Check port availability
lsof -i :8000

# Use different port
PORT=8080 python3 app.py
```

**Voice not working:**
- Check browser permissions
- Use HTTPS for production
- Test microphone access

**Database errors:**
```bash
# Reset database
rm voiceagent.db
python3 database.py
```

**Calendar sync failing:**
- Check `credentials.json`
- Re-authenticate: `rm token.json`
- Verify API quotas

### 📞 **Support**

1. **Check Logs**
   - Console output
   - Error messages
   - Browser developer tools

2. **Test Components**
   ```bash
   # Test database
   python3 database.py

   # Test calendar
   python3 calendar_integration.py

   # Test reminders
   python3 reminder_system.py
   ```

---

## 🎯 **What's Next?**

Your AI Voice Agent is **production-ready**! Here's how to scale:

### 📈 **Growth Features**
- [ ] Multi-language support
- [ ] AI-powered responses (OpenAI/Claude integration)
- [ ] Advanced analytics dashboard
- [ ] Mobile app development
- [ ] Enterprise features (SSO, multi-tenant)

### 🔄 **Maintenance**
- [ ] Regular database backups
- [ ] Security updates
- [ ] Performance monitoring
- [ ] User feedback collection

### 🚀 **Scaling**
- [ ] Load balancing
- [ ] CDN integration
- [ ] Database clustering
- [ ] Microservices architecture

---

## 💡 **Tips for Success**

1. **Start Simple** - Enable basic features first
2. **Test Thoroughly** - Use all channels before going live
3. **Monitor Usage** - Check analytics regularly
4. **Get Feedback** - Ask customers for input
5. **Iterate Fast** - Add features based on demand

## 🎊 **Congratulations!**

You now have a **world-class AI Voice Agent** that can:
- Handle customer inquiries 24/7
- Book appointments automatically
- Send reminders reliably
- Work across multiple channels
- Scale with your business

**Your customers will love the seamless experience!** 🚀

---

*Need help? Check the troubleshooting section or review the individual component documentation.*
