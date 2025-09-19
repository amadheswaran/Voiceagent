#!/usr/bin/env python3
"""
AI Voice Agent Startup Script
Simple launcher for the chat interface and backend server
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_requirements():
    """Check if required dependencies are installed"""
    try:
        import flask
        import flask_cors
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\n🔧 Installing requirements...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies")
            print("Please run: pip install -r requirements.txt")
            return False

def main():
    """Main startup function"""
    print("🤖 AI Voice Agent - Starting...")
    print("=" * 50)

    # Check if we're in the right directory
    if not os.path.exists("call_text_agent.py"):
        print("❌ Error: call_text_agent.py not found")
        print("Please run this script from the VoiceAgent directory")
        return

    # Check dependencies
    if not check_requirements():
        return

    # Start the Flask server
    print("\n🚀 Starting the AI Chat Agent...")
    print("📱 Chat Interface will open at: http://localhost:5000")
    print("📊 Admin Dashboard available at: http://localhost:5000/admin")
    print("\n💡 Press Ctrl+C to stop the server")
    print("=" * 50)

    try:
        # Give a moment for the message to be read
        time.sleep(2)

        # Import and run the Flask app
        from app import app

        # Open browser automatically
        def open_browser():
            time.sleep(1.5)
            webbrowser.open('http://localhost:5000')

        import threading
        timer = threading.Timer(1.5, open_browser)
        timer.start()

        # Start the Flask server
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False
        )

    except KeyboardInterrupt:
        print("\n\n👋 AI Voice Agent stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("Please check the error message above and try again.")

if __name__ == "__main__":
    main()
