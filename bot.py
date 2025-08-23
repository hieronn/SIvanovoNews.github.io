import json
import os
from datetime import datetime
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import subprocess
import os

# Настройки GitHub
GITHUB_REPO = "https://github.com/hieronn/SIvanovoNews.github.io.git"
LOCAL_REPO_PATH = "./site_repo"  # Локальная папка для клонирования
GITHUB_TOKEN = "ghp_..."  # ⚠️ Замени на твой токен (Settings → Developer settings → Personal access tokens)

def prepare_github_repo():
    """Клонирует или обновляет репозиторий"""
    if not os.path.exists(LOCAL_REPO_PATH):
        os.makedirs(LOCAL_REPO_PATH)
        subprocess.run(["git", "clone", f"https://{GITHUB_TOKEN}@github.com/hieronn/SIvanovoNews.github.io.git", "."], cwd=LOCAL_REPO_PATH)
    else:
        subprocess.run(["git", "pull"], cwd=LOCAL_REPO_PATH)

def copy_files_to_repo():
    """Копируем нужные файлы в локальный репозиторий"""
    import shutil
    for file in ["news.json", "reviews.json", "index.html", "otzyvy.html"]:
        if os.path.exists(file):
            shutil.copy(file, os.path.join(LOCAL_REPO_PATH, file))

async def push_to_github():
    """Автоматически пушит изменения в GitHub"""
    try:
        prepare_github_repo()
        copy_files_to_repo()

        # Делаем коммит
        subprocess.run(["git", "add", "."], cwd=LOCAL_REPO_PATH)
        subprocess.run(["git", "commit", "-m", "🔄 Автообновление: новость/отзыв опубликован"], cwd=LOCAL_REPO_PATH)
        subprocess.run(["git", "push"], cwd=LOCAL_REPO_PATH)

        print("✅ Файлы успешно отправлены в GitHub")
    except Exception as e:
        print(f"❌ Ошибка автопуша: {e}")

# === НАСТРОЙКИ ===
BOT_TOKEN = "8299964233:AAFa4I3gFSjWxodUWQMx8j5W0yWkPRRhx6M"  # ⚠️ Убедись, что токен правильный
ADMIN_USER_ID = 5207981986  # ⚠️ Твой ID
CHANNEL_ID = "-1002995985111"  # ID канала

# Файлы для хранения
NEWS_FILE = "news.json"
REVIEWS_FILE = "reviews.json"

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# === ХРАНЕНИЕ В ПАМЯТИ ===
user_news_count = {}
user_published = {}

