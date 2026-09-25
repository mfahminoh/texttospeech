"""Tukar teks kepada suara menggunakan Gemini Text-to-Speech.

Guna:
    export GEMINI_API_KEY="kunci-api-anda"
    python tts.py "Selamat pagi, apa khabar?" -o output.wav
"""

import argparse
import io
import os
import sys
import wave

from google import genai
from google.genai import types

DEFAULT_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")

# Gemini TTS pulangkan audio PCM mentah: 24 kHz, 16-bit, mono
SAMPLE_RATE = 24000
SAMPLE_WIDTH = 2
CHANNELS = 1


def text_to_speech(text: str, voice: str = "Kore", model: str = DEFAULT_MODEL) -> bytes:
    """Hantar teks ke Gemini dan pulangkan data audio PCM."""
    client = genai.Client()  # baca GEMINI_API_KEY daripada environment

    response = client.models.generate_content(
        model=model,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        ),
    )
    return response.candidates[0].content.parts[0].inline_data.data


def pcm_to_wav(pcm: bytes) -> bytes:
    """Bungkus data PCM mentah dengan header WAV."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)
    return buf.getvalue()


def save_wav(path: str, pcm: bytes) -> None:
    with open(path, "wb") as f:
        f.write(pcm_to_wav(pcm))


def main() -> int:
    parser = argparse.ArgumentParser(description="Gemini Text-to-Speech")
    parser.add_argument("text", help="Teks yang hendak dibacakan")
    parser.add_argument("-o", "--output", default="output.wav", help="Fail .wav output")
    parser.add_argument("-v", "--voice", default="Kore", help="Nama suara (cth. Kore, Puck, Charon, Leda)")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help="Model TTS Gemini")
    args = parser.parse_args()

    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        print("Ralat: tetapkan GEMINI_API_KEY dahulu.", file=sys.stderr)
        return 1

    pcm = text_to_speech(args.text, voice=args.voice, model=args.model)
    save_wav(args.output, pcm)
    print(f"Audio disimpan ke {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
