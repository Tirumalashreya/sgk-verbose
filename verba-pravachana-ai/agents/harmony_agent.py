"""
Detects shloka/chanting regions in audio based on melodic/harmonic properties.
When a speaker chants a shloka, their voice becomes more melodic:
  - Higher pitch variation (singing vs speaking)
  - More regular rhythm
  - Slower speech rate
"""

from graph.state import VerbaState
import os

def harmony_agent(state: VerbaState) -> VerbaState:
    audio_path = state.get("audio_path")
    if not audio_path or not os.path.exists(audio_path):
        state["harmonic_regions"] = []
        return state

    try:
        import librosa
        import numpy as np

        print(f"[harmony] analysing {audio_path} for melodic/chanting regions...")
        y, sr = librosa.load(audio_path, sr=16000, mono=True)

        # Split audio into 3-second frames
        frame_len  = sr * 3
        hop        = sr * 1
        regions    = []

        for start in range(0, len(y) - frame_len, hop):
            frame = y[start : start + frame_len]
            t_start = start / sr
            t_end   = (start + frame_len) / sr

            # 1. Pitch variance — melodic speech has higher variance than regular speech
            f0, voiced_flag, _ = librosa.pyin(
                frame, fmin=60, fmax=500, sr=sr, frame_length=1024
            )
            voiced_f0 = f0[voiced_flag & ~np.isnan(f0)]
            pitch_var = float(np.std(voiced_f0)) if len(voiced_f0) > 3 else 0.0

            # 2. Harmonicity — ratio of harmonic energy to total energy
            harmonic, _ = librosa.effects.hpss(frame)
            h_ratio = float(np.mean(harmonic ** 2) / (np.mean(frame ** 2) + 1e-9))

            # 3. Spectral rolloff — chanting tends to have more mid-frequency energy
            rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=frame, sr=sr)))

            # Score: combination of pitch variance and harmonicity
            score = (pitch_var / 80.0) * 0.6 + h_ratio * 0.4
            is_melodic = score > 0.35 and pitch_var > 15

            if is_melodic:
                regions.append({
                    "start": round(t_start, 1),
                    "end":   round(t_end, 1),
                    "score": round(score, 3),
                    "pitch_var": round(pitch_var, 1),
                })

        # Merge overlapping regions
        merged = _merge_regions(regions)
        print(f"[harmony] found {len(merged)} melodic/chanting region(s):")
        for r in merged:
            print(f"  [{r['start']}s → {r['end']}s] score={r['score']}")

        state["harmonic_regions"] = merged

    except Exception as e:
        print(f"[harmony] error: {e}")
        state["harmonic_regions"] = []

    return state


def _merge_regions(regions, gap=2.0):
    """Merge regions that are less than `gap` seconds apart."""
    if not regions:
        return []
    merged = [regions[0].copy()]
    for r in regions[1:]:
        if r["start"] - merged[-1]["end"] <= gap:
            merged[-1]["end"]   = r["end"]
            merged[-1]["score"] = max(merged[-1]["score"], r["score"])
        else:
            merged.append(r.copy())
    return merged
