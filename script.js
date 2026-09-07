document.addEventListener('DOMContentLoaded', () => {
    const seriesList = document.getElementById('series-list');
    const episodesList = document.getElementById('episodes-list');
    const episodesSection = document.getElementById('episodes-section');
    const playerSection = document.getElementById('player-section');
    const videoPlayer = document.getElementById('video-player');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const loadingDiv = document.getElementById('loading');
    const seriesTitle = document.getElementById('series-title');

    let currentTaskId = null;
    let progressInterval = null;

    // 1. جلب قائمة المسلسلات
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

    // 2. جلب الحلقات لمسلسل معين
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
                    btn.onclick = () => watchEpisode(ep.id);
                    episodesList.appendChild(btn);
                });
            })
            .catch(err => {
                episodesList.innerHTML = '<p style="color:red;">فشل في تحميل الحلقات</p>';
                console.error(err);
            });
    }

    // 3. تشغيل حلقة (طلب تحميل وضغط)
    function watchEpisode(episodeId) {
        // إخفاء المشغل القديم وإظهار شريط التقدم
        playerSection.style.display = 'none';
        videoPlayer.src = '';
        loadingDiv.style.display = 'block';
        progressFill.style.width = '0%';
        progressText.textContent = '0%';

        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }

        fetch('/api/watch', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ episode_id: episodeId })
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
            playerSection.style.display = 'block';
            startPolling(currentTaskId);
        })
        .catch(err => {
            alert('خطأ في بدء التحميل: ' + err);
            loadingDiv.style.display = 'none';
        });
    }

    // 4. استطلاع حالة التقدم
    function startPolling(taskId) {
        if (progressInterval) clearInterval(progressInterval);

        progressInterval = setInterval(() => {
            fetch(`/api/progress/${taskId}`)
                .then(res => res.json())
                .then(status => {
                    progressFill.style.width = status.progress + '%';
                    progressText.textContent = status.progress + '%';

                    if (status.status === 'completed') {
                        clearInterval(progressInterval);
                        progressInterval = null;
                        // تحميل الفيديو في المشغل
                        videoPlayer.src = `/api/video/${taskId}`;
                        videoPlayer.load();
                        videoPlayer.play().catch(() => {});
                        // إعادة ضبط شريط التقدم بعد 3 ثوانٍ
                        setTimeout(() => {
                            progressFill.style.width = '0%';
                            progressText.textContent = 'جاهز';
                        }, 3000);
                    } else if (status.status === 'error') {
                        clearInterval(progressInterval);
                        progressInterval = null;
                        alert('حدث خطأ: ' + status.error);
                        progressText.textContent = 'خطأ';
                    }
                })
                .catch(err => {
                    console.error('خطأ في الاستطلاع:', err);
                });
        }, 1000);
    }
});