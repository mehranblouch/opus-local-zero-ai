document.addEventListener('DOMContentLoaded', () => {
  const tabUrlBtn = document.getElementById('tab-url-btn');
  const tabUploadBtn = document.getElementById('tab-upload-btn');
  const urlInputBlock = document.getElementById('url-input-block');
  const uploadInputBlock = document.getElementById('upload-input-block');

  const form = document.getElementById('generate-form');
  const submitBtn = document.getElementById('submit-btn');
  const uploadSubmitBtn = document.getElementById('upload-submit-btn');
  const videoUrlInput = document.getElementById('video-url');
  const videoFileInput = document.getElementById('video-file');
  const durationSelect = document.getElementById('duration-select');
  const maxClipsSelect = document.getElementById('max-clips');
  const layoutSelect = document.getElementById('layout-select');
  const captionStyleSelect = document.getElementById('caption-style');

  const progressContainer = document.getElementById('progress-container');
  const progressMessage = document.getElementById('progress-message');
  const progressPercent = document.getElementById('progress-percent');
  const progressBarFill = document.getElementById('progress-bar-fill');

  const stepDownload = document.getElementById('step-download');
  const stepWhisper = document.getElementById('step-whisper');
  const stepAnalyze = document.getElementById('step-analyze');
  const stepRender = document.getElementById('step-render');

  const resultsSection = document.getElementById('results-section');
  const videoSourceTitle = document.getElementById('video-source-title');
  const clipsGrid = document.getElementById('clips-grid');
  const downloadAllBtn = document.getElementById('download-all-btn');

  let activeMode = 'url'; // 'url' or 'upload'
  let pollInterval = null;

  // Tab switching
  tabUrlBtn.addEventListener('click', () => {
    activeMode = 'url';
    tabUrlBtn.classList.add('active');
    tabUploadBtn.classList.remove('active');
    urlInputBlock.classList.remove('hidden');
    uploadInputBlock.classList.add('hidden');
    stepDownload.textContent = '1. Download';
  });

  tabUploadBtn.addEventListener('click', () => {
    activeMode = 'upload';
    tabUploadBtn.classList.add('active');
    tabUrlBtn.classList.remove('active');
    uploadInputBlock.classList.remove('hidden');
    urlInputBlock.classList.add('hidden');
    stepDownload.textContent = '1. Process Audio';
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const [minDur, maxDur] = durationSelect.value.split('-').map(Number);
    const maxClips = parseInt(maxClipsSelect.value, 10);
    const layout = layoutSelect.value;
    const captionStyle = captionStyleSelect.value;

    if (activeMode === 'url') {
      const url = videoUrlInput.value.trim();
      if (!url) {
        alert('Please enter a YouTube video URL.');
        return;
      }
      processUrl(url, minDur, maxDur, maxClips, layout, captionStyle);
    } else {
      const file = videoFileInput.files[0];
      if (!file) {
        alert('Please select a video file (.mp4, .mov, etc.) to upload.');
        return;
      }
      processFileUpload(file, minDur, maxDur, maxClips, layout, captionStyle);
    }
  });

  async function processUrl(url, minDur, maxDur, maxClips, layout, captionStyle) {
    setProcessingUI('Connecting to AI pipeline...');
    try {
      const response = await fetch('/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          min_duration: minDur,
          max_duration: maxDur,
          max_clips: maxClips,
          layout,
          caption_style: captionStyle
        })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Failed to start video processing');
      startPolling(data.job_id);
    } catch (err) {
      handleError(err.message);
    }
  }

  async function processFileUpload(file, minDur, maxDur, maxClips, layout, captionStyle) {
    setProcessingUI('Uploading video file to server...');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('min_duration', minDur);
    formData.append('max_duration', maxDur);
    formData.append('max_clips', maxClips);
    formData.append('layout', layout);
    formData.append('caption_style', captionStyle);

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Failed to upload video');
      startPolling(data.job_id);
    } catch (err) {
      handleError(err.message);
    }
  }

  function setProcessingUI(msg) {
    submitBtn.disabled = true;
    uploadSubmitBtn.disabled = true;
    submitBtn.innerHTML = `<span>Processing...</span>`;
    uploadSubmitBtn.innerHTML = `<span>Uploading...</span>`;
    progressContainer.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    clipsGrid.innerHTML = '';
    updateProgressUI(msg, 2);
    resetSteps();
  }

  function startPolling(jobId) {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/status/${jobId}`);
        if (!res.ok) throw new Error('Status check failed');

        const job = await res.json();
        updateProgressUI(job.message || 'Processing...', job.progress || 0);
        updateStepsUI(job.progress || 0);

        if (job.status === 'completed') {
          clearInterval(pollInterval);
          resetButtons();
          renderResults(job);
        } else if (job.status === 'failed') {
          clearInterval(pollInterval);
          handleError(job.error || job.message);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 1500);
  }

  function updateProgressUI(message, percent) {
    progressMessage.textContent = message;
    progressPercent.textContent = `${Math.round(percent)}%`;
    progressBarFill.style.width = `${percent}%`;
  }

  function resetSteps() {
    [stepDownload, stepWhisper, stepAnalyze, stepRender].forEach(el => {
      el.className = 'step-badge';
    });
    stepDownload.classList.add('active');
  }

  function updateStepsUI(pct) {
    [stepDownload, stepWhisper, stepAnalyze, stepRender].forEach(el => {
      el.classList.remove('active', 'completed');
    });

    if (pct < 25) {
      stepDownload.classList.add('active');
    } else if (pct < 55) {
      stepDownload.classList.add('completed');
      stepWhisper.classList.add('active');
    } else if (pct < 60) {
      stepDownload.classList.add('completed');
      stepWhisper.classList.add('completed');
      stepAnalyze.classList.add('active');
    } else if (pct < 100) {
      stepDownload.classList.add('completed');
      stepWhisper.classList.add('completed');
      stepAnalyze.classList.add('completed');
      stepRender.classList.add('active');
    } else {
      [stepDownload, stepWhisper, stepAnalyze, stepRender].forEach(el => el.classList.add('completed'));
    }
  }

  function handleError(errMsg) {
    resetButtons();
    progressMessage.textContent = '❌ ' + errMsg;
    progressMessage.style.color = '#ef4444';
    alert('Error: ' + errMsg);
  }

  function resetButtons() {
    submitBtn.disabled = false;
    uploadSubmitBtn.disabled = false;
    submitBtn.innerHTML = `<span>Generate Shorts</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>`;
    uploadSubmitBtn.innerHTML = `<span>Upload & Generate</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>`;
  }

  function renderResults(job) {
    resultsSection.classList.remove('hidden');
    
    if (job.video_info && job.video_info.title) {
      videoSourceTitle.textContent = `Source: ${job.video_info.title}`;
    }

    clipsGrid.innerHTML = '';
    const clips = job.clips || [];

    if (clips.length === 0) {
      clipsGrid.innerHTML = `<p style="color: var(--text-muted); text-align: center; grid-column: 1/-1;">No clips generated.</p>`;
      return;
    }

    clips.forEach((clip, index) => {
      const card = document.createElement('div');
      card.className = 'clip-card';

      const viralityScore = clip.score || 85;
      card.innerHTML = `
        <div class="video-player-box">
          <video src="${clip.video_url}" controls playsinline preload="metadata"></video>
        </div>
        <div class="clip-content">
          <div class="clip-badges">
            <span class="badge-rank">#${clip.rank || (index + 1)}</span>
            <span class="badge-score">🔥 Score: ${viralityScore}/100</span>
            <span class="badge-dur">${Math.round(clip.duration)}s</span>
          </div>

          <h3 class="clip-title-text">${escapeHtml(clip.title)}</h3>
          <p class="clip-text-snippet">${escapeHtml(clip.text || '')}</p>

          <a href="${clip.video_url}" download="${clip.filename}" class="btn-download">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            <span>Download MP4</span>
          </a>
        </div>
      `;

      clipsGrid.appendChild(card);
    });

    resultsSection.scrollIntoView({ behavior: 'smooth' });
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
});
