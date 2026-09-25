"""Aplikasi web ringkas untuk Gemini Text-to-Speech.

Guna:
    export GEMINI_API_KEY="kunci-api-anda"
    python app.py
Kemudian buka http://127.0.0.1:5000
"""

import os

from flask import Flask, Response, jsonify, render_template, request

from tts import DEFAULT_MODEL, pcm_to_wav, text_to_speech

VOICES = [
    "Kore", "Puck", "Charon", "Fenrir", "Leda", "Aoede", "Zephyr", "Orus",
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
]
MAX_CHARS = 5000

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html", voices=VOICES, max_chars=MAX_CHARS)


@app.post("/api/tts")
def api_tts():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    voice = data.get("voice") or "Kore"
    style = (data.get("style") or "").strip()

    if not text:
        return jsonify(error="Sila masukkan teks."), 400
    if len(text) > MAX_CHARS:
        return jsonify(error=f"Teks terlalu panjang (maksimum {MAX_CHARS} aksara)."), 400
    if voice not in VOICES:
        return jsonify(error="Suara tidak sah."), 400
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        return jsonify(error="GEMINI_API_KEY belum ditetapkan pada server."), 500

    prompt = f"{style}: {text}" if style else text
    try:
        pcm = text_to_speech(prompt, voice=voice, model=DEFAULT_MODEL)
    except Exception as e:  # ralat daripada Gemini API (key salah, kuota, dsb.)
        app.logger.exception("Gemini TTS gagal")
        return jsonify(error=f"Gagal menjana audio: {e}"), 502

    return Response(pcm_to_wav(pcm), mimetype="audio/wav")


if __name__ == "__main__":
    app.run(debug=True)
