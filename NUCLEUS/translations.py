"""translations.py — simple global localization layer for NUCLEUS.

A flat dictionary maps a stable key to its Indonesian (``id``) and English
(``en``) strings. The UI never hard-codes display text; it calls ``t(key)``,
which resolves against the language stored in ``st.session_state``.

Indonesian is the default language. ``t`` degrades gracefully: an unknown key
returns the key itself so a missing translation is visible but non-fatal, and
positional ``{}`` / named ``{name}`` placeholders can be filled via ``.format``.
"""
from __future__ import annotations

DEFAULT_LANG = "EN"
SUPPORTED = ("EN", "ID")
_SESSION_KEY = "nucleus_lang"

# key -> {"id": ..., "en": ...}
TRANSLATIONS: dict[str, dict[str, str]] = {
    # --- Header / branding --------------------------------------------- #
    "app.tagline": {
        "id": "Network, Unified Compute, and Layered Environment Under "
              "Surveillance",
        "en": "Network, Unified Compute, and Layered Environment Under "
              "Surveillance",
    },
    "lang.label": {"id": "Bahasa", "en": "Language"},

    # --- Sidebar ------------------------------------------------------- #
    "sidebar.settings": {"id": "⚙️ Pengaturan Prediksi", "en": "⚙️ Forecast Settings"},
    "sidebar.upload": {"id": "Unggah Dokumen", "en": "Upload File"},
    "sidebar.granularity": {"id": "Atur Waktu", "en": "Time granularity"},
    "sidebar.granularity.help": {
        "id": "Pilihan mengikuti interval data pada berkas Anda. Auto memilih "
              "'{suggested}'. Pilih 'Rentang Khusus' untuk menyaring berdasarkan "
              "tanggal.",
        "en": "Options follow the sampling interval detected in your file. Auto "
              "picks '{suggested}'. Pick 'Custom Range' to filter history by "
              "start/end date.",
    },
    "sidebar.date_range": {"id": "Rentang Tanggal", "en": "Date range"},
    "sidebar.date_range.help": {
        "id": "Hanya data historis dalam rentang ini yang diprediksi.",
        "en": "Only historical data within this range is forecasted.",
    },
    "sidebar.device": {"id": "Perangkat", "en": "Device"},
    "sidebar.device.help": {
        "id": "Pilih satu atau beberapa perangkat untuk diprediksi.",
        "en": "Pick one or more devices to forecast.",
    },
    "sidebar.interface": {"id": "Antarmuka", "en": "Interface"},
    "sidebar.interface.help": {
        "id": "Antarmuka yang tersedia untuk perangkat terpilih.",
        "en": "Interfaces available for the selected device(s).",
    },
    "sidebar.metric": {"id": "Metrik", "en": "Metric"},
    "sidebar.metric.help": {
        "id": "Pilih satu atau beberapa metrik.",
        "en": "Pick one or more metrics.",
    },
    "sidebar.horizon": {"id": "Jangka Waktu Prediksi", "en": "Forecast horizon"},
    "sidebar.horizon.amount": {"id": "Jumlah", "en": "Amount"},
    "sidebar.horizon.unit": {"id": "Satuan", "en": "Unit"},
    "sidebar.method": {"id": "Metode Prediksi", "en": "Forecasting method"},

    # --- Horizon units ------------------------------------------------- #
    "unit.day": {"id": "Hari", "en": "Day"},
    "unit.month": {"id": "Bulan", "en": "Month"},
    "unit.year": {"id": "Tahun", "en": "Year"},

    # --- Granularity options ------------------------------------------- #
    "gran.Auto": {"id": "Auto", "en": "Auto"},
    "gran.Minute": {"id": "Menit", "en": "Minute"},
    "gran.Hourly": {"id": "Per Jam", "en": "Hourly"},
    "gran.Daily": {"id": "Harian", "en": "Daily"},
    "gran.Weekly": {"id": "Mingguan", "en": "Weekly"},
    "gran.Monthly": {"id": "Bulanan", "en": "Monthly"},
    "gran.Custom Range": {"id": "Rentang Khusus", "en": "Custom Range"},

    # --- Frequency labels (prose) -------------------------------------- #
    "freq.min": {"id": "per-menit", "en": "per-minute"},
    "freq.h": {"id": "per-jam", "en": "hourly"},
    "freq.D": {"id": "harian", "en": "daily"},
    "freq.W": {"id": "mingguan", "en": "weekly"},
    "freq.MS": {"id": "bulanan", "en": "monthly"},

    # --- Detection / analysis ------------------------------------------ #
    "detect.summary": {
        "id": "Analisis NUCLEUS telah selesai. Mengevaluasi {devices} pada "
              "{metrics}.",
        "en": "NUCLEUS analysis finalized. Evaluated {devices} across "
              "{metrics}.",
    },
    "detect.metrics.found": {
        "id": "Berhasil mendeteksi {n} metrik: {names}.",
        "en": "Successfully detected {n} metrics: {names}.",
    },
    "detect.metrics.found.one": {
        "id": "Berhasil mendeteksi {n} metrik: {names}.",
        "en": "Successfully detected {n} metric: {names}.",
    },
    "count.device.one": {"id": "{n} perangkat", "en": "{n} device"},
    "count.device.many": {"id": "{n} perangkat", "en": "{n} devices"},
    "count.metric.one": {"id": "{n} metrik utama", "en": "{n} core metric"},
    "count.metric.many": {"id": "{n} metrik utama", "en": "{n} core metrics"},
    "forecast.opt": {
        "id": "{prefix}Optimasi Model Selesai: {model} dipilih berdasarkan "
              "galat backtest terendah (MAPE: {mape}). Peringkat Algoritma: "
              "{ranking}.",
        "en": "{prefix}Model Optimization Complete: {model} selected based on "
              "lowest backtest error (MAPE: {mape}). Algorithmic Ranking: "
              "{ranking}.",
    },
    "forecast.opt.manual": {
        "id": "{prefix}Evaluasi Model Selesai: {model} diterapkan sesuai "
              "konfigurasi (MAPE backtest: {mape}).",
        "en": "{prefix}Model Evaluation Complete: {model} applied as "
              "configured (backtest MAPE: {mape}).",
    },
    "forecast.opt.item": {"id": "{model} (MAPE: {mape})",
                          "en": "{model} (MAPE: {mape})"},
    "detect.expander": {
        "id": "🔎 Struktur & metrik terdeteksi",
        "en": "🔎 Detected structure & metrics",
    },
    "detect.devices": {"id": "Perangkat", "en": "Devices"},
    "detect.interfaces": {"id": "Antarmuka", "en": "Interfaces"},
    "detect.metrics": {"id": "Metrik yang dianalisis", "en": "Metrics to be analyzed"},
    "detect.mapping": {"id": "Pemetaan kolom", "en": "Column mapping"},
    "detect.unreadable": {
        "id": "**NUCLEUS tidak dapat membaca berkas ini.** Format yang diterima:\n"
              "- **Format panjang (long)**: kolom waktu, kolom perangkat "
              "(opsional), kolom nama metrik, dan kolom nilai, atau\n"
              "- **Format lebar (wide)**: kolom waktu plus satu kolom numerik "
              "per metrik.\n\nNama kolom fleksibel (mis. `time`, `host`, `nilai` "
              "dikenali). Berikut kolom yang terbaca NUCLEUS:",
        "en": "**NUCLEUS couldn't interpret this file.** It accepts either:\n"
              "- **Long format**: a timestamp column, an optional device column, "
              "a metric-name column and a value column, or\n"
              "- **Wide format**: a timestamp column plus one numeric column per "
              "metric.\n\nColumn names are flexible (e.g. `time`, `host`, `nilai` "
              "are recognized). Here are the columns NUCLEUS saw:",
    },

    # --- Granularity captions ------------------------------------------ #
    "gran.custom.caption": {
        "id": "🗓️ Rentang khusus pada granularitas **{freq}**: {start} → {end}.",
        "en": "🗓️ Custom range at **{freq}** granularity: {start} → {end}.",
    },
    "gran.auto.caption": {
        "id": "🕒 Granularitas otomatis: **{freq}** (dideteksi dari timestamp Anda).",
        "en": "🕒 Auto granularity: **{freq}** (detected from your timestamps).",
    },
    "gran.custom.need_both": {
        "id": "📅 Pilih tanggal mulai dan selesai untuk melanjutkan.",
        "en": "📅 Select both a start and end date to continue.",
    },

    # --- Dataset summary ----------------------------------------------- #
    "dataset.summary": {
        "id": "📋 Ringkasan Dataset (setelah pembersihan)",
        "en": "📋 Dataset summary (after cleaning)",
    },

    # --- KPI cards ----------------------------------------------------- #
    "kpi.current": {"id": "Nilai Terkini ({name})", "en": "Current ({name})"},
    "kpi.peak": {
        "id": "Puncak Prediksi (maks. seleksi)",
        "en": "Peak Predicted (max of selection)",
    },
    "kpi.change": {"id": "Proyeksi Perubahan (utama)", "en": "Projected Change (primary)"},

    # --- Forecast caption / status ------------------------------------- #
    "forecast.caption": {
        "id": "Memprediksi **{n} deret** · jangka **{horizon}** "
              "({steps} × langkah {freq}) · metode **{method}**.",
        "en": "Forecasting **{n} series** · horizon **{horizon}** "
              "({steps} × {freq} steps) · method **{method}**.",
    },
    "forecast.skipped": {
        "id": "⚠️ Melewati {n} deret dengan titik terlalu sedikit pada "
              "granularitas **{freq}** (butuh ≥ {min}). Coba granularitas lebih "
              "halus atau pilih lebih sedikit deret beresolusi tinggi.",
        "en": "⚠️ Skipped {n} series with too few points at **{freq}** "
              "granularity (need ≥ {min}). Try a finer granularity or fewer, "
              "higher-resolution selections.",
    },
    "forecast.none": {
        "id": "Tidak ada deret yang dapat diprediksi pada seleksi saat ini.",
        "en": "No forecastable series in the current selection.",
    },
    "forecast.pick_prompt": {
        "id": "👈 Pilih minimal satu perangkat dan satu metrik untuk memprediksi.",
        "en": "👈 Select at least one device and one metric to run a forecast.",
    },
    "forecast.pick_interface_prompt": {
        "id": "👈 Dataset ini memiliki data tingkat antarmuka. Pilih minimal "
              "satu antarmuka untuk memprediksi.",
        "en": "👈 This dataset has interface-level data. Select at least one "
              "interface to run a forecast.",
    },

    # --- Chart --------------------------------------------------------- #
    "chart.history": {"id": "historis", "en": "history"},
    "chart.forecast": {"id": "prediksi", "en": "forecast"},
    "chart.band": {"id": "Pita proyeksi", "en": "Projection band"},
    "chart.multi_title": {
        "id": "{n} deret — historis vs prediksi",
        "en": "{n} series — historical vs forecast",
    },
    "chart.title_suffix": {"id": "jangka {horizon}", "en": "horizon {horizon}"},
    "chart.x": {"id": "Tanggal", "en": "Date"},
    "chart.y": {"id": "Nilai", "en": "Value"},

    # --- Analytics streams --------------------------------------------- #
    "stream.label": {"id": "Aliran Analitik", "en": "Analytics Stream"},
    "stream.pick_prompt": {
        "id": "👆 Pilih salah satu Analytics Stream untuk mulai mengunggah "
              "data dan melihat analitik.",
        "en": "👆 Select an Analytics Stream above to start uploading data and "
              "viewing analytics.",
    },
    "stream.compute": {"id": "🖥️ Compute Stream", "en": "🖥️ Compute Stream"},
    "stream.network": {"id": "🌐 Network Stream", "en": "🌐 Network Stream"},
    "stream.facility": {"id": "🏢 Facility Stream", "en": "🏢 Facility Stream"},
    "stream.upload": {
        "id": "Unggah data stream (.csv / .xlsx)",
        "en": "Upload stream data (.csv / .xlsx)",
    },
    "stream.upload.help": {
        "id": "Kolom dibaca otomatis dari berkas dan dipetakan ke tabel "
              "SQLite khusus stream ini.",
        "en": "Columns are read automatically from the file and mapped to this "
              "stream's dedicated SQLite table.",
    },
    "stream.ingest.ok": {
        "id": "✅ {rows} baris × {cols} kolom dipetakan ke tabel **{table}**.",
        "en": "✅ {rows} rows × {cols} columns mapped into table **{table}**.",
    },
    "stream.ingest.replaced": {
        "id": "♻️ Data sebelumnya pada stream ini diperbarui (replace).",
        "en": "♻️ Previous data for this stream was replaced (upsert).",
    },
    "stream.persist.loaded": {
        "id": "Sinkronisasi database selesai. Sebanyak {rows} catatan historis "
              "hingga {date} kini tersimpan pada tabel {table} dan siap untuk "
              "peramalan otomatis.",
        "en": "Database synchronization complete. A total of {rows} historical "
              "records up to {date} are now stored in the {table} table and "
              "ready for automated forecasting.",
    },
    "stream.persist.loaded.nodate": {
        "id": "Sinkronisasi database selesai. Sebanyak {rows} catatan historis "
              "kini tersimpan pada tabel {table} dan siap untuk peramalan "
              "otomatis.",
        "en": "Database synchronization complete. A total of {rows} historical "
              "records are now stored in the {table} table and ready for "
              "automated forecasting.",
    },
    "stream.persist.stored": {
        "id": "Sinkronisasi database selesai. Sebanyak {rows} catatan historis "
              "hingga {date} kini tersimpan pada tabel {table}.",
        "en": "Database synchronization complete. A total of {rows} historical "
              "records up to {date} are now stored in the {table} table.",
    },
    "stream.persist.stored.nodate": {
        "id": "Sinkronisasi database selesai. Sebanyak {rows} catatan historis "
              "kini tersimpan pada tabel {table}.",
        "en": "Database synchronization complete. A total of {rows} historical "
              "records are now stored in the {table} table.",
    },
    "stream.persist.empty": {
        "id": "Repositori belum memiliki catatan historis untuk stream ini. "
              "Unggah berkas untuk menginisialisasi database.",
        "en": "The repository holds no historical records for this stream yet. "
              "Upload a file to initialize the database.",
    },
    "stream.persist.demo": {
        "id": "Data demonstrasi ditampilkan hingga unggahan pertama "
              "tersinkronisasi.",
        "en": "Demonstration data is displayed until the first upload is "
              "synchronized.",
    },
    "stream.sync.ok": {
        "id": "✅ Tersinkron ke tabel **{table}**: **{inserted}** baris baru, "
              "**{updated}** diperbarui, **{unchanged}** identik (dilewati).",
        "en": "✅ Synced to table **{table}**: **{inserted}** new rows, "
              "**{updated}** updated, **{unchanged}** unchanged (skipped).",
    },
    "stream.sync.created": {
        "id": "🆕 Tabel **{table}** dibuat dari file ini: **{inserted}** baris, "
              "{cols} kolom.",
        "en": "🆕 Table **{table}** created from this file: **{inserted}** rows, "
              "{cols} columns.",
    },
    "stream.sync.replaced": {
        "id": "♻️ Struktur kolom berbeda dari data tersimpan, jadi tabel "
              "**{table}** diganti dengan file ini ({rows} baris).",
        "en": "♻️ The columns differ from the stored data, so table "
              "**{table}** was replaced with this file ({rows} rows).",
    },
    "stream.sync.keys": {
        "id": "Kunci upsert: {keys}",
        "en": "Upsert key: {keys}",
    },
    "stream.sync.keys.none": {
        "id": "Tidak ada kolom waktu: baris identik dilewati, baris baru "
              "ditambahkan.",
        "en": "No time column found: identical rows are skipped, new rows are "
              "added.",
    },
    "stream.sync.newcols": {
        "id": "➕ Kolom baru ditambahkan ke tabel: {cols}",
        "en": "➕ New columns added to the table: {cols}",
    },
    "stream.sync.dups": {
        "id": "{n} baris dalam file memiliki kunci yang sama dan digabung "
              "(baris terakhir dipakai).",
        "en": "{n} rows in the file shared a key and were merged (the last one "
              "is kept).",
    },
    "stream.sync.skipped": {
        "id": "⚠️ {n} baris dilewati karena waktunya tidak valid.",
        "en": "⚠️ {n} rows were skipped because their timestamp is invalid.",
    },
    "stream.ingest.error": {
        "id": "❌ Gagal memproses berkas: {err}",
        "en": "❌ Could not process the file: {err}",
    },
    "stream.stored.title": {
        "id": "🗄️ Data tersimpan (SQLite)",
        "en": "🗄️ Stored data (SQLite)",
    },
    "stream.stored.summary": {
        "id": "Tabel **{table}** · {rows} baris · {cols} kolom.",
        "en": "Table **{table}** · {rows} rows · {cols} columns.",
    },
    "stream.empty": {
        "id": "Belum ada data untuk dianalisis pada stream ini. Unggah berkas "
              "melalui panel di sisi kiri untuk memulai.",
        "en": "There is no data to analyze for this stream yet. Upload a file "
              "from the left-hand panel to begin.",
    },
    "stream.placeholder": {
        "id": "Modul analitik untuk stream ini sedang disiapkan. Data yang "
              "Anda unggah disimpan dan dipratinjau di bawah.",
        "en": "The analytics module for this stream is being prepared. Data you "
              "upload is stored and previewed below.",
    },

    # --- NUCLEUS Intelligent Insight ----------------------------------- #
    "insight.header": {
        "id": "🧬 Wawasan Cerdas NUCLEUS",
        "en": "🧬 NUCLEUS Intelligent Insight",
    },
    "insight.speak": {"id": "🔊 Dengarkan", "en": "🔊 Speak"},
    "insight.per_series": {
        "id": "📑 Ringkasan prediksi per deret",
        "en": "📑 Per-series forecast summary",
    },

    # --- Results table columns ----------------------------------------- #
    "table.device": {"id": "Perangkat", "en": "Device"},
    "table.interface": {"id": "Antarmuka", "en": "Interface"},
    "table.metric": {"id": "Metrik", "en": "Metric"},
    "table.unit": {"id": "Satuan", "en": "Unit"},
    "table.current": {"id": "Terkini", "en": "Current"},
    "table.peak": {"id": "Puncak (prediksi)", "en": "Peak (forecast)"},
    "table.method": {"id": "Metode", "en": "Method"},

    # --- Profile table columns (data_loader) --------------------------- #
    "profile.device": {"id": "Perangkat", "en": "Device"},
    "profile.interface": {"id": "Antarmuka", "en": "Interface"},
    "profile.metric": {"id": "Metrik", "en": "Metric"},
    "profile.unit": {"id": "Satuan", "en": "Unit"},
    "profile.points": {"id": "Jumlah Titik", "en": "Points"},
    "profile.start": {"id": "Mulai", "en": "Start"},
    "profile.end": {"id": "Selesai", "en": "End"},
    "profile.min": {"id": "Min", "en": "Min"},
    "profile.mean": {"id": "Rata-rata", "en": "Mean"},
    "profile.max": {"id": "Maks", "en": "Max"},

    # --- Errors -------------------------------------------------------- #
    "error.read": {
        "id": "❌ Kesalahan tak terduga saat membaca berkas: {err}",
        "en": "❌ Unexpected error reading the file: {err}",
    },
    "error.no_range_data": {
        "id": "❌ Tidak ada data dalam rentang tanggal yang dipilih.",
        "en": "❌ No data falls within the selected date range.",
    },

    # --- Login portal -------------------------------------------------- #
    "login.welcome": {
        "id": "Selamat datang di NUCLEUS",
        "en": "Welcome to NUCLEUS",
    },
    "login.subtitle": {
        "id": "Masuk untuk mengakses platform pemantauan & analitik infrastruktur.",
        "en": "Sign in to access the infrastructure monitoring & analytics platform.",
    },
    "login.username": {"id": "Nama Pengguna", "en": "Username"},
    "login.password": {"id": "Kata Sandi", "en": "Password"},
    "login.submit": {"id": "Masuk", "en": "Sign In"},
    "export.excel": {"id": "Ekspor ke Excel (.xlsx)", "en": "Export to Excel (.xlsx)"},
    "session.expired": {
        "id": "Sesi Anda telah berakhir karena tidak ada aktivitas selama {duration}. Silakan masuk kembali untuk melanjutkan.",
        "en": "Your session has expired due to {duration} of inactivity. Please sign in again to continue.",
    },
    "login.error": {
        "id": "❌ Nama pengguna atau kata sandi salah.",
        "en": "❌ Invalid username or password.",
    },
    "login.hint": {
        "id": "Kredensial demo — pengguna: `admin`, sandi: `nucleus`.",
        "en": "Demo credentials — user: `admin`, password: `nucleus`.",
    },
    "login.footer": {
        "id": "Network, Unified Compute, and Layered Environment Under Surveillance",
        "en": "Network, Unified Compute, and Layered Environment Under Surveillance",
    },

    # --- Mode selector (landing) --------------------------------------- #
    "selector.title": {"id": "Pilih Modul", "en": "Select a Module"},
    "selector.subtitle": {
        "id": "Pilih bagaimana Anda ingin mengelola infrastruktur Anda hari ini.",
        "en": "Choose how you want to govern your infrastructure today.",
    },
    "selector.analytics.title": {"id": "Analytics", "en": "Analytics"},
    "selector.analytics.desc": {
        "id": "Prediksi kapasitas, pemodelan machine learning, dan wawasan "
              "cerdas NUCLEUS atas data metrik historis Anda.",
        "en": "Capacity forecasting, machine-learning models, and NUCLEUS "
              "intelligent insight over your historical metric data.",
    },
    "selector.analytics.cta": {"id": "Buka Analytics", "en": "Open Analytics"},
    "selector.monitoring.title": {"id": "Monitoring", "en": "Monitoring"},
    "selector.database.title": {"id": "Database", "en": "Database"},
    "selector.monitoring.desc": {
        "id": "Pemantauan status perangkat secara real-time dan kesehatan "
              "infrastruktur yang aktif.",
        "en": "Real-time device status monitoring and live infrastructure "
              "health.",
    },
    "selector.monitoring.cta": {"id": "Buka Monitoring", "en": "Open Monitoring"},

    # --- Navigation / session ------------------------------------------ #
    "nav.back_to_menu": {"id": "🏠 Kembali ke Pemilihan Modul",
                        "en": "🏠 Back to Module Selection"},
    "nav.home": {"id": "Beranda — kembali ke pemilihan modul",
                "en": "Home — back to module selection"},
    "nav.hide_sidebar": {"id": "Sembunyikan Panel", "en": "Hide Panel"},
    "nav.show_sidebar": {"id": "Tampilkan Panel", "en": "Show Panel"},
    "nav.logout": {"id": "🚪 Keluar", "en": "🚪 Log Out"},
    "nav.signed_in_as": {"id": "Masuk sebagai **{user}**", "en": "Signed in as **{user}**"},
    "nav.navigation": {"id": "Navigasi", "en": "Navigation"},

    # --- Monitoring placeholder ---------------------------------------- #
    "monitoring.header": {
        "id": "📡 Pemantauan Real-Time",
        "en": "📡 Real-Time Monitoring",
    },
    "monitoring.subtitle": {
        "id": "Status perangkat infrastruktur yang aktif saat ini.",
        "en": "Live status of active infrastructure devices.",
    },
    "monitoring.coming_soon": {
        "id": "🚧 Modul pemantauan real-time sedang dalam pengembangan. "
              "Di bawah ini adalah pratinjau status perangkat (data contoh).",
        "en": "🚧 The real-time monitoring module is under development. Below "
              "is a preview of device status (sample data).",
    },
    "monitoring.col.device": {"id": "Perangkat", "en": "Device"},
    "monitoring.col.status": {"id": "Status", "en": "Status"},
    "monitoring.col.uptime": {"id": "Waktu Aktif", "en": "Uptime"},
    "monitoring.col.cpu": {"id": "CPU", "en": "CPU"},
    "monitoring.col.mem": {"id": "Memori", "en": "Memory"},
    "monitoring.kpi.online": {"id": "Perangkat Online", "en": "Devices Online"},
    "monitoring.kpi.alerts": {"id": "Peringatan Aktif", "en": "Active Alerts"},
    "monitoring.kpi.avg_cpu": {"id": "Rata-rata CPU", "en": "Avg. CPU"},
    "monitoring.status.online": {"id": "🟢 Online", "en": "🟢 Online"},
    "monitoring.status.warning": {"id": "🟡 Peringatan", "en": "🟡 Warning"},
    "monitoring.status.offline": {"id": "🔴 Offline", "en": "🔴 Offline"},

    # --- Roles --------------------------------------------------------- #
    "role.administrator": {"id": "Administrator", "en": "Administrator"},
    "role.engineer": {"id": "Engineer / Analis Kapasitas",
                      "en": "Engineer / Capacity Analyst"},
    "role.viewer": {"id": "Viewer / Eksekutif", "en": "Viewer / Executive"},

    # --- Login hint (updated for multiple demo accounts) --------------- #
    "login.hint.multi": {
        "id": "Akun demo — `admin`/`nucleus` (Administrator), "
              "`engineer`/`engineer`, `viewer`/`viewer`.",
        "en": "Demo accounts — `admin`/`nucleus` (Administrator), "
              "`engineer`/`engineer`, `viewer`/`viewer`.",
    },
    "login.disabled": {
        "id": "❌ Akun ini nonaktif. Hubungi administrator.",
        "en": "❌ This account is disabled. Contact an administrator.",
    },

    # --- Mode selector: user management card --------------------------- #
    "selector.users.title": {"id": "⚙️ Settings", "en": "⚙️ Settings"},
    "selector.users.desc": {
        "id": "Manajemen pengguna & peran, konfigurasi forecasting, sumber "
              "data, dan preferensi sistem. Khusus Administrator.",
        "en": "User & role management, forecasting config, data sources, and "
              "system preferences. Administrators only.",
    },
    "selector.users.cta": {"id": "Buka Settings", "en": "Open Settings"},
    "selector.users.short": {"id": "⚙️ Settings", "en": "⚙️ Settings"},

    # --- Settings page (tabbed) ---------------------------------------- #
    "settings.header": {"id": "⚙️ Settings", "en": "⚙️ Settings"},
    "settings.subtitle": {
        "id": "Pusat pengaturan tata kelola, forecasting, data, dan sistem "
              "NUCLEUS.",
        "en": "Central hub for NUCLEUS governance, forecasting, data and "
              "system settings.",
    },
    "settings.tab.users": {"id": "👥 Manajemen Pengguna", "en": "👥 User Management"},
    "settings.tab.forecasting": {"id": "📈 Konfigurasi Forecasting",
                                 "en": "📈 Forecasting Config"},
    "settings.tab.data": {"id": "🗄️ Data", "en": "🗄️ Data"},
    "settings.tab.system": {"id": "🖥️ Sistem", "en": "🖥️ System"},

    # Forecasting config tab
    "settings.fc.title": {"id": "Model Forecasting Default",
                         "en": "Default Forecasting Model"},
    "settings.fc.desc": {
        "id": "Pilih model prediksi default yang ditampilkan pada modul "
              "Analytics.",
        "en": "Choose the default forecasting model shown in the Analytics "
              "module.",
    },
    "settings.fc.default_model": {"id": "Model default", "en": "Default model"},
    "settings.fc.enabled_models": {"id": "Model yang diaktifkan",
                                   "en": "Enabled models"},
    "settings.fc.save": {"id": "Simpan Konfigurasi", "en": "Save Config"},
    "settings.fc.saved": {"id": "✅ Konfigurasi forecasting disimpan.",
                         "en": "✅ Forecasting config saved."},

    # Data tab
    "settings.data.title": {"id": "Sumber Data & Preferensi",
                           "en": "Data Source & Preferences"},
    "settings.data.source": {"id": "Saat repositori masih kosong",
                            "en": "While the repository is empty"},
    "settings.data.source.sample": {"id": "Tampilkan data demonstrasi",
                                    "en": "Show demonstration data"},
    "settings.data.source.upload": {"id": "Tampilkan status kosong (wajib unggah)",
                                    "en": "Show an empty state (upload required)"},
    "settings.data.retention": {"id": "Retensi data (hari)",
                               "en": "Data retention (days)"},
    "settings.data.save": {"id": "Simpan Preferensi Data",
                          "en": "Save Data Preferences"},
    "settings.data.saved": {"id": "✅ Preferensi data disimpan.",
                           "en": "✅ Data preferences saved."},

    # System tab
    "settings.sys.title": {"id": "Preferensi Sistem", "en": "System Preferences"},
    "settings.sys.language": {"id": "Bahasa utama sistem", "en": "System language"},
    "settings.sys.theme.note": {
        "id": "Tampilan NUCLEUS menggunakan tema gelap Apple Liquid Glass "
              "secara permanen.",
        "en": "NUCLEUS uses a permanent dark Apple Liquid Glass theme.",
    },
    "settings.sys.save": {"id": "Simpan Preferensi Sistem",
                         "en": "Save System Preferences"},
    "settings.sys.saved": {"id": "✅ Preferensi sistem disimpan.",
                          "en": "✅ System preferences saved."},

    # --- Database module ------------------------------------------------ #
    "db.header": {"id": '🗄 Database', "en": '🗄 Database'},
    "db.subtitle": {"id": 'Jelajahi, kueri, dan kelola repository SQLite lokal NUCLEUS. Khusus Administrator.', "en": 'Browse, query and maintain the local NUCLEUS SQLite repository. Administrators only.'},
    "db.kpi.tables": {"id": 'Tabel', "en": 'Tables'},
    "db.kpi.rows": {"id": 'Total baris', "en": 'Total rows'},
    "db.kpi.size": {"id": 'Ukuran file', "en": 'File size'},
    "db.kpi.modified": {"id": 'Terakhir diubah', "en": 'Last modified'},
    "db.path": {"id": 'File database: {path}', "en": 'Database file: {path}'},
    "db.tab.browser": {"id": 'Penjelajah Tabel', "en": 'Table Browser'},
    "db.tab.console": {"id": 'Konsol Kueri', "en": 'Query Console'},
    "db.tab.manage": {"id": 'Manajemen Data', "en": 'Data Management'},
    "db.tab.transfer": {"id": 'Impor & Ekspor', "en": 'Import & Export'},
    "db.empty": {"id": 'Database belum memiliki tabel.', "en": 'The database has no tables yet.'},
    "db.browser.title": {"id": 'Daftar Tabel', "en": 'Tables'},
    "db.browser.pick": {"id": 'Tabel', "en": 'Table'},
    "db.browser.schema": {"id": 'Skema kolom', "en": 'Column schema'},
    "db.browser.preview": {"id": 'Pratinjau ({n} baris pertama)', "en": 'Preview (first {n} rows)'},
    "db.col.table": {"id": 'Tabel', "en": 'Table'},
    "db.col.rows": {"id": 'Baris', "en": 'Rows'},
    "db.col.columns": {"id": 'Kolom', "en": 'Columns'},
    "db.col.column": {"id": 'Kolom', "en": 'Column'},
    "db.col.type": {"id": 'Tipe data', "en": 'Data type'},
    "db.col.notnull": {"id": 'Wajib isi', "en": 'Not null'},
    "db.col.pk": {"id": 'Kunci utama', "en": 'Primary key'},
    "db.console.title": {"id": 'Konsol Kueri SQL', "en": 'SQL Query Console'},
    "db.console.readonly": {"id": 'Berjalan pada koneksi hanya-baca: perintah yang mengubah data akan ditolak. Maksimal {rows} baris ditampilkan; kueri dihentikan setelah {secs} detik.', "en": 'Runs on a read-only connection: statements that change data are rejected. Up to {rows} rows are shown; a query is stopped after {secs} seconds.'},
    "db.console.sql": {"id": 'SQL', "en": 'SQL'},
    "db.console.run": {"id": 'Jalankan Kueri', "en": 'Run Query'},
    "db.console.stats": {"id": '{n} baris · {ms} ms', "en": '{n} rows · {ms} ms'},
    "db.console.truncated": {"id": 'Hanya {rows} baris pertama yang ditampilkan.', "en": 'Only the first {rows} rows are shown.'},
    "db.console.no_rows": {"id": 'Perintah tidak mengembalikan hasil.', "en": 'The statement returned no result set.'},
    "db.confirm.ack": {"id": 'Saya paham tindakan ini tidak dapat dibatalkan dari aplikasi.', "en": 'I understand this cannot be undone from the app.'},
    "db.confirm.type": {"id": 'Ketik {phrase} untuk konfirmasi', "en": 'Type {phrase} to confirm'},
    "db.manage.table.title": {"id": 'Hapus Data Tabel', "en": 'Delete Table Data'},
    "db.manage.table.pick": {"id": 'Tabel', "en": 'Table'},
    "db.manage.action": {"id": 'Tindakan', "en": 'Action'},
    "db.manage.clear": {"id": 'Hapus semua baris', "en": 'Delete all rows'},
    "db.manage.drop": {"id": 'Hapus tabel', "en": 'Drop table'},
    "db.manage.clear.help": {"id": 'Menghapus seluruh {rows} baris dari {table}; tabel dan kolomnya tetap ada.', "en": 'Removes all {rows} rows from {table}; the table and its columns stay.'},
    "db.manage.drop.help": {"id": 'Menghapus tabel {table} beserta {rows} barisnya secara permanen.', "en": 'Removes the table {table} and its {rows} rows completely.'},
    "db.manage.clear.btn": {"id": 'Hapus Baris', "en": 'Delete Rows'},
    "db.manage.drop.btn": {"id": 'Hapus Tabel', "en": 'Drop Table'},
    "db.manage.clear.done": {"id": '{rows} baris dihapus dari {table}.', "en": 'Deleted {rows} rows from {table}.'},
    "db.manage.drop.done": {"id": 'Tabel {table} telah dihapus.', "en": 'Table {table} was dropped.'},
    "db.reset.title": {"id": 'Reset Database', "en": 'Reset Database'},
    "db.reset.help": {"id": 'Menghapus semua tabel di database ({n}). Analytics akan kosong sampai data baru diunggah.', "en": 'Drops every table in the database ({n}). Analytics will be empty until new data is uploaded.'},
    "db.reset.btn": {"id": 'Reset Database', "en": 'Reset Database'},
    "db.reset.done": {"id": 'Database direset: {n} tabel dihapus.', "en": 'Database reset: {n} tables dropped.'},
    "db.backup.note": {"id": 'Salinan cadangan disimpan di samping file database sebelum setiap hapus, reset, atau impor ({keep} terbaru disimpan).', "en": 'A backup copy is saved next to the database file before every delete, reset or import (the newest {keep} are kept).'},
    "db.export.title": {"id": 'Ekspor', "en": 'Export'},
    "db.export.db.label": {"id": "Seluruh database (SQLite)", "en": "Whole database (SQLite)"},
    "db.export.db.help": {"id": 'Seluruh database sebagai file SQLite.', "en": 'The whole database as a SQLite file.'},
    "db.export.db": {"id": 'Unduh Database (.db)', "en": 'Download Database (.db)'},
    "db.export.csv.pick": {"id": 'Tabel untuk diekspor ke CSV', "en": 'Table to export as CSV'},
    "db.export.csv": {"id": 'Unduh Tabel (.csv)', "en": 'Download Table (.csv)'},
    "db.import.title": {"id": 'Impor Database', "en": 'Import Database'},
    "db.import.file": {"id": 'File database SQLite', "en": 'SQLite database file'},
    "db.import.help": {"id": 'Unggah file .db / .sqlite. File diperiksa sebelum ada perubahan.', "en": 'Upload a .db / .sqlite file. It is checked before anything changes.'},
    "db.import.valid": {"id": 'Database SQLite valid dengan {n} tabel: {tables}', "en": 'Valid SQLite database with {n} tables: {tables}'},
    "db.import.mode": {"id": 'Mode impor', "en": 'Import mode'},
    "db.import.mode.update": {"id": 'Perbarui tabel', "en": 'Update tables'},
    "db.import.mode.replace": {"id": 'Ganti seluruh database', "en": 'Replace whole database'},
    "db.import.mode.update.help": {"id": 'Tabel di file menggantikan tabel bernama sama; tabel lain yang sudah ada tetap disimpan.', "en": 'Tables in the file replace tables with the same name; other existing tables are kept.'},
    "db.import.mode.replace.help": {"id": 'Database saat ini diganti seluruhnya oleh file yang diunggah.', "en": 'The current database is replaced entirely by the uploaded file.'},
    "db.import.btn": {"id": 'Impor', "en": 'Import'},
    "db.import.done.update": {"id": 'Impor selesai: {n} tabel diperbarui.', "en": 'Import complete: {n} tables updated.'},
    "db.import.done.replace": {"id": 'Database diganti: {n} tabel dimuat.', "en": 'Database replaced: {n} tables loaded.'},
    "db.err.not_sqlite": {"id": 'File bukan database SQLite yang valid.', "en": 'The file is not a valid SQLite database.'},
    "db.err.integrity": {"id": 'File database gagal dalam pemeriksaan integritas.', "en": 'The database file failed the integrity check.'},
    "db.err.missing": {"id": 'File database belum ada.', "en": 'The database file does not exist yet.'},
    "db.err.unknown_table": {"id": 'Tabel tersebut sudah tidak ada.', "en": 'That table no longer exists.'},
    "db.err.empty_query": {"id": 'Masukkan perintah SQL terlebih dahulu.', "en": 'Enter a SQL statement first.'},
    "db.err.timeout": {"id": 'Kueri dihentikan setelah {secs} detik.', "en": 'The query was stopped after {secs} seconds.'},
    "db.err.generic": {"id": 'Kesalahan database: {err}', "en": 'Database error: {err}'},
    # --- Access control ------------------------------------------------ #
    "access.denied": {
        "id": "🔒 Anda tidak memiliki izin untuk mengakses modul ini.",
        "en": "🔒 You do not have permission to access this module.",
    },
    "access.readonly": {
        "id": "👁️ Mode hanya-baca — peran Anda tidak dapat mengubah data "
              "atau mengunggah berkas.",
        "en": "👁️ Read-only mode — your role cannot change data or upload files.",
    },
    "access.role_badge": {"id": "Peran: **{role}**", "en": "Role: **{role}**"},

    # --- User Management page ------------------------------------------ #
    "users.header": {"id": "👥 Manajemen Pengguna", "en": "👥 User Management"},
    "users.subtitle": {
        "id": "Kelola akun, peran, dan status aktif pengguna NUCLEUS.",
        "en": "Manage NUCLEUS user accounts, roles, and active status.",
    },
    "users.table.title": {"id": "Daftar Pengguna", "en": "System Users"},
    "users.col.username": {"id": "Nama Pengguna", "en": "Username"},
    "users.col.full_name": {"id": "Nama Lengkap", "en": "Full Name"},
    "users.col.email": {"id": "Email", "en": "Email"},
    "users.col.role": {"id": "Peran", "en": "Role"},
    "users.col.status": {"id": "Status", "en": "Status"},
    "users.status.active": {"id": "🟢 Aktif", "en": "🟢 Active"},
    "users.status.inactive": {"id": "⚪ Nonaktif", "en": "⚪ Inactive"},

    "users.add.title": {"id": "➕ Tambah Pengguna", "en": "➕ Add User"},
    "users.edit.title": {"id": "✏️ Edit Pengguna", "en": "✏️ Edit User"},
    "users.delete.title": {"id": "🗑️ Hapus / Nonaktifkan",
                          "en": "🗑️ Delete / Disable"},
    "users.field.password": {"id": "Kata Sandi", "en": "Password"},
    "users.field.password.keep": {
        "id": "Kata Sandi (kosongkan untuk tidak mengubah)",
        "en": "Password (leave blank to keep unchanged)",
    },
    "users.field.active": {"id": "Aktif", "en": "Active"},
    "users.btn.add": {"id": "Tambah Pengguna", "en": "Add User"},
    "users.btn.save": {"id": "Simpan Perubahan", "en": "Save Changes"},
    "users.btn.toggle": {"id": "Aktif/Nonaktifkan", "en": "Toggle Active"},
    "users.btn.delete": {"id": "Hapus Pengguna", "en": "Delete User"},
    "users.select.user": {"id": "Pilih pengguna", "en": "Select user"},

    "users.msg.added": {"id": "✅ Pengguna **{user}** ditambahkan.",
                       "en": "✅ User **{user}** added."},
    "users.msg.updated": {"id": "✅ Pengguna **{user}** diperbarui.",
                         "en": "✅ User **{user}** updated."},
    "users.msg.deleted": {"id": "✅ Pengguna **{user}** dihapus.",
                         "en": "✅ User **{user}** deleted."},
    "users.msg.toggled": {"id": "✅ Status **{user}** diubah.",
                         "en": "✅ Status for **{user}** changed."},

    "users.err.username_required": {"id": "❌ Nama pengguna wajib diisi.",
                                    "en": "❌ Username is required."},
    "users.err.username_exists": {"id": "❌ Nama pengguna sudah digunakan.",
                                  "en": "❌ Username already exists."},
    "users.err.invalid_role": {"id": "❌ Peran tidak valid.",
                               "en": "❌ Invalid role."},
    "users.err.password_required": {"id": "❌ Kata sandi wajib diisi.",
                                    "en": "❌ Password is required."},
    "users.err.user_not_found": {"id": "❌ Pengguna tidak ditemukan.",
                                 "en": "❌ User not found."},
    "users.err.last_admin": {
        "id": "❌ Tidak dapat menghapus/menonaktifkan administrator aktif "
              "terakhir.",
        "en": "❌ Cannot remove or disable the last active administrator.",
    },
}


# --------------------------------------------------------------------------- #
# Resolution
# --------------------------------------------------------------------------- #
def normalize(lang: str | None) -> str:
    lang = (lang or DEFAULT_LANG).upper()
    return lang if lang in SUPPORTED else DEFAULT_LANG


def get_lang() -> str:
    """Current language from Streamlit session state (falls back to default)."""
    try:
        import streamlit as st
        return normalize(st.session_state.get(_SESSION_KEY, DEFAULT_LANG))
    except Exception:  # noqa: BLE001 - usable outside Streamlit (e.g. tests)
        return DEFAULT_LANG


def set_lang(lang: str) -> None:
    try:
        import streamlit as st
        st.session_state[_SESSION_KEY] = normalize(lang)
    except Exception:  # noqa: BLE001
        pass


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """Translate ``key`` into the active (or given) language, with formatting.

    Unknown keys return the key itself so missing strings are visible but never
    crash the UI. ``kwargs`` fill ``{named}`` placeholders.
    """
    lang = normalize(lang) if lang else get_lang()
    entry = TRANSLATIONS.get(key)
    if not entry:
        text = key
    else:
        text = entry.get(lang.lower()) or entry.get("id") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            pass
    return text
