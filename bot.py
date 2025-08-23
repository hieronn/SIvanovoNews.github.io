import json
import os
import logging
from datetime import datetime, timedelta
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# === НАСТРОЙКИ ===
BOT_TOKEN = "8299964233:AAFa4I3gFSjWxodUWQMx8j5W0yWkPRRhx6M"
ADMIN_USER_ID = 5207981986
CHANNEL_ID = "-1002995985111"

# Пути к файлам
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEWS_FILE = os.path.join(BASE_DIR, "news.json")
BANNED_USERS_FILE = os.path.join(BASE_DIR, "banned_users.json")
MUTED_USERS_FILE = os.path.join(BASE_DIR, "muted_users.json")
LOG_FILE = os.path.join(BASE_DIR, "moderation_log.json")

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# === ХРАНЕНИЕ В ПАМЯТИ ===
user_news_count = {}  # user_id → сколько прислал
user_published = {}   # user_id → сколько опубликовано
user_last_msg_time = {}  # user_id → время последнего сообщения (антиспам)
banned_users = set()     # user_id
muted_users = {}         # {user_id: until_datetime}
moderation_logs = []     # [{action, user_id, admin_id, timestamp, ...}]

# === Загрузка данных из файлов ===
def load_json(filename, default=None):
    if default is None:
        default = []
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else default
        except Exception as e:
            logging.error(f"Ошибка чтения {filename}: {e}")
            return default
    return default

def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"✅ Данные сохранены: {filename}")
    except Exception as e:
        logging.error(f"❌ Ошибка записи {filename}: {e}")

# Загружаем данные при старте
banned_users = set(load_json(BANNED_USERS_FILE))
muted_users_data = load_json(MUTED_USERS_FILE)
for item in muted_users_data:
    user_id = item["user_id"]
    until = datetime.fromisoformat(item["until"])
    if datetime.now() < until:
        muted_users[user_id] = until
    else:
        # Чистим просроченные муты
        pass

moderation_logs = load_json(LOG_FILE)

# === Список запрещённых слов ===
BAD_WORDS = {
    'бля', 'блядь', 'сука', 'сучка', 'ебан', 'ебать', 'ёб', 'хуй', 'хуя', 'хуё', 'пизд', 'пиздец', 'наху', 'наеб', 'заеб',
    'блять', 'долбаёб', 'мудак', 'идиот', 'тварь', 'выродок', 'гондон', 'чмо', 'пидор', 'педик', 'уёбище', 'заёб',
    'говно', 'дроч', 'залуп', 'пох', 'бляд', 'сукин', 'ебуч', 'ахуел', 'охуел', 'охуенный', 'блядский', 'пидорас',
    'мразь', 'скотина', 'шлюха', 'проститутка', 'еблан', 'член', 'вагина', 'жопа', 'анус', 'залупа', 'ебись', 'пошел на',
    'иди на', 'пошла на', 'нах', 'на х', 'на ху', 'на хуй', 'на хуя', 'на хуёв', 'нахер', 'на хер', 'на хуев', 'на хуёв'
}

def contains_bad_words(text):
    text = text.lower()
    return any(word in text for word in BAD_WORDS)

