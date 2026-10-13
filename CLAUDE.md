# Nota untuk Claude

## Review video (`review.py`, `batches/`)

Pengguna review video dalam aplikasi `review.py`. Maklum balas disimpan dalam
`batches/<batch>/reviews.json`; manifest video dalam `batches/<batch>/batch.json`.

Bila diminta buat adjustment:

1. Jalankan `python3 review.py pending <batch>` (atau baca teks yang pengguna tampal)
   untuk senarai adjustment yang belum dibuat. Masa seperti `0:20` merujuk masa
   dalam video versi semasa.
2. Ubah atau jana semula video tersebut (simpan di laluan `file` yang sama).
3. Kemas kini `batch.json` untuk video itu: naikkan `version` dengan 1, dan
   kemas kini `duration`, `cuts`, `layers`, `transcript` jika berubah.
4. Jalankan `python3 review_scan.py scan batches/<batch> --preview` untuk jana
   semula frame dan preview.
5. Jangan ubah `reviews.json` — ia sejarah maklum balas pengguna.

Bila menjana batch baru, isi `batch.json` dengan `code`, `title`, `category`,
`layers`, `cuts` dan `transcript` supaya paparan review lengkap.
