# Panduan Membagikan Dashboard NUCLEUS

Dokumen ini menjelaskan tiga cara membagikan dashboard **NUCLEUS** (`app.py`) kepada rekan satu tim:

| Metode | Cocok untuk | Perlu internet? | Tautan permanen? |
| --- | --- | --- | --- |
| **1. Jaringan Wi-Fi/LAN yang sama** | Demo cepat, rapat di kantor, tim satu ruangan | Tidak | Tidak (hanya aktif selama Mac Anda menyala) |
| **2. Streamlit Community Cloud + GitHub** | Akses dari mana saja, berbagi jangka panjang | Ya | Ya (contoh: `https://nucleus-dashboard.streamlit.app`) |
| **3. Streamlit Community Cloud + Bitbucket** | Sama seperti Metode 2, untuk tim yang memakai Bitbucket | Ya | Ya (contoh: `https://nucleus-dashboard.streamlit.app`) |

> Catatan: Metode 1 mengharuskan Mac Anda tetap menyala dan menjalankan aplikasi. Metode 2 dan 3 berjalan di server cloud sehingga tetap bisa diakses walau laptop Anda mati. Pilih Metode 2 jika tim Anda memakai GitHub, atau Metode 3 jika memakai Bitbucket.

---

## Metode 1 — Akses Lokal Lewat Jaringan Wi-Fi yang Sama

Rekan kerja bisa membuka dashboard langsung dari browser mereka, **tanpa deploy ke internet**, selama berada di **jaringan Wi-Fi/LAN yang sama** dengan Mac Anda.

### Langkah 1 — Jalankan aplikasi agar bisa diakses dari jaringan

Secara default Streamlit hanya bisa diakses dari komputer Anda sendiri (`localhost`). Agar perangkat lain di jaringan bisa mengaksesnya, jalankan dengan alamat `0.0.0.0`:

```bash
cd "/Users/ramadhanipuratama/workplace/kirocrew-workspace/NUCLEUS"
python3 -m streamlit run app.py --server.address 0.0.0.0
```

Jika Anda memakai virtual environment proyek (`.venv`) seperti yang sudah disiapkan, jalankan lewat venv agar semua dependensi tersedia:

```bash
cd "/Users/ramadhanipuratama/workplace/kirocrew-workspace/NUCLEUS"
source .venv/bin/activate
streamlit run app.py --server.address 0.0.0.0
```

Setelah aplikasi berjalan, biarkan terminal ini tetap terbuka. Menutup terminal atau menekan `Ctrl+C` akan menghentikan dashboard.

### Langkah 2 — Cari alamat IP lokal Mac Anda

Buka terminal baru lalu jalankan:

```bash
ipconfig getifaddr en0
```

Perintah ini menampilkan IP lokal Mac Anda, misalnya `192.168.1.10`.

- `en0` biasanya adalah Wi-Fi pada MacBook. Jika Anda tersambung lewat kabel LAN/adaptor dan `en0` tidak memberi hasil, coba `en1`:

  ```bash
  ipconfig getifaddr en1
  ```

### Langkah 3 — Bagikan URL ke rekan kerja

Minta rekan kerja membuka browser dan mengetik alamat berikut (ganti `<IP-Address>` dengan IP dari Langkah 2):

```
http://<IP-Address>:8501
```

Contoh nyata:

```
http://192.168.1.10:8501
```

> `8501` adalah port default Streamlit. Jika Anda menjalankan di port lain (misalnya `PORT=8600 ./run.sh`), sesuaikan angka port pada URL.

### Tips: Jika rekan kerja gagal terhubung (cek Firewall Mac)

Kalau URL tidak bisa dibuka, kemungkinan besar Firewall macOS memblokir koneksi masuk. Periksa hal berikut:

1. **Pastikan satu jaringan.** Mac Anda dan laptop rekan kerja harus terhubung ke Wi-Fi/LAN yang **sama persis** (bukan Wi-Fi tamu/guest yang terisolasi).
2. **Cek pengaturan Firewall:**
   - Buka **System Settings → Network → Firewall** (di macOS lama: **System Preferences → Security & Privacy → Firewall**).
   - Jika Firewall **aktif**, klik **Options…** lalu pastikan Python/Streamlit diizinkan menerima koneksi masuk ("Allow incoming connections"). Saat pertama kali menjalankan, macOS biasanya menampilkan dialog izin — pilih **Allow**.
   - Untuk uji cepat, Anda bisa mematikan Firewall sementara, lakukan tes koneksi, lalu nyalakan kembali.
