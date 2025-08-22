# import logging
# import json
# import os
# from datetime import datetime

# # === БИБЛИОТЕКИ ДЛЯ GOOGLE SHEETS И RSS ===
# import gspread
# from google.oauth2.service_account import Credentials
# import feedparser

# from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
# from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# # === НАСТРОЙКИ ===
# BOT_TOKEN = "78350931780:AAFJMjDn2De1bV0pfQAtXUS4pkWIc_giEzQ"
# ADMIN_USER_ID = 5207981986
# CHANNEL_USERNAME = "@nseloivanovo"

# # Настройка Google Sheets
# GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1m1uIOOlxoaPvgeU5PcTBs_qugJkNWhcapuNpMB3gEVA"
# SERVICE_ACCOUNT_FILE = "service_account.json"  # 🔴 Теперь совпадает с именем файла

# # Авторизация в Google
# def authorize_google():
#     SCOPES = [
#         "https://www.googleapis.com/auth/spreadsheets",
#         "https://www.googleapis.com/auth/drive"
#     ]
#     creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
#     client = gspread.authorize(creds)
#     return client.open_by_url(GOOGLE_SHEET_URL)

# # Подключаемся к таблице
# try:
#     gc = authorize_google()
#     sheet_users = gc.worksheet("Пользователи")
#     sheet_news = gc.worksheet("Новости")
#     sheet_moderation = gc.worksheet("Модерация")
#     print("✅ Успешно подключились к Google Таблице")
# except Exception as e:
#     print(f"❌ Ошибка подключения к Google Таблице: {e}")
#     exit()

# # === КЛАВИАТУРА ===
# def get_main_menu():
#     keyboard = [
#         [KeyboardButton("📤 Прислать новость")],
#         [KeyboardButton("ℹ️ Как отправить новость?"), KeyboardButton("📊 Мои новости")]
#     ]
#     return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# # === ОБРАБОТЧИКИ ===
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user = update.effective_user
#     text = (
#         f"👋 Здравствуйте, {user.first_name}!\n\n"
#         "Вы можете прислать новость из села Иваново — событие, фото, замечание.\n"
#         "Мы рассмотрим и, возможно, опубликуем на сайте!\n\n"
#         "📌 Нажмите кнопку ниже или просто напишите сообщение."
#     )
#     await update.message.reply_text(text, reply_markup=get_main_menu())

# async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     help_text = (
#         "📝 <b>Как прислать новость:</b>\n\n"
#         "1. Напишите: <b>что произошло</b>\n"
#         "2. Укажите: <b>где и когда</b>\n"
#         "3. Прикрепите <b>фото или видео</b> (по желанию)\n\n"
#         "✅ Пример:\n"
#         "<i>Сегодня убрали мусор у школы. Было 10 участников. Фото прилагаю.</i>"
#     )
#     await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=get_main_menu())

# async def my_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user = update.effective_user
#     try:
#         records = sheet_moderation.findall(str(user.id), in_column=5)
#         count = len(records)
#         published = len([r for r in records if sheet_moderation.cell(r.row, 6).value == "опубликовано"])
#         await update.message.reply_text(
#             f"📬 Вы прислали <b>{count}</b> новостей\n"
#             f"✅ Опубликовано: <b>{published}</b>\n"
#             f"⏳ На модерации: <b>{count - published}</b>",
#             parse_mode='HTML',
#             reply_markup=get_main_menu()
#         )
#     except Exception as e:
#         await update.message.reply_text("⚠️ Не удалось загрузить статистику. Попробуйте позже.")

# async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user = update.effective_user
#     message = update.message

#     if message.photo and not message.caption:
#         await message.reply_text(
#             "📸 Вы отправили фото, но не написали, что на нём.\n"
#             "Пожалуйста, кратко опишите событие: где, что, когда?",
#             reply_markup=get_main_menu()
#         )
#         return

#     text_content = message.text or message.caption or "[без текста]"

#     try:
#         sheet_moderation.append_row([
#             datetime.now().strftime("%Y-%m-%d %H:%M"),
#             text_content,
#             "на модерации",
#             f"@{user.username}" if user.username else "аноним",
#             user.id,
#             ""
#         ])

