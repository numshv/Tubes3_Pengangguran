<div align="center">
<h1>CV ATS Search System</h1>
<h2>(Tugas Besar 3 IF2211 Strategi Algoritma)</h2>
</div>

## About
Sistem ini merupakan implementasi *Applicant Tracking System (ATS)* berbasis pencocokan pola teks untuk menyaring dan menampilkan informasi kandidat dari CV digital. Sistem mendukung pencarian kata kunci dengan algoritma pencocokan string KMP, BM, dan Aho-corasic, serta pencarian fuzzy jika tidak ditemukan kecocokan persis. Aplikasi ini juga menggunakan regex untuk ekstraksi informasi.

---

## Algoritma yang Diimplementasikan

## Knuth-Morris-Pratt (KMP)
Algoritma KMP digunakan untuk mencari kemunculan sebuah pattern (pola) di dalam teks dengan efisiensi tinggi. Keunggulan KMP terletak pada kemampuannya untuk tidak membandingkan ulang karakter pada teks yang sudah pernah dicocokkan. Hal ini dicapai dengan melakukan pra-pemrosesan pada pattern untuk membangun sebuah struktur data yang disebut Fungsi Pembatas, yakni Longest Proper Prefix Suffix - LPS.

### Fungsi Pembatas (LPS Array)
Fungsi pembatas adalah sebuah array yang untuk setiap sub-pola dari pattern yang menyimpan panjang dari awalan (prefix) terpanjang tapi juga merupakan akhiran (suffix).

### Mekanisme Pergeseran
Ketika terjadi mismatch antara karakter di teks dan di pattern, KMP tidak menggeser pattern satu langkah ke kanan secara naif. Sebaliknya, digunakan nilai dari Fungsi Pembatas untuk melakukan pergeseran yang optimal.

Jika mismatch terjadi pada karakter ke-j dari pattern, KMP akan melihat nilai pada LPS[j-1]. Nilai ini menunjukkan panjang dari awalan pada pattern yang kita tahu pasti cocok dengan akhiran pada teks sebelum titik mismatch.

Algoritma akan menggeser pattern ke kanan sehingga awalan tersebut sejajar dengan akhiran yang sudah cocok, dan melanjutkan perbandingan dari sana. Hasilnya, waktu pencarian pada kasus terburuk pun tetap optimal, yaitu O(n + m), dengan n adalah panjang teks dan m adalah panjang pattern.

### Boyer-Moore (BM)
Boyer-Moore merupakan algoritma pencocokan teks yang sering kali menjadi yang tercepat dalam praktik. Kecepatan superiornya berasal dari dua ide brilian: pencocokan dari kanan ke kiri dan kemampuan untuk melompati banyak karakter sekaligus saat terjadi mismatch.

Kemampuan melompat ini dimungkinkan oleh penggunaan fungsi heuristik, terutama Heuristik Bad Character.

### Fungsi Heuristik Last Occurence
Fungsi ini dipanggil saat terjadi mismatch. Fungsi ini bertujuan untuk menentukan pergeseran aman sejauh mungkin ke kanan berdasarkan posisi kemunculan terakhir dari karakter yang tidak cocok di dalam pattern.

### Mekanisme Pergeseran
Saat mismatch terjadi antara karakter teks T[i] dan karakter pattern P[j]:
Algoritma melihat karakter bad character di teks, yaitu T[i].
kemudian periksa di mana T[i] terakhir kali muncul di dalam pattern (di sebelah kiri dari posisi j).

Terdapat Dua Kemungkinan Pergeseran:

Kasus 1: Bad Character tidak ada di pattern. Algoritma tahu bahwa tidak ada kemungkinan kecocokan sampai pattern digeser sepenuhnya melewati posisi T[i].

Kasus 2: Bad Character ada di pattern. Algoritma menggeser pattern ke kanan sehingga kemunculan terakhir dari karakter tersebut di pattern sejajar dengan T[i] di teks. 
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