# === КЛАВИАТУРА ===
def get_main_menu():
    keyboard = [
        [KeyboardButton("📤 Прислать новость")],
        [KeyboardButton("ℹ️ Как отправить новость?"), KeyboardButton("📊 Мои новости")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_moderation_buttons(user_id):
    keyboard = [
        [
            InlineKeyboardButton("✅ Опубликовать", callback_data=f"publish_{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in banned_users:
        await update.message.reply_text("🚫 Вы заблокированы.")
        return
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

    # Проверка бана
    if user.id in banned_users:
        await message.reply_text("🚫 Вы заблокированы.")
        return

    # Проверка мута
    if user.id in muted_users and datetime.now() < muted_users[user.id]:
        mute_time = muted_users[user.id] - datetime.now()
        hours = int(mute_time.total_seconds() // 3600)
        await message.reply_text(f"🔇 Вы в муте. Осталось: {hours} часов.")
        return

    # Антиспам: 1 сообщение в 30 секунд
    last_time = user_last_msg_time.get(user.id)
    if last_time and (datetime.now() - last_time).seconds < 30:
        await message.reply_text("⏳ Подождите 30 секунд перед следующей отправкой.")
        return

    # Проверка на маты
    if contains_bad_words(text_content):
        muted_users[user.id] = datetime.now() + timedelta(days=3)
        save_json(MUTED_USERS_FILE, [{"user_id": uid, "until": dt.isoformat()} for uid, dt in muted_users.items()])
        await message.reply_text("🤬 Обнаружен мат. Вы получили мут на 3 дня.")
        return

    # Сохраняем время
    user_last_msg_time[user.id] = datetime.now()

    # Сохраняем сообщение
    context.bot_data[f"last_message_{user.id}"] = {
        "from_chat_id": message.chat_id,
        "message_id": message.message_id,
        "text": text_content,
        "has_photo": bool(message.photo),
        "has_video": bool(message.video)
    }

    # Проверка: фото без подписи
    if message.photo and not message.caption:
        await message.reply_text(
            "📸 Вы отправили фото, но не написали, что на нём.\n"
            "Пожалуйста, кратко опишите событие: где, что, когда?",
            reply_markup=get_main_menu()
        )
        return

    # Увеличиваем счётчик
    user_news_count[user.id] = user_news_count.get(user.id, 0) + 1

    # Отправляем админу с кнопками
    admin_msg = (
        f"📬 НОВАЯ НОВОСТЬ НА МОДЕРАЦИИ\n"
        f"👤 {user.full_name} ({'@'+user.username if user.username else 'аноним'})\n"
        f"🆔 {user.id}\n"
        f"⏰ {datetime.now().strftime('%H:%M %d.%m')}\n\n"
        f"💬 {text_content}"
    )
    try:
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=admin_msg,
            reply_markup=get_moderation_buttons(user.id)
        )
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
        logging.error(f"Ошибка отправки админу: {e}")
        await message.reply_text("⚠️ Не удалось отправить новость. Попробуйте позже.")

# === Обработка кнопок (Опубликовать / Отклонить) ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = int(data.split("_")[1])

    if data.startswith("publish_"):
        await publish_news(query, context, user_id)
    elif data.startswith("reject_"):
        await reject_news(query, context, user_id)

# === Публикация новости ===
async def publish_news(query, context, user_id):
    try:
        user_info = await context.bot.get_chat(user_id)
        user_name = user_info.full_name
        username = f"@{user_info.username}" if user_info.username else "аноним"

        last_msg = context.bot_data.get(f"last_message_{user_id}")
        if not last_msg:
            await query.edit_message_text("❌ Не удалось найти сообщение пользователя.")
            return

        # Сохраняем в news.json
        news = load_json(NEWS_FILE)
        news.insert(0, {
            "user_id": user_id,
            "name": user_name,
            "username": username,
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
            text=f"🎉 Поздравляем!\n\n"
                 f"Ваша новость опубликована:\n"
                 f"👉 https://t.me/nseloivanovo\n\n"
                 f"🌐 Сайт: https://hieronn.github.io/SIvanovoNews.github.io/"
        )

        # Обновляем статистику
        user_published[user_id] = user_published.get(user_id, 0) + 1

        # 🔹 СОХРАНЯЕМ ЛОГ
        log_entry = {
            "action": "published",
            "admin_id": query.from_user.id,
            "admin_name": query.from_user.full_name,
            "user_id": user_id,
            "user_name": user_name,
            "text_preview": last_msg["text"][:100] + ("..." if len(last_msg["text"]) > 100 else ""),
            "timestamp": datetime.now().isoformat()
        }
        moderation_logs.append(log_entry)
        save_json(LOG_FILE, moderation_logs)

        # Редактируем сообщение
        await query.edit_message_text(
            f"✅ Новость от {user_name} опубликована и добавлена на сайт."
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {e}")

# === Отклонение новости ===
async def reject_news(query, context, user_id):
    try:
        user_info = await context.bot.get_chat(user_id)
        user_name = user_info.full_name

        await context.bot.send_message(
            chat_id=user_id,
            text="Спасибо за новость! Пока мы не можем её опубликовать, но продолжайте присылать — следующая точно подойдёт! 🙏"
        )

        # 🔹 СОХРАНЯЕМ ЛОГ
        log_entry = {
            "action": "rejected",
            "admin_id": query.from_user.id,
            "admin_name": query.from_user.full_name,
            "user_id": user_id,
            "user_name": user_name,
            "text_preview": "отклонено",
            "timestamp": datetime.now().isoformat()
        }
        moderation_logs.append(log_entry)
        save_json(LOG_FILE, moderation_logs)

        await query.edit_message_text(f"✅ Отклонено: {user_name}")
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {e}")

# === Админ-команды ===

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("UsageId: `/ban <user_id>`")
        return
    try:
        user_id = int(context.args[0])
        banned_users.add(user_id)
        save_json(BANNED_USERS_FILE, list(banned_users))
        await context.bot.send_message(chat_id=user_id, text="🚫 Вы заблокированы за нарушение правил.")
        await update.message.reply_text(f"✅ Пользователь {user_id} заблокирован.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("UsageId: `/unban <user_id>`")
        return
    try:
        user_id = int(context.args[0])
        banned_users.discard(user_id)
        save_json(BANNED_USERS_FILE, list(banned_users))
        await update.message.reply_text(f"✅ Пользователь {user_id} разблокирован.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("UsageId: `/mute <user_id>`")
        return
    try:
        user_id = int(context.args[0])
        muted_users[user_id] = datetime.now() + timedelta(days=3)
        save_json(MUTED_USERS_FILE, [{"user_id": uid, "until": dt.isoformat()} for uid, dt in muted_users.items()])
        await context.bot.send_message(chat_id=user_id, text="🔇 Вы в муте на 3 дня.")
        await update.message.reply_text(f"✅ Пользователь {user_id} отправлен в мут на 3 дня.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("UsageId: `/unmute <user_id>`")
        return
    try:
        user_id = int(context.args[0])
        muted_users.pop(user_id, None)
        save_json(MUTED_USERS_FILE, [{"user_id": uid, "until": dt.isoformat()} for uid, dt in muted_users.items()])
        await update.message.reply_text(f"✅ Пользователь {user_id} размучен.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    total_users = len(user_news_count)
    total_news = sum(user_news_count.values())
    published_total = sum(user_published.values())
    muted_count = len(muted_users)
    banned_count = len(banned_users)

    msg = (
        f"🛡️ <b>Админ-панель</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📬 Новостей прислано: {total_news}\n"
        f"✅ Опубликовано: {published_total}\n"
        f"🔇 В муте: {muted_count}\n"
        f"🚫 Забанено: {banned_count}\n\n"
        f"Команды:\n"
        f"/ban <id> — забанить\n"
        f"/unban <id> — разбанить\n"
        f"/mute <id> — мут 3 дня\n"
        f"/unmute <id> — размутить\n"
        f"/logs — история модерации"
    )
    await update.message.reply_text(msg, parse_mode='HTML')

# === /logs — просмотр истории модерации ===
async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    logs = moderation_logs
    if not logs:
        await update.message.reply_text("📝 Логов модерации пока нет.")
        return

    msg = "📋 <b>Логи модерации (последние 10):</b>\n\n"
    for log in reversed(logs[-10:]):
        time = datetime.fromisoformat(log["timestamp"]).strftime("%H:%M %d.%m")
        action = "✅ Опубликовано" if log["action"] == "published" else "❌ Отклонено"
        msg += (
            f"<b>{action}</b> в <code>{time}</code>\n"
            f"👤 <b>Автор:</b> {log['user_name']} (ID: {log['user_id']})\n"
            f"👮 <b>Модератор:</b> {log['admin_name']}\n"
            f"💬 <i>{log['text_preview']}</i>\n\n"
        )

    await update.message.reply_text(msg, parse_mode='HTML')

# === ЗАПУСК БОТА ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("my_news", my_news))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("logs", logs_command))

    # Кнопки
    app.add_handler(MessageHandler(filters.Regex("^ℹ️ Как отправить новость\\?$"), help_command))
    app.add_handler(MessageHandler(filters.Regex("^📤 Прислать новость$"), lambda u, c: None))
    app.add_handler(MessageHandler(filters.Regex("^📊 Мои новости$"), my_news))

    # Контент
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(MessageHandler(filters.VIDEO, handle_message))

    # Кнопки модерации
    app.add_handler(CallbackQueryHandler(button_callback))

    print("✅ Бот запущен. Ожидаю сообщений...")
    app.run_polling()