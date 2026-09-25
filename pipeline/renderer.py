import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

class ShortsRenderer:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def format_ass_time(self, seconds: float) -> str:
        """Convert float seconds to ASS subtitle timestamp format: H:MM:SS.cc"""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int(round((seconds - int(seconds)) * 100))
        if centis == 100:
            secs += 1
            centis = 0
        return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"

    def generate_ass_subtitles(self, words: List[Dict[str, Any]], clip_start: float, ass_path: str, style_name: str = "mrbeast"):
        """
        Generate ASS subtitle file with animated/highlighted word styling.
        """
        # Style color definitions (ASS uses &HBBGGRR format)
        # Primary: White (&H00FFFFFF), Highlight: Yellow (&H0000FFFF) or Green (&H0027F804)
        highlight_color = "&H0000FFFF" # Yellow
        if style_name == "neon":
            highlight_color = "&H0027F804" # Neon green

        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,65,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,2,40,40,320,1
Style: Highlight,Arial,68,{highlight_color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,105,105,0,0,1,7,3,2,40,40,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        
        # Group words into 3-5 word clusters for readable pacing
        chunk_size = 4
        words_relative = []
        for w in words:
            rel_start = w["start"] - clip_start
            rel_end = w["end"] - clip_start
            if rel_start >= 0:
                words_relative.append({
                    "word": w["word"].upper().strip(),
                    "start": rel_start,
                    "end": rel_end
                })

        for i in range(0, len(words_relative), chunk_size):
            chunk = words_relative[i:i + chunk_size]
            if not chunk:
                continue

            chunk_start = chunk[0]["start"]
            chunk_end = chunk[-1]["end"]

            for target_idx, active_word in enumerate(chunk):
                w_start = self.format_ass_time(max(0, active_word["start"]))
                w_end = self.format_ass_time(max(0, active_word["end"]))

                # Build line with active word highlighted
                line_parts = []
                for idx, w in enumerate(chunk):
                    word_text = w["word"]
                    if idx == target_idx:
                        # Highlight active word
                        line_parts.append(f"{{\\rHighlight}}{{\\c{highlight_color}}}{word_text}{{\\rDefault}}")
                    else:
                        line_parts.append(word_text)

                event_text = " ".join(line_parts)
                events.append(f"Dialogue: 0,{w_start},{w_end},Default,,0,0,0,,{event_text}")

        full_content = ass_header + "\n".join(events)
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(full_content)

    def render_clip(
        self,
        video_path: str,
        clip_data: Dict[str, Any],
        output_filename: str,
        layout: str = "blur", # "blur" or "crop"
        caption_style: str = "mrbeast",
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> str:
        """
        Cut slice, convert to 9:16 (1080x1920), burn subtitles, and encode crisp MP4.
        """
        start_sec = clip_data["start"]
        end_sec = clip_data["end"]
        duration = end_sec - start_sec

        output_path = str(self.output_dir / output_filename)
        ass_path = str(self.output_dir / f"{Path(output_filename).stem}.ass")

        # Generate subtitle file
        if clip_data.get("words"):
            self.generate_ass_subtitles(clip_data["words"], start_sec, ass_path, caption_style)
            has_subtitles = os.path.exists(ass_path)
        else:
            has_subtitles = False

        if progress_callback:
            progress_callback(f"Rendering Short #{clip_data.get('rank', 1)} ({duration:.1f}s)...", 70)

        # Build FFmpeg Filter Graph for 9:16 vertical layout
        # Escape path for Windows ffmpeg ass filter
        escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:")

        if layout == "blur":
            # Blurred background filling 1080x1920 + sharp centered 16:9 foreground
            filter_complex = (
                "[0:v]split=2[bg][fg];"
                "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg_blurred];"
                "[fg]scale=1080:-1[fg_scaled];"
                "[bg_blurred][fg_scaled]overlay=(W-w)/2:(H-h)/2[combined]"
            )
            if has_subtitles:
                filter_complex += f";[combined]ass='{escaped_ass}'[v]"
                final_map = "[v]"
            else:
                final_map = "[combined]"
        else:
            # Direct Center Crop to 9:16
            filter_complex = "[0:v]scale=-1:1920,crop=1080:1920:(in_w-1080)/2:0[cropped]"
            if has_subtitles:
                filter_complex += f";[cropped]ass='{escaped_ass}'[v]"
                final_map = "[v]"
            else:
                final_map = "[cropped]"

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_sec),
            "-to", str(end_sec),
            "-i", video_path,
            "-filter_complex", filter_complex,
            "-map", final_map,
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            output_path
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        except Exception as e:
            # Fallback if ass filter fails (e.g. libass missing), render without subtitles
            print(f"[Renderer] Subtitle burning warning: {e}. Retrying with direct layout...")
            filter_simple = (
                "[0:v]split=2[bg][fg];"
                "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg_blurred];"
                "[fg]scale=1080:-1[fg_scaled];"
                "[bg_blurred][fg_scaled]overlay=(W-w)/2:(H-h)/2"
            )
            cmd_fallback = [
                "ffmpeg", "-y",
                "-ss", str(start_sec),
                "-to", str(end_sec),
                "-i", video_path,
                "-filter_complex", filter_simple,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                output_path
            ]
            subprocess.run(cmd_fallback, check=True)

        return output_path
