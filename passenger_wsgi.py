import os
import sys
import threading

sys.path.insert(0, os.path.dirname(__file__))

from app import application

def run_bot_thread():
    from bot import start_bot
    token = os.getenv("DISCORD_TOKEN")
    if token:
        try:
            start_bot(token)
        except Exception as e:
            print("Bot crash:", e)

# DOM Cloud uses Passenger, which loads this file.
# We spawn the Discord bot in a background thread before handing the Flask app to Passenger.
if not any(t.name == "DiscordBotThread" for t in threading.enumerate()):
    t = threading.Thread(target=run_bot_thread, name="DiscordBotThread")
    t.daemon = True
    t.start()
