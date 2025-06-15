<div align="center">
<h1>CV ATS Search System</h1>
<h2>(Tugas Besar 3 IF2211 Strategi Algoritma)</h2>
</div>

## About
Sistem ini merupakan implementasi *Applicant Tracking System (ATS)* berbasis pencocokan pola teks untuk menyaring dan menampilkan informasi kandidat dari CV digital. Sistem mendukung pencarian kata kunci dengan algoritma pencocokan string KMP, BM, dan Aho-corasic, serta pencarian fuzzy jika tidak ditemukan kecocokan persis. Aplikasi ini juga menggunakan regex untuk ekstraksi informasi.

---

## Algoritma yang Diimplementasikan

### Knuth-Morris-Pratt (KMP)
Algoritma KMP digunakan untuk mencari kemunculan sebuah pattern di dalam teks dengan efisiensi tinggi. KMP menghindari pemeriksaan ulang karakter dengan menggunakan *prefix function* (border array), sehingga waktu pencarian optimal pada kasus terburuk adalah O(n + m).

### Boyer-Moore (BM)
Boyer-Moore merupakan algoritma pencocokan teks yang sangat efisien dalam praktik. Dengan menggunakan heuristik *bad character*, BM melakukan pencarian dari kanan ke kiri dan dapat melompati banyak karakter sekaligus saat mismatch terjadi, menghasilkan performa lebih cepat pada teks panjang.

---

## Requirement & Instalasi

Sebelum menjalankan program, pastikan kamu sudah menginstal Python dan library berikut:

```bash
pip install flet mysql-connector-python
pip install PyMuPDF
```

Library yang digunakan:
- `flet`: untuk antarmuka desktop
- `mysql-connector-python`: koneksi ke database MySQL
- `PyMuPDF` (`fitz`): untuk membaca file PDF


Lalu Download file .zip pada release terbaru atau clone repository ini secara keseluruhan

---

## Konfigurasi Awal

Ubah isi file `src/config.py` dan sesuaikan isi konfigurasi database dan secret key enkripsi sesuai dengan kebutuhan, berikut adalah contohnya:

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'pw123',
    'database': 'ats_pengangguran'
}

# Kunci rahasia untuk enkripsi dan dekripsi
SECRET_KEY = "RAHASIA"
```
---

## Cara Menjalankan Program

1. Masuk ke root folder repository:

2. Jalankan program:
```bash
python src/Main.py
```

---

## Author

| Nama                          | NIM       | Prodi                  |
|-------------------------------|-----------|-------------------------|
| Noumisyifa Nabila Nareswari   | 13523058  | Teknik Informatika - STEI ITB |
| Qodri Azkarayan               | 13523010  | Teknik Informatika - STEI ITB |
| Rendi Adinata                 | 10123083  | Matematika - FMIPA ITB |

