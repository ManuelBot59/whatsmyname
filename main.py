from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from socid_extractor import extract
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import signal
import sys

app = Flask(__name__)
app.secret_key = 'Password'
socketio = SocketIO(app)
search_flags = {}
lock = Lock()

def fetch_sites_data():
    response = requests.get("https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json")
    data = response.json()
    sites = data["sites"]
    categories = data.get("categories", [])
    return sites, categories

def extract_social_info(response_text, url):
    try:
        extracted_data = extract(response_text)
        if extracted_data:
            formatted_data = {}
            for key, value in extracted_data.items():
                formatted_key = " ".join(word.capitalize() for word in key.split("_"))
                formatted_data[formatted_key] = value
            return formatted_data
        return None
    except Exception as e:
        return None

def check_sites_concurrently(sites, username, sid):
    total_sites = len(sites)
    found_count = 0
    with requests.Session() as session:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
        }
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(check_site, site, username, headers, session): site for site in sites}
            for index, future in enumerate(as_completed(futures), start=1):
                result = future.result()
                socketio.emit('progress', {'processed': index, 'total': total_sites}, room=sid)
                if result:
                    site_name, uri_display, category, extracted_info = result
                    found_count += 1
                    data = {
                        'site_name': site_name,
                        'url': uri_display,
                        'category': category,
                        'username': username,
                        'extracted_info': extracted_info
                    }
                    socketio.emit('new_result', data, room=sid)
                socketio.emit('found_count', {'found': found_count}, room=sid)
                if index == total_sites:
                    socketio.emit('search_complete', {'total': total_sites, 'found': found_count}, room=sid)

def check_site(site, username, headers, session):
    uri_check = site["uri_check"].format(account=username)
    uri_pretty = site.get("uri_pretty", uri_check).format(account=username)
    uri_display = uri_pretty if "uri_pretty" in site else uri_check
    try:
        res = session.get(uri_check, headers=headers, timeout=10)
        estring_pos = site["e_string"] in res.text
        estring_neg = site["m_string"] in res.text
        if res.status_code == site["e_code"] and estring_pos and not estring_neg:
            category = site["cat"]
            extracted_info = extract_social_info(res.text, uri_check)
            return site["name"], uri_display, category, extracted_info
    except:
        pass
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    sites, categories = fetch_sites_data()
    return render_template("index.html", categories=categories)

@socketio.on('start_search')
def handle_search(data):
    username = data.get('username')
    selected_category = data.get('category')
    sid = request.sid
    with lock:
        search_flags[sid] = True
    sites, categories = fetch_sites_data()
    filtered_sites = [site for site in sites if site["cat"] == selected_category] if selected_category else sites
    check_sites_concurrently(filtered_sites, username, sid)

@socketio.on('request_categories')
def send_categories():
    sites, categories = fetch_sites_data()
    socketio.emit('categories', {'categories': categories}, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    with lock:
        if sid in search_flags:
            del search_flags[sid]

def signal_handler(sig, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':
    import os
    # Detecta el puerto de la nube automáticamente
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)