from flask import Flask, request, send_file, jsonify, after_this_request
import yt_dlp
import os
import time
import re

app = Flask(__name__)

def sanitize_filename(filename):
    """Membersihkan karakter yang tidak valid dari nama file."""
    if not filename:
        return "audio"
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.replace(' ', '_')
    filename = filename[:100]
    return filename if filename.strip() else "audio"

def remove_file_with_retry(filepath, max_attempts=3, delay=2):
    """Menghapus file dengan mekanisme retry."""
    for attempt in range(max_attempts):
        try:
            os.remove(filepath)
            print(f"File {filepath} dihapus.")
            return True
        except OSError as e:
            print(f"Gagal menghapus {filepath} (percobaan {attempt+1}/{max_attempts}): {e}")
            if attempt < max_attempts - 1:
                time.sleep(delay)
    return False

@app.route('/')
def index():
    return open('index.html').read()

@app.route('/download', methods=['POST'])
def download():
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({'error': 'URL tidak ditemukan'}), 400

        unique_filename = f'temp_{int(time.time() * 1000)}'
        print(f"Membuat file sementara: {unique_filename}.mp3")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{unique_filename}.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'nocheckcertificate': True,
            'youtube_skip_dash_manifest': True,
            'extractor_args': {
                'youtube': {
                    'player_client': 'web'
                }
            },
            'noplaylist': True,
            'verbose': True,
            'get_title': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            print(f"Full info_dict: {info_dict}")
            video_title = info_dict.get('title', None)
            if video_title is None:
                print("Judul tidak ditemukan, menggunakan fallback 'audio'")
                video_title = 'audio'
            sanitized_title = sanitize_filename(video_title)
            print(f"Judul video: {video_title}")
            print(f"Nama file yang disanitasi: {sanitized_title}.mp3")

            ydl.download([url])

        mp3_file = f'{unique_filename}.mp3'
        if os.path.exists(mp3_file):
            print(f"File siap dikirim: {mp3_file}")
            @after_this_request
            def cleanup(response):
                time.sleep(2)
                remove_file_with_retry(mp3_file)
                return response
            return send_file(
                mp3_file,
                as_attachment=True,
                download_name=f'{sanitized_title}.mp3',
                mimetype='audio/mpeg'
            )
        else:
            return jsonify({'error': 'Gagal membuat file MP3'}), 500

    except Exception as e:
        print(f"Error selama proses: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)