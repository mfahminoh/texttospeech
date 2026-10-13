# Gemini Text-to-Speech

Contoh ringkas untuk menukar teks kepada suara menggunakan Gemini API.

## Langkah

1. Dapatkan API key di [Google AI Studio](https://aistudio.google.com/apikey).
2. Pasang pakej:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Tetapkan API key:
   ```bash
   export GEMINI_API_KEY="kunci-api-anda"
   ```
4. Jalankan dari command line:
   ```bash
   python3 tts.py "Selamat pagi, apa khabar semua?" -o salam.wav -v Kore
   ```

## Aplikasi web

```bash
python3 app.py
```

Buka http://127.0.0.1:8000 — taip teks, pilih suara, tekan **Jana Suara**,
kemudian dengar atau muat turun fail WAV.

## Tetapan

Tukar model dengan `-m` atau pemboleh ubah `GEMINI_TTS_MODEL`
(lalai: `gemini-2.5-flash-preview-tts`).

Arahan gaya boleh diletak terus dalam teks, cth:
`"Sebut dengan nada ceria: Selamat hari jadi!"`

## Sistem review video

Aplikasi untuk review dan approve video yang dijana (gaya storyboard):
senarai video, preview, timeline layer, senarai potongan, frame demi frame
dan transkrip. Setiap video boleh diberi **adjustment** atau **Approve**.
Maklum balas disimpan supaya Claude boleh baca dan buat perubahan.

Perlu `ffmpeg` (`brew install ffmpeg` di macOS).

```bash
python3 review_scan.py demo        # cipta batch contoh (pilihan)
python3 review.py                  # buka http://127.0.0.1:8001
```

### Tambah batch baru

1. Letak video dalam `batches/<nama-batch>/videos/` (cth. `batches/batch-3/videos/KIRA-03.mp4`).
2. Imbas batch:
   ```bash
   python3 review_scan.py scan batches/batch-3 --preview --transcribe
   ```
   - `--preview` buat versi 360x640 supaya laju dimainkan
   - `--transcribe` jana transkrip bertanda masa dengan Gemini (perlu `GEMINI_API_KEY`)
3. (Pilihan) Isi maklumat tambahan dalam `batches/batch-3/batch.json` —
   biasanya Claude yang isi semasa menjana video:

```json
{
  "title": "Storyboard Batch 3",
  "eyebrow": "@akaun · Batch 3 · 30 reels · Storyboard untuk review",
  "videos": [{
    "id": "C0811", "code": "KIRA-03", "category": "Fail kamera",
    "title": "Jual RM20 kat GrabFood, untung berapa?",
    "file": "videos/KIRA-03.mp4", "version": 1,
    "duration": 62, "source_duration": 97.4,
    "cuts": [{"start": 2.1, "end": 3.4, "note": "Buang 'emm'"}],
    "layers": [{"track": "Hook", "start": 0, "end": 2.5, "label": "Teks hook"}],
    "transcript": [{"start": 0, "end": 2.5, "text": "Jual RM20 kat GrabFood…"}]
  }]
}
```

### Aliran kerja dengan Claude

1. Review setiap video: tulis adjustment (butang **+ Masa semasa** masukkan
   masa video, cth. `0:20 — buang card RM30`) dan tekan **Hantar adjustment**,
   atau tekan **Approve**.
2. Tekan **Salin adjustment untuk Claude** dan tampal dalam sesi Claude, atau
   commit `reviews.json` dan minta Claude "buat adjustment batch-3".
   Senarai yang sama boleh dicetak dengan `python3 review.py pending batch-3`.
3. Claude ubah video dan naikkan `version` dalam `batch.json`. Video itu
   kembali ke status **belum review** untuk versi baru; maklum balas lama
   kekal dalam sejarah.

Status setiap video dikira daripada maklum balas terakhir untuk versi semasa:
*belum review*, *ada adjustment* atau *approved*.
