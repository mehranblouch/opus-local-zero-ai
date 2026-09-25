document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('generate-form');
  const submitBtn = document.getElementById('submit-btn');
  const videoUrlInput = document.getElementById('video-url');
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

  let pollInterval = null;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const url = videoUrlInput.value.trim();
    if (!url) return;

    const [minDur, maxDur] = durationSelect.value.split('-').map(Number);
    const maxClips = parseInt(maxClipsSelect.value, 10);
    const layout = layoutSelect.value;
    const captionStyle = captionStyleSelect.value;

    // Reset and show progress
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span>Processing...</span>`;
    progressContainer.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    clipsGrid.innerHTML = '';
    updateProgressUI('Connecting to local AI pipeline...', 2);
    resetSteps();

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

      if (!response.ok) {
        throw new Error(data.error || 'Failed to start video processing');
      }

      const jobId = data.job_id;
      startPolling(jobId);

    } catch (err) {
      alert('Error: ' + err.message);
      resetSubmitButton();
      progressContainer.classList.add('hidden');
    }
  });

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
          resetSubmitButton();
          renderResults(job);
        } else if (job.status === 'failed') {
          clearInterval(pollInterval);
          resetSubmitButton();
          alert('Processing Error: ' + (job.error || job.message));
          progressMessage.textContent = '❌ ' + (job.error || 'Processing Failed');
          progressMessage.style.color = '#ef4444';
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

  function resetSubmitButton() {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `
      <span>Generate Shorts</span>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
    `;
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
      let badgeClass = 'score-high';
      if (viralityScore < 70) badgeClass = 'score-mid';
      if (viralityScore < 50) badgeClass = 'score-low';

      card.innerHTML = `
        <div class="video-preview-wrapper">
          <video src="${clip.video_url}" controls playsinline preload="metadata"></video>
          <div class="virality-badge ${badgeClass}">
            <span class="fire-icon">🔥</span>
            <span>Virality Score: <strong>${viralityScore}/100</strong></span>
          </div>
        </div>
        <div class="clip-info">
          <div class="clip-title-row">
            <h3 class="clip-title">${escapeHtml(clip.title)}</h3>
            <span class="clip-duration">${Math.round(clip.duration)}s</span>
          </div>
          
          <div class="score-breakdown">
            <div class="score-item">
              <span class="label">Hook</span>
              <span class="val">${clip.hook_score || 85}%</span>
            </div>
            <div class="score-item">
              <span class="label">Engagement</span>
              <span class="val">${clip.engagement_score || 80}%</span>
            </div>
            <div class="score-item">
              <span class="label">Pacing</span>
              <span class="val">${clip.coherence_score || 90}%</span>
            </div>
          </div>

          <p class="clip-transcript-snippet">${escapeHtml(clip.text || '')}</p>

          <a href="${clip.video_url}" download="${clip.filename}" class="btn-download">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            <span>Download Short MP4</span>
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
