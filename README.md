# Sistem Rawat Jalan Puskesmas

Aplikasi web manajemen rawat jalan Puskesmas berbasis Python (Flask) + SQLite.

---

## 🚀 Cara Menjalankan

### 1. Pastikan Python sudah terinstall (versi 3.8+)
```
python --version
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Jalankan aplikasi
```bash
python app.py
```

### 4. Buka di browser
```
http://localhost:5000
```

---

## 👤 Akun Default

| Role         | Username   | Password    |
|--------------|------------|-------------|
| Super Admin  | superadmin | admin123    |
| Admin Loket  | loket1     | loket123    |
| Admin Cek Vital | cekvi1  | cekvi123    |
| Dokter / Poli | dokter1   | dokter123   |

> ⚠️ Ganti password default setelah login pertama kali!

---

## 🗂️ Fitur per Role

### Super Admin
- Login & Logout
- Tambah / Edit / Hapus Admin (Loket, Cek Vital, Poli)
- Lihat semua data pasien
- Akses semua fitur

### Admin Loket (Admin 1)
- Login & Logout
- Input data pasien baru
- Cari data pasien
- Daftarkan rawat jalan (generate nomor antrian)

### Admin Cek Vital (Admin 2)
- Login & Logout
- Lihat daftar pasien yang menunggu
- Input data tanda vital (tekanan darah, nadi, suhu, SpO₂, BB, TB)
- Simpan RM Awal

### Dokter / Poli (Admin 3)
- Login & Logout
- Lihat RM Awal (termasuk vital signs)
- Input pemeriksaan dokter (anamnesis, diagnosis, resep, dll)
- Simpan & selesaikan kunjungan
- Lihat arsip rekam medis

---

## 🗄️ Database

Database SQLite otomatis dibuat di `instance/puskesmas.db` saat pertama kali dijalankan.

### Tabel:
- `admin` – data pengguna sistem
- `pasien` – data master pasien
- `kunjungan` – data pendaftaran rawat jalan
- `cek_vital` – data tanda vital per kunjungan
- `rekam_medis` – rekam medis lengkap per kunjungan

---

## 📁 Struktur Folder

```
puskesmas/
├── app.py                  # Aplikasi utama Flask
├── requirements.txt        # Dependencies Python
├── README.md               # Dokumentasi ini
├── instance/
│   └── puskesmas.db        # Database SQLite (auto-generated)
├── static/
│   ├── css/style.css       # Stylesheet utama
│   └── js/main.js          # JavaScript utama
└── templates/
    ├── base.html                  # Layout utama
    ├── login.html                 # Halaman login
    ├── dashboard_super_admin.html
    ├── dashboard_loket.html
    ├── dashboard_cek_vital.html
    ├── dashboard_poli.html
    ├── admin_list.html
    ├── admin_form.html
    ├── pasien_list.html
    ├── pasien_form.html
    ├── pasien_detail.html
    ├── rawat_jalan_daftar.html
    ├── cek_vital_form.html
    ├── rekam_medis_form.html
    └── arsip_rm.html
```

---

## 🔄 Alur Sistem

```
Pasien Datang
     ↓
[LOKET] Daftar Pasien + Input Rawat Jalan → No. Antrian
     ↓
[CEK VITAL] Ukur Tanda Vital → Simpan RM Awal
     ↓
[POLI/DOKTER] Pemeriksaan → Input Rekam Medis → Selesai
```

---

## ⚙️ Konfigurasi Tambahan (Opsional)

Edit `app.py` untuk mengubah:
- `app.secret_key` → ganti dengan key acak yang kuat di produksi
- `SQLALCHEMY_DATABASE_URI` → bisa diganti ke PostgreSQL/MySQL
- Port default: 5000
