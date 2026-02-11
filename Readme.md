# 🏪 Bot Utang Jo Shop

Bot Telegram untuk mencatat transaksi penjualan dan tracking utang pelanggan dengan integrasi Google Sheets.

## ✨ Fitur

- 📝 Pencatatan transaksi otomatis
- 🎓 Kategorisasi berdasarkan tingkat (1-4)
- 🛒 Pilihan barang: Roti, Singkong, Basreng
- 💰 Tracking utang per pelanggan (auto-akumulasi)
- ✅ Sistem pelunasan
- 📊 Cek total utang
- 📈 Integrasi Google Sheets real-time

## 📦 Barang & Harga

| Barang | Harga |
|--------|-------|
| 🍞 Roti | Rp 3.000 |
| 🥔 Singkong | Rp 5.000 |
| 🌶️ Basreng | Rp 7.500 |

## 🚀 Setup

### 1. Clone Repository

```bash
git clone https://github.com/dhimazyusuf19/botutangjoshop.git
cd botutangjoshop
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Telegram Bot

1. Buka Telegram dan cari **@BotFather**
2. Ketik `/newbot`
3. Ikuti instruksi untuk membuat bot baru
4. Simpan **token** yang diberikan

### 4. Setup Google Sheets API

#### A. Buat Project di Google Cloud Console

1. Buka [Google Cloud Console](https://console.cloud.google.com/)
2. Buat project baru atau pilih project yang ada
3. Enable **Google Sheets API**:
   - Pergi ke "APIs & Services" > "Library"
   - Cari "Google Sheets API"
   - Klik "Enable"

#### B. Buat Service Account

1. Pergi ke "APIs & Services" > "Credentials"
2. Klik "Create Credentials" > "Service Account"
3. Isi nama service account, klik "Create"
4. Klik "Done" (skip optional steps)
5. Klik service account yang baru dibuat
6. Pergi ke tab "Keys"
7. Klik "Add Key" > "Create new key"
8. Pilih format **JSON**
9. Download file JSON dan rename menjadi `credentials.json`
10. Pindahkan file ke folder project

#### C. Buat Google Spreadsheet

1. Buka [Google Sheets](https://sheets.google.com/)
2. Buat spreadsheet baru
3. Copy **Spreadsheet ID** dari URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit
   ```
4. **PENTING**: Share spreadsheet dengan email service account
   - Buka file `credentials.json`
   - Copy email yang ada di field `client_email`
   - Share spreadsheet ke email tersebut dengan akses **Editor**

### 5. Konfigurasi Environment Variables

1. Copy file `.env.example` menjadi `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit file `.env` dan isi dengan data Anda:
   ```bash
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   GOOGLE_SHEETS_CREDENTIALS=credentials.json
   SPREADSHEET_ID=1AbC2dEf3GhI4jKl5MnO6pQr7StU8vWx9YzA
   ```

### 6. Jalankan Bot

```bash
python bot.py
```

Jika berhasil, akan muncul log:
```
INFO - Google Sheets initialized successfully
INFO - Bot is starting...
```

## 📱 Cara Menggunakan Bot

### Membuat Transaksi Baru

1. Ketik `/start`
2. Pilih tingkat pembeli (1-4)
3. Masukkan nama pembeli
4. Pilih barang yang dibeli
5. Masukkan jumlah barang
6. Bot akan mencatat transaksi dan menampilkan konfirmasi

**Contoh Flow:**
```
User: /start
Bot: Pilih tingkat pembeli: [1] [2] [3] [4]
User: [Klik: 2]
Bot: Masukkan nama pembeli:
User: Yusuf
Bot: Pilih barang: [Roti] [Singkong] [Basreng]
User: [Klik: Roti]
Bot: Masukkan jumlah:
User: 5
Bot: ✅ Transaksi Berhasil!
     Nama: Yusuf
     Tingkat: 2
     Barang: Roti
     Jumlah: 5
     Total: Rp 15.000
     Total Utang Yusuf: Rp 15.000
```

### Melunasi Utang

1. Ketik `/lunas`
2. Pilih nama dari daftar yang muncul
3. Bot akan update status menjadi "Lunas"

### Cek Total Utang

```
/cek Yusuf
```

Bot akan menampilkan total utang **Yusuf**.

### Membatalkan Transaksi

Jika sedang dalam proses input, ketik `/cancel`

## 📊 Struktur Google Sheets

Bot akan otomatis membuat sheet dengan struktur:

### Sheet: Transaksi

| Tanggal | Tingkat | Nama | Barang | Jumlah | Harga Satuan | Total | Status |
|---------|---------|------|---------|--------|--------------|-------|--------|
| 2026-02-11 10:30:00 | 2 | Yusuf | Roti | 5 | 3000 | 15000 | Belum Lunas |
| 2026-02-11 11:15:00 | 3 | Andi | Basreng | 2 | 7500 | 15000 | Lunas |

## 🛠️ Troubleshooting

### Bot tidak merespon

- Pastikan token Telegram sudah benar
- Cek koneksi internet
- Pastikan bot sudah di-start dengan `/start` di @BotFather

### Error "Google Sheets credentials file not found"

- Pastikan file `credentials.json` ada di folder project
- Pastikan path di `.env` sudah benar

### Error "Permission denied" di Google Sheets

- Pastikan spreadsheet sudah di-share ke email service account
- Berikan akses **Editor**, bukan hanya **Viewer**

### Data tidak tersimpan

- Cek log untuk error message
- Pastikan Spreadsheet ID sudah benar
- Pastikan internet stabil

## 📝 Commands

| Command | Deskripsi |
|---------|-----------|
| `/start` | Mulai transaksi baru |
| `/lunas` | Tandai pelunasan |
| `/cek [nama]` | Cek total utang |
| `/cancel` | Batalkan transaksi |

## 🤝 Kontribusi

Silakan buat issue atau pull request jika ingin berkontribusi!

## 📄 License

MIT License

---

**Dibuat dengan ❤️ untuk Jo Shop**
