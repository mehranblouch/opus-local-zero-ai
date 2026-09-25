import os
import uuid
import threading
import time
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from pipeline.downloader import VideoDownloader
from pipeline.transcriber import SpeechTranscriber
from pipeline.analyzer import ViralClipAnalyzer
from pipeline.renderer import ShortsRenderer

BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "output"

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024 # 500 MB max upload
CORS(app)

# In-memory job state tracker
jobs = {}

downloader = VideoDownloader(download_dir=str(DOWNLOADS_DIR))
transcriber = SpeechTranscriber(model_size="tiny")
renderer = ShortsRenderer(output_dir=str(OUTPUT_DIR))

def process_video_job(job_id: str, url_or_path: str, min_dur: float, max_dur: float, max_clips: int, layout: str, caption_style: str, is_local_file: bool = False):
    job = jobs[job_id]
    
    def update_progress(msg: str, pct: float):
        job["status"] = "processing"
        job["message"] = msg
        job["progress"] = round(pct, 1)

    try:
        # Step 1: Video & Audio Preparation
        if is_local_file:
            update_progress("Processing uploaded video...", 5)
            video_path = url_or_path
            filename = Path(video_path).stem
            audio_path = str(DOWNLOADS_DIR / f"{filename}.mp3")
            downloader.extract_audio(video_path, audio_path)
            video_info = {
                "title": filename,
                "video_path": video_path,
                "audio_path": audio_path,
                "duration": 0
            }
        else:
            update_progress("Connecting to YouTube video stream...", 5)
            video_info = downloader.download(url_or_path, progress_callback=update_progress)

        job["video_info"] = {
            "title": video_info.get("title", "Video"),
            "thumbnail": video_info.get("thumbnail", ""),
            "duration": video_info.get("duration", 0),
            "uploader": video_info.get("uploader", "")
        }

        # Step 2: Transcribe Speech with Local Whisper AI
        update_progress("Transcribing speech with Whisper AI...", 25)
        segments = transcriber.transcribe(video_info["audio_path"], progress_callback=update_progress)
        job["segments_count"] = len(segments)

        # Step 3: Analyze & Find Viral Highlights
        update_progress("Detecting viral hooks & engaging segments...", 55)
        analyzer = ViralClipAnalyzer(min_duration=min_dur, max_duration=max_dur, max_clips=max_clips)
        clips = analyzer.analyze(segments)

        if not clips:
            raise RuntimeError("No speech highlight segments met the duration criteria.")

        # Step 4: Render Vertical 9:16 Shorts with Captions
        rendered_clips = []
        total_clips = len(clips)
        
        for idx, clip_data in enumerate(clips):
            step_progress = 60 + ((idx + 1) / total_clips) * 35
            update_progress(f"Rendering Vertical Short {idx + 1} of {total_clips}...", step_progress)

            out_filename = f"short_{job_id}_{idx + 1}.mp4"
            rendered_path = renderer.render_clip(
                video_path=video_info["video_path"],
                clip_data=clip_data,
                output_filename=out_filename,
                layout=layout,
                caption_style=caption_style,
                progress_callback=lambda m, p: None
            )

            rendered_clips.append({
                "rank": clip_data.get("rank", idx + 1),
                "title": clip_data.get("title", f"Short #{idx + 1}"),
                "score": clip_data.get("score", 90),
                "hook_score": clip_data.get("hook_score", 90),
                "engagement_score": clip_data.get("engagement_score", 90),
                "coherence_score": clip_data.get("coherence_score", 90),
                "duration": clip_data.get("duration", 0),
                "text": clip_data.get("text", ""),
                "video_url": f"/output/{out_filename}",
                "filename": out_filename
            })

        job["status"] = "completed"
        job["progress"] = 100
        job["message"] = "All shorts generated successfully!"
        job["clips"] = rendered_clips

    except Exception as e:
        print(f"[Job Error] {e}")
        job["status"] = "failed"
        job["error"] = str(e)
        job["message"] = f"Error: {str(e)}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/process", methods=["POST"])
def start_process():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    
    if not url:
        return jsonify({"error": "YouTube video URL is required"}), 400

    min_dur = float(data.get("min_duration", 20))
    max_dur = float(data.get("max_duration", 60))
    max_clips = int(data.get("max_clips", 5))
    layout = data.get("layout", "blur")
    caption_style = data.get("caption_style", "mrbeast")

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "progress": 0,
        "message": "Initializing...",
        "created_at": time.time(),
        "clips": []
    }

    thread = threading.Thread(
        target=process_video_job,
        args=(job_id, url, min_dur, max_dur, max_clips, layout, caption_style, False),
        daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id, "status": "queued"})

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    job_id = str(uuid.uuid4())[:8]
    saved_path = str(DOWNLOADS_DIR / f"{job_id}_{filename}")
    file.save(saved_path)

    min_dur = float(request.form.get("min_duration", 20))
    max_dur = float(request.form.get("max_duration", 60))
    max_clips = int(request.form.get("max_clips", 5))
    layout = request.form.get("layout", "blur")
    caption_style = request.form.get("caption_style", "mrbeast")

    jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "progress": 0,
        "message": "Initializing video upload...",
        "created_at": time.time(),
        "clips": []
    }

    thread = threading.Thread(
        target=process_video_job,
        args=(job_id, saved_path, min_dur, max_dur, max_clips, layout, caption_style, True),
        daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id, "status": "queued"})

@app.route("/api/status/<job_id>", methods=["GET"])
def get_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory(str(OUTPUT_DIR), filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Local AI Shorts Generator running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
