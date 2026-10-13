"""
Transcribe a clip with AI4Bharat IndicConformer (NeMo-based, runs locally) for the
ASR comparison. Needs its own environment (torch, transformers, onnxruntime) and a
Hugging Face token for the gated model:

    HF_TOKEN=... python scripts/indicconformer_transcribe.py CLIP.mp3 --out DIR [--lang te]

Writes DIR/asr_outputs/IndicConformer_rnnt.txt and IndicConformer_ctc.txt, which
compare_asr.py includes automatically.
"""
import argparse, os, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIECE_SECONDS = 20
MODEL_ID = "ai4bharat/indic-conformer-600m-multilingual"


def pieces_16k(clip: str, workdir: str) -> list[str]:
    pattern = os.path.join(workdir, "piece_%04d.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", clip, "-ar", "16000", "-ac", "1",
                    "-f", "segment", "-segment_time", str(PIECE_SECONDS), pattern], check=True)
    return sorted(os.path.join(workdir, f) for f in os.listdir(workdir) if f.startswith("piece_"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lang", default="te")
    args = ap.parse_args()

    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
    if not os.getenv("HF_TOKEN"):
        sys.exit("HF_TOKEN is not set (add it to verba-pravachana-ai/.env)")

    import soundfile as sf, torch
    from transformers import AutoModel

    t0 = time.time()
    model = AutoModel.from_pretrained(MODEL_ID, trust_remote_code=True, token=os.environ["HF_TOKEN"])
    print(f"[indicconformer] model loaded in {time.time() - t0:.0f}s")

    with tempfile.TemporaryDirectory() as tmp:
        files = pieces_16k(os.path.abspath(args.clip), tmp)
        audio_seconds = 0.0
        results = {"rnnt": [], "ctc": []}
        timings = {"rnnt": 0.0, "ctc": 0.0}
        for i, path in enumerate(files):
            data, sr = sf.read(path, dtype="float32")
            if len(data) < sr // 2:
                continue  # ffmpeg can leave a few-ms tail piece; the preprocessor can't pad it
            audio_seconds += len(data) / sr
            wav = torch.from_numpy(data).unsqueeze(0)
            for decoder in ("rnnt", "ctc"):
                t = time.time()
                with torch.inference_mode():
                    text = model(wav, args.lang, decoder)
                timings[decoder] += time.time() - t
                results[decoder].append(str(text).strip())
            print(f"  [piece {i + 1}/{len(files)}] {results['rnnt'][-1][:80]}")

    out_dir = os.path.join(args.out, "asr_outputs")
    os.makedirs(out_dir, exist_ok=True)
    for decoder, texts in results.items():
        with open(os.path.join(out_dir, f"IndicConformer_{decoder}.txt"), "w", encoding="utf-8") as f:
            f.write(" ".join(t for t in texts if t))
        print(f"[indicconformer] {decoder}: {timings[decoder]:.0f}s for {audio_seconds / 60:.1f} min of audio "
              f"({audio_seconds / max(timings[decoder], 1e-6):.1f}x real time)")


if __name__ == "__main__":
    main()
