import asyncio
import os
import random
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, ChatWriteForbiddenError

# =========================
# KONFIGURASI
# =========================

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
STRING_SESSION = os.getenv("STRING_SESSION", "")

IMAGE_FOLDER = "images"       # Folder tempat menyimpan beberapa variasi gambar (promo1.jpg, promo2.jpg, dst)
FALLBACK_IMAGE = "promo.jpg"  # Gambar cadangan jika folder tidak ada
CAPTION_FILE = "pesan.txt"

# === DELAY AMAN 24 JAM ===
DELAY_MIN = 35                # Jeda minimum antar grup (detik)
DELAY_MAX = 60                # Jeda maksimum antar grup (detik)
LONG_BREAK_EVERY = 8          # Istirahat batch setiap 8 grup
LONG_BREAK_MIN = 120          # 2 menit
LONG_BREAK_MAX = 300          # 5 menit
REST_AFTER_FULL_CYCLE = 7200  # Istirahat 2 jam penuh setelah 1 putaran selesai


def load_captions():
    if not os.path.exists(CAPTION_FILE):
        return ["Promo menarik hari ini! Cek info lengkapnya."]
    with open(CAPTION_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        captions = [c.strip() for c in content.split("---") if c.strip()]
        return captions if captions else [content]


def get_random_image():
    if os.path.exists(IMAGE_FOLDER) and os.path.isdir(IMAGE_FOLDER):
        images = [os.path.join(IMAGE_FOLDER, img) for img in os.listdir(IMAGE_FOLDER) if img.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if images:
            return random.choice(images)
    if os.path.exists(FALLBACK_IMAGE):
        return FALLBACK_IMAGE
    return None


async def send_to_all_groups(client):
    captions = load_captions()
    
    groups = []
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        is_group = getattr(entity, "megagroup", False) or entity.__class__.__name__ == "Chat"
        if is_group and not getattr(entity, "left", True) and not getattr(entity, "kicked", False):
            groups.append(dialog)

    if not groups:
        print("[!] Tidak ada grup ditemukan.")
        return

    print(f"[✓] Ditemukan {len(groups)} grup valid. Memulai pengiriman...")

    berhasil = 0
    gagal = 0

    for index, dialog in enumerate(groups, 1):
        name = dialog.name
        image_path = get_random_image()
        
        base_caption = random.choice(captions)
        unique_caption = base_caption + "\n" + "".join(random.choices(["\u200b", "\u200c", "\u200d"], k=random.randint(1, 3)))

        print(f"[{index}/{len(groups)}] KIRIM → {name}")

        try:
            # Coba kirim gambar + caption terlebih dahulu
            if image_path:
                try:
                    await client.send_file(dialog.entity, image_path, caption=unique_caption)
                    print("        ✓ BERHASIL (gambar + teks)")
                    berhasil += 1
                except Exception as img_err:
                    # Jika grup menolak media/gambar, fallback otomatis ke teks saja
                    print(f"        ⚠ Grup menolak media ({img_err}), beralih mengirim teks saja...")
                    await client.send_message(dialog.entity, unique_caption)
                    print("        ✓ BERHASIL (teks saja)")
                    berhasil += 1
            else:
                await client.send_message(dialog.entity, unique_caption)
                print("        ✓ BERHASIL (teks saja)")
                berhasil += 1

        except FloodWaitError as e:
            wait = e.seconds + 60
            print(f"\n[!] TERKENA FLOODWAIT {e.seconds}s → Tidur pengaman selama {wait} detik...")
            await asyncio.sleep(wait)
            continue

        except ChatWriteForbiddenError:
            print("        ✗ Tidak punya izin kirim pesan di grup ini")
            gagal += 1
        except Exception as e:
            print(f"        ✗ Gagal total: {e}")
            gagal += 1

        # Pengaturan Jeda (Delay) Acak
        if index < len(groups):
            if index % LONG_BREAK_EVERY == 0:
                long_delay = random.randint(LONG_BREAK_MIN, LONG_BREAK_MAX)
                print(f"        ⏳ Jeda istirahat batch selama {long_delay // 60} menit...")
                await asyncio.sleep(long_delay)
            else:
                delay = random.randint(DELAY_MIN, DELAY_MAX)
                print(f"        Menunggu jeda {delay} detik...")
                await asyncio.sleep(delay)

    print(f"\n[SELESAI 1 PUTARAN] Berhasil: {berhasil} | Gagal: {gagal}")


async def main():
    print("🚀 Telegram Auto Promo (24H Safe Mode) dimulai...")

    if not all([API_ID, API_HASH, STRING_SESSION]):
        print("[!] API_ID / API_HASH / STRING_SESSION belum di-set di Environment Variables Railway.")
        return

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

    print("[*] Menghubungkan ke Telegram...")
    await client.start()
    me = await client.get_me()
    print(f"[✓] Login berhasil sebagai: {me.first_name}")

    while True:
        try:
            await send_to_all_groups(client)

            print(f"\n😴 Istirahat siklus penuh selama {REST_AFTER_FULL_CYCLE // 3600} jam sebelum putaran berikutnya...\n")
            await asyncio.sleep(REST_AFTER_FULL_CYCLE)

        except Exception as e:
            print(f"[ERROR UTAMA] {e}")
            print("Terjadi kendala, sistem tidur 10 menit lalu mencoba ulang...")
            await asyncio.sleep(600)


if __name__ == "__main__":
    asyncio.run(main())
    
