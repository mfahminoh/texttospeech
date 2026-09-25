# Gemini Text-to-Speech

Contoh ringkas untuk menukar teks kepada suara menggunakan Gemini API.

## Langkah

1. Dapatkan API key di [Google AI Studio](https://aistudio.google.com/apikey).
2. Pasang pakej:
   ```bash
   pip install -r requirements.txt
   ```
3. Tetapkan API key:
   ```bash
   export GEMINI_API_KEY="kunci-api-anda"
   ```
4. Jalankan dari command line:
   ```bash
   python tts.py "Selamat pagi, apa khabar semua?" -o salam.wav -v Kore
   ```

## Aplikasi web

```bash
python app.py
```

Buka http://127.0.0.1:5000 — taip teks, pilih suara, tekan **Jana Suara**,
kemudian dengar atau muat turun fail WAV.

## Tetapan

Tukar model dengan `-m` atau pemboleh ubah `GEMINI_TTS_MODEL`
(lalai: `gemini-2.5-flash-preview-tts`).

Arahan gaya boleh diletak terus dalam teks, cth:
`"Sebut dengan nada ceria: Selamat hari jadi!"`
