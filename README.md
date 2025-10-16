# 🚀 MPP Digital Tracking API

[![Status](https://img.shields.io/badge/status-ready-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License](https://img.shields.io/badge/license-private-orange)]()

**Deskripsi:**  
API sederhana berbasis **Flask** untuk melakukan _scraping_ dan tracking status permohonan pada sistem **MPP Digital**. Project ini dapat melakukan login otomatis (mengambil CSRF token), mencari pemohon berdasarkan nama, dan mengambil detail (termasuk link PDF izin atau alasan tolak).

---

## 🔎 Fitur

- Autentikasi via header `Authorization` (token statis)
- Endpoint pencarian pemohon (`/api/tracking/search`)
- Endpoint detail pemohon (`/api/tracking/detail`)
- Endpoint health check (`/api/tracking/health`)
- Ambil link PDF jika tahapan `SK DITERBITKAN`
- Ambil alasan tolak jika tahapan `DITOLAK`

---

## 📁 Isi Repository

- `app.py` — source utama Flask app
- `requirements.txt` — daftar dependency
- `README.md` — file ini

---

## 🧾 Requirement

- Python **3.10+**
- Sistem operasi: Linux / macOS / Windows
- Koneksi internet untuk mengakses `base_url` MPP Digital

File `requirements.txt` minimal:

```
flask
requests
beautifulsoup4
urllib3
```

---

## ⚙️ Cara Instalasi & Menjalankan (cepat)

1. Clone repo / salin folder proyek:

```bash
git clone https://github.com/IchsanCh/trackingmpp.git
cd trackingmpp
```

2. Buat virtual environment (disarankan):

```bash
python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows PowerShell
venv\Scripts\Activate.ps1
```

3. Install dependency:

```bash
pip install -r requirements.txt
```

4. Jalankan aplikasi:

```bash
python app.py
```

Aplikasi akan berjalan di:

```
http://0.0.0.0:23459
```

(Port default: `23459` — dapat diubah di bagian akhir `app.py`)

---

## 🔐 Konfigurasi Authorization

Default token disimpan di `app.py`:

```python
API_TOKEN = "tokentrackingmpp20251110"
```

Semua endpoint penting mengharuskan header:

```
Authorization: tokentrackingmpp20251110
```

Ganti `API_TOKEN` jika ingin menggunakan token lain.

---

## 🛠️ Environment / Konfigurasi Tambahan (opsional)

- Ubah `REQUEST_TIMEOUT` di `app.py` bila butuh timeout berbeda.
- Jika ingin non-verbose, hapus/ubah `print` debug di fungsi `search_pemohon` dan `extract_pdf_from_detail`.
- Jika ingin mematikan verifikasi SSL (saat development), `urllib3.disable_warnings` sudah dipakai; **jangan** gunakan ini di production.

---

## 📡 Endpoint Detail

### `GET /api/tracking/health`

**Deskripsi:** Health check sederhana.

**Response (200)**

```json
{
  "success": true,
  "message": "MPP Digital Tracking API is running",
  "version": "1.0.0"
}
```

---

### `POST /api/tracking/search`

**Deskripsi:** Mencari pemohon berdasarkan `nama_pemohon`.

**Headers**

```
Authorization: tokentrackingmpp20251110
Content-Type: application/json
```

**Body (JSON)**

```json
{
  "base_url": "https://admin.mppdigital.go.id",
  "username": "username_mpp",
  "password": "password_mpp",
  "lokasi": "1",
  "nama_pemohon": "Budi"
}
```

**Respons sukses (200) — contoh**

```json
{
  "success": true,
  "message": "Ditemukan 2 hasil untuk \"Budi\"",
  "data": [
    {
      "no_permohonan": "12345",
      "nama_izin": "Izin Usaha",
      "nama": "Budi Santoso",
      "nomor_hp": "08123456789",
      "tgl_pengajuan": "2025-10-15",
      "tahapan": "SK DITERBITKAN",
      "detail_link": "https://admin.mppdigital.go.id/sim/permohonan/detail/123",
      "link_izin": "https://admin.mppdigital.go.id/files/izin/123.pdf",
      "alasan_tolak": null
    }
  ],
  "total": 2
}
```

**Error umum**

- `401 Unauthorized` — token salah atau login gagal ke `base_url`
- `400 Bad Request` — field yang dibutuhkan tidak lengkap

---

### `POST /api/tracking/detail`

**Deskripsi:** Ambil data detail (termasuk link PDF) dari `detail_link` hasil search.

**Headers**

```
Authorization: tokentrackingmpp20251110
Content-Type: application/json
```

**Body (JSON)**

```json
{
  "base_url": "https://admin.mppdigital.go.id",
  "username": "username_mpp",
  "password": "password_mpp",
  "lokasi": "1",
  "detail_link": "https://admin.mppdigital.go.id/sim/permohonan/detail/123"
}
```

**Respons sukses (200) — contoh**

```json
{
  "success": true,
  "message": "Detail pemohon berhasil diambil",
  "data": {
    "pdf_link": "https://admin.mppdigital.go.id/files/izin/123.pdf"
  }
}
```

---

## ⚡ Contoh Pemanggilan (cURL)

**Search**

```bash
curl -X POST http://localhost:23459/api/tracking/search \
  -H "Authorization: tokentrackingmpp20251110" \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "https://admin.mppdigital.go.id",
    "username": "user",
    "password": "pass",
    "lokasi": "1",
    "nama_pemohon": "Budi"
  }'
```

**Detail**

```bash
curl -X POST http://localhost:23459/api/tracking/detail \
  -H "Authorization: tokentrackingmpp20251110" \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "https://admin.mppdigital.go.id",
    "username": "user",
    "password": "pass",
    "lokasi": "1",
    "detail_link": "https://admin.mppdigital.go.id/sim/permohonan/detail/123"
  }'
```

---

## 🐞 Troubleshooting (Masalah yang sering muncul)

- **CSRF token tidak ditemukan**: Pastikan halaman login `base_url + /sim` bisa diakses dan struktur HTML tidak berubah drastis. Fungsi `get_csrf_token` mengandalkan pencocokan pola tertentu.
- **PDF tidak ditemukan**: Server detail mungkin menyimpan PDF lewat `<embed>` atau path relatif; fungsi mencoba beberapa pola tapi tidak sempurna untuk semua variasi.
- **Login gagal padahal kredensial benar**: Cek parameter `lokasi` (db_name) dan struktur response setelah post login. Beberapa instalasi MPP mungkin mengarahkan atau memberi response berbeda.

---



## 🧾 Lisensi & Catatan

Project ini bersifat **private/internal**. Gunakan untuk integrasi internal dan jangan dipublikasikan tanpa izin.

---