#         admin_msg = (
#             f"📬 НОВАЯ НОВОСТЬ НА МОДЕРАЦИЮ\n"
#             f"👤 {user.full_name} ({'@'+user.username if user.username else 'нет юзернейма'})\n"
#             f"🆔 {user.id}\n\n"
#             f"💬 {text_content}"
#         )
#         await context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_msg)

#         if message.photo:
#             photo_file = await message.photo[-1].get_file()
#             await context.bot.send_photo(chat_id=ADMIN_USER_ID, photo=photo_file.file_id)
#         if message.video:
#             video_file = await message.video.get_file()
#             await context.bot.send_video(chat_id=ADMIN_USER_ID, video=video_file.file_id)

#         await message.reply_text(
#             "✅ Спасибо за новость!\n\n"
#             "Мы её проверим. Если подойдёт — опубликуем на сайте, и вы получите уведомление 💌",
#             reply_markup=get_main_menu()
#         )
#     except Exception as e:
#         logging.error(f"Ошибка: {e}")
#         await message.reply_text("⚠️ Ошибка при отправке. Попробуйте позже.")

# async def published(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     if update.effective_user.id != ADMIN_USER_ID:
#         return
#     if len(context.args) != 1:
#         await update.message.reply_text("UsageId: `/опубликовано 123456`")
#         return
#     try:
#         user_id = int(context.args[0])
#         cell = sheet_moderation.find(str(user_id), in_column=5)
#         if cell:
#             sheet_moderation.update_cell(cell.row, 6, "опубликовано")
#         await context.bot.send_message(
#             chat_id=user_id,
#             text="🎉 Поздравляем!\n\nВаша новость опубликована на сайте:\n👉 https://ivanovo-news.ru  \n\nСпасибо, что делитесь жизнью села! ❤️"
#         )
#         await update.message.reply_text(f"✅ Новость пользователя {user_id} отмечена как опубликованная.")
#     except Exception as e:
#         await update.message.reply_text(f"❌ Ошибка: {e}")

# async def rejected(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     if update.effective_user.id != ADMIN_USER_ID:
#         return
#     if len(context.args) != 1:
#         await update.message.reply_text("UsageId: `/отклонено 123456`")
#         return
#     try:
#         user_id = int(context.args[0])
#         cell = sheet_moderation.find(str(user_id), in_column=5)
#         if cell:
#             sheet_moderation.update_cell(cell.row, 6, "отклонено")
#         await context.bot.send_message(
#             chat_id=user_id,
#             text="Спасибо за новость! Пока мы не можем её опубликовать, но продолжайте присылать — следующая точно подойдёт! 🙏"
#         )
#         await update.message.reply_text(f"✅ Отклонено: {user_id}")
#     except Exception as e:
#         await update.message.reply_text(f"❌ Ошибка: {e}")

# async def rss_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     feed_url = f"https://rss.telega.link/channel.php?channel={CHANNEL_USERNAME.lstrip('@')}"
#     feed = feedparser.parse(feed_url)
#     if feed.entries:
#         msg = "🗞 <b>Последние новости из канала:</b>\n\n"
#         for i, entry in enumerate(feed.entries[:3]):
#             title = entry.title or "(без заголовка)"
#             link = entry.link
#             msg += f"{i+1}. <a href='{link}'>{title}</a>\n"
#         msg += f"\n🔗 Полная лента: {feed_url}"
#     else:
#         msg = "📭 Нет новостей в канале."
#     await update.message.reply_text(msg, parse_mode='HTML', disable_web_page_preview=False)

