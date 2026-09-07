import os
import threading
import uuid
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from scraper import get_video_url_from_episode
from downloader import download_and_compress

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
CORS(app)

tasks = {}

@app.route('/')
def index():
    return render_template('index.html')

# قائمة المسلسلات (نستخدم نفس الـ API السابقة)
@app.route('/api/series')
def api_series():
    # سنستخدم الـ API القديمة من esheq1.store
    import requests
    try:
        resp = requests.get('https://esheq1.store/wp-json/esheeq/v1/series', timeout=10)
        resp.raise_for_status()
        return jsonify(resp.json().get('series', []))
    except:
        return jsonify([])

@app.route('/api/episodes/<int:series_id>')
def api_episodes(series_id):
    import requests
    try:
        resp = requests.get(f'https://esheq1.store/wp-json/esheeq/v1/series/{series_id}/episodes', timeout=10)
        resp.raise_for_status()
        return jsonify(resp.json().get('episodes', []))
    except:
        return jsonify([])

@app.route('/api/watch', methods=['POST'])
def api_watch():
    data = request.json
    episode_url = data.get('episode_url')  # الرابط الكامل للحلقة (مثل https://esheq1.store/watch/.../)
    if not episode_url:
        return jsonify({'error': 'episode_url مطلوب'}), 400

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        'status': 'starting',
        'progress': 0,
        'message': 'جارٍ بدء العملية...',
        'file_path': None,
        'error': None
    }

    def process():
        try:
            # 1. البحث عن رابط فيديو صالح من السيرفرات
            def update_progress(msg, percent):
                tasks[task_id]['message'] = msg
                tasks[task_id]['progress'] = percent
                tasks[task_id]['status'] = 'searching' if percent < 35 else 'downloading'

            video_url, error = get_video_url_from_episode(episode_url, progress_callback=update_progress)
            if error:
                tasks[task_id]['status'] = 'error'
                tasks[task_id]['error'] = error
                return

            # 2. تحميل وضغط الفيديو
            def download_progress(msg, percent):
                tasks[task_id]['message'] = msg
                tasks[task_id]['progress'] = percent
                tasks[task_id]['status'] = 'downloading' if percent < 65 else 'converting'

            output_file = download_and_compress(video_url, task_id, progress_callback=download_progress)
            tasks[task_id]['file_path'] = output_file
            tasks[task_id]['status'] = 'completed'
            tasks[task_id]['progress'] = 100
            tasks[task_id]['message'] = 'اكتمل! يمكنك مشاهدة الفيديو.'

        except Exception as e:
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['error'] = str(e)
            tasks[task_id]['message'] = f'فشل: {str(e)}'

    thread = threading.Thread(target=process)
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
        'message': task.get('message', ''),
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
