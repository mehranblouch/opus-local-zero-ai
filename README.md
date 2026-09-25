# 🎬 Opus Local — AI YouTube to Shorts Generator

> **100% Free & Open-Source · Zero API Keys · Runs Completely Locally & Deployable to Railway**

Turn long-form YouTube videos into viral vertical shorts (9:16 for YouTube Shorts, Instagram Reels, TikTok) with animated karaoke captions, smart hook detection, and virality scoring.

---

## ✨ Features

- 🆓 **Zero API Keys Required:** Runs local speech recognition models (`openai-whisper`), local NLP heuristic scoring, and local video rendering (`ffmpeg`).
- 📥 **Fast YouTube Downloader:** Powered by `yt-dlp` to fetch high-definition video and extract clean 16kHz mono audio.
- 🎙️ **Speech-to-Text with Timestamps:** Local Whisper AI extracts every spoken word with precise word-level timestamps.
- 🔥 **Viral Hook & Highlight Detection:** Analyzes speech velocity, question/answer structures, sentiment, and emotional triggers to isolate top viral segments with virality scores (0–100).
- 📱 **9:16 Vertical Video Engine:** 
  - **Studio Blurred Background:** Centers the 16:9 video with a stylish blurred and darkened background.
  - **Smart Center Crop:** Seamless vertical crop.
- 🟡 **Karaoke Subtitles:** High-energy animated subtitles (MrBeast style yellow highlight or Cyber neon) baked directly into the video.
- 🌐 **Modern Web UI:** Dark-mode dashboard with live progress indicators and embedded HTML5 video players.
- ☁️ **Railway & Docker Ready:** Includes `Dockerfile` and `railway.json` for 1-click cloud deployment.

---

## 🚀 Quick Start (Local Windows)

### Option 1: 1-Click Batch File
Simply double-click:
```cmd
run.bat
```
This will automatically set up a virtual environment, install requirements, and launch the web server at `http://localhost:5000`.

---

### Option 2: Manual Setup

1. **Prerequisites:**
   - Python 3.10 or 3.11 installed.
   - [FFmpeg](https://ffmpeg.org/download.html) installed and in your system PATH (`winget install Gyan.FFmpeg`).

2. **Install Dependencies:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run the Web Application:**
   ```bash
   python app.py
   ```
   Open your browser and navigate to `http://localhost:5000`.

---

## 💻 CLI Mode (Command Line)

You can also generate shorts directly from your terminal:

```bash
python cli.py --url "https://www.youtube.com/watch?v=YOUR_VIDEO_ID" --clips 3 --layout blur
```

### CLI Arguments:
| Argument | Description | Default |
|---|---|---|
| `--url`, `-u` | Full YouTube video URL *(required)* | - |
| `--clips`, `-c` | Number of viral clips to extract | `3` |
| `--min-duration` | Minimum clip duration in seconds | `20` |
| `--max-duration` | Maximum clip duration in seconds | `60` |
| `--layout`, `-l` | Layout style (`blur` or `crop`) | `blur` |
| `--caption-style` | Caption highlight style (`mrbeast` or `neon`) | `mrbeast` |
| `--whisper-model` | Whisper model size (`tiny`, `base`, `small`) | `base` |
| `--outdir`, `-o` | Output directory | `output` |

---

## 🚂 Deploy to Railway

This project is pre-configured for **Railway** cloud hosting with Docker and FFmpeg:

1. Push this folder to a GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Opus Local"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/opus-local.git
   git push -u origin main
   ```

2. Go to [Railway.app](https://railway.app) and create a **New Project**.
3. Select **Deploy from GitHub repo** and pick your repository.
4. Railway will detect the `Dockerfile`, install `ffmpeg`, build the container, and assign a live public URL automatically.

---

## 📁 Project Structure

```
opus.pro/
├── app.py                  # Flask web backend & API endpoints
├── cli.py                  # Standalone CLI generator
├── run.bat                 # 1-click Windows runner
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container config with FFmpeg for Railway
├── railway.json            # Railway deployment settings
├── pipeline/
│   ├── downloader.py       # yt-dlp video & audio download
│   ├── transcriber.py      # Local Whisper speech-to-text
│   ├── analyzer.py         # Viral hook detection & ranking
│   └── renderer.py         # 9:16 vertical video & ASS subtitle burner
├── static/
│   ├── app.js              # Frontend interactivity & live polling
│   └── style.css           # Modern dark UI theme
├── templates/
│   └── index.html          # Web dashboard layout
├── downloads/              # Temporary source media
└── output/                 # Generated 9:16 shorts
```

---

## 📜 License
MIT License. Free for personal and commercial use.
