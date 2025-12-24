import subprocess
import sys
import json
import time
import threading
import traceback
from scraper import scrape
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import asyncio

playwright_lock = threading.Lock()

# Event to pause/resume background scraper
scraper_pause_event = threading.Event()
scraper_pause_event.set()  # Initially not paused

# Priority flag for add_technician
add_technician_priority = threading.Event()
add_technician_priority.clear()

# Preemption flag: set when add_technician is requested, so scraper can pause ASAP
add_technician_requested = threading.Event()
add_technician_requested.clear()

USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

app = Flask(__name__, static_folder="static/dist", static_url_path="")
CORS(app, supports_credentials=True)

user_tasks = {}
background_scraping_started = False
# Global asyncio lock to ensure only one Playwright instance runs at a time
scrape_lock = asyncio.Lock()

WORKERS_FILE = os.path.join(os.path.dirname(__file__), 'workers.json')

def load_workers():
    if not os.path.exists(WORKERS_FILE):
        # Default initial workers
        default_workers = [
            "Amir Laith Samir", "Muhammad Jasim Muhammad",
            "Khaldoun Adel Mohalhal Zaji",
            "yousif muyad majeed",
            "sadiq faaiq Jassim", "Hussein Nizar Hameed",
            "Ali Salman Ibrahim",
            "Ali Abdul Hussein Abdul Wahid", "Muhammad Omar Hasan"
        ]
        with open(WORKERS_FILE, 'w') as f:
            json.dump(default_workers, f)
        return default_workers
    with open(WORKERS_FILE, 'r') as f:
        return json.load(f)

def save_workers(workers):
    with open(WORKERS_FILE, 'w') as f:
        json.dump(workers, f)

