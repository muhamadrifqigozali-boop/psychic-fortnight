import asyncio
import os
import random
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, ChatWriteForbiddenError

# =========================
# KONFIGURASI
# =========================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
STRING_SESSION = os.getenv("STRING_SESSION")

IMAGE = "promo.jpg"
CAPTION_FILE = "pesan.txt"

# === DELAY ===
DELAY_MIN = 7
DELAY_MAX = 15
LONG_BREAK_EVERY = 12
LONG_BREAK_MIN = 45
LONG_BREAK_MAX = 90
REST_AFTER_FULL_CYCLE = 45 * 60   # 45 menit


def load_caption():
    if not os.path.exists(CAPTION_FILE):
        raise FileNotFoundError(f"{CAPTION_FILE} tidak ditemukan")
    with open(CAPTION_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


async def send_to_all_groups(client, caption):
    groups = []
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if getattr(entity, "megagroup", False) or entity.__class__.__name__ == "Chat":
            groups.append(dialog)

    if not groups:
        print("[!] Tidak ada grup ditemukan.")
        return

    print(f"[✓] Ditemukan {len(groups)} grup. Mulai kirim...")

    berhasil = 0
    gagal = 0

    for index, dialog in enumerate(groups, 1):
        name = dialog.name
        print(f"[{index}/{len(groups)}] KIRIM → {name}")

        try:
            # Coba kirim gambar + caption
            await client.send_file(dialog.entity, IMAGE, caption=caption)
            print("        ✓ BERHASIL (gambar)")
            berhasil += 1

        except FloodWaitError as e:
            wait = e.seconds + 20
            print(f"\n[!] FloodWait {e.seconds}s → tidur {wait} detik")
            await asyncio.sleep(wait)
            continue

        except Exception:
            # Gagal kirim gambar → coba teks saja
            try:
                await client.send_message(dialog.entity, caption)
                print("        ✓ BERHASIL (teks saja)")
                berhasil += 1
            except ChatWriteForbiddenError:
                print("        ✗ Tidak punya izin kirim")
                gagal += 1
            except Exception as e2:
                print(f"        ✗ Gagal total: {e2}")
                gagal += 1

        # Delay
        if index < len(groups):
            if index % LONG_BREAK_EVERY == 0:
                long_delay = random.randint(LONG_BREAK_MIN, LONG_BREAK_MAX)
                print(f"        ⏳ Jeda panjang {long_delay} detik...")
                await asyncio.sleep(long_delay)
            else:
                delay = random.randint(DELAY_MIN, DELAY_MAX)
                print(f"        Menunggu {delay} detik...")
                await asyncio.sleep(delay)

    print(f"\n[SELESAI 1 PUTARAN] Berhasil: {berhasil} | Gagal: {gagal}")


async def main():
    print("🚀 Telegram Auto Promo dimulai...")

    if not all([API_ID, API_HASH, STRING_SESSION]):
        print("[!] API_ID / API_HASH / STRING_SESSION belum di-set")
        return

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

    await client.start()
    me = await client.get_me()
    print(f"[✓] Login sebagai: {me.first_name}")

    while True:
        try:
            caption = load_caption()
            await send_to_all_groups(client, caption)

            print(f"\n😴 Istirahat {REST_AFTER_FULL_CYCLE // 60} menit sebelum putaran berikutnya...\n")
            await asyncio.sleep(REST_AFTER_FULL_CYCLE)

        except Exception as e:
            print(f"[ERROR] {e}")
            print("Tidur 5 menit lalu coba lagi...")
            await asyncio.sleep(300)


if __name__ == "__main__":
    asyncio.run(main())