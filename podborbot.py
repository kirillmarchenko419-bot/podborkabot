import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import sqlite3

# === КОНФИДЕНЦИАЛЬНАЯ ИНФОРМАЦИЯ ===
BOT_TOKEN = "8262805313:AAGjF33gSYGGqVzl1ElEnyzWUEU-wFakVEo"
ADMIN_CHAT_ID = 5541820448  # Ваш Telegram ID
# ===================================

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Состояния диалога
LOCATION, DISTRICT, BUDGET, ROOMS, TYPE, CONTACT = range(6)

# Актуальные цены по Краснодару
KRASNODAR_PRICES = {
    'studio': '3-4 млн ₽',
    '1_room': '4.5-6 млн ₽',
    '2_rooms': '6-8 млн ₽',
    '3_rooms': '8-12 млн ₽',
    'new_building': 'от 120 тыс ₽/м²',
    'secondary': 'от 100 тыс ₽/м²'
}

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('krasnodar_real_estate.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            location TEXT,
            district TEXT,
            budget TEXT,
            rooms TEXT,
            property_type TEXT,
            phone TEXT,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    conn.commit()
    conn.close()

# Клавиатуры
def get_location_keyboard():
    return ReplyKeyboardMarkup([
        ['🏙 Краснодар'],
        ['🌊 Краснодарский край'],
        ['🤷 Не важно']
    ], resize_keyboard=True, one_time_keyboard=True)

def get_krasnodar_district_keyboard():
    return ReplyKeyboardMarkup([
        ['Центральный', 'ФМР'],
        ['ЧМР', 'ГМР'],
        ['ЮМР', 'СХИ'],
        ['РИП', 'Пашковский'],
        ['Любой район']
    ], resize_keyboard=True, one_time_keyboard=True)

def get_krai_district_keyboard():
    return ReplyKeyboardMarkup([
        ['Сочи', 'Анапа'],
        ['Геленджик', 'Новороссийск'],
        ['Армавир', 'Ейск'],
        ['Туапсе', 'Славянск-на-Кубани'],
        ['Любой город']
    ], resize_keyboard=True, one_time_keyboard=True)

def get_budget_keyboard():
    return ReplyKeyboardMarkup([
        ['до 3 млн', '3-5 млн'],
        ['5-8 млн', '8-12 млн'],
        ['12-20 млн', '20+ млн']
    ], resize_keyboard=True, one_time_keyboard=True)

def get_rooms_keyboard():
    return ReplyKeyboardMarkup([
        ['Студия', '1'],
        ['2', '3'],
        ['4+', 'Любое']
    ], resize_keyboard=True, one_time_keyboard=True)

def get_type_keyboard():
    return ReplyKeyboardMarkup([
        ['Новостройка', 'Вторичка'],
        ['Квартира', 'Апартаменты'],
        ['Таунхаус', 'Коттедж'],
        ['Любой тип']
    ], resize_keyboard=True, one_time_keyboard=True)

def get_contact_keyboard():
    return ReplyKeyboardMarkup([[
        KeyboardButton("📱 Отправить номер", request_contact=True)
    ]], resize_keyboard=True, one_time_keyboard=True)

# Обработчик /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    # сохраняем пользователя
    conn = sqlite3.connect('krasnodar_real_estate.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
        (user_id, user.username, user.first_name, user.last_name)
    )
    conn.commit()
    conn.close()

    welcome_text = (
        "🏠 *Добро пожаловать в бот-подборщик недвижимости Краснодара и Краснодарского края!*\n\n"
        "Я помогу вам найти идеальный вариант недвижимости по вашим параметрам.\n\n"
        "*Как это работает:*\n"
        "1. Вы отвечаете на несколько вопросов\n"
        "2. Я сохраняю ваши предпочтения в базе\n"
        "3. Как только появится подходящий вариант - я сразу вам напишу!"
    )
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_location_keyboard()
    )
    return LOCATION

# Обработчик выбора локации
async def location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location_text = update.message.text
    context.user_data['location'] = location_text
    if location_text == '🏙 Краснодар':
        await update.message.reply_text(
            'Отлично! Выберите район Краснодара:',
            reply_markup=get_krasnodar_district_keyboard()
        )
        return DISTRICT
    elif location_text == '🌊 Краснодарский край':
        await update.message.reply_text(
            'Прекрасный выбор! Выберите город в Краснодарском крае:',
            reply_markup=get_krai_district_keyboard()
        )
        return DISTRICT
    else:
        # Не важно
        context.user_data['district'] = 'Любой'
        await update.message.reply_text(
            '💰 *Какой у вас бюджет?*',
            parse_mode='Markdown',
            reply_markup=get_budget_keyboard()
        )
        return BUDGET

# Обработка выбора района
async def district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['district'] = update.message.text
    await update.message.reply_text(
        '💰 *Какой у вас бюджет?*',
        parse_mode='Markdown',
        reply_markup=get_budget_keyboard()
    )
    return BUDGET

# Обработка бюджета
async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['budget'] = update.message.text
    await update.message.reply_text(
        '🏘 *Сколько комнат вам нужно?*',
        parse_mode='Markdown',
        reply_markup=get_rooms_keyboard()
    )
    return ROOMS