@app.route('/check_new_tasks', methods=['GET'])
def check_new_tasks():
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'Username required'}), 400
    columns = user_tasks.get(username)
    if not columns:
        return jsonify({'columns': {'NEW': [], 'Pending': [], 'In Progress': []}})
    # Attach messages from latest CSV to each task
    import csv, glob
    csv_files = glob.glob(os.path.join(os.path.dirname(__file__), 'scraped_results', 'scraped_*.csv'))
    uuid_to_messages = {}
    if csv_files:
        latest_csv = max(csv_files, key=os.path.getmtime)
        with open(latest_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                uuid = row.get('uuid')
                messages_json = row.get('messages')
                if uuid and messages_json:
                    try:
                        messages = json.loads(messages_json.replace('""', '"'))
                    except Exception:
                        messages = []
                    uuid_to_messages[uuid] = messages
    for col_tasks in columns.values():
        for task in col_tasks:
            task['messages'] = uuid_to_messages.get(task.get('uuid'), [])
            task['has_new_message'] = len(task['messages']) > 0
    return jsonify({'columns': columns})

# Endpoint to assign a technician to a task on the real website
@app.route('/add_technician', methods=['POST'])
def add_technician():
    data = request.json
    print(f"[DEBUG] /add_technician request data: {data}")
    task_uuid = data.get('task_uuid')
    worker_name = data.get('worker_name')
    missing = []
    if not task_uuid:
        missing.append('task_uuid')
    if not worker_name:
        missing.append('worker_name')
    if missing:
        return jsonify({'error': f"Missing required field(s): {', '.join(missing)}", 'received': data}), 400
    # Use hardcoded username/password from users.json
    username = "e_morahas"
    password = "4RW,Xlo22*50"
    try:
        print("[add_technician] Launching add_technician.py in a new browser instance", flush=True)
        # No lock, no pause, just launch a new process
        result = subprocess.run([
            sys.executable, 'add_technician.py',
            task_uuid, worker_name, username, password
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__), timeout=180)
        output = result.stdout + '\n' + result.stderr
        print(f"[DEBUG] add_technician.py output:\n{output}")
        print(f"[DEBUG] add_technician.py returncode: {result.returncode}")
        if result.returncode == 0:
            return jsonify({'success': True, 'output': output})
        else:
            return jsonify({'success': False, 'output': output}), 500
    except Exception as e:
        print(f"[ERROR] Exception in /add_technician: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Endpoint to get all technicians (persistent)
@app.route('/api/workers', methods=['GET'])
def get_workers():
    workers = load_workers()
    return jsonify(workers)

def start_background_scraping():
    def background_scraper():
        import csv, glob
        print("[Background] Scraper subprocess loop started.")
        while True:
            scraper_pause_event.wait()
            if add_technician_priority.is_set():
                print("[Background] add_technician is waiting, skipping this scraper cycle.")
                time.sleep(2)
                continue
            print("[Background] Waiting for lock...", flush=True)
            print("[Background] Scraper run started ---")
            try:
                users = load_users()
                for user in users:
                    # Preemption: pause ASAP if add_technician_requested is set
                    if add_technician_requested.is_set():
                        print("[Background] Preemption requested, pausing scraper for add_technician.")
                        break
                    username = user['username']
                    password = user['password']
                    print(f"[Background] Scraping for user: {username}")
                    try:
                        with playwright_lock:
                            # Check preemption again right before starting Playwright
                            if add_technician_requested.is_set():
                                print("[Background] Preemption requested before Playwright session, skipping user.")
                                break
                            print("[Background] Acquired lock, running scraper.py", flush=True)
                            process = subprocess.Popen([
                                sys.executable, 'scraper.py', username, password
                            ], cwd=os.path.dirname(__file__), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                            print(f"[Background] scraper.py output for {username}:")
                            for line in process.stdout:
                                print(line, end='')
                            process.wait()
                        print("[Background] Released lock", flush=True)
                        if process.returncode != 0:
                            print(f"[Background] scraper.py failed for {username} with code {process.returncode}")
                    except Exception as e:
                        print(f"[Background] Exception running scraper.py for {username}: {e}")
                        print("[Background] Delaying 5s after error to allow add_technician to run.", flush=True)
                        time.sleep(5)
                # If preemption was requested, give add_technician a chance to run
                if add_technician_requested.is_set():
                    print("[Background] Preemption: waiting 2s for add_technician to acquire lock...")
                    time.sleep(2)
            except Exception as e:
                print(f"[Background] Error during scraping: {e}")
                print(traceback.format_exc())
                print("[Background] Delaying 5s after error to allow add_technician to run.", flush=True)
                time.sleep(5)
            print("[Background] Scraper run finished --- Waiting 120s\n")
            print("[Background] About to sleep for 120s...")
            time.sleep(120)
            print("[Background] Woke up from 120s sleep, will start next run...")
    t = threading.Thread(target=background_scraper, daemon=True)
    t.start()
    print(f"[Main] Background scraper subprocess thread started. Thread ident: {t.ident}, is_alive: {t.is_alive()}")

@app.route('/check_task_messages', methods=['GET'])
def check_task_messages():
    import csv
    import glob
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'Username required'}), 400
    columns = user_tasks.get(username)
    if not columns:
        return jsonify({'messages': {}})
    # Find the latest CSV file in scraped_results
    csv_files = glob.glob(os.path.join(os.path.dirname(__file__), 'scraped_results', 'scraped_*.csv'))
    if not csv_files:
        return jsonify({'messages': {}})
    latest_csv = max(csv_files, key=os.path.getmtime)
    # Build a mapping from uuid to messages
    uuid_to_messages = {}
    with open(latest_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            uuid = row.get('uuid')
            messages_json = row.get('messages')
            if uuid and messages_json:
                try:
                    messages = json.loads(messages_json.replace('""', '"'))
                except Exception:
                    messages = []
                uuid_to_messages[uuid] = messages
    result = {}
    for col_tasks in columns.values():
        for task in col_tasks:
            case_number = task.get('CaseNumber')
            task_uuid = task.get('uuid')
            messages = uuid_to_messages.get(task_uuid, [])
            last_message = messages[-1]['message'] if messages else None
            last_message_date = messages[-1]['date'] if messages else None
            result[case_number] = {
                'messages': messages,
                'uuid': task_uuid,
                'last_message': last_message,
                'last_message_date': last_message_date
            }
    return jsonify({'messages': result})

@app.route('/login', methods=['POST'])
def login():
    global background_scraping_started
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        # Add user to users.json if not present
        users = load_users()
        if not any(u['username'] == username for u in users):
            users.append({'username': username, 'password': password})
            save_users(users)
            print(f"[Login] Added new user to users.json: {username}")
        # Run scraping for this user and store results
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def locked_scrape():
            async with scrape_lock:
                return await scrape(username, password)
        scraped_data = loop.run_until_complete(locked_scrape())
        columns = {
            'NEW': [],
            'Pending': [],
            'In Progress': []
        }
        # Load messages from latest CSV and merge into tasks by uuid
        import csv, glob
        csv_files = glob.glob(os.path.join(os.path.dirname(__file__), 'scraped_results', 'scraped_*.csv'))
        uuid_to_messages = {}
        if csv_files:
            latest_csv = max(csv_files, key=os.path.getmtime)
            with open(latest_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    uuid = row.get('uuid')
                    messages_json = row.get('messages')
                    if uuid and messages_json:
                        try:
                            messages = json.loads(messages_json.replace('""', '"'))
                        except Exception:
                            messages = []
                        uuid_to_messages[uuid] = messages
        for task in scraped_data:
            col = task.get('Column')
            # Ensure uuid is present for every task
            if 'uuid' not in task or not task['uuid']:
                task['uuid'] = None
            # Attach messages from CSV if available
            task['messages'] = uuid_to_messages.get(task['uuid'], [])
            if col == 'New':
                task['has_new_message'] = len(task['messages']) > 0
                columns['NEW'].append(task)
            elif col == 'Pending':
                task['has_new_message'] = len(task['messages']) > 0
                columns['Pending'].append(task)
            elif col == 'In Progress':
                task['has_new_message'] = len(task['messages']) > 0
                columns['In Progress'].append(task)
        user_tasks[username] = columns
        print(f"[Login] Updated tasks for {username}: {json.dumps(columns)[:500]} ...")
        # Start background scraping only after first login
        if not background_scraping_started:
            print("Starting background scraping thread after first login...")
            start_background_scraping()
            background_scraping_started = True
        return jsonify({
            'success': True,
            'columns': {
                'NEW': columns['NEW'],
                'Pending': columns['Pending'],
                'In Progress': columns['In Progress']
            }
        })
    except Exception as e:
        print(f"[ERROR] Exception in /login: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
# In-memory upload status store
UPLOAD_STATUS = {}
# Endpoint to save form template JSON
@app.route('/api/save-form-template', methods=['POST'])
def save_form_template():
    data = request.get_json()
    task_id = data.get('taskId')
    form_data = data.get('formData')
    if not task_id or not form_data:
        return jsonify({'error': 'Missing taskId or formData'}), 400
    save_dir = os.path.join(os.path.dirname(__file__), 'form-templates')
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f'{task_id}.json')
    try:
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(form_data, f, ensure_ascii=False, indent=2)
        return jsonify({'success': True, 'path': save_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

import requests

TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'token.json')

def load_token():
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE, 'r') as f:
        data = json.load(f)
        return data.get('token')


# Endpoint to fetch dynamic form JSON for a task
@app.route('/api/form/<task_id>', methods=['GET'])
def get_task_form(task_id):
    token = load_token()
    if not token:
        return jsonify({'error': 'Token not found'}), 401
    api_url = f"https://fmsapi.el.earthlink.iq/api/tasks/tasks/{task_id}/template-form"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(api_url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # Save the JSON response to api-form.json in the backend directory
        save_path = os.path.join(os.path.dirname(__file__), 'api-form.json')
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify(data)
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch form from {api_url}")
        print(f"[ERROR] Status code: {getattr(e.response, 'status_code', None)}")
        print(f"[ERROR] Response text: {getattr(e.response, 'text', None)}")
        print(f"[ERROR] Exception: {e}")
        return jsonify({'error': str(e), 'status_code': getattr(e.response, 'status_code', None), 'details': getattr(e.response, 'text', None)}), 502

# --- CATCH-ALL ROUTE FOR REACT SPA ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    # Serve static files if they exist
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # Otherwise, serve index.html for React Router
    return send_from_directory(app.static_folder, 'index.html')

# Endpoint to list all saved form templates
@app.route('/api/list-form-templates', methods=['GET'])
def list_form_templates():
    templates_dir = os.path.join(os.path.dirname(__file__), 'form-templates')
    files = []
    if os.path.exists(templates_dir):
        files = [f for f in os.listdir(templates_dir) if f.endswith('.json')]
    return jsonify({'files': files})

# Endpoint to serve a form template by filename
@app.route('/api/form-template/<filename>', methods=['GET'])
def get_form_template(filename):
    import os
    from flask import abort
    templates_dir = os.path.join(os.path.dirname(__file__), 'form-templates')
    file_path = os.path.join(templates_dir, filename)
    if not os.path.exists(file_path) or not filename.endswith('.json'):
        return abort(404)
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)

    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)