# === Загрузка и сохранение ===
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# === КЛАВИАТУРА ===
def get_main_menu():
    keyboard = [
        [KeyboardButton("📤 Прислать новость")],
        [KeyboardButton("📝 Оставить отзыв")],
        [KeyboardButton("ℹ️ Как отправить новость?"), KeyboardButton("📊 Мои новости")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# === ОБРАБОТЧИКИ ===

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        "Вы можете:\n"
        "📬 Прислать новость из села\n"
        "💬 Оставить отзыв о жизни в Иваново\n\n"
        "Мы рассмотрим и, возможно, опубликуем на сайте!"
    )
    await update.message.reply_text(text, reply_markup=get_main_menu())

# /help
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

# /my_news — статистика пользователя
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

# Приём новостей и отзывов
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    text_content = message.text or message.caption or "[без текста]"

    # === 🔥 СОХРАНЯЕМ СООБЩЕНИЕ ДО ОТПРАВКИ АДМИНУ ===
    context.bot_data[f"last_message_{user.id}"] = {
        "from_chat_id": message.chat_id,
        "message_id": message.message_id,
        "text": text_content,
        "has_photo": bool(message.photo),
        "has_video": bool(message.video)
    }
    # ================================================

    # Обработка: "Оставить отзыв"
    if text_content == "📝 Оставить отзыв":
        await message.reply_text(
            "💬 Отлично!\n\n"
            "Напишите ваш отзыв о жизни в селе Иваново — что нравится, что можно улучшить.\n\n"
            "📌 Можно анонимно.",
            reply_markup=get_main_menu()
        )
        context.user_data['awaiting_review'] = True
        return

    # Если идёт приём отзыва
    if context.user_data.get('awaiting_review'):
        context.user_data['awaiting_review'] = False

        review_msg = (
            f"📬 НОВЫЙ ОТЗЫВ НА МОДЕРАЦИИ\n"
            f"👤 {user.full_name} ({'@'+user.username if user.username else 'аноним'})\n"
            f"🆔 {user.id}\n"
            f"⏰ {datetime.now().strftime('%H:%M %d.%m')}\n\n"
            f"💬 {text_content}"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_USER_ID, text=review_msg)
            await message.reply_text(
                "✅ Спасибо за отзыв!\n\n"
                "Мы его рассмотрим. Если подойдёт — добавим на сайт и уведомим вас 💌",
                reply_markup=get_main_menu()
            )
        except Exception as e:
            logging.error(f"Ошибка отправки отзыва: {e}")
            await message.reply_text("⚠️ Не удалось отправить отзыв. Попробуйте позже.")
        return

    # Обработка фото без текста
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
        await message.reply_text("⚠️ Ошибка при отправке. Попробуйте позже.")

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
        username = f"@{user_info.username}" if user_info.username else "аноним"

        last_msg = context.bot_data.get(f"last_message_{user_id}")
        if not last_msg:
            await update.message.reply_text("❌ Не удалось найти сообщение пользователя.")
            return

        text = last_msg["text"]
        is_review = any(word in text.lower() for word in ["отзыв", "нравится", "можно улучшить", "предложение", "мнение"])

        now = datetime.now().strftime("%d.%m.%Y")
        item = {
            "user_id": user_id,
            "name": user_name,
            "username": username,
            "text": text,
            "date": now,
            "timestamp": datetime.now().isoformat()
        }

        html_block = ""  # Готовый HTML-код

        if is_review:
            # Это отзыв
            reviews = load_json(REVIEWS_FILE)
            reviews.insert(0, item)
            save_json(REVIEWS_FILE, reviews)

            # Отправляем в канал
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"💬 <b>Новый отзыв от {user_name}:</b>\n\n“{text}”",
                parse_mode='HTML'
            )

            # 🔥 ГОТОВЫЙ HTML-БЛОК ДЛЯ ОТЗЫВА
            html_block = f'''
<!-- Отзыв жителя -->
<div class="col-12 mb-4">
  <div class="review-card" style="transition-delay: 0ms;">
    <div class="p-4">
      <div class="review-header">
        <i class="fas fa-user-circle review-avatar"></i>
        <div>
          <p class="review-name">{user_name}</p>
          <p class="review-username">{username}</p>
        </div>
      </div>
      <p class="review-text">{text}</p>
      <div class="review-date">
        <i class="fas fa-calendar-alt"></i>
        <span>{now}</span>
      </div>
    </div>
  </div>
</div>
            '''

        else:
            # Это новость
            news = load_json(NEWS_FILE)
            news.insert(0, item)
            save_json(NEWS_FILE, news)

            await context.bot.forward_message(
                chat_id=CHANNEL_ID,
                from_chat_id=last_msg["from_chat_id"],
                message_id=last_msg["message_id"]
            )

            # 🔥 ГОТОВЫЙ HTML-БЛОК ДЛЯ НОВОСТИ
            html_block = f'''
<!-- Карточка новости -->
<div class="col-md-6 col-lg-4 animate-on-scroll">
  <div class="news-card">
    <div class="p-4">
      <span class="date-badge" style="background: #4CAF50;">{now}</span>
      <h5>{text[:60]}{"..." if len(text) > 60 else ""}</h5>
      <p class="text-muted">Автор: {user_name}</p>
      <a href="https://t.me/nseloivanovo" target="_blank" class="btn btn-sm btn-outline-primary">
        Подробнее
      </a>
    </div>
  </div>
</div>
            '''

        # ✅ Отправляем HTML-код админу
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"✅ <b>Готовый HTML-блок для сайта:</b>\n\n"
                 f"<pre>{html_block}</pre>\n\n"
                 f"<i>Скопируйте и вставьте в index.html или otzyvy.html</i>",
            parse_mode='HTML'
        )

        # ✅ Отправляем уведомление автору
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎉 Спасибо!\n\n"
                 f"Ваш отзыв добавлен на сайт:\n👉 https://hieronn.github.io/SIvanovoNews.github.io/otzyvy.html\n\n"
                 f"Спасибо за участие! ❤️"
        )

        # ✅ Автопуш в GitHub
        await push_to_github()

        await update.message.reply_text(f"✅ Отзыв от {user_name} опубликован и отправлен на сайт.")
        user_published[user_id] = user_published.get(user_id, 0) + 1

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# /reject <user_id> — отклонить
async def rejected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("UsageId: `/reject <user_id>`")
        return

    try:
        user_id = int(context.args[0])
        await context.bot.send_message(
            chat_id=user_id,
            text="Спасибо за новость! Пока мы не можем её опубликовать, но продолжайте присылать — следующая точно подойдёт! 🙏"
        )
        await update.message.reply_text(f"✅ Отклонено: {user_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# /stats — статистика
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    total_users = len(user_news_count)
    total_news = sum(user_news_count.values())
    published_total = sum(user_published.values())

    top_users = sorted(user_news_count.items(), key=lambda x: x[1], reverse=True)[:3]

    msg = (
        f"📊 Статистика бота:\n"
        f"👥 Авторов: {total_users}\n"
        f"📬 Всего новостей: {total_news}\n"
        f"✅ Опубликовано: {published_total}\n\n"
        f"🏆 Топ-3 активных:\n"
    )
    for i, (uid, cnt) in enumerate(top_users, 1):
        try:
            user_info = await context.bot.get_chat(uid)
            name = user_info.first_name
            username = f" @{user_info.username}" if user_info.username else ""
            msg += f"{i}. {name}{username} — {cnt} новостей\n"
        except:
            msg += f"{i}. Пользователь {uid} — {cnt} новостей\n"

    await update.message.reply_text(msg)

# /rss — последние посты из канала
async def rss_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        import feedparser
        feed_url = f"https://rss.telega.link/channel.php?channel=nseloivanovo"
        feed = feedparser.parse(feed_url)
        if feed.entries:
            msg = "🗞 <b>Последние новости из канала:</b>\n\n"
            for i, entry in enumerate(feed.entries[:3]):
                title = entry.title or "(без заголовка)"
                link = entry.link
                msg += f"{i+1}. <a href='{link}'>{title}</a>\n"
            msg += f"\n🔗 Полная лента: {feed_url}"
        else:
            msg = "📭 Нет новостей в канале."
        await update.message.reply_text(msg, parse_mode='HTML', disable_web_page_preview=False)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка RSS: {e}")

# === ЗАПУСК БОТА ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("publish", published))
    app.add_handler(CommandHandler("reject", rejected))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("rss", rss_command))

    # Кнопки
    app.add_handler(MessageHandler(filters.Regex("^ℹ️ Как отправить новость\\?$"), help_command))
    app.add_handler(MessageHandler(filters.Regex("^📤 Прислать новость$"), lambda u, c: None))
    app.add_handler(MessageHandler(filters.Regex("^📊 Мои новости$"), my_news))
    app.add_handler(MessageHandler(filters.Regex("^📝 Оставить отзыв$"), lambda u, c: None))

    # Текст, фото, видео
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(MessageHandler(filters.VIDEO, handle_message))

    print("🤖 Бот запущен... Ждём новостей и отзывов от жителей!")
    app.run_polling()