# async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     if update.effective_user.id != ADMIN_USER_ID:
#         return
#     try:
#         records = sheet_moderation.get_all_records()
#         total_news = len(records)
#         published = len([r for r in records if r.get('status') == 'опубликовано'])
#         users = {}
#         for r in records:
#             uid = r['user_id']
#             users[uid] = users.get(uid, 0) + 1
#         top_users = sorted(users.items(), key=lambda x: x[1], reverse=True)[:3]
#         msg = (
#             f"📊 Статистика:\n"
#             f"📬 Всего новостей: {total_news}\n"
#             f"✅ Опубликовано: {published}\n\n"
#             f"🏆 Топ-3 автора:\n"
#         )
#         for i, (uid, cnt) in enumerate(top_users, 1):
#             msg += f"{i}. Пользователь {uid} — {cnt} новостей\n"
#         await update.message.reply_text(msg)
#     except Exception as e:
#         await update.message.reply_text(f"❌ Ошибка при сборе статистики: {e}")

# # === ЗАПУСК ===
# if __name__ == '__main__':
#     app = ApplicationBuilder().token(BOT_TOKEN).build()
#     app.add_handler(CommandHandler("start", start))
#     app.add_handler(CommandHandler("help", help_command))
#     app.add_handler(CommandHandler("опубликовано", published))
#     app.add_handler(CommandHandler("отклонено", rejected))
#     app.add_handler(CommandHandler("статистика", stats))
#     app.add_handler(CommandHandler("rss", rss_command))
#     app.add_handler(MessageHandler(filters.Regex("^ℹ️ Как отправить новость\\?$"), help_command))
#     app.add_handler(MessageHandler(filters.Regex("^📤 Прислать новость$"), lambda u, c: None))
#     app.add_handler(MessageHandler(filters.Regex("^📊 Мои новости$"), my_news))
#     app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, handle_message))

#     print("🤖 Бот запущен... Ждём новостей от жителей!")
#     app.run_polling()
import json
import os

REVIEWS_FILE = "reviews.json"

# Загрузка отзывов
def load_reviews():
    if os.path.exists(REVIEWS_FILE):
        with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Сохранение отзывов
def save_reviews(reviews):
    with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)
import logging
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# === НАСТРОЙКИ ===
BOT_TOKEN = "8299964233:AAFa4I3gFSjWxodUWQMx8j5W0yWkPRRhx6M"  # ⚠️ Убедись, что токен правильный
ADMIN_USER_ID = 5207981986  # ⚠️ Твой ID
CHANNEL_USERNAME = "nseloivanovo"  # ⚠️ Только username, без пробелов и https://

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# === ХРАНЕНИЕ В ПАМЯТИ (не сохраняется после перезапуска) ===
user_news_count = {}  # user_id → количество новостей
user_published = {}   # user_id → сколько опубликовано

# === КЛАВИАТУРА ===
def get_main_menu():
    keyboard = [
        [KeyboardButton("📤 Прислать новость")],
        [KeyboardButton("📝 Оставить отзыв")],  # Новая кнопка
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

# Приём новостей
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    text_content = message.text or message.caption or "[без текста]"

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

        # Отправляем отзыв админу
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

        # Получаем данные пользователя
        user_info = await context.bot.get_chat(user_id)
        user_name = user_info.full_name
        username = f"@{user_info.username}" if user_info.username else "аноним"

        # Формируем текст отзыва (пример)
        review_text = "Благодарим за участие в жизни села!"  # Можно улучшить — см. ниже

        # Загружаем существующие отзывы
        reviews = load_reviews()

        # Добавляем новый отзыв
        new_review = {
            "user_id": user_id,
            "name": user_name,
            "username": username,
            "text": review_text,
            "date": datetime.now().strftime("%d.%m.%Y")
        }
        reviews.append(new_review)
        save_reviews(reviews)

        # Уведомляем автора
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎉 Спасибо!\n\nВаш отзыв добавлен на сайт:\n👉 https://ivanovo-news.ru/otzyvy.html\n\nСпасибо, что делитесь мнением! ❤️"
        )
        await update.message.reply_text(f"✅ Отзыв от {user_name} добавлен в reviews.json и появится на сайте.")
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
        feed_url = f"https://rss.telega.link/channel.php?channel={CHANNEL_USERNAME}"
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

#     /publish 5207981986
# Публикует новость в канал и уведомляет автора
# /reject 5207981986
# Отклоняет, отправляет вежливый ответ
# /stats
# Показывает статистику по авторам
# /rss
# Показывает последние посты из канала