3. **Uji dari Mac sendiri dulu.** Buka `http://<IP-Address>:8501` di browser Mac Anda sendiri. Jika berhasil di sini tapi gagal di perangkat lain, masalahnya ada di Firewall atau isolasi jaringan.
4. **Periksa VPN.** Jika Mac Anda sedang terhubung ke VPN, matikan sementara karena VPN sering memblokir akses jaringan lokal.

---

## Metode 2 — Deployment Publik Gratis via GitHub + Streamlit Community Cloud

Metode ini menghasilkan **tautan publik permanen** yang bisa dibuka siapa saja, kapan saja, tanpa laptop Anda harus menyala.

### Prasyarat

- Akun **GitHub** (gratis) — https://github.com
- Akun **Streamlit Community Cloud** (gratis) — https://share.streamlit.io (bisa login pakai akun GitHub)
- **Git** terpasang di Mac. Cek dengan `git --version`; jika belum ada, jalankan `xcode-select --install`.

### Langkah 1 — Siapkan file `requirements.txt`

Streamlit Community Cloud akan membaca `requirements.txt` di root proyek dan **menginstal otomatis** semua pustaka Python yang tercantum di sana saat aplikasi dideploy. File ini **sudah tersedia** di proyek NUCLEUS, berisi antara lain:

```text
streamlit==1.50.0
pandas>=2.0
numpy>=1.24
openpyxl>=3.1
plotly>=5.18
scikit-learn>=1.3
statsmodels>=0.14
prophet>=1.1
xgboost>=2.0
lightgbm>=4.0
gTTS>=2.5
pyttsx3>=2.90
SpeechRecognition>=3.10
pytest>=8.0
```

Pastikan file ini ikut ter-commit ke GitHub (langkah berikutnya). Tanpa `requirements.txt`, aplikasi akan gagal start di cloud karena pustaka tidak terpasang.

> Catatan: `pyttsx3` butuh audio lokal dan tidak berfungsi di server cloud (fitur suara akan tersembunyi otomatis, tanpa error). `prophet`, `xgboost`, dan `lightgbm` berukuran besar sehingga proses build pertama di cloud bisa agak lama — ini normal.

### Langkah 2 — Buat file `.gitignore`

Agar folder lingkungan virtual dan berkas sementara **tidak** ikut terunggah, buat berkas `.gitignore` di root proyek dengan isi:

```text
.venv/
__pycache__/
.pytest_cache/
.DS_Store
*.pyc
```

### Langkah 3 — Unggah (push) proyek ke GitHub

**a. Buat repository baru di GitHub**

1. Masuk ke https://github.com dan klik tombol **New** (atau **+ → New repository**).
2. Beri nama, misalnya `nucleus-dashboard`.
3. Pilih **Public** (wajib publik untuk versi gratis Streamlit Community Cloud).
4. **Jangan** centang "Add a README" (karena proyek sudah punya file sendiri). Klik **Create repository**.

**b. Inisialisasi Git dan push dari terminal Mac**

Jalankan dari dalam folder proyek (ganti `USERNAME` dengan username GitHub Anda):

```bash
cd "/Users/ramadhanipuratama/workplace/kirocrew-workspace/NUCLEUS"
git init
git add .
git commit -m "NUCLEUS dashboard - initial commit"
git branch -M main
git remote add origin https://github.com/USERNAME/nucleus-dashboard.git
git push -u origin main
```

> Saat `git push`, GitHub mungkin meminta login. Gunakan **Personal Access Token** sebagai pengganti password (buat di GitHub: **Settings → Developer settings → Personal access tokens**), atau login lebih mudah lewat **GitHub CLI** (`gh auth login`).

Setelah berhasil, refresh halaman repository di GitHub — Anda akan melihat `app.py`, `requirements.txt`, dan file lainnya sudah terunggah.

### Langkah 4 — Hubungkan ke Streamlit Community Cloud

1. Buka https://share.streamlit.io lalu **Sign in with GitHub** dan beri izin akses.
2. Klik tombol **Create app** / **New app** → pilih **Deploy a public app from GitHub**.
3. Isi formulir deploy:
   - **Repository:** `USERNAME/nucleus-dashboard`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL (opsional):** atur subdomain, misalnya `nucleus-dashboard` → menghasilkan `https://nucleus-dashboard.streamlit.app`
4. Klik **Deploy**.

Streamlit akan membaca `requirements.txt`, memasang semua dependensi, lalu menjalankan `app.py`. Proses build pertama bisa memakan beberapa menit (karena ada paket besar seperti prophet/xgboost). Setelah selesai, Anda mendapat tautan publik permanen yang tinggal dibagikan ke rekan tim.

### Langkah 5 — Memperbarui aplikasi di kemudian hari

Setiap kali Anda mengubah kode, cukup push ulang ke GitHub:

```bash
cd "/Users/ramadhanipuratama/workplace/kirocrew-workspace/NUCLEUS"
git add .
git commit -m "Perbarui dashboard"
git push
```

