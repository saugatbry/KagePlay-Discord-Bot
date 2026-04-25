from flask import Flask, render_template, request, redirect, session, url_for
import os
import json
import threading
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'kageplay-secret-key-123'

def get_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {
        "welcomeChannel": "",
        "welcomeMessage": "Welcome to the server, {user}!",
        "welcomeReaction": "celebrate",
        "leaveChannel": "",
        "leaveMessage": "Goodbye, {user}.",
        "ticketCategory": "",
        "announcementChannel": "",
        "pingRole": "",
        "adminPassword": "admin"
    }

def save_config(data):
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'w') as f:
        json.dump(data, f, indent=4)

def check_auth():
    return session.get('logged_in') is True

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        config = get_config()
        if request.form.get('password') == config.get('adminPassword', 'admin'):
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid password')
    return render_template('login.html', error=None)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    if not check_auth():
        return redirect(url_for('login'))
    
    config = get_config()
    success = request.args.get('success')

    if request.method == 'POST':
        for key in request.form:
            config[key] = request.form.get(key)
        save_config(config)
        return redirect(url_for('dashboard', success="1"))
        
    reactions = ["airkiss","angrystare","bite","bleh","blush","brofist","celebrate","cheers","clap","confused","cool","cry","cuddle","dance","drool","evillaugh","facepalm","handhold","happy","headbang","hug","huh","kiss","laugh","lick","love","mad","nervous","no","nom","nosebleed","nuzzle","nyah","pat","peek","pinch","poke","pout","punch","roll","run","sad","scared","shout","shrug","shy","sigh","sing","sip","slap","sleep","slowclap","smack","smile","smug","sneeze","sorry","stare","stop","surprised","sweat","thumbsup","tickle","tired","wave","wink","woah","yawn","yay","yes"]
    return render_template('dashboard.html', config=config, success=success, reactions=reactions)

@app.route('/env', methods=['GET', 'POST'])
def env_settings():
    if not check_auth():
        return redirect(url_for('login'))
    
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    success = None
    
    if request.method == 'POST':
        with open(env_path, 'w') as f:
            f.write(request.form.get('envContent', ''))
        success = 'Environment variables saved successfully! Restart the app on DOM Cloud to apply.'
        
    env_content = ''
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            env_content = f.read()
            
    return render_template('env.html', envContent=env_content, success=success)

# Export for DOM Cloud Passenger
application = app

def run_bot():
    token = os.getenv("DISCORD_TOKEN")
    if token:
        from bot import start_bot
        start_bot(token)
    else:
        print("DISCORD_TOKEN missing in .env! Cannot start bot thread.")

if __name__ == '__main__':
    # Start bot in background when running locally
    t = threading.Thread(target=run_bot)
    t.daemon = True
    t.start()
    app.run(port=int(os.getenv("DASHBOARD_PORT", 4000)))
