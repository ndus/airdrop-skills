# GTD Watch — pantauan registrasi GTD (guaranteed whitelist) NFT

Sistem kecil untuk memastikan tidak ada jatah GTD yang hangus: setiap registrasi GTD yang sudah disubmit dicatat, lalu **dicek sekali sehari** (deadline-nya terlihat di halaman proyek sendiri, jadi tidak perlu polling terus-menerus).

## Alur end-to-end

1. **Radar menemukan** launch NFT legit yang membuka registrasi GTD (dari radar airdrop kamu).
2. **Vet dulu** — legit, bukan drainer, biaya free / gas-only saja. Tanda bahaya (minta seed phrase, approval tak terbatas, domain tiruan) = SKIP permanen.
3. **Daftarkan wallet garapan** secepatnya (jatah GTD terkunci untuk yang daftar awal):
   - Agent utama: EVM `0xALAMAT_EVM_KAMU` atau Solana `ALAMAT_SOLANA_KAMU` (sesuai chain launch-nya).
   - Agent kedua (Hermes): HANYA wallet burner `0xALAMAT_BURNER_EVM` / `ALAMAT_BURNER_SOLANA` — tidak pernah wallet utama.
   - Registrasi yang butuh tugas X/Discord mengikuti aturan perlindungan akun yang berlaku (akun X utama hanya dari browser kamu sendiri).
   - Langkah yang butuh tanda tangan/gas mainnet dari wallet utama: disiapkan sampai siap-klik, user yang menandatangani.
4. **Catat ke registry** segera setelah submit (lihat `add.py` di bawah) — wajib isi `mint_deadline` dan `result_source` (URL halaman pengumuman hasil / daftar pemenang, atau catatan tempat hasil diumumkan).
5. **Checker harian** membaca registry sekali sehari: melaporkan hanya bila (a) hasil GTD ditemukan (wallet/handle muncul di halaman hasil → status `won`, dilaporkan menonjol dengan 🎉), atau (b) deadline mint ≤24 jam lagi. Deadline lewat tanpa hasil terkonfirmasi → status `expired`.

## File

- `registry.json` — daftar entri: `{project, chain, wallet, register_url, result_source, mint_deadline (ISO 8601), submitted_at, status: pending|won|lost|minted|expired, notes}`.
- `add.py` — tambah entri:
  ```
  python3 add.py --project "NamaProyek" --chain base \
    --wallet 0xALAMAT_EVM_KAMU \
    --register-url https://... --result-source https://... \
    --mint-deadline 2026-11-25T12:00:00Z --notes "..."
  ```
  Duplikat (project + wallet yang sama, masih pending) ditolak.
- `check.py` — cek sekali jalan:
  ```
  python3 check.py            # registry.json di folder yang sama
  GTD_REGISTRY=/path/registry.json python3 check.py
  ```
  Output: baris-baris perhatian, atau persis `NO_NEWS` kalau tidak ada apa-apa. check.py murni read-only (GET saja, tanpa kode wallet/signing); satu-satunya tulisannya adalah memperbarui status di registry.

## Jadwal

- Agent utama: cron harian — diam kecuali ada hasil GTD atau deadline ≤24 jam.
- Agent Hermes: skill `gtd-watch` — registry terpisah (wallet burner), dicek sekali sehari, menang GTD dilaporkan ke kamu.

## Keamanan

- Checker tidak pernah memegang kunci, tidak pernah sign, tidak pernah kirim transaksi.
- Registrasi GTD sendiri adalah aksi terpisah yang selalu melewati vetting (dan drain-guard) sebelum wallet didaftarkan ke situs mana pun.
