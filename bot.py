import os
import io
import telebot
import yt_dlp
from photo import download_from_tikwm, expand_url
from main import TOKEN

bot = telebot.TeleBot(TOKEN)
DOWNLOAD_DIR = "downloads"

os.environ["PATH"] += os.pathsep + os.path.join(os.getcwd(), "bin")


# ---------- Автоматическое добавление FFmpeg в PATH ----------
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
ffmpeg_path = os.path.join(os.getcwd(), "bin")

# ---------- YT-DLP OPTIONS ----------
ydl_opts = {
    "format": "bestvideo+bestaudio/best",
    "merge_output_format": "mp4",
    "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
    "quiet": True,
    "noplaylist": True,
    "socket_timeout": 60,
    "retries": 5,
    "continuedl": True
}

# ---------- START ----------
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
    bot.send_message(chat_id, "⏳ Ожидайте, может потребоваться немного времени…")

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
            # если фото нет → считаем что это видео
            pass

    # ------ Видео и фото через yt-dlp ------
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Проверяем Instagram карусель / несколько медиа
            entries = info.get("entries")
            if entries:
                media = []
                for entry in entries:
                    filename = ydl.prepare_filename(entry)
                    if not filename.endswith(".mp4"):
                        filename = filename.rsplit(".", 1)[0] + ".mp4"
                    # Определяем тип
                    if entry.get("duration"):  # видео
                        with open(filename, "rb") as f:
                            bot.send_video(chat_id, f)
                        os.remove(filename)
                    else:  # фото
                        bio = io.BytesIO(open(filename, "rb").read())
                        bio.name = os.path.basename(filename)
                        media.append(telebot.types.InputMediaPhoto(bio))
                        os.remove(filename)
                if media:
                    bot.send_media_group(chat_id, media)
                return

            # Одиночное медиа
            filename = ydl.prepare_filename(info)
            if not filename.endswith(".mp4"):
                filename = filename.rsplit(".", 1)[0] + ".mp4"

        with open(filename, "rb") as f:
            if info.get("duration"):
                bot.send_video(chat_id, f)
            else:
                bot.send_document(chat_id, f)
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
