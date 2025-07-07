from flask import Flask, request, send_file, jsonify
import requests
import time
import itertools

app = Flask(__name__)

SERVERS = [
    'http://182.30.5.189:5001',  # Laptop 1 aldi
    'http://182.30.5.140:5002',  # Laptop 2 tika
    'http://182.30.6.69:5003',  # Laptop 3 pranaja
    'http://182.30.8.158:5004'   # Laptop 4 eza
]

server_status = {server: True for server in SERVERS}
current_server = itertools.cycle(SERVERS)

def check_server_health(server):
    try:
        response = requests.head(server, timeout=2)
        return response.status_code == 200
    except requests.RequestException:
        return False

def update_server_status():
    for server in SERVERS:
        server_status[server] = check_server_health(server)
        print(f"Status {server}: {'UP' if server_status[server] else 'DOWN'}")

@app.route('/')
def index():
    update_server_status()
    available_servers = [s for s in SERVERS if server_status[s]]
    if not available_servers:
        return open('error.html').read(), 503
    return open('index.html').read()

@app.route('/download', methods=['POST'])
def download():
    update_server_status()
    available_servers = [s for s in SERVERS if server_status[s]]
    if not available_servers:
        return jsonify({'error': 'Tidak ada server yang tersedia'}), 503
    for _ in range(len(SERVERS)):
        server = next(current_server)
        if server in available_servers:
            break
    else:
        return jsonify({'error': 'Tidak ada server yang tersedia'}), 503
    print(f"Meneruskan permintaan ke: {server}")
    try:
        response = requests.post(
            f'{server}/download',
            json=request.get_json(),
            stream=True,
            timeout=60
        )
        if response.status_code != 200:
            return jsonify({'error': response.json().get('error', 'Gagal memproses')}), response.status_code
        filename = response.headers.get('Content-Disposition', 'attachment; filename=audio.mp3').split('filename=')[1].strip('"')
        return send_file(
            response.raw,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name=filename
        )
    except requests.RequestException as e:
        print(f"Error saat meneruskan ke {server}: {str(e)}")
        server_status[server] = False
        return jsonify({'error': 'Server tidak responsif, coba lagi'}), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)