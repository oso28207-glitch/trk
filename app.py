from flask import Flask, request, jsonify, send_file, render_template, url_for
from flask_cors import CORS
import threading
import uuid
import os
from scraper import get_all_series, get_series_episodes, get_video_download_url
from downloader import download_and_compress, tasks
from cleaner import clean_old_files

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
CORS(app)

# تنظيف الملفات القديمة عند بدء التشغيل
clean_old_files()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/series')
def api_series():
    """إرجاع قائمة المسلسلات"""
    series = get_all_series()
    return jsonify(series)

@app.route('/api/episodes/<int:series_id>')
def api_episodes(series_id):
    """إرجاع حلقات مسلسل معين"""
    episodes = get_series_episodes(series_id)
    return jsonify(episodes)

@app.route('/api/watch', methods=['POST'])
def api_watch():
    """بدء عملية تحميل وضغط حلقة معينة"""
    data = request.json
    episode_id = data.get('episode_id')
    if not episode_id:
        return jsonify({'error': 'episode_id مطلوب'}), 400

    # استخراج رابط التحميل من API الخاص بنا
    download_url = get_video_download_url(episode_id)
    if not download_url:
        return jsonify({'error': 'تعذر العثور على رابط تحميل لهذه الحلقة'}), 404

    # إنشاء معرف فريد للمهمة
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        'status': 'queued',
        'progress': 0,
        'file_path': None,
        'error': None
    }

    # تشغيل عملية التحميل والضغط في خيط منفصل
    thread = threading.Thread(target=download_and_compress, args=(episode_id, download_url, task_id))
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id})

@app.route('/api/progress/<task_id>')
def api_progress(task_id):
    """التحقق من تقدم المهمة"""
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
    """تقديم ملف الفيديو المضغوط للمستخدم"""
    task = tasks.get(task_id)
    if not task or task.get('status') != 'completed':
        return jsonify({'error': 'الفيديو غير جاهز بعد'}), 404

    file_path = task.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'الملف مفقود'}), 404

    return send_file(file_path, mimetype='video/mp4', as_attachment=False)

# تشغيل الخادم
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)