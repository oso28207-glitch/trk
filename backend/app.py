import os
import threading
import uuid
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from scraper import get_all_series, get_series_episodes, get_video_download_url
from downloader import download_and_compress, tasks

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/series')
def api_series():
    return jsonify(get_all_series())

@app.route('/api/episodes/<int:series_id>')
def api_episodes(series_id):
    return jsonify(get_series_episodes(series_id))

@app.route('/api/watch', methods=['POST'])
def api_watch():
    data = request.json
    episode_id = data.get('episode_id')
    if not episode_id:
        return jsonify({'error': 'episode_id مطلوب'}), 400

    download_url = get_video_download_url(episode_id)
    if not download_url:
        return jsonify({'error': 'تعذر العثور على رابط التحميل'}), 404

    task_id = str(uuid.uuid4())
    tasks[task_id] = {'status': 'queued', 'progress': 0, 'file_path': None, 'error': None}
    thread = threading.Thread(target=download_and_compress, args=(episode_id, download_url, task_id))
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id})

@app.route('/api/progress/<task_id>')
def api_progress(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': 'المهمة غير موجودة'}), 404
    return jsonify({
        'status': task.get('status'),
        'progress': task.get('progress', 0),
        'error': task.get('error')
    })

@app.route('/api/video/<task_id>')
def api_video(task_id):
    task = tasks.get(task_id)
    if not task or task.get('status') != 'completed':
        return jsonify({'error': 'الفيديو غير جاهز'}), 404
    file_path = task.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'الملف مفقود'}), 404
    return send_file(file_path, mimetype='video/mp4')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
