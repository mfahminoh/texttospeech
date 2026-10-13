"""Sediakan batch video untuk sistem review.

Guna:
    # Letak video dalam batches/<nama-batch>/videos/ dahulu, kemudian:
    python3 review_scan.py scan batches/batch-3
    python3 review_scan.py scan batches/batch-3 --preview --transcribe

    # Batch contoh untuk cuba sistem (perlu ffmpeg):
    python3 review_scan.py demo

scan akan:
  - tambah setiap video baru ke batch.json (data sedia ada tidak diusik)
  - baca tempoh video (ffprobe)
  - ambil frame untuk paparan "frame demi frame" (ffmpeg)
  - --preview: buat versi kecil 360x640 supaya laju dimainkan
  - --transcribe: jana transkrip bertanda masa dengan Gemini (perlu GEMINI_API_KEY)
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from review import read_json, write_json

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm"}
TRANSCRIBE_MODEL = "gemini-2.5-flash"


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def probe_duration(path: Path) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", str(path)])
    return round(float(out.strip()), 1)


def is_stale(output: Path, source: Path) -> bool:
    return not output.exists() or output.stat().st_mtime < source.stat().st_mtime


def extract_frames(root: Path, video: dict, count: int) -> None:
    src = root / video["file"]
    out_dir = root / "frames" / video["id"]
    first = out_dir / "00.jpg"
    if not is_stale(first, src) and len(video.get("frames", [])) == count:
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.jpg"):
        old.unlink()

    duration = video["duration"]
    frames = []
    for i in range(count):
        # Ambil frame di tengah setiap bahagian supaya elak frame hitam di hujung
        t = round(duration * (i + 0.5) / count, 1)
        name = f"{i:02d}.jpg"
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(src),
             "-frames:v", "1", "-vf", "scale=180:-2", "-q:v", "4", str(out_dir / name)])
        frames.append({"t": t, "src": f"frames/{video['id']}/{name}"})
    video["frames"] = frames


def make_preview(root: Path, video: dict) -> None:
    src = root / video["file"]
    out = root / "previews" / f"{video['id']}.mp4"
    if is_stale(out, src):
        out.parent.mkdir(exist_ok=True)
        run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
             "-vf", "scale=360:640:force_original_aspect_ratio=decrease,pad=360:640:-1:-1",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
             "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)])
    video["preview"] = f"previews/{video['id']}.mp4"


def transcribe(root: Path, video: dict) -> None:
    from google import genai
    from google.genai import types

    client = genai.Client()
    uploaded = client.files.upload(file=str(root / video["file"]))
    # Fail video perlu diproses dulu sebelum boleh digunakan
    while uploaded.state and uploaded.state.name == "PROCESSING":
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)

    prompt = (
        "Transkripkan semua percakapan dalam video ini mengikut bahasa asal. "
        "Pulangkan JSON: senarai objek {\"start\": saat, \"end\": saat, \"text\": ayat}. "
        "Satu objek untuk setiap ayat pendek."
    )
    response = client.models.generate_content(
        model=TRANSCRIBE_MODEL,
        contents=[uploaded, prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    video["transcript"] = json.loads(response.text)
    client.files.delete(name=uploaded.name)


def scan(root: Path, frames: int, preview: bool, do_transcribe: bool, force: bool) -> None:
    manifest_path = root / "batch.json"
    batch = read_json(manifest_path, {"title": root.name.replace("-", " ").title(), "videos": []})
    videos = batch.setdefault("videos", [])
    by_file = {v.get("file"): v for v in videos}

    files = sorted(p for p in (root / "videos").glob("*") if p.suffix.lower() in VIDEO_EXTS)
    if not files:
        print(f"Tiada video dalam {root / 'videos'}", file=sys.stderr)

    for path in files:
        rel = path.relative_to(root).as_posix()
        video = by_file.get(rel)
        if video is None:
            video = {"id": path.stem, "code": path.stem, "title": path.stem, "file": rel, "version": 1}
            videos.append(video)
            print(f"+ {rel}")
        video["duration"] = probe_duration(path)
        if frames:
            extract_frames(root, video, frames)
        if preview:
            make_preview(root, video)
        if do_transcribe and (force or not video.get("transcript")):
            print(f"  transkrip {video['id']}…")
            transcribe(root, video)

    write_json(manifest_path, batch)
    print(f"{len(videos)} video dalam {manifest_path}")


# ---------- batch contoh ----------

DEMO = [
    {
        "id": "C0001", "code": "KIRA-01", "category": "Fail kamera",
        "title": "Jual RM20 kat GrabFood, untung berapa?", "color": "0x2d6a4f",
        "duration": 16, "source_duration": 21.4,
        "cuts": [
            {"start": 2.1, "end": 3.4, "note": "Buang 'emm' sebelum hook"},
            {"start": 9.0, "end": 11.8, "note": "Ulang ayat, ambil take kedua"},
            {"start": 18.2, "end": 19.2, "note": "Jeda panjang"},
        ],
        "layers": [
            {"track": "Hook", "start": 0, "end": 2.5, "label": "Teks hook besar"},
            {"track": "Scene", "start": 2.5, "end": 9, "label": "Bercakap ke kamera"},
            {"track": "Zoom", "start": 5, "end": 8, "label": "Punch-in 115%"},
            {"track": "Cards", "start": 9, "end": 13, "label": "Kad pecahan kos"},
            {"track": "Banner", "start": 13, "end": 16, "label": "CTA: komen KIRA"},
        ],
        "transcript": [
            {"start": 0, "end": 2.5, "text": "Jual RM20 kat GrabFood, sebenarnya untung berapa?"},
            {"start": 2.5, "end": 6, "text": "Ramai tak sedar GrabFood ambil komisen sampai 30 peratus."},
            {"start": 6, "end": 9, "text": "Tolak kos bahan, packaging, tinggal berapa?"},
            {"start": 9, "end": 13, "text": "Jom kira sama-sama."},
            {"start": 13, "end": 16, "text": "Komen KIRA kalau nak template kalkulator ni."},
        ],
    },
    {
        "id": "C0002", "code": "HOT-01", "category": "AI avatar",
        "title": "Tak tahu kos seunit, jangan buat promo", "color": "0x9d0208",
        "duration": 12,
        "layers": [
            {"track": "Hook", "start": 0, "end": 2, "label": "Hook merah"},
            {"track": "Scene", "start": 2, "end": 12, "label": "Avatar AI"},
            {"track": "Cards", "start": 6, "end": 10, "label": "Contoh kiraan"},
        ],
        "transcript": [
            {"start": 0, "end": 2, "text": "Tak tahu kos seunit? Jangan buat promo."},
            {"start": 2, "end": 7, "text": "Diskaun tanpa kira kos boleh buat anda rugi setiap jualan."},
            {"start": 7, "end": 12, "text": "Kira kos seunit dulu, baru tetapkan harga promo."},
        ],
    },
    {
        "id": "C0003", "code": "DIAG-01", "category": "Diagram",
        "title": "Hujung minggu penuh, Isnin sampai Khamis sunyi", "color": "0x1d3557",
        "duration": 14,
        "layers": [
            {"track": "Hook", "start": 0, "end": 3, "label": "Graf jualan"},
            {"track": "Scene", "start": 3, "end": 14, "label": "Animasi diagram"},
            {"track": "Banner", "start": 11, "end": 14, "label": "CTA"},
        ],
        "transcript": [
            {"start": 0, "end": 3, "text": "Hujung minggu penuh, tapi Isnin sampai Khamis sunyi?"},
            {"start": 3, "end": 9, "text": "Cuba buat menu set khas hari bekerja untuk pekerja pejabat."},
            {"start": 9, "end": 14, "text": "Simpan video ni dan cuba minggu depan."},
        ],
    },
]


def demo(root: Path) -> None:
    (root / "videos").mkdir(parents=True, exist_ok=True)
    videos = []
    for i, d in enumerate(DEMO):
        d = dict(d)
        color = d.pop("color")
        rel = f"videos/{d['code']}.mp4"
        run(["ffmpeg", "-v", "error", "-y",
             "-f", "lavfi", "-i", f"color=c={color}:s=1080x1920:d={d['duration']}:r=30",
             "-f", "lavfi", "-i", f"testsrc2=s=600x600:d={d['duration']}:r=30",
             "-f", "lavfi", "-i", f"sine=frequency={330 + i * 110}:duration={d['duration']}",
             "-filter_complex", "[0][1]overlay=(W-w)/2:(H-h)/2[v]",
             "-map", "[v]", "-map", "2", "-c:v", "libx264", "-preset", "veryfast",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(root / rel)])
        videos.append({**d, "file": rel, "version": 1})
    write_json(root / "batch.json", {
        "title": "Storyboard Demo",
        "eyebrow": "@akaun-anda · Batch demo · 3 reels · Storyboard untuk review",
        "videos": videos,
    })
    scan(root, frames=8, preview=True, do_transcribe=False, force=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sediakan batch video untuk review")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scan", help="Imbas folder videos/ dalam batch")
    p.add_argument("batch", type=Path, help="Folder batch, cth. batches/batch-3")
    p.add_argument("--frames", type=int, default=8, help="Bilangan frame setiap video (0 = tiada)")
    p.add_argument("--preview", action="store_true", help="Buat preview 360x640")
    p.add_argument("--transcribe", action="store_true", help="Jana transkrip dengan Gemini")
    p.add_argument("--force", action="store_true", help="Jana semula transkrip yang sudah ada")
    d = sub.add_parser("demo", help="Cipta batch contoh")
    d.add_argument("--dir", type=Path, default=Path(__file__).parent / "batches" / "demo")
    args = parser.parse_args()

    if args.cmd == "demo":
        demo(args.dir)
    else:
        scan(args.batch, args.frames, args.preview, args.transcribe, args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
