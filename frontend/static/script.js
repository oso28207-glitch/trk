document.addEventListener('DOMContentLoaded', () => {
    const seriesList = document.getElementById('series-list');
    const episodesList = document.getElementById('episodes-list');
    const episodesSection = document.getElementById('episodes-section');
    const playerSection = document.getElementById('player-section');
    const videoPlayer = document.getElementById('video-player');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const statusMessage = document.getElementById('status-message');
    const loadingDiv = document.getElementById('loading');
    const seriesTitle = document.getElementById('series-title');

    let currentTaskId = null;
    let progressInterval = null;

    // جلب المسلسلات
    fetch('/api/series')
        .then(res => res.json())
        .then(series => {
            seriesList.innerHTML = '';
            series.forEach(s => {
                const btn = document.createElement('button');
                btn.textContent = s.title;
                btn.dataset.id = s.id;
                btn.onclick = () => loadEpisodes(s.id, s.title);
                seriesList.appendChild(btn);
            });
        })
        .catch(err => alert('حدث خطأ في تحميل المسلسلات: ' + err));

    function loadEpisodes(seriesId, title) {
        episodesSection.style.display = 'block';
        seriesTitle.textContent = `📺 ${title}`;
        episodesList.innerHTML = '<p>جاري التحميل...</p>';

        fetch(`/api/episodes/${seriesId}`)
            .then(res => res.json())
            .then(episodes => {
                episodesList.innerHTML = '';
                if (episodes.length === 0) {
                    episodesList.innerHTML = '<p>لا توجد حلقات متاحة.</p>';
                    return;
                }
                episodes.forEach(ep => {
                    const btn = document.createElement('button');
                    btn.textContent = `الحلقة ${ep.episode_number || ep.id}`;
                    btn.dataset.id = ep.id;
                    btn.dataset.url = ep.link; // الرابط الكامل للحلقة
                    btn.onclick = () => watchEpisode(ep.link);
                    episodesList.appendChild(btn);
                });
            })
            .catch(err => {
                episodesList.innerHTML = '<p style="color:red;">فشل في تحميل الحلقات</p>';
                console.error(err);
            });
    }

    function watchEpisode(episodeUrl) {
        // إخفاء المشغل القديم وإظهار شريط التقدم
        playerSection.style.display = 'block';
        videoPlayer.style.display = 'none';
        videoPlayer.src = '';
        loadingDiv.style.display = 'block';
        progressFill.style.width = '0%';
        progressText.textContent = '0%';
        statusMessage.textContent = 'جارٍ بدء العملية...';

        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }

        fetch('/api/watch', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ episode_url: episodeUrl })
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                loadingDiv.style.display = 'none';
                return;
            }
            currentTaskId = data.task_id;
            loadingDiv.style.display = 'none';
            startPolling(currentTaskId);
        })
        .catch(err => {
            alert('خطأ في بدء التحميل: ' + err);
            loadingDiv.style.display = 'none';
        });
    }

    function startPolling(taskId) {
        if (progressInterval) clearInterval(progressInterval);

        progressInterval = setInterval(() => {
            fetch(`/api/progress/${taskId}`)
                .then(res => res.json())
                .then(status => {
                    progressFill.style.width = status.progress + '%';
                    progressText.textContent = status.progress + '%';
                    statusMessage.textContent = status.message || '';

                    if (status.status === 'completed') {
                        clearInterval(progressInterval);
                        progressInterval = null;
                        // تحميل الفيديو في المشغل
                        videoPlayer.style.display = 'block';
                        videoPlayer.src = `/api/video/${taskId}`;
                        videoPlayer.load();
                        videoPlayer.play().catch(() => {});
                        // إعادة ضبط شريط التقدم بعد 3 ثوانٍ
                        setTimeout(() => {
                            progressFill.style.width = '0%';
                            progressText.textContent = 'جاهز';
                            statusMessage.textContent = 'جاهز للمشاهدة';
                        }, 3000);
                    } else if (status.status === 'error') {
                        clearInterval(progressInterval);
                        progressInterval = null;
                        alert('حدث خطأ: ' + status.error);
                        statusMessage.textContent = 'فشل: ' + status.error;
                        progressText.textContent = 'خطأ';
                    }
                })
                .catch(err => {
                    console.error('خطأ في الاستطلاع:', err);
                });
        }, 1000);
    }
});
