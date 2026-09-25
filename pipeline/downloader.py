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
        self.cookies_file = Path("cookies.txt")

        # Support cookies passed via environment variable (useful on Railway)
        env_cookies = os.environ.get("YOUTUBE_COOKIES", "")
        if env_cookies and not self.cookies_file.exists():
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                f.write(env_cookies)

    def clean_url(self, url: str) -> str:
        """Strip tracking query parameters from YouTube URLs."""
        url = url.strip()
        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0].split("&")[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        elif "watch?v=" in url:
            video_id = url.split("watch?v=")[1].split("&")[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        return url

    def sanitize_filename(self, name: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()[:80]

    def _get_base_ydl_opts(self) -> dict:
        """Base options with cloud bot-protection bypasses for Railway/servers."""
        opts = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 10,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
            # Use iOS/Android/Creator player clients to bypass YouTube datacenter bot detection
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android', 'web_creator', 'tv_embedded'],
                }
            }
        }
        if self.cookies_file.exists():
            opts['cookiefile'] = str(self.cookies_file.resolve())
        return opts

    def get_info(self, url: str) -> Dict[str, Any]:
        """Fetch metadata without downloading."""
        clean_u = self.clean_url(url)
        try:
            import yt_dlp
            ydl_opts = self._get_base_ydl_opts()
            ydl_opts['extract_flat'] = False

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
                # CLI fallback with client args
                cmd = [
                    "yt-dlp", "-J", "--no-warnings",
                    "--extractor-args", "youtube:player_client=ios,android,web_creator",
                    clean_u
                ]
                if self.cookies_file.exists():
                    cmd.extend(["--cookies", str(self.cookies_file)])

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
            progress_callback("Connecting to YouTube stream...", 5)

        clean_u = self.clean_url(url)
        info = self.get_info(clean_u)
        video_id = info['id']
        safe_title = self.sanitize_filename(info['title'])
        
        output_template = str(self.download_dir / f"{video_id}_{safe_title}.%(ext)s")
        video_path = str(self.download_dir / f"{video_id}_{safe_title}.mp4")
        audio_path = str(self.download_dir / f"{video_id}_{safe_title}.mp3")

        # If already downloaded, reuse
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

            format_selector = (
                "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
                "best[height<=1080][ext=mp4]/"
                "bestvideo[height<=1080]+bestaudio/"
                "best[height<=1080]/"
                "best"
            )

            ydl_opts = self._get_base_ydl_opts()
            ydl_opts.update({
                'format': format_selector,
                'outtmpl': output_template,
                'merge_output_format': 'mp4',
                'progress_hooks': [ydl_progress_hook],
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]
            })

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([clean_u])

            # Locate downloaded video file
            matched_files = list(self.download_dir.glob(f"{video_id}_*.mp4"))
            if matched_files:
                video_path = str(matched_files[0])
            else:
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
            if progress_callback:
                progress_callback("Retrying with mobile client stream...", 10)
            
            cmd = [
                "yt-dlp",
                "--extractor-args", "youtube:player_client=ios,android,web_creator",
                "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                "--merge-output-format", "mp4",
                "-o", output_template,
                clean_u
            ]
            if self.cookies_file.exists():
                cmd.extend(["--cookies", str(self.cookies_file)])

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
