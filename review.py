"""Sistem review & approve video (storyboard).

Setiap batch ialah satu folder dalam batches/ yang ada batch.json (manifest
video) dan fail video. Maklum balas (adjustment / approve) disimpan dalam
reviews.json dalam folder batch yang sama, supaya Claude boleh baca dan buat
perubahan.

Guna:
    python3 review.py                   # buka http://127.0.0.1:8001
    python3 review.py pending [batch]   # cetak adjustment yang belum dibuat
"""

import json
import os
import sys
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

BATCHES_DIR = Path(os.environ.get("REVIEW_BATCHES_DIR", Path(__file__).parent / "batches"))
MAX_NOTE = 5000

app = Flask(__name__)
_lock = threading.Lock()


# ---------- fail batch ----------

def batch_dir(slug: str) -> Path:
    path = (BATCHES_DIR / slug).resolve()
    if path.parent != BATCHES_DIR.resolve() or not (path / "batch.json").is_file():
        abort(404)
    return path


def read_json(path: Path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def write_json(path: Path, data) -> None:
    # Tulis ke fail sementara dulu supaya reviews.json tak rosak kalau terputus
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def list_batches() -> list[str]:
    if not BATCHES_DIR.is_dir():
        return []
    return sorted(p.parent.name for p in BATCHES_DIR.glob("*/batch.json"))


def video_status(video: dict, entries: list[dict]) -> str:
    """Status video berdasarkan maklum balas terakhir untuk versi semasa.

    belum   - belum ada maklum balas untuk versi ini
    adjust  - ada adjustment yang Claude belum buat
    approved
    """
    version = video.get("version", 1)
    current = [e for e in entries if e.get("version", 1) == version]
    if not current:
        return "belum"
    return "approved" if current[-1]["type"] == "approve" else "adjust"


def load_batch(slug: str) -> tuple[dict, dict]:
    path = batch_dir(slug)
    batch = read_json(path / "batch.json", {})
    reviews = read_json(path / "reviews.json", {})
    for v in batch.get("videos", []):
        entries = reviews.get(v["id"], [])
        v["status"] = video_status(v, entries)
        v["feedback"] = entries
    return batch, reviews


def summary(batch: dict) -> dict:
    counts = {"total": 0, "belum": 0, "adjust": 0, "approved": 0}
    for v in batch.get("videos", []):
        counts["total"] += 1
        counts[v["status"]] += 1
    return counts


# ---------- laman ----------

@app.get("/")
def index():
    batches = []
    for slug in list_batches():
        batch, _ = load_batch(slug)
        batches.append({"slug": slug, "title": batch.get("title", slug), "counts": summary(batch)})
    return render_template("review_index.html", batches=batches, batches_dir=BATCHES_DIR)


@app.get("/b/<slug>")
def batch_page(slug):
    batch, _ = load_batch(slug)
    return render_template("review.html", slug=slug, batch=batch)


@app.get("/media/<slug>/<path:filename>")
def media(slug, filename):
    # send_from_directory sokong Range request, jadi video boleh di-seek
    return send_from_directory(batch_dir(slug), filename, conditional=True)


# ---------- API ----------

@app.get("/api/batch/<slug>")
def api_batch(slug):
    batch, _ = load_batch(slug)
    return jsonify(batch=batch, counts=summary(batch))


@app.post("/api/batch/<slug>/video/<video_id>/feedback")
def api_feedback(slug, video_id):
    data = request.get_json(silent=True) or {}
    kind = data.get("type")
    note = (data.get("note") or "").strip()

    if kind not in ("adjust", "approve"):
        return jsonify(error="Jenis maklum balas tidak sah."), 400
    if kind == "adjust" and not note:
        return jsonify(error="Tulis adjustment dulu sebelum hantar."), 400
    if len(note) > MAX_NOTE:
        return jsonify(error=f"Maklum balas terlalu panjang (maksimum {MAX_NOTE} aksara)."), 400

    path = batch_dir(slug)
    with _lock:
        batch = read_json(path / "batch.json", {})
        video = next((v for v in batch.get("videos", []) if v["id"] == video_id), None)
        if video is None:
            return jsonify(error="Video tidak dijumpai."), 404

        reviews = read_json(path / "reviews.json", {})
        entry = {
            "type": kind,
            "note": note,
            "version": video.get("version", 1),
            "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        reviews.setdefault(video_id, []).append(entry)
        write_json(path / "reviews.json", reviews)

    batch, _ = load_batch(slug)
    return jsonify(batch=batch, counts=summary(batch))


@app.get("/api/batch/<slug>/pending.md")
def api_pending(slug):
    batch, _ = load_batch(slug)
    return pending_markdown(slug, batch), 200, {"Content-Type": "text/markdown; charset=utf-8"}


# ---------- eksport untuk Claude ----------

def pending_markdown(slug: str, batch: dict) -> str:
    """Senarai adjustment yang belum dibuat, dalam format yang Claude faham."""
    pending = [v for v in batch.get("videos", []) if v["status"] == "adjust"]
    lines = [f"# Adjustment untuk {batch.get('title', slug)}", ""]
    if not pending:
        lines.append("Tiada adjustment tertunggak.")
        return "\n".join(lines) + "\n"

    lines += [
        f"Batch: `batches/{slug}` · {len(pending)} video perlu diubah.",
        "Selepas ubah setiap video: naikkan `version` dalam batch.json supaya "
        "ia muncul semula untuk review.",
        "",
    ]
    for v in pending:
        version = v.get("version", 1)
        notes = [e for e in v["feedback"] if e.get("version", 1) == version and e["type"] == "adjust"]
        lines.append(f"## {v.get('code', '')} {v['id']} — {v.get('title', '')} (v{version})")
        lines.append(f"Fail: `{v.get('file', '')}`")
        for e in notes:
            lines.append("- " + e["note"].replace("\n", "\n  "))
        lines.append("")
    return "\n".join(lines)


def cli_pending(args: list[str]) -> int:
    slugs = args or list_batches()
    if not slugs:
        print(f"Tiada batch dalam {BATCHES_DIR}", file=sys.stderr)
        return 1
    with app.test_request_context():
        for slug in slugs:
            batch, _ = load_batch(slug)
            print(pending_markdown(slug, batch))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "pending":
        sys.exit(cli_pending(sys.argv[2:]))
    app.run(debug=True, port=int(os.environ.get("PORT", 8001)))