Streamlit Community Cloud akan **otomatis mendeteksi perubahan** dan men-deploy ulang aplikasi — tautan publik tetap sama.

---

## Metode 3 — Deployment via Bitbucket + Streamlit Community Cloud

Sama seperti Metode 2, tetapi kode disimpan di **Bitbucket**. Cocok untuk tim yang sudah memakai Bitbucket/Jira. Hasil akhirnya juga berupa **tautan publik permanen**.

### Prasyarat

- Akun **Bitbucket** (gratis) — https://bitbucket.org
- Akun **Streamlit Community Cloud** (gratis) — https://share.streamlit.io
- **Git** terpasang di Mac. Cek dengan `git --version`; jika belum ada, jalankan `xcode-select --install`.
- File `requirements.txt` dan `.gitignore` sudah disiapkan (lihat Langkah 1 & 2 pada Metode 2).

### Langkah 1 — Buat repository baru di Bitbucket

1. Masuk ke https://bitbucket.org lalu klik **Create → Repository**.
2. Isi detail repository:
   - **Workspace:** pilih workspace Anda.
   - **Project:** pilih atau buat project (mis. `NUCLEUS`).
   - **Repository name:** `nucleus-dashboard`.
   - **Access level:** untuk kolaborasi tim, biarkan **Private** (Bitbucket mendukung repo privat gratis). Streamlit Cloud tetap bisa mengaksesnya setelah akun terhubung.
   - **Include a README / .gitignore:** pilih **No** agar tidak bentrok dengan file proyek yang sudah ada.
3. Klik **Create repository**. Catat URL remote-nya, biasanya berformat:
   `https://USERNAME@bitbucket.org/WORKSPACE/nucleus-dashboard.git`

### Langkah 2 — Push kode NUCLEUS ke Bitbucket

Jalankan dari dalam folder proyek. Ganti `WORKSPACE` dan `USERNAME` sesuai akun Anda:

```bash
cd "/Users/ramadhanipuratama/workplace/kirocrew-workspace/NUCLEUS"
git init
git add .
git commit -m "NUCLEUS dashboard - initial commit"
git branch -M main
git remote add origin https://bitbucket.org/WORKSPACE/nucleus-dashboard.git
git push -u origin main
```

> **Autentikasi Bitbucket:** saat `git push`, jangan gunakan password akun biasa. Buat **App Password** di Bitbucket (**Personal settings → App passwords → Create app password**) dengan izin minimal **Repositories: Read & Write**, lalu pakai App Password itu sebagai pengganti password saat diminta.
>
> **Nama branch:** perintah di atas memakai `main`. Beberapa repo lama memakai `master`. Pastikan nama branch yang Anda push cocok dengan yang akan dipilih di Streamlit Cloud (lihat Langkah 4).

Setelah berhasil, refresh halaman repository di Bitbucket — `app.py`, `requirements.txt`, dan file lain sudah terunggah.

### Langkah 3 — Hubungkan akun Bitbucket ke Streamlit Community Cloud

1. Buka https://share.streamlit.io dan login.
2. Masuk ke **Settings → Linked accounts** (atau ikuti dialog yang muncul saat membuat app baru).
3. Klik **Connect** pada bagian **Bitbucket**, lalu **Grant access** agar Streamlit memperoleh izin membaca repository Anda. Anda akan diarahkan ke halaman otorisasi Bitbucket — setujui permintaannya.

> Jika repository bersifat **Private**, langkah pemberian izin ini wajib agar Streamlit Cloud dapat menarik (clone) kode dari Bitbucket.

### Langkah 4 — Buat app baru dan pilih repository Bitbucket

1. Di dashboard Streamlit, klik **Create app** / **New app**.
2. Pilih sumber **Bitbucket** (bukan GitHub).
3. Isi formulir deploy:
   - **Repository:** `WORKSPACE/nucleus-dashboard`
   - **Branch:** `main` (atau `master`, sesuai nama branch yang Anda push di Langkah 2)
   - **Main file path:** `app.py`
   - **App URL (opsional):** atur subdomain, misalnya `nucleus-dashboard` → `https://nucleus-dashboard.streamlit.app`
4. Klik **Deploy**.

### Langkah 5 — Pastikan `requirements.txt` ikut ter-push

Streamlit Cloud membaca `requirements.txt` di root repository Bitbucket dan **memasang otomatis** semua library (Streamlit, Prophet, Plotly, pandas, scikit-learn, statsmodels, dll.). Tanpa file ini, aplikasi akan gagal start karena dependensi tidak terpasang.

Cek dengan cepat bahwa file sudah ada di repo:

```bash
git ls-files | grep requirements.txt
```

