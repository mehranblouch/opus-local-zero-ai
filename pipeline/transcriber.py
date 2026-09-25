import os
import gc
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

class SpeechTranscriber:
    def __init__(self, model_size: str = "tiny"):
        # "tiny" uses ~75MB RAM with faster-whisper (vs 800MB with openai-whisper+PyTorch)
        self.model_size = os.environ.get("WHISPER_MODEL", model_size)
        self._model = None

    def load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            # Use int8 quantization for minimum memory footprint on Railway
            compute_type = "int8"
            print(f"[SpeechTranscriber] Loading faster-whisper '{self.model_size}' (int8, CPU, low-memory)...")
            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type=compute_type,
                cpu_threads=2,
                num_workers=1
            )
        return self._model

    def transcribe(self, audio_path: str, progress_callback: Optional[Callable[[str, float], None]] = None) -> List[Dict[str, Any]]:
        """
        Transcribe audio file into timestamped segments with word timings.
        Uses faster-whisper (CTranslate2) for 4x less memory than openai-whisper.
        """
        cache_path = f"{audio_path}.transcript.json"
        if os.path.exists(cache_path):
            if progress_callback:
                progress_callback("Loaded cached transcript.", 45)
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

        if progress_callback:
            progress_callback(f"Loading Whisper AI ({self.model_size}) speech model...", 25)

        try:
            model = self.load_model()

            if progress_callback:
                progress_callback(f"Transcribing speech with Whisper AI...", 30)
            
            # Run faster-whisper transcription with word timestamps
            raw_segments, info = model.transcribe(
                audio_path,
                word_timestamps=True,
                beam_size=1,        # Minimize memory usage
                best_of=1,          # Single pass for speed
                vad_filter=True,    # Skip silence segments (faster + saves memory)
                vad_parameters=dict(min_silence_duration_ms=500)
            )

            segments = []
            total_duration = info.duration if info.duration else 1

            for s in raw_segments:
                # Update progress based on segment position
                if progress_callback and total_duration > 0:
                    pct = min(50, 30 + (s.end / total_duration) * 20)
                    progress_callback(f"Transcribing... {int(s.end)}s / {int(total_duration)}s", pct)

                seg_data = {
                    "id": len(segments),
                    "start": round(s.start, 3),
                    "end": round(s.end, 3),
                    "text": s.text.strip(),
                    "words": []
                }
                
                # Word-level timing
                if s.words:
                    for w in s.words:
                        seg_data["words"].append({
                            "word": w.word.strip(),
                            "start": round(w.start, 3),
                            "end": round(w.end, 3),
                            "probability": round(w.probability, 2)
                        })
                else:
                    # Synthesize approximate word timing
                    words_list = seg_data["text"].split()
                    if words_list:
                        dur = (seg_data["end"] - seg_data["start"]) / len(words_list)
                        cur = seg_data["start"]
                        for word in words_list:
                            seg_data["words"].append({
                                "word": word,
                                "start": round(cur, 3),
                                "end": round(cur + dur, 3),
                                "probability": 0.95
                            })
                            cur += dur

                segments.append(seg_data)

            # Aggressive memory cleanup
            gc.collect()

            # Cache transcript to disk
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(segments, f, indent=2, ensure_ascii=False)

            if progress_callback:
                progress_callback("Transcription completed successfully.", 50)

            return segments

        except Exception as e:
            print(f"[SpeechTranscriber Error] {e}")
            raise RuntimeError(f"Transcription failed: {e}")
