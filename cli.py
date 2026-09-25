import argparse
import sys
from pathlib import Path

from pipeline.downloader import VideoDownloader
from pipeline.transcriber import SpeechTranscriber
from pipeline.analyzer import ViralClipAnalyzer
from pipeline.renderer import ShortsRenderer

def main():
    parser = argparse.ArgumentParser(description="Opus Local — Turn Long YouTube Videos into Viral Shorts (100% Free & Local)")
    parser.add_argument("--url", "-u", type=str, required=True, help="YouTube video URL")
    parser.add_argument("--clips", "-c", type=int, default=3, help="Number of viral shorts to extract (default: 3)")
    parser.add_argument("--min-duration", type=float, default=20.0, help="Minimum clip duration in seconds (default: 20)")
    parser.add_argument("--max-duration", type=float, default=60.0, help="Maximum clip duration in seconds (default: 60)")
    parser.add_argument("--layout", "-l", type=str, choices=["blur", "crop"], default="blur", help="Video layout: 'blur' (blurred background) or 'crop' (center crop)")
    parser.add_argument("--caption-style", type=str, choices=["mrbeast", "neon"], default="mrbeast", help="Caption style: 'mrbeast' or 'neon'")
    parser.add_argument("--whisper-model", type=str, default="base", help="Whisper model size: tiny, base, small, medium (default: base)")
    parser.add_argument("--outdir", "-o", type=str, default="output", help="Output directory for generated shorts")

    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    download_dir = base_dir / "downloads"
    output_dir = Path(args.outdir).resolve() if Path(args.outdir).is_absolute() else base_dir / args.outdir

    download_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("🎬 OPUS LOCAL AI SHORTS GENERATOR (NO API KEYS REQUIRED)")
    print("=" * 60)

    # 1. Download
    print(f"\n[1/4] 📥 Downloading Video from: {args.url}")
    downloader = VideoDownloader(download_dir=str(download_dir))
    video_info = downloader.download(args.url, progress_callback=lambda msg, pct: print(f"  -> {msg} ({pct}%)"))
    print(f"  ✅ Title: {video_info['title']}")
    print(f"  ✅ Duration: {video_info['duration']:.1f}s")

    # 2. Transcribe
    print(f"\n[2/4] 🎙️ Transcribing Audio with local Whisper AI ('{args.whisper_model}' model)...")
    transcriber = SpeechTranscriber(model_size=args.whisper_model)
    segments = transcriber.transcribe(video_info["audio_path"], progress_callback=lambda msg, pct: print(f"  -> {msg} ({pct}%)"))
    print(f"  ✅ Extracted {len(segments)} speech segments with word timestamps")

    # 3. Analyze Virality
    print(f"\n[3/4] 🧠 Analyzing Hooks and Virality Potential...")
    analyzer = ViralClipAnalyzer(
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        max_clips=args.clips
    )
    clips = analyzer.analyze(segments)

    if not clips:
        print("❌ Error: No viral highlight segments met the criteria.")
        sys.exit(1)

    print(f"  ✅ Found {len(clips)} viral segments:")
    for idx, clip in enumerate(clips, 1):
        print(f"     #{idx}: [{clip['start']:.1f}s -> {clip['end']:.1f}s] Score: {clip['score']}/100 | '{clip['title']}'")

    # 4. Render
    print(f"\n[4/4] 🎨 Rendering 9:16 Vertical Shorts with Karaoke Captions...")
    renderer = ShortsRenderer(output_dir=str(output_dir))

    for idx, clip in enumerate(clips, 1):
        filename = f"short_{idx}_{int(clip['score'])}pts.mp4"
        print(f"\n  ▶ Rendering Short #{idx}: '{clip['title']}' -> {filename}")
        rendered_path = renderer.render_clip(
            video_path=video_info["video_path"],
            clip_data=clip,
            output_filename=filename,
            layout=args.layout,
            caption_style=args.caption_style
        )
        print(f"    ✨ Created: {rendered_path}")

    print("\n" + "=" * 60)
    print(f"🎉 ALL SHORTS COMPLETED! Check output folder: {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()