Jika tidak muncul, tambahkan lalu push:

```bash
git add requirements.txt
git commit -m "Tambahkan requirements.txt"
git push
```

> Catatan sama seperti Metode 2: build pertama bisa agak lama karena `prophet`, `xgboost`, dan `lightgbm` berukuran besar, dan fitur suara (`pyttsx3`) otomatis tersembunyi di server karena tidak ada perangkat audio.

### Langkah 6 — Memperbarui aplikasi

Setiap perubahan kode cukup di-push ulang; Streamlit Cloud akan men-deploy ulang otomatis:

```bash
git add .
git commit -m "Perbarui dashboard"
git push
```

### Kolaborasi tim di Bitbucket

Agar rekan tim bisa ikut mengembangkan kode NUCLEUS secara bersama-sama, beri mereka akses lewat salah satu cara berikut:

**A. Akses per repository (Repository access)**
1. Buka repository `nucleus-dashboard` di Bitbucket.
2. Masuk ke **Repository settings → User and group access**.
3. Pada kolom **Users**, masukkan email/username rekan tim, pilih tingkat izin, lalu klik **Add**:
   - **Read** — hanya bisa melihat/clone kode.
   - **Write** — bisa push perubahan (umumnya ini yang dipakai untuk kolaborator).
   - **Admin** — bisa mengubah pengaturan repository.

**B. Akses sekaligus lewat Workspace (Workspace permission)**
1. Buka **Workspace settings → User groups** (atau **Members**).
2. Undang rekan tim ke workspace via email, lalu tetapkan mereka ke grup (mis. `Developers`) yang punya izin **Write** ke repository.
3. Ini praktis bila banyak repo dalam satu workspace karena izin diatur sekali untuk banyak proyek.

Setelah menerima undangan, rekan tim bisa langsung meng-clone dan ikut mengembangkan:

```bash
git clone https://bitbucket.org/WORKSPACE/nucleus-dashboard.git
cd nucleus-dashboard
# buat perubahan, lalu:
git add .
git commit -m "Deskripsi perubahan"
git push
```

> Tips kolaborasi: untuk menjaga kualitas kode, pertimbangkan setiap orang bekerja di branch sendiri lalu membuka **Pull Request** di Bitbucket sebelum digabung ke `main`.

---

## Ringkasan Perintah Cepat

**Berbagi lewat jaringan lokal:**
```bash
source .venv/bin/activate
streamlit run app.py --server.address 0.0.0.0
ipconfig getifaddr en0        # cari IP, lalu buka http://<IP>:8501 di perangkat lain
```

**Deploy publik via GitHub (sekali setup):**
```bash
git init && git add . && git commit -m "NUCLEUS dashboard"
git branch -M main
git remote add origin https://github.com/USERNAME/nucleus-dashboard.git
git push -u origin main
# lalu hubungkan repo di https://share.streamlit.io
```

**Deploy publik via Bitbucket (sekali setup):**
```bash
git init && git add . && git commit -m "NUCLEUS dashboard"
git branch -M main
git remote add origin https://bitbucket.org/WORKSPACE/nucleus-dashboard.git
git push -u origin main
# lalu di share.streamlit.io: Settings → Linked accounts → Connect Bitbucket,
# baru Create app (Branch: main/master, Main file: app.py)
```

---

## Pemecahan Masalah Singkat

| Masalah | Kemungkinan penyebab & solusi |
| --- | --- |
| `zsh: command not found: streamlit` | Streamlit ada di dalam `.venv`. Jalankan `source .venv/bin/activate` dulu, atau pakai `python3 -m streamlit run app.py`. |
| Rekan kerja tidak bisa buka URL lokal | Beda jaringan Wi-Fi, Firewall Mac aktif, atau VPN menyala. Lihat bagian **Tips Firewall** di Metode 1. |
| Build gagal di Streamlit Cloud | Pastikan `requirements.txt` ter-push dan nama paket benar. Cek log build di dashboard Streamlit. |
| Fitur suara (TTS) tidak muncul di cloud | Normal. `pyttsx3` butuh audio lokal; fitur disembunyikan otomatis di server. |
| Repo GitHub harus publik | Versi gratis Streamlit Community Cloud mendukung repository GitHub **publik**. |
| `git push` ke Bitbucket ditolak / minta password | Gunakan **App Password** Bitbucket (Personal settings → App passwords, izin Repositories: Read & Write), bukan password akun. |
| Streamlit tidak melihat repo Bitbucket privat | Hubungkan dulu akun di **Settings → Linked accounts → Connect Bitbucket** dan beri **Grant access**. |
| Branch tidak ditemukan saat deploy | Nama branch yang di-push harus sama dengan yang dipilih di Streamlit (`main` atau `master`). |
