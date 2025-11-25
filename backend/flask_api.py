import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import threading
import time
from scraper import scrape

app = Flask(__name__)
CORS(app, supports_credentials=True)

user_sessions = {}
user_tasks = {}

def start_background_scraping():
    def background_scraper():
        print("Background scraping thread started.")
        while True:
            print(f"Background scrape tick: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            for username, password in user_sessions.items():
                print(f"Scraping for user: {username}")
                try:
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


if __name__ == '__main__':
    start_background_scraping()
    app.run(debug=True, host='0.0.0.0', port=5000)
