import asyncio
import logging
import os
import random
from telethon import TelegramClient
from telethon.errors import ChatWriteForbiddenError, FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
STRING_SESSION = os.getenv("STRING_SESSION", "")

IMAGE_FOLDER = "images"
FALLBACK_IMAGE = "promo.jpg"
CAPTION_FILE = "pesan.txt"

DELAY_MIN = 45
DELAY_MAX = 90
LONG_BREAK_EVERY = 5
LONG_BREAK_MIN = 180
LONG_BREAK_MAX = 360
REST_AFTER_FULL_CYCLE = 10800  # 3 Jam


def load_captions():
  if not os.path.exists(CAPTION_FILE):
    return ["Promo menarik hari ini! Cek info lengkapnya."]
  with open(CAPTION_FILE, "r", encoding="utf-8") as f:
    content = f.read().strip()
    captions = [c.strip() for c in content.split("---") if c.strip()]
    return captions if captions else [content]


def get_random_image():
  if os.path.exists(IMAGE_FOLDER) and os.path.isdir(IMAGE_FOLDER):
    images = [
        os.path.join(IMAGE_FOLDER, img)
        for img in os.listdir(IMAGE_FOLDER)
        if img.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if images:
      return random.choice(images)
  if os.path.exists(FALLBACK_IMAGE):
    return FALLBACK_IMAGE
  return None


def generate_unique_caption(base_caption):
  # Menambahkan variasi zero-width space yang lebih acak untuk menghindari filter hash spam
  invisible_chars = ["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"]
  random_padding = "".join(random.choices(invisible_chars, k=random.randint(2, 5)))
  return f"{base_caption}\n{random_padding}"


async def send_to_all_groups(client):
  captions = load_captions()

  groups = []
  async for dialog in client.iter_dialogs():
    entity = dialog.entity
    is_group = isinstance(entity, Chat) or (
        isinstance(entity, Channel) and getattr(entity, "megagroup", False)
    )
    is_active = not getattr(entity, "left", True) and not getattr(
        entity, "kicked", False
    )
    # Pastikan bot/akun memiliki izin mengirim pesan
    can_send = not getattr(entity, "forbidden", False)

    if is_group and is_active and can_send:
      groups.append(dialog)

  if not groups:
    logger.warning("Tidak ada grup valid ditemukan.")
    return

  logger.info(
      f"Ditemukan {len(groups)} grup valid. Memulai pengiriman aman..."
  )

  berhasil = 0
  gagal = 0

  # Acak urutan grup agar pola pengiriman tidak monoton (mengurangi deteksi pola bot)
  random.shuffle(groups)

  for index, dialog in enumerate(groups, 1):
    name = dialog.name
    image_path = get_random_image()
    base_caption = random.choice(captions)
    unique_caption = generate_unique_caption(base_caption)

    logger.info(f"[{index}/{len(groups)}] Mengirim ke: {name}")

    try:
      if image_path:
        try:
          await client.send_file(
              dialog.input_entity, image_path, caption=unique_caption
          )
          logger.info("  Berhasil mengirim (Media + Teks)")
          berhasil += 1
        except Exception as img_err:
          logger.warning(
              f"  Gagal kirim media ({img_err}), fallback ke teks saja..."
          )
          await client.send_message(dialog.input_entity, unique_caption)
          logger.info("  Berhasil mengirim (Teks saja)")
          berhasil += 1
      else:
        await client.send_message(dialog.input_entity, unique_caption)
        logger.info("  Berhasil mengirim (Teks saja)")
        berhasil += 1

    except FloodWaitError as e:
      wait_time = e.seconds + 120  # Extra buffer aman
      logger.error(
          f"TERKENA FLOODWAIT! Istirahat total selama {wait_time} detik..."
      )
      await asyncio.sleep(wait_time)
      continue

    except ChatWriteForbiddenError:
      logger.warning("  Gagal: Tidak punya izin menulis di grup ini.")
      gagal += 1
    except Exception as e:
      logger.error(f"  Gagal total: {e}")
      gagal += 1

    # Jeda antar pesan dengan randomisasi tinggi
    if index < len(groups):
      if index % LONG_BREAK_EVERY == 0:
        long_delay = random.randint(LONG_BREAK_MIN, LONG_BREAK_MAX)
        logger.info(
            f"Istirahat batch selama {long_delay // 60} menit untuk keamanan..."
        )
        await asyncio.sleep(long_delay)
      else:
        delay = random.randint(DELAY_MIN, DELAY_MAX)
        logger.info(f"Menunggu jeda {delay} detik...")
        await asyncio.sleep(delay)

  logger.info(f"PUTARAN SELESAI. Berhasil: {berhasil} | Gagal: {gagal}")


async def main():
  if not all([API_ID, API_HASH, STRING_SESSION]):
    logger.error("API_ID, API_HASH, atau STRING_SESSION belum dikonfigurasi!")
    return

  client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

  logger.info("Menghubungkan ke Telegram...")
  await client.start()
  me = await client.get_me()
  logger.info(f"Berhasil login sebagai: {me.first_name} (@{me.username})")

  while True:
    try:
      if not client.is_connected():
        await client.connect()

      await send_to_all_groups(client)

      logger.info(
          f"Siklus selesai. Masuk mode tidur panjang selama"
          f" {REST_AFTER_FULL_CYCLE // 3600} jam..."
      )
      await asyncio.sleep(REST_AFTER_FULL_CYCLE)

    except Exception as e:
      logger.error(f"Error pada loop utama: {e}")
      logger.info("Mencoba ulang dalam 15 menit...")
      await asyncio.sleep(900)


if __name__ == "__main__":
  asyncio.run(main())
              
