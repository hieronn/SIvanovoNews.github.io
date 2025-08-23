import json
import os
import logging
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# === НАСТРОЙКИ ===
BOT_TOKEN = "8299964233:AAFa4I3gFSjWxodUWQMx8j5W0yWkPRRhx6M"
ADMIN_USER_ID = 5207981986
CHANNEL_ID = "-1002995985111"

# Пути к файлам
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEWS_FILE = os.path.join(BASE_DIR, "news.json")

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# === ХРАНЕНИЕ ===
user_news_count = {}
user_published = {}

# === Загрузка и сохранение новостей ===
def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка записи {filename}: {e}")

# === КЛАВИАТУРА (без кнопки "Отзыв") ===
def get_main_menu():
    keyboard = [
        [KeyboardButton("📤 Прислать новость")],
        [KeyboardButton("ℹ️ Как отправить новость?"), KeyboardButton("📊 Мои новости")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        "Вы можете прислать новость из села Иваново.\n\n"
        "Мы рассмотрим и, возможно, опубликуем на сайте!"
    )
    await update.message.reply_text(text, reply_markup=get_main_menu())

# === /help ===
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📝 <b>Как прислать новость:</b>\n\n"
        "1. Напишите: <b>что произошло</b>\n"
        "2. Укажите: <b>где и когда</b>\n"
        "3. Прикрепите <b>фото или видео</b> (по желанию)\n\n"
        "✅ Пример:\n"
        "<i>Сегодня убрали мусор у школы. Было 10 участников. Фото прилагаю.</i>"
    )
    await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=get_main_menu())

# === /my_news ===
async def my_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    total = user_news_count.get(user.id, 0)
    published = user_published.get(user.id, 0)
    await update.message.reply_text(
        f"📬 Вы прислали <b>{total}</b> новостей\n"
        f"✅ Опубликовано: <b>{published}</b>\n"
        f"⏳ На модерации: <b>{total - published}</b>",
        parse_mode='HTML',
        reply_markup=get_main_menu()
    )

# === Приём новостей ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    text_content = message.text or message.caption or "[без текста]"

    # Сохраняем сообщение
    context.bot_data[f"last_message_{user.id}"] = {
        "from_chat_id": message.chat_id,
        "message_id": message.message_id,
        "text": text_content,
        "has_photo": bool(message.photo),
        "has_video": bool(message.video)
    }

    if message.photo and not message.caption:
        await message.reply_text(
            "📸 Вы отправили фото, но не написали, что на нём.\n"
            "Пожалуйста, кратко опишите событие: где, что, когда?",
            reply_markup=get_main_menu()
        )
        return

    # Приём новости
    user_news_count[user.id] = user_news_count.get(user.id, 0) + 1
    admin_msg = (
        f"📬 НОВАЯ НОВОСТЬ НА МОДЕРАЦИИ\n"
        f"👤 {user.full_name} ({'@'+user.username if user.username else 'нет юзернейма'})\n"
        f"🆔 {user.id}\n"
        f"⏰ {datetime.now().strftime('%H:%M %d.%m')}\n\n"
        f"💬 {text_content}"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_msg)
        if message.photo:
            photo_file = await message.photo[-1].get_file()
            await context.bot.send_photo(chat_id=ADMIN_USER_ID, photo=photo_file.file_id, caption="📸 Фото от жителя")
        if message.video:
            video_file = await message.video.get_file()
            await context.bot.send_video(chat_id=ADMIN_USER_ID, video=video_file.file_id, caption="🎥 Видео от жителя")

        await message.reply_text(
            "✅ Спасибо за новость!\n\n"
            "Мы её проверим. Если подойдёт — опубликуем на сайте, и вы получите уведомление 💌",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.reply_text("⚠️ Ошибка при отправке.")

# === /publish <user_id> ===
async def published(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("UsageId: `/publish <user_id>`")
        return

    try:
        user_id = int(context.args[0])
        user_info = await context.bot.get_chat(user_id)
        user_name = user_info.full_name

        last_msg = context.bot_data.get(f"last_message_{user_id}")
        if not last_msg:
            await update.message.reply_text("❌ Не удалось найти сообщение.")
            return

        # Сохраняем новость
        news = load_json(NEWS_FILE)
        news.insert(0, {
            "user_id": user_id,
            "name": user_name,
            "username": f"@{user_info.username}" if user_info.username else "аноним",
            "text": last_msg["text"],
            "date": datetime.now().strftime("%d.%m.%Y"),
            "timestamp": datetime.now().isoformat()
        })
        save_json(NEWS_FILE, news)

        # Публикуем в канал
        await context.bot.forward_message(
            chat_id=CHANNEL_ID,
            from_chat_id=last_msg["from_chat_id"],
            message_id=last_msg["message_id"]
        )

        # Уведомляем автора
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎉 Поздравляем!\n\nВаша новость опубликована:\n👉 https://t.me/nseloivanovo\n\nСайт: https://hieronn.github.io/SIvanovoNews.github.io/"
        )
        await update.message.reply_text(f"✅ Новость от {user_name} добавлена и опубликована")

        user_published[user_id] = user_published.get(user.id, 0) + 1

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# === /reject, /stats, /rss ===
async def rejected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    if len(context.args) != 1:
        return
    user_id = int(context.args[0])
    await context.bot.send_message(chat_id=user_id, text="Спасибо! Пока не можем опубликовать, но продолжайте присылать!")
    await update.message.reply_text(f"✅ Отклонено: {user_id}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    total_users = len(user_news_count)
    total_news = sum(user_news_count.values())
    published_total = sum(user_published.values())
    await update.message.reply_text(f"📊 Авторов: {total_users}\n📬 Новостей: {total_news}\n✅ Опубликовано: {published_total}")

async def rss_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        import feedparser
        feed = feedparser.parse("https://rss.telega.link/channel.php?channel=nseloivanovo")
        msg = "🗞 Последние 3 новости:\n\n"
        for i, e in enumerate(feed.entries[:3]):
            title = e.title or "Без заголовка"
            msg += f"{i+1}. {title}\n"
        await update.message.reply_text(msg)
    except:
        await update.message.reply_text("❌ Ошибка RSS")

# === ЗАПУСК ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("publish", published))
    app.add_handler(CommandHandler("reject", rejected))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("rss", rss_command))
    app.add_handler(MessageHandler(filters.Regex("^ℹ️ Как отправить новость\\?$"), help_command))
    app.add_handler(MessageHandler(filters.Regex("^📤 Прислать новость$"), lambda u, c: None))
    app.add_handler(MessageHandler(filters.Regex("^📊 Мои новости$"), my_news))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(MessageHandler(filters.VIDEO, handle_message))

    print("✅ Бот запущен. Ожидаю сообщений...")
    app.run_polling()