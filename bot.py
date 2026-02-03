import os
import io
import uuid
import telebot
import yt_dlp
from photo import download_from_tikwm, expand_url
from main import TOKEN

bot = telebot.TeleBot(TOKEN)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ---------- YT-DLP OPTIONS ----------
ydl_opts = {
    "format": "bestvideo+bestaudio/best",
    "merge_output_format": "mp4",
    "quiet": True,
    "noplaylist": True,
    "socket_timeout": 60,
    "retries": 5,
    "continuedl": True
}

# ---------- START COMMAND ----------
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Привет!\n\n"
        "Отправь ссылку на TikTok, YouTube, Instagram или Pinterest.\n"
        "Файлы будут автоматически скачаны и отправлены.",
        parse_mode="Markdown"
    )

# ---------- LINK HANDLER ----------
@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def handle_link(message):
    chat_id = message.chat.id
    url = message.text.strip()
    bot.send_message(chat_id, "⏳ Ожидайте, скачивание может занять немного времени…")

    # Расширяем ссылку
    url = expand_url(url)

    # ------ TikTok фото ------
    if "tiktok.com" in url:
        try:
            api_data = download_from_tikwm(url, return_data=True)
            if api_data.get("images"):
                files = download_from_tikwm(url)
                media = []
                for f in files[:10]:
                    with open(f, "rb") as file:
                        bio = io.BytesIO(file.read())
                        bio.name = os.path.basename(f)
                        media.append(telebot.types.InputMediaPhoto(bio))
                if media:
                    bot.send_media_group(chat_id, media)
                for f in files:
                    os.remove(f)
                return
        except Exception:
            pass  # если фото нет → считаем что это видео

    # ------ Видео и фото через yt-dlp ------
    try:
        # Генерируем уникальное имя файла
        unique_filename = f"{DOWNLOAD_DIR}/{uuid.uuid4()}.%(ext)s"
        ydl_opts_updated = ydl_opts.copy()
        ydl_opts_updated["outtmpl"] = unique_filename

        with yt_dlp.YoutubeDL(ydl_opts_updated) as ydl:
            info = ydl.extract_info(url, download=True)

            # Если несколько видео/карусель
            entries = info.get("entries")
            if entries:
                for entry in entries:
                    filename = ydl.prepare_filename(entry)
                    if not filename.endswith(".mp4"):
                        filename = filename.rsplit(".", 1)[0] + ".mp4"

                    # Видео
                    if entry.get("duration"):
                        with open(filename, "rb") as f:
                            bot.send_video(chat_id, f, supports_streaming=True)
                        os.remove(filename)
                    else:  # Фото
                        with open(filename, "rb") as f:
                            bio = io.BytesIO(f.read())
                            bio.name = os.path.basename(filename)
                            bot.send_photo(chat_id, bio)
                        os.remove(filename)
                return

            # Одиночное медиа
            filename = ydl.prepare_filename(info)
            if not filename.endswith(".mp4"):
                filename = filename.rsplit(".", 1)[0] + ".mp4"

        # Отправка файла
        with open(filename, "rb") as f:
            if info.get("duration"):  # видео
                bot.send_video(chat_id, f, supports_streaming=True)
            else:  # фото
                bio = io.BytesIO(f.read())
                bio.name = os.path.basename(filename)
                bot.send_photo(chat_id, bio)
        os.remove(filename)

    except yt_dlp.utils.DownloadError as e:
        err_msg = str(e)
        if "This content is only available for registered users" in err_msg or \
           "private" in err_msg.lower():
            bot.send_message(chat_id, "❌ Данный профиль закрыт, скачать фото/видео невозможно.")
        else:
            bot.send_message(chat_id, f"❌ Ошибка загрузки:\n{e}")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка загрузки:\n{e}")

# ---------- RUN ----------
print("🤖 Бот запущен")
bot.infinity_polling()
