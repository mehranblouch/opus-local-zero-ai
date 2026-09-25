import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

class SpeechTranscriber:
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def load_model(self):
        if self._model is None:
            import whisper
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"[SpeechTranscriber] Loading Whisper '{self.model_size}' model on {device}...")
            self._model = whisper.load_model(self.model_size, device=device)
        return self._model

    def transcribe(self, audio_path: str, progress_callback: Optional[Callable[[str, float], None]] = None) -> List[Dict[str, Any]]:
        """
        Transcribe audio file into timestamped segments with word timings.
        Returns a list of segments: [{ 'start': float, 'end': float, 'text': str, 'words': [...] }]
        """
        cache_path = f"{audio_path}.transcript.json"
        if os.path.exists(cache_path):
            if progress_callback:
                progress_callback("Loaded cached transcript.", 45)
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

        if progress_callback:
            progress_callback(f"Transcribing audio with Whisper AI ({self.model_size})...", 25)

        try:
            model = self.load_model()
            
            # Run whisper transcription with word timestamps enabled
            result = model.transcribe(
                audio_path,
                word_timestamps=True,
                verbose=False
            )

            segments = []
            raw_segments = result.get("segments", [])

            for s in raw_segments:
                seg_data = {
                    "id": s.get("id", len(segments)),
                    "start": round(s.get("start", 0.0), 3),
                    "end": round(s.get("end", 0.0), 3),
                    "text": s.get("text", "").strip(),
                    "words": []
                }
                
                # Word-level timing if available
                words = s.get("words", [])
                if words:
                    for w in words:
                        seg_data["words"].append({
                            "word": w.get("word", "").strip(),
                            "start": round(w.get("start", 0.0), 3),
                            "end": round(w.get("end", 0.0), 3),
                            "probability": round(w.get("probability", 1.0), 2)
                        })
                else:
                    # Synthesize approximate word timing if word_timestamps was not supported
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

            # Cache transcript
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(segments, f, indent=2, ensure_ascii=False)

            if progress_callback:
                progress_callback("Transcription completed successfully.", 50)

            return segments

        except Exception as e:
            print(f"[SpeechTranscriber Error] {e}")
            raise RuntimeError(f"Transcription failed: {e}")
