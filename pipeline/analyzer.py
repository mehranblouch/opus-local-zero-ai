import re
import math
from typing import List, Dict, Any, Optional

VIRAL_KEYWORDS = {
    # High curiosity & hooks
    "secret": 15, "never": 12, "always": 10, "mistake": 14, "truth": 15,
    "insane": 14, "shocking": 15, "crazy": 12, "unbelievable": 14, "million": 12,
    "billion": 12, "money": 10, "dollar": 10, "rich": 10, "hack": 14,
    "trick": 12, "hidden": 12, "why": 10, "how": 10, "stop": 12,
    "start": 10, "worst": 12, "best": 12, "warning": 15, "nobody": 14,
    "everyone": 10, "advice": 10, "rule": 12, "lesson": 12, "danger": 14,
    "exposed": 15, "proven": 12, "genius": 12, "smart": 10, "stupid": 10,
    "free": 10, "guaranteed": 12, "formula": 12, "strategy": 10
}

HOOK_STARTERS = [
    r"^(did you know|have you ever|what if|here is why|here's why|the reason why)",
    r"^(most people don't|nobody talks about|the biggest mistake|stop doing)",
    r"^(this is how|if you want to|the secret to|never do this|you won't believe)",
    r"^(one of the most|the number one|in my experience|i realized that)"
]

class ViralClipAnalyzer:
    def __init__(self, min_duration: float = 20.0, max_duration: float = 60.0, max_clips: int = 5):
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.max_clips = max_clips

    def score_hook(self, text: str) -> float:
        """Score how engaging the first 3-5 seconds are (0-100)."""
        score = 60.0
        lower = text.lower().strip()

        # Check for questions
        if "?" in text[:80] or lower.startswith(("why", "how", "what", "who", "where", "can you", "did you")):
            score += 15.0

        # Check for hook starter phrases
        for pattern in HOOK_STARTERS:
            if re.search(pattern, lower):
                score += 18.0
                break

        # Check for keywords in beginning
        for kw, boost in VIRAL_KEYWORDS.items():
            if kw in lower[:60]:
                score += boost * 0.5

        return min(99.0, max(50.0, score))

    def score_engagement(self, text: str, duration: float) -> float:
        """Score word pacing and emotional keyword density."""
        lower = text.lower()
        word_count = len(text.split())
        words_per_sec = word_count / max(duration, 1.0)

        # Ideal short speech rate: 2.2 - 3.5 words/second
        pacing_score = 75.0
        if 2.0 <= words_per_sec <= 3.8:
            pacing_score += 12.0
        elif words_per_sec < 1.5:
            pacing_score -= 10.0

        # Keyword density
        kw_hits = sum(1 for kw in VIRAL_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', lower))
        kw_score = min(20.0, kw_hits * 4.0)

        # Punctuation / emphasis
        exclamations = min(10.0, text.count("!") * 3.0)

        total = pacing_score + kw_score + exclamations
        return min(98.0, max(45.0, total))

    def score_coherence(self, start_seg: Dict[str, Any], end_seg: Dict[str, Any], full_text: str) -> float:
        """Check if segment starts cleanly (capitalized/not mid-sentence) and ends with punctuation."""
        score = 75.0
        st = start_seg.get("text", "").strip()
        et = end_seg.get("text", "").strip()

        if st and st[0].isupper():
            score += 10.0
        if et and et[-1] in ".!?":
            score += 15.0

        return min(99.0, max(60.0, score))

    def generate_title(self, text: str) -> str:
        """Create a punchy title from clip content."""
        sentences = [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]
        if not sentences:
            return "Viral Moment"
        
        first = sentences[0]
        words = first.split()
        if len(words) > 8:
            title = " ".join(words[:7]) + "..."
        else:
            title = first
        
        # Capitalize nicely
        return title.strip().title()

    def analyze(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group continuous segments into high-scoring short clips.
        Returns a list of candidate clips sorted by viral score.
        """
        if not segments:
            return []

        candidates = []
        n = len(segments)

        for i in range(n):
            accumulated_text = []
            accumulated_words = []
            start_time = segments[i]["start"]
            
            for j in range(i, n):
                accumulated_text.append(segments[j]["text"])
                accumulated_words.extend(segments[j].get("words", []))
                end_time = segments[j]["end"]
                duration = end_time - start_time

                if duration > self.max_duration:
                    break

                if duration >= self.min_duration:
                    full_text = " ".join(accumulated_text).strip()
                    
                    hook_score = self.score_hook(segments[i]["text"])
                    eng_score = self.score_engagement(full_text, duration)
                    coh_score = self.score_coherence(segments[i], segments[j], full_text)
                    
                    # Overall Virality Score
                    viral_score = round((hook_score * 0.40) + (eng_score * 0.40) + (coh_score * 0.20))
                    
                    title = self.generate_title(full_text)

                    candidates.append({
                        "start": start_time,
                        "end": end_time,
                        "duration": round(duration, 2),
                        "text": full_text,
                        "words": accumulated_words,
                        "score": viral_score,
                        "hook_score": round(hook_score),
                        "engagement_score": round(eng_score),
                        "coherence_score": round(coh_score),
                        "title": title
                    })

        # Sort all candidates by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # Select non-overlapping top clips
        selected_clips = []
        for cand in candidates:
            # Check overlap with already selected
            overlap = False
            for sel in selected_clips:
                # If overlap > 10 seconds, skip
                overlap_start = max(cand["start"], sel["start"])
                overlap_end = min(cand["end"], sel["end"])
                if overlap_end > overlap_start and (overlap_end - overlap_start) > 8.0:
                    overlap = True
                    break

            if not overlap:
                cand["rank"] = len(selected_clips) + 1
                selected_clips.append(cand)
                if len(selected_clips) >= self.max_clips:
                    break

        # Fallback if no clips reached min duration
        if not selected_clips and segments:
            total_dur = segments[-1]["end"] - segments[0]["start"]
            full_text = " ".join(s["text"] for s in segments)
            selected_clips.append({
                "rank": 1,
                "start": segments[0]["start"],
                "end": segments[-1]["end"],
                "duration": round(total_dur, 2),
                "text": full_text,
                "words": [w for s in segments for w in s.get("words", [])],
                "score": 85,
                "hook_score": 88,
                "engagement_score": 82,
                "coherence_score": 85,
                "title": self.generate_title(full_text)
            })

        return selected_clips
