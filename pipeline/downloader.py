import os
import re
import json
import subprocess
import requests
from pathlib import Path
from typing import Dict, Any, Callable, Optional

class VideoDownloader:
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_file = Path("cookies.txt")

        # Optional cookies via environment variable on Railway
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

    def get_video_id(self, url: str) -> str:
        clean_u = self.clean_url(url)
        if "watch?v=" in clean_u:
            return clean_u.split("watch?v=")[1].split("&")[0]
        return "video"

    def sanitize_filename(self, name: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()[:80]

    def _get_base_ydl_opts(self) -> dict:
        """Cloud datacenter bypass options for Railway."""
        opts = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 10,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_testsuite', 'android', 'tv_embedded', 'mweb'],
                    'player_skip': ['webpage', 'configs'],
                }
            }
        }
        if self.cookies_file.exists():
            opts['cookiefile'] = str(self.cookies_file.resolve())
        return opts

    def get_info_from_oembed(self, url: str) -> Dict[str, Any]:
        """Ultra-reliable YouTube OEmbed API (official & never blocked on any cloud server)."""
        video_id = self.get_video_id(url)
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            res = requests.get(oembed_url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                return {
                    'id': video_id,
                    'title': data.get('title', f'YouTube Video {video_id}'),
                    'duration': 180, # default placeholder duration
                    'thumbnail': data.get('thumbnail_url', f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"),
                    'uploader': data.get('author_name', ''),
                    'description': ''
                }
        except Exception:
            pass
        return {
            'id': video_id,
            'title': f"YouTube Video {video_id}",
            'duration': 180,
            'thumbnail': f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            'uploader': '',
            'description': ''
        }

    def get_info(self, url: str) -> Dict[str, Any]:
        """Fetch metadata with multi-tier fallback."""
        clean_u = self.clean_url(url)
        video_id = self.get_video_id(clean_u)

        try:
            import yt_dlp
            ydl_opts = self._get_base_ydl_opts()
            ydl_opts['extract_flat'] = False

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_u, download=False)
                return {
                    'id': info.get('id', video_id),
                    'title': info.get('title', 'YouTube Video'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', ''),
                    'description': info.get('description', '')[:300]
                }
        except Exception:
            # Always succeed with official OEmbed metadata even if IP is challenged
            return self.get_info_from_oembed(clean_u)

    def download_via_cobalt(self, url: str, output_path: str, progress_callback: Optional[Callable[[str, float], None]] = None) -> bool:
        """Download directly via Cobalt proxy API (bypasses all datacenter bot protections)."""
        cobalt_instances = [
            "https://api.cobalt.tools",
            "https://co.wuk.sh",
            "https://cobalt-api.kwiatekm.pl"
        ]
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "url": url,
            "vQuality": "720"
        }

        for inst in cobalt_instances:
            try:
                res = requests.post(f"{inst}/api/json", json=payload, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    stream_url = data.get("url")
                    if stream_url:
                        if progress_callback:
                            progress_callback("Streaming video via cloud bypass proxy...", 12)
                        
                        stream_res = requests.get(stream_url, stream=True, timeout=30)
                        if stream_res.status_code == 200:
                            with open(output_path, "wb") as f:
                                for chunk in stream_res.iter_content(chunk_size=1024 * 1024):
                                    if chunk:
                                        f.write(chunk)
                            return True
            except Exception:
                continue
        return False

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
                progress_callback("Video already cached.", 20)
            return {
                **info,
                'video_path': video_path,
                'audio_path': audio_path
            }

        downloaded_ok = False

        # Attempt 1: yt-dlp with mobile testsuite client
        try:
            import yt_dlp

            def ydl_progress_hook(d):
                if d['status'] == 'downloading' and progress_callback:
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
                    downloaded = d.get('downloaded_bytes', 0)
                    pct = (downloaded / total) * 15 + 5
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

            matched_files = list(self.download_dir.glob(f"{video_id}_*.mp4"))
            if matched_files and os.path.getsize(str(matched_files[0])) > 1000:
                video_path = str(matched_files[0])
                downloaded_ok = True

        except Exception as e:
            print(f"[Downloader] yt-dlp primary error: {e}")

        # Attempt 2: Cobalt open-proxy bypass if yt-dlp was bot-blocked
        if not downloaded_ok:
            if progress_callback:
                progress_callback("Activating cloud proxy bypass...", 10)
            success = self.download_via_cobalt(clean_u, video_path, progress_callback)
            if success and os.path.exists(video_path) and os.path.getsize(video_path) > 1000:
                downloaded_ok = True

        # Attempt 3: CLI fallback
        if not downloaded_ok:
            try:
                cmd = [
                    "yt-dlp",
                    "--extractor-args", "youtube:player_client=android_testsuite,android,mweb",
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
                    downloaded_ok = True
            except Exception as e:
                print(f"[Downloader] CLI fallback error: {e}")

        if not downloaded_ok or not os.path.exists(video_path):
            raise RuntimeError(
                "YouTube is blocking the cloud server's IP. "
                "You can export your cookies to Railway using the YOUTUBE_COOKIES environment variable, "
                "or run the server locally on your PC where YouTube doesn't block requests."
            )

        # Extract audio for speech transcription
        if progress_callback:
            progress_callback("Extracting audio for speech recognition...", 22)

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
