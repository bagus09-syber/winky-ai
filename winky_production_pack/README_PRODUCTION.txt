Winky AI Production Pack

Tujuan:
- Menyiapkan project untuk 50 user prototype.
- Production config siap dipasang setelah VPS Active.
- Menyediakan struktur Redis/PostgreSQL/vector-ready tanpa memaksa migrasi sekarang.

Urutan:
1. Salin isi pack ke D:\winky atau /opt/winky sesuai kebutuhan.
2. Jalankan syntax check.
3. Commit dan push.
4. Saat VPS Active, deploy.
5. Setelah online, baru lakukan load test nyata.

Catatan:
- SQLite tetap dipakai sebagai default agar tidak merusak database saat ini.
- Redis/PostgreSQL/vector DB disiapkan sebagai konfigurasi opsional.
- Jangan masukkan secret ke Git.
