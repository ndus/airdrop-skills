# Airdrop Skills Pack

Kumpulan skill + script pola garap airdrop **testnet-only & gratis** untuk agent Muse / Hermes. Semua alamat wallet di paket ini sudah diganti placeholder — ganti dengan alamat burner kamu sendiri sebelum dipakai.

## Isi paket

| Folder | Isi |
|---|---|
| `drain-guard/` | Checklist pre-flight wajib sebelum aksi on-chain apa pun: cek chain, kontrak, calldata, approval, tanda tangan. Anti-drain. |
| `testnet-routine/` | Pola rutinitas testnet aman: faucet + swap kecil nominal bervariasi, ritme manusiawi, cap biaya harian, selesai flat. |
| `radar-scam-check/` | Skill + script vetting postingan airdrop (fetch Telegram publik, cek scam heuristik, skor GARAP/SANTAI/SKIP). Read-only. |
| `airdrop-radar/` | Dokumen desain radar airdrop (sumber publik → dedupe → scam check + scoring → laporan) + script radar-nya. |
| `gtd-watch/` | Pencatat + pengecek harian registrasi GTD (guaranteed whitelist) NFT: `add.py`, `check.py`, `registry.json` (kosong), plus paket versi Hermes di `hermes-package/`. |
| `claim-tge-watcher/` | Skill + script pantau deadline claim/TGE: dicatat sekali, dicek harian, dilaporkan di T-3/T-1/T-0. `watchlist.json` mulai kosong; format ada di `watchlist.example.json`. |
| `sepolia-mining/` | Rutinitas aktivitas harian di Sepolia testnet (swap kecil di Uniswap V3) dengan cap keras 0,1 ETH/hari yang ditegakkan di kode. |
| `titan-analyst/` | Script snapshot teknikal + sentimen (`market_snapshot.py`, `sentiment_snapshot.py`) dan brief analis untuk sesi trading perps testnet. |
| `humanizer/` | Panduan menulis teks (postingan X/Discord, dsb.) yang terasa ditulis manusia, bukan bot. |

## Cara pasang

- **Muse:** salin folder skill yang berisi `SKILL.md` ke folder custom-skills Muse kamu (mis. `~/workspace/custom-skills/<nama-skill>/`), lengkap dengan subfolder `scripts/`-nya bila ada.
- **Hermes:** salin folder skill ke folder skills Hermes kamu (mis. `~/.hermes/skills/<kategori>/<nama-skill>/`).
- Script Python jalan dengan `python3 <script>.py --help` untuk melihat opsi masing-masing.
- Beberapa skill menyebut CLI `aa` (paket [airdrop-agent](https://github.com/setyamickala/airdrop-agent)) sebagai mesin eksekusi on-chain — skill-nya adalah lapisan aturan & keamanannya.

## Catatan penting

- Semua pola di sini **testnet-only dan gratis**. Mainnet tidak pernah disentuh.
- Pakai **wallet burner kamu sendiri** — jangan pernah pakai wallet utama untuk garapan, dan jangan pernah bagikan seed phrase / private key ke siapa pun atau situs mana pun.
- Placeholder yang harus diganti: `0xALAMAT_...`, `ALAMAT_...`, `id-burner-kamu`, dan env `GTD_HANDLE` (handle kamu, untuk deteksi nama di halaman hasil GTD).
- Tidak ada jaminan cuan. Airdrop bisa tidak bayar, berubah aturan, atau batal — skill ini hanya membantu bekerja rapi dan aman.
