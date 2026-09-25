import os
import re
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Callable, Optional

class VideoDownloader:
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def clean_url(self, url: str) -> str:
        """Strip tracking query parameters from YouTube URLs."""
        url = url.strip()
        if "youtu.be/" in url:
            # Format: https://youtu.be/VIDEO_ID?si=...
            video_id = url.split("youtu.be/")[1].split("?")[0].split("&")[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        elif "watch?v=" in url:
            video_id = url.split("watch?v=")[1].split("&")[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        return url

    def sanitize_filename(self, name: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()[:80]

    def get_info(self, url: str) -> Dict[str, Any]:
        """Fetch metadata without downloading."""
        clean_u = self.clean_url(url)
        try:
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'socket_timeout': 30,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_u, download=False)
                return {
                    'id': info.get('id', 'video'),
                    'title': info.get('title', 'YouTube Video'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', ''),
                    'description': info.get('description', '')[:300]
                }
        except Exception as e:
            try:
                cmd = ["yt-dlp", "-J", "--no-warnings", clean_u]
                res = subprocess.run(cmd, capture_output=True, text=True, check=True)
                info = json.loads(res.stdout)
                return {
                    'id': info.get('id', 'video'),
                    'title': info.get('title', 'YouTube Video'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', ''),
                    'description': info.get('description', '')[:300]
                }
            except Exception as sub_e:
                raise RuntimeError(f"Failed to extract video information: {str(e)} / {str(sub_e)}")

    def download(self, url: str, progress_callback: Optional[Callable[[str, float], None]] = None) -> Dict[str, Any]:
        """Download fast 1080p/720p MP4 video and separate 16kHz audio track."""
        if progress_callback:
            progress_callback("Fetching video metadata...", 5)

        clean_u = self.clean_url(url)
        info = self.get_info(clean_u)
        video_id = info['id']
        safe_title = self.sanitize_filename(info['title'])
        
        output_template = str(self.download_dir / f"{video_id}_{safe_title}.%(ext)s")
        video_path = str(self.download_dir / f"{video_id}_{safe_title}.mp4")
        audio_path = str(self.download_dir / f"{video_id}_{safe_title}.mp3")

        # If already downloaded, reuse immediately
        if os.path.exists(video_path) and os.path.exists(audio_path):
            if progress_callback:
                progress_callback("Video already cached locally.", 20)
            return {
                **info,
                'video_path': video_path,
                'audio_path': audio_path
            }

        try:
            import yt_dlp

            def ydl_progress_hook(d):
                if d['status'] == 'downloading' and progress_callback:
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
                    downloaded = d.get('downloaded_bytes', 0)
                    pct = (downloaded / total) * 15 + 5 # Scale to 5%-20%
                    speed = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', d.get('_speed_str', '')).strip()
                    speed_display = f" ({speed})" if speed else ""
                    progress_callback(f"Downloading video... {pct:.1f}%{speed_display}", pct)

            # Max 1080p for fast download and crisp 9:16 rendering without bloat
            format_selector = (
                "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
                "best[height<=1080][ext=mp4]/"
                "bestvideo[height<=1080]+bestaudio/"
                "best[height<=1080]/"
                "best"
            )

            ydl_opts = {
                'format': format_selector,
                'outtmpl': output_template,
                'merge_output_format': 'mp4',
                'progress_hooks': [ydl_progress_hook],
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 30,
                'retries': 5,
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([clean_u])

            # Locate downloaded video file
            matched_files = list(self.download_dir.glob(f"{video_id}_*.mp4"))
            if matched_files:
                video_path = str(matched_files[0])
            else:
                # Any extension fallback
                matched_any = list(self.download_dir.glob(f"{video_id}_*.*"))
                if matched_any:
                    video_path = str(matched_any[0])

            # Extract audio for speech transcription
            if progress_callback:
                progress_callback("Extracting audio track for speech recognition...", 22)

            self.extract_audio(video_path, audio_path)

            return {
                **info,
                'video_path': video_path,
                'audio_path': audio_path
            }

        except Exception as e:
            # CLI fallback
            if progress_callback:
                progress_callback("Retrying download with standard stream...", 10)
            cmd = [
                "yt-dlp",
                "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                "--merge-output-format", "mp4",
                "-o", output_template,
                clean_u
            ]
            subprocess.run(cmd, check=True)
            matched_files = list(self.download_dir.glob(f"{video_id}_*.mp4"))
            if matched_files:
                video_path = str(matched_files[0])
            else:
                matched_any = list(self.download_dir.glob(f"{video_id}_*.*"))
                video_path = str(matched_any[0])

            self.extract_audio(video_path, audio_path)

            return {
                **info,
                'video_path': video_path,
                'audio_path': audio_path
            }

    def extract_audio(self, video_path: str, audio_path: str):
        """Extract high-quality 16kHz mono audio optimized for Whisper."""
        try:
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vn", "-acodec", "libmp3lame",
                "-ar", "16000", "-ac", "1",
                "-q:a", "2",
                audio_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            try:
                from moviepy.editor import VideoFileClip
                clip = VideoFileClip(video_path)
                clip.audio.write_audiofile(audio_path, verbose=False, logger=None)
                clip.close()
            except Exception as e:
                raise RuntimeError(f"Failed to extract audio track: {e}")
