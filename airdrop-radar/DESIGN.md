# Radar + Rutinitas Testnet

Dokumen desain: ambil KONSEP paket airdrop-agent (radar + testnet) saja, diadaptasi ke
aturan main yang aman. Paket aslinya TIDAK dipasang (doktrin burner paksa, grinder quest,
selfbot Discord, mode RISK — semua bentrok dengan aturan di bawah).

## Aturan keras
- Wallet: HANYA wallet testnet kamu sendiri (EVM + Solana), kunci lokal mode 600.
  Mainnet tidak pernah disentuh sistem ini.
- Tidak ada mode RISK ON. Proyek BARU selalu: laporan vetting dulu → digarap hanya setelah
  user bilang "garap". Skor = rekomendasi, bukan izin.
- Dilarang: grinding quest platform (Galxe/Zealy/Layer3), selfbot/grinder Discord,
  multi-akun/sybil, auto-join/follow/login akun pribadi user (Google/X/Telegram tetap manual).
- Telegram hanya via pratinjau publik t.me/s/<channel> (tanpa perlu akun Telegram).
  X hanya pencarian publik gratis, tanpa API berbayar.
- Laporan: chat utama + WhatsApp, model digest (anti banjir, ada cap frekuensi).
- Kerja yang butuh PC user ≥ 11:00 WIB; server-side kapan saja; ritme manusiawi.
- Kill switch: file KILL di folder ini + matikan cron = semua berhenti. Setiap job cek KILL dulu.

## Komponen
1. **Radar** — baca sumber publik (channel Telegram via t.me/s/, pencarian X publik, sumber web
   yang sudah kita pantau). Filter kata kunci include/exclude/high-risk, bobot trust per sumber,
   dedupe 14 hari, skor minimum untuk dilaporkan. Link "claim" tidak pernah dieksekusi — review
   manusia saja.
2. **Penyaring / scoring** — scam check heuristik: domain lookalike/punycode vs domain resmi,
   TLD berisiko, umur domain (RDAP), pola teks drainer (minta seed/private key = BLOCK,
   "kirim dulu untuk dapat" = BLOCK, bayar fee untuk unlock = BLOCK, urgensi/admin ngajak DM =
   WARN). Skor riset dari fakta manual (funding, investor, token sudah launch?, program poin,
   tim publik, KYC, biaya farm): ≥70 GARAP, 50–69 GARAP SANTAI, <50 SKIP — dipadukan kriteria
   kita: legit & terlacak, testnet masih jalan, pre-TGE, gratis.
3. **Rutinitas testnet** — HANYA proyek yang sudah disetujui user. Katalog faucet per chain
   (cooldown jam + syarat login/captcha/dll), cap per chain (maks per tx / harian / gas).
   Kandidat awal: proyek dari portofolio kamu sendiri (daily claim, cek poin berkala,
   quest sisa). Proyek baru masuk daftar hanya lewat gerbang persetujuan kamu.
4. **Pelaporan** — digest radar 2×/hari (usulan 12:15 + 19:45 WIB) + laporan hasil rutinitas
   menyatu di laporan harian 19:00 bila memungkinkan. Temuan HIGH-risk: lapor segera, jangan
   buka link-nya.

## Alur data
Sumber publik → dedupe → scam check + scoring → laporan vetting ke user → user bilang "garap"
→ proyek masuk daftar rutinitas (config) → rutinitas jalan per jadwal dengan cap + pacing →
hasil tercatat & dilaporkan.

## Tata letak folder airdrop-radar/
- DESIGN.md (file ini)
- config/ — sources.yaml (sumber + trust), keywords.yaml, caps.yaml, projects.yaml (proyek disetujui)
- data/ — seen.json (dedupe), scores/ (hasil vetting per kandidat)
- scripts/ — radar_fetch, scam_check, score, routine_<project>, report
- KILL — kill switch (dibuat saat darurat saja)

## Fase bangun
- **Fase 1 — radar read-only + laporan.** Sumber publik, filter, dedupe, scam check, scoring,
  digest. Nol transaksi, nol login.
- **Fase 2 — rutinitas testnet proyek disetujui.** Faucet + aksi testnet ber-cap untuk proyek
  di projects.yaml saja, per-project script.

