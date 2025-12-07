import subprocess
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import asyncio
import threading
import time
from scraper import scrape
import os

app = Flask(__name__, static_folder="static/dist", static_url_path="")
CORS(app, supports_credentials=True)

user_sessions = {}
user_tasks = {}

def start_background_scraping():
    def background_scraper():
        print("Background scraping thread started.")
        while True:
            print(f"Background scrape tick: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            for username, password in list(user_sessions.items()):
                print(f"Scraping for user: {username}")
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    scraped_data = loop.run_until_complete(scrape(username, password))
                    # Merge messages for tasks with same uuid to preserve old messages
                    prev_columns = user_tasks.get(username, {
                        'NEW': [],
                        'Pending': [],
                        'In Progress': []
                    })
                    def merge_messages(old_tasks, new_task):
                        for old_task in old_tasks:
                            if old_task.get('uuid') == new_task.get('uuid') and new_task.get('uuid'):
                                # Merge messages, avoid duplicates
                                old_msgs = old_task.get('messages', [])
                                new_msgs = new_task.get('messages', [])
                                # Only add messages not already present
                                msg_texts = set(m['message'] for m in old_msgs)
                                merged_msgs = old_msgs + [m for m in new_msgs if m['message'] not in msg_texts]
                                new_task['messages'] = merged_msgs
                                return new_task
                        return new_task
                    columns = {
                        'NEW': [],
                        'Pending': [],
                        'In Progress': []
                    }
                    for task in scraped_data:
                        col = task.get('Column')
                        if 'uuid' not in task or not task['uuid']:
                            task['uuid'] = None
                        if col == 'New':
                            task['has_new_message'] = False
                            task = merge_messages(prev_columns['NEW'], task)
                            columns['NEW'].append(task)
                        elif col == 'Pending':
                            task['has_new_message'] = False
                            task = merge_messages(prev_columns['Pending'], task)
                            columns['Pending'].append(task)
                        elif col == 'In Progress':
                            task['has_new_message'] = False
                            task = merge_messages(prev_columns['In Progress'], task)
                            columns['In Progress'].append(task)
                    user_tasks[username] = columns
                    print(f"Scraped: NEW={len(columns['NEW'])}, Pending={len(columns['Pending'])}, In Progress={len(columns['In Progress'])} for {username}")
                    print(f"Returned data for {username}: {json.dumps(columns, indent=2)}")
                except Exception as e:
                    print(f"Error scraping for {username}: {e}")
            time.sleep(120)  # time interval between scrapes (2 minutes)
    t = threading.Thread(target=background_scraper, daemon=True)
    t.start()


@app.route('/check_task_messages', methods=['GET'])
def check_task_messages():
    username = request.args.get('username')
    if not username or username not in user_sessions:
        return jsonify({'error': 'User not logged in'}), 401
    columns = user_tasks.get(username)
    if not columns:
        return jsonify({'messages': {}})
    # For each task, check if there are new messages (by date or count)
    result = {}
    for col in ['NEW', 'Pending', 'In Progress']:
        for task in columns[col]:
            msg_list = task.get('messages', [])
            has_new = len(msg_list) > 0
            last_message = msg_list[-1]['message'] if has_new and 'message' in msg_list[-1] else None
            last_message_date = msg_list[-1].get('date') if has_new and 'date' in msg_list[-1] else None
            result[task['CaseNumber']] = {
                'has_new_message': has_new,
                'messages': msg_list,
                'uuid': task.get('uuid'),
                'last_message': last_message,
                'last_message_date': last_message_date
            }
    return jsonify({'messages': result})




@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    user_sessions[username] = password
    # Run scraping for this user and store results
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    scraped_data = loop.run_until_complete(scrape(username, password))
    columns = {
        'NEW': [],
        'Pending': [],
        'In Progress': []
    }
    for task in scraped_data:
        col = task.get('Column')
        # Ensure uuid is present for every task
        if 'uuid' not in task or not task['uuid']:
            task['uuid'] = None
        if col == 'New':
            task['has_new_message'] = False
            columns['NEW'].append(task)
        elif col == 'Pending':
            task['has_new_message'] = False
            columns['Pending'].append(task)
        elif col == 'In Progress':
            task['has_new_message'] = False
            columns['In Progress'].append(task)
    user_tasks[username] = columns
    return jsonify({
        'success': True,
        'columns': {
            'NEW': columns['NEW'],
            'Pending': columns['Pending'],
            'In Progress': columns['In Progress']
        }
    })

@app.route('/check_new_tasks', methods=['GET'])
def check_new_tasks():
    username = request.args.get('username')
    if not username or username not in user_sessions:
        return jsonify({'error': 'User not logged in'}), 401
    columns = user_tasks.get(username)
    if not columns:
        return jsonify({'columns': {'NEW': [], 'Pending': [], 'In Progress': []}})
    return jsonify({'columns': columns})


@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

@app.errorhandler(404)
def not_found(e):
    return send_from_directory(app.static_folder, "index.html")
    
# Endpoint to trigger Playwright automation for adding technician
@app.route('/add_technician', methods=['POST'])
def add_technician():
    data = request.json
    task_uuid = data.get('task_uuid')
    worker_name = data.get('worker_name')
    case_number = data.get('case_number')
    print(f"/add_technician called with: task_uuid={task_uuid}, worker_name={worker_name}, case_number={case_number}")
    if not worker_name:
        print("Error: Missing worker_name")
        return jsonify({'error': 'Missing worker_name'}), 400
    # If uuid is missing, try to scrape it using the case_number
    if not task_uuid and case_number:
        username = request.args.get('username') or next(iter(user_sessions.keys()), None)
        password = user_sessions.get(username)
        print(f"Scraping for uuid: username={username}, password={'***' if password else None}")
        if not username or not password:
            print("Error: No user session available for scraping")
            return jsonify({'error': 'No user session available for scraping'}), 400
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        scraped_data = loop.run_until_complete(scrape(username, password))
        found_uuid = None
        for task in scraped_data:
            print(f"Checking task: CaseNumber={task.get('CaseNumber')}, uuid={task.get('uuid')}")
            if str(task.get('CaseNumber')) == str(case_number):
                found_uuid = task.get('uuid')
                break
        if not found_uuid:
            print("Error: Could not find uuid for given case_number")
            return jsonify({'error': 'Could not find uuid for given case_number'}), 400
        task_uuid = found_uuid
    if not task_uuid:
        print("Error: Missing task_uuid after scraping")
        return jsonify({'error': 'Missing task_uuid'}), 400
    try:
        # Get username and password from session
        username = request.args.get('username') or next(iter(user_sessions.keys()), None)
        password = user_sessions.get(username)
        if not username or not password:
            return jsonify({'error': 'No user session available for automation'}), 400
        # Run the Playwright script as a subprocess with all arguments
        result = subprocess.run([
            'python3', 'add_technician.py', task_uuid, worker_name, username, password
        ], cwd='.', capture_output=True, text=True)
        return jsonify({
            'status': 'started',
            'task_uuid': task_uuid,
            'worker_name': worker_name,
            'stdout': result.stdout,
            'stderr': result.stderr
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    
if __name__ == '__main__':
    start_background_scraping()
    app.run(debug=True, host='0.0.0.0', port=5000)