# Обработка количества комнат
async def rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['rooms'] = update.message.text
    await update.message.reply_text(
        '🏢 *Какой тип недвижимости вас интересует?*',
        parse_mode='Markdown',
        reply_markup=get_type_keyboard()
    )
    return TYPE

# Обработка типа недвижимости
async def property_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['property_type'] = update.message.text

    # сохраняем заявку
    user = update.message.from_user
    user_id = user.id
    user_data = context.user_data

    conn = sqlite3.connect('krasnodar_real_estate.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO requests 
        (user_id, username, first_name, last_name, location, district, budget, rooms, property_type) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        user.username,
        user.first_name,
        user.last_name,
        user_data.get('location', 'Не указано'),
        user_data.get('district', 'Не указано'),
        user_data.get('budget', 'Не указано'),
        user_data.get('rooms', 'Не указано'),
        user_data.get('property_type', 'Не указано')
    ))
    conn.commit()
    conn.close()

    # отправляем сводку
    summary = (
        "✅ *Ваша заявка сохранена!*\n"
        f"Ваши параметры:\n"
        f"👤 Пользователь: {user.first_name}\n"
        f"(@{user.username})\n"
        f"📍 Локация: {user_data.get('location')}\n"
        f"🏙 Район: {user_data.get('district')}\n"
        f"💰 Бюджет: {user_data.get('budget')}\n"
        f"🏘 Комнат: {user_data.get('rooms')}\n"
        f"🏢 Тип: {user_data.get('property_type')}\n\n"
        "Что дальше?\n"
        "1. Мы ищем подходящие варианты по вашим параметрам\n"
        "2. Как только появится подходящий — напишем вам!\n"
        "3. Для ускорения оставьте ваш телефон для связи"
    )
    await update.message.reply_text(
        summary,
        parse_mode='Markdown',
        reply_markup=get_contact_keyboard()
    )
    return CONTACT

# Обработка контакта или номера для связи
async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text
    user = update.message.from_user
    user_id = user.id

    # обновляем заявку с телефоном
    conn = sqlite3.connect('krasnodar_real_estate.db')
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE requests SET phone = ? WHERE user_id = ? AND status = "new"',
        (phone, user_id)
    )
    conn.commit()

    # получаем последнюю заявку этого пользователя
    cursor.execute('SELECT * FROM requests WHERE user_id=? AND status="new" ORDER BY created_at DESC LIMIT 1', (user_id,))
    request_data = cursor.fetchone()
    conn.close()

    if request_data:
        # request_data: (id, user_id, username, first_name, last_name, location, district, budget, rooms, property_type, phone, status, created_at)
        (id, user_id_db, username, first_name, last_name, location, district, budget, rooms, property_type, phone_db, status, created_at) = request_data
        # отправляем админу
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                f"🎯 *Новая заявка!*\n\n"
                f"👤 Пользователь: {first_name}\n"
                f"(@{username})\n"
                f"📞 Телефон: {phone}\n"
                f"📍 Локация: {location}\n"
                f"🏙 Район: {district}\n"
                f"💰 Бюджет: {budget}\n"
                f"🏘 Комнат: {rooms}\n"
                f"🏢 Тип: {property_type}"
            ),
            parse_mode='Markdown'
        )

    # финальное сообщение с ссылкой на канал
    final_text = (
        "🎉 *Заявка полностью оформлена!*\n\n"
        f"✅ *Ваш телефон:* {phone}\n\n"
        "*Мы сохранили ваш телефон. В скором времени свяжемся.*\n\n"
        "📊 *Статистика по Краснодару:*\n"
        f"• Средняя цена 1-комнатной: {KRASNODAR_PRICES['1_room']}\n"
        f"• 2-комнатной: {KRASNODAR_PRICES['2_rooms']}\n"
        f"• Новостройки: {KRASNODAR_PRICES['new_building']}\n"
        f"• Вторичка: {KRASNODAR_PRICES['secondary']}\n\n"
        "*Подписывайтесь на наш канал:*\n"
        "[Подписаться на канал](https://t.me/arenda_Krasnadar_coub)\n\n"
        "*Для нового поиска нажмите /start*"
    )
    await update.message.reply_text(
        final_text,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

# Статистика
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats_text = (
        "📊 *Актуальные цены в Краснодаре:*\n\n"
        "*Квартиры:*\n"
        f"• Студия: {KRASNODAR_PRICES['studio']}\n"
        f"• 1-комнатная: {KRASNODAR_PRICES['1_room']}\n"
        f"• 2-комнатная: {KRASNODAR_PRICES['2_rooms']}\n"
        f"• 3-комнатная: {KRASNODAR_PRICES.get('3_rooms', 'Не указано')}\n\n"
        "*Стоимость м²:*\n"
        f"• Новостройки: {KRASNODAR_PRICES['new_building']}\n"
        f"• Вторичка: {KRASNODAR_PRICES['secondary']}"
    )
    await update.message.reply_text(stats_text, parse_mode='Markdown')

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Поиск отменен. Если захотите начать снова — нажмите /start.',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# Обработчик ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Произошла ошибка: {context.error}")

def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, location)],
            DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, district)],
            BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, budget)],
            ROOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, rooms)],
            TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, property_type)],
            CONTACT: [
                MessageHandler(filters.CONTACT | filters.TEXT, contact)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("stats", stats))
    application.add_error_handler(error_handler)

    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()