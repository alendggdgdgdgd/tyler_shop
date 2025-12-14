import json
import os
from aiogram import Bot, Dispatcher, executor, types
from aiocryptopay import AioCryptoPay, Networks

DATA_FILE = "data.json"

# Создать файл если отсутствует
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "users": {},
            "logs": [],
            "spent": {}
        }, f, ensure_ascii=False, indent=4)


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
def add_purchase_log(user_id, item_name, price):
    data = load_data()
    user_id = str(user_id)

    if user_id not in data["users"]:
        data["users"][user_id] = {"purchases": []}

    if user_id not in data["spent"]:
        data["spent"][user_id] = 0

    data["users"][user_id]["purchases"].append({
        "item": item_name,
        "price": price
    })

    data["spent"][user_id] += price

    data["logs"].append({
        "user_id": user_id,
        "item": item_name,
        "price": price
    })

    save_data(data)


# ---------------------------------------------------------
# 🔧 НАСТРОЙКИ (ВСТАВЬ СВОЙ BOT TOKEN И CRYPTO TOKEN!)
# ---------------------------------------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_TOKEN = os.getenv("CRYPTOPAY_TOKEN")

ADMIN_ID = 5239669503

# Каналы
PUBLIC_CHANNEL = -1003457021157      # Публичный канал TylerShop
PRIVATE_CHANNEL = -1003373194409     # Приватный канал логов

# Канал обязательной подписки
REQUIRED_CHANNEL = "@tylershops"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
crypto = AioCryptoPay(token=CRYPTO_TOKEN, network=Networks.MAIN_NET)

# ---------------------------------------------------------
# 📦 ЗАГРУЗКА ТОВАРОВ
# ---------------------------------------------------------

def load_products():
    try:
        with open("products.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

products = load_products()

item_index = {}
for category, items in products.items():
    for name, item in items.items():
        item_id = item.get("id")
        if item_id:
            item_index[item_id] = {
                "category": category,
                "name": name,
                "data": item
            }

user_purchases = {}

# ---------------------------------------------------------
# 🔐 ПРОВЕРКА ПОДПИСКИ
# ---------------------------------------------------------

async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ("member", "creator", "administrator")
    except:
        return False

# ---------------------------------------------------------
# 🏁 START — ПРОВЕРКА ПОДПИСКИ + ПРИВЕТСТВИЕ
# ---------------------------------------------------------

def main_menu(user_id=None):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.add("🛒 Магазин", "🎁 Мои покупки")
    kb.add("📞 Поддержка")
    kb.add("👤 Профиль")

    # 🔥 Админ панель видна ТОЛЬКО ТЕБЕ
    if user_id == 5239669503:
        kb.add("⚙ Админ панель")

    return kb

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):

    if not await is_subscribed(msg.from_user.id):

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/tylershops"))
        kb.add(types.InlineKeyboardButton("✔ Проверить подписку", callback_data="check_sub"))

        return await msg.answer(
            "Чтобы пользоваться ботом — подпишитесь на канал Tyler Shop.\n👉 @tylershops",
            reply_markup=kb
        )

    await msg.answer(
        "💠 Tyler Shop приветствует вас!\n"
        "Качественные услуги, быстрая работа и топовый результат.\n"
        "Выберите действие: ⚡",
        reply_markup=main_menu(msg.from_user.id)
    )

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_sub(call: types.CallbackQuery):

    if not await is_subscribed(call.from_user.id):

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/tylershops"))
        kb.add(types.InlineKeyboardButton("✔ Проверить подписку", callback_data="check_sub"))

        return await call.message.answer("❗ Вы не подписаны!", reply_markup=kb)

    await call.message.answer(
        "💠 Подписка подтверждена!\nДобро пожаловать!",
        reply_markup=main_menu()
    )

# ---------------------------------------------------------
# 📞 ПОДДЕРЖКА
# ---------------------------------------------------------

@dp.message_handler(lambda m: m.text == "📞 Поддержка")
async def support(msg: types.Message):
    await msg.answer(
        "💎 Поддержка Tyler Shop\n"
        "Задай вопрос — и получишь ответ максимально быстро.\n"
        "🤝 Связь: @alenn22"
    )

# ---------------------------------------------------------
# 📂 КАТЕГОРИИ
# ---------------------------------------------------------

@dp.message_handler(lambda m: m.text == "🛒 Магазин")
async def show_categories(msg: types.Message):

    if not await is_subscribed(msg.from_user.id):
        return await msg.answer("❗ Подпишитесь, чтобы открыть магазин.")

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🌍 GTA 5", callback_data="cat:GTA 5"))
    kb.add(types.InlineKeyboardButton("🎮 SAMP", callback_data="cat:SAMP"))

    await msg.answer("📂 Выберите категорию:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("cat:"))
async def show_products(call: types.CallbackQuery):

    category = call.data.split(":")[1]
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅ Назад", callback_data="back_shop"))

    for name, item in products[category].items():
        kb.add(types.InlineKeyboardButton(name, callback_data=f"item:{item['id']}"))

    await call.message.edit_text(
        f"📦 Категория: <b>{category}</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )
# ---------------------------------------------------------
# 🖼 СТРАНИЦА ТОВАРА
# ---------------------------------------------------------

@dp.callback_query_handler(lambda c: c.data.startswith("item:"))
async def item_page(call: types.CallbackQuery):

    item_id = call.data.split(":")[1]

    if item_id not in item_index:
        return await call.answer("Ошибка: товар не найден!")

    item = item_index[item_id]
    name = item["name"]
    data = item["data"]
    category = item["category"]

    # Пытаемся отправить картинку товара
    try:
        photo = types.InputFile(f"{item_id}.jpg")
        await call.message.answer_photo(photo, caption=f"<b>{name}</b>", parse_mode="HTML")
    except:
        await call.message.answer(f"<b>{name}</b>", parse_mode="HTML")

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 Купить", callback_data=f"buy:{item_id}"))
    kb.add(types.InlineKeyboardButton("⬅ Назад", callback_data=f"back_products:{category}"))

    text = f"{data['desc']}\n\n💰 Цена: <b>{data['price']} TON</b>"

    await call.message.answer(text, reply_markup=kb, parse_mode="HTML")

# ---------------------------------------------------------
# ↩ НАЗАД В КАТЕГОРИЮ
# ---------------------------------------------------------

@dp.callback_query_handler(lambda c: c.data.startswith("back_products:"))
async def back_to_products(call):

    category = call.data.split(":")[1]

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅ Назад", callback_data="back_shop"))

    for name, item in products[category].items():
        kb.add(types.InlineKeyboardButton(name, callback_data=f"item:{item['id']}"))

    await call.message.edit_text(
        f"📂 Категория: <b>{category}</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.callback_query_handler(lambda c: c.data == "back_shop")
async def back_shop(call):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🌍 GTA 5", callback_data="cat:GTA 5"))
    kb.add(types.InlineKeyboardButton("🎮 SAMP", callback_data="cat:SAMP"))
    await call.message.edit_text("📂 Выберите категорию:", reply_markup=kb)

# ---------------------------------------------------------
# 💳 ОПЛАТА
# ---------------------------------------------------------

@dp.callback_query_handler(lambda c: c.data.startswith("buy:"))
async def buy_item(call: types.CallbackQuery):

    item_id = call.data.split(":")[1]
    item = item_index[item_id]

    invoice = await crypto.create_invoice(
        asset="TON",
        amount=item["data"]["price"]
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 Оплатить", url=invoice.bot_invoice_url))
    kb.add(types.InlineKeyboardButton("🔄 Проверить оплату",
                                      callback_data=f"check:{invoice.invoice_id}:{item_id}"))

    await call.message.answer(
        "💳 Счёт создан! Оплатите и нажмите «Проверить оплату».",
        reply_markup=kb
    )

# ---------------------------------------------------------
# 🔍 ПРОВЕРКА ОПЛАТЫ
# ---------------------------------------------------------

@dp.callback_query_handler(lambda c: c.data.startswith("check:"))
async def check_payment(call: types.CallbackQuery):
    _, invoice_id, item_id = call.data.split(":")
    invoice = await crypto.get_invoices(invoice_ids=int(invoice_id))

    if invoice.items[0].status != "paid":
        return await call.message.answer("❗ Оплата ещё не прошла. Попробуйте позже.")

    # Найти товар
    item = item_index[item_id]
    data = item["data"]
    name = item["name"]

    # 🔥 ДОБАВЛЕНИЕ В ЛОГ
    add_purchase_log(
        user_id=call.from_user.id,
        item_name=name,
        price=data["price"]
    )

    # Выдача товара
    await call.message.answer(data["content"])
    await call.message.answer("🎉 Покупка успешна!")

    # ---------------------------------------------------------
    # 📢 УВЕДОМЛЕНИЕ В ПУБЛИЧНЫЙ КАНАЛ
    # ---------------------------------------------------------

    msg_public = (
        f"🎉 <b>НОВАЯ ПОКУПКА</b>\n\n"
        f"👤 Покупатель: <a href=\"tg://user?id={call.from_user.id}\">{call.from_user.first_name}</a>\n"
        f"🛒 Товар: <b>{name}</b>\n"
        f"💰 Цена: <b>{data['price']} TON</b>\n"
        f"📦 ID товара: <code>{item_id}</code>"
    )

    await bot.send_message(PUBLIC_CHANNEL, msg_public, parse_mode="HTML")

    # ---------------------------------------------------------
    # 📥 ЛОГ В ПРИВАТНЫЙ КАНАЛ
    # ---------------------------------------------------------

    msg_private = (
        f"📊 ЛОГ ПОКУПКИ\n\n"
        f"User ID: {call.from_user.id}\n"
        f"Имя: {call.from_user.first_name}\n"
        f"Товар: {name}\n"
        f"Цена: {price} TON\n"
        f"ID товара: {item_id}"
    )

    await bot.send_message(PRIVATE_CHANNEL, msg_private)

    # ---------------------------------------------------------
    # 🔔 УВЕДОМЛЕНИЕ АДМИНУ
    # ---------------------------------------------------------

    await bot.send_message(
        ADMIN_ID,
        f"🔔 Покупка: {name}\nПользователь: {call.from_user.first_name} ({call.from_user.id})"
    )

# ---------------------------------------------------------
# 🎁 МОИ ПОКУПКИ
# ---------------------------------------------------------

@dp.message_handler(lambda m: m.text == "🎁 Мои покупки")
async def my_purchases(msg: types.Message):

    uid = msg.from_user.id

    if uid not in user_purchases or len(user_purchases[uid]) == 0:
        return await msg.answer("💎 У вас пока нет покупок. Но это легко исправить — загляните в магазин! 🛒✨")

    text = "🎁 <b>Ваши покупки:</b>\n\n"
    total = 0

    for p in user_purchases[uid]:
        text += f"• <b>{p['name']}</b> — {p['price']} TON\n"
        total += p["price"]

    text += f"\n💰 Итоговая сумма: <b>{total} TON</b>"

    await msg.answer(text, parse_mode="HTML")
# ---------------------------------------------------------
# 👤 ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ
# ---------------------------------------------------------

def get_rank(total_purchases):
    if total_purchases >= 20:
        return "💎 Diamond"
    elif total_purchases >= 8:
        return "🥇 Gold"
    elif total_purchases >= 3:
        return "🥈 Silver"
    else:
        return "🥉 Bronze"

@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def profile(msg: types.Message):

    uid = msg.from_user.id
    name = msg.from_user.first_name

    # Если нет покупок
    if uid not in user_purchases or len(user_purchases[uid]) == 0:
        return await msg.answer(
            f"👤 Профиль пользователя: <b>{name}</b>\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"🎁 Покупок: <b>0</b>\n"
            f"💰 Сумма: <b>0 TON</b>\n"
            f"⭐ Статус: 🥉 Bronze\n"
            f"🎉 Бонусы: отсутствуют\n\n"
            "💎 У вас пока нет покупок. Но это легко исправить — загляните в магазин! 🛒✨",
            parse_mode="HTML"
        )

    purchases = user_purchases[uid]
    total = sum([p["price"] for p in purchases])
    rank = get_rank(len(purchases))

    last_items = "\n".join([f"• {p['name']} ({p['price']} TON)" for p in purchases[-5:]])

    await msg.answer(
        f"👤 <b>Профиль пользователя: {name}</b>\n\n"
        f"🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"🎁 <b>Количество покупок:</b> {len(purchases)}\n"
        f"💰 <b>Сумма покупок:</b> {total} TON\n"
        f"⭐ <b>Уровень аккаунта:</b> {rank}\n"
        f"🎉 <b>Персональные бонусы:</b> доступны!\n\n"
        f"📦 <b>Последние покупки:</b>\n"
        f"{last_items}",
        parse_mode="HTML"
    )

# ---------------------------------------------------------
# ⚙ АДМИН-ПАНЕЛЬ (ВИДНА ТОЛЬКО ТЕБЕ)
# ---------------------------------------------------------

ADMIN_ID = 5239669503  # ← ТВОЙ ID, НИКТО кроме тебя доступ не получит


# ---------------------------------------------------------
# КНОПКА «⚙ Админ панель» в главном меню
# ---------------------------------------------------------

@dp.message_handler(lambda m: m.text == "⚙ Админ панель")
async def admin_panel(msg: types.Message):

    # Проверка — только ты можешь видеть панель
    if msg.from_user.id != ADMIN_ID:
        return await msg.answer("⛔ У вас нет доступа.")

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📦 Товары", callback_data="admin_items"))
    kb.add(types.InlineKeyboardButton("💰 Доход", callback_data="admin_income"))
    kb.add(types.InlineKeyboardButton("👥 Пользователи", callback_data="admin_users"))
    kb.add(types.InlineKeyboardButton("🧾 Логи", callback_data="admin_logs"))

    await msg.answer(
        "<b>⚙ Админ-панель</b>\nВыберите действие:",
        reply_markup=kb,
        parse_mode="HTML"
    )


# ---------------------------------------------------------
# 📦 ТОВАРЫ — список всех товаров
# ---------------------------------------------------------

@dp.callback_query_handler(lambda c: c.data == "admin_items")
async def admin_show_items(call: types.CallbackQuery):

    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Нет доступа.", show_alert=True)

    text = "📦 <b>Все товары магазина:</b>\n\n"

    for category, items in products.items():
        text += f"<b>📂 {category}</b>\n"
        for name, item in items.items():
            text += f"— {name} | {item['price']} TON | ID: <code>{item['id']}</code>\n"
        text += "\n"

    await call.message.answer(text, parse_mode="HTML")


# ---------------------------------------------------------
# 💰 ДОХОД — общая сумма TON
# ---------------------------------------------------------

@dp.callback_query_handler(lambda c: c.data == "admin_income")
async def admin_income(call: types.CallbackQuery):

    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Нет доступа.", show_alert=True)

    total_income = 0
    total_sales = 0

    for uid in user_purchases:
        for item in user_purchases[uid]:
            total_income += item["price"]
            total_sales += 1

    await call.message.answer(
        f"💰 <b>Доход магазина</b>\n\n"
        f"📦 Продаж: <b>{total_sales}</b>\n"
        f"💳 Общий доход: <b>{total_income} TON</b>",
        parse_mode="HTML"
    )


# ---------------------------------------------------------
# 👥 ПОЛЬЗОВАТЕЛИ — список покупателей
# ---------------------------------------------------------

@dp.callback_query_handler(lambda c: c.data == "admin_users")
async def admin_users(call: types.CallbackQuery):

    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Нет доступа.", show_alert=True)

    text = "👥 <b>Пользователи с покупками:</b>\n\n"

    if len(user_purchases) == 0:
        return await call.message.answer("❗ Пока никто не купил товар.")

    for uid in user_purchases:
        text += (
            f"— <a href=\"tg://user?id={uid}\">{uid}</a> | "
            f"Покупок: <b>{len(user_purchases[uid])}</b>\n"
        )

    await call.message.answer(text, parse_mode="HTML")


# ---------------------------------------------------------
# 🧾 ЛОГИ — последние покупки
# ---------------------------------------------------------

@dp.callback_query_handler(lambda c: c.data == "admin_logs")
async def admin_logs(call: types.CallbackQuery):

    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Нет доступа.", show_alert=True)

    logs = []

    for uid in user_purchases:
        for item in user_purchases[uid]:
            logs.append(
                f"👤 <a href=\"tg://user?id={uid}\">{uid}</a> — "
                f"{item['name']} ({item['price']} TON)"
            )

    logs = logs[-20:]  # последние 20

    if not logs:
        return await call.message.answer("🧾 Логи пусты.", parse_mode="HTML")

    text = "🧾 <b>Последние покупки:</b>\n\n" + "\n".join(logs)

    await call.message.answer(text, parse_mode="HTML")


# ---------------------------------------------------------
# ⬅ НАЗАД В МЕНЮ
# ---------------------------------------------------------

@dp.message_handler(lambda m: m.text == "⬅ Назад в меню")
async def back_to_menu(msg: types.Message):
    await msg.answer("Меню открыто ⚡", reply_markup=main_menu())

# ---------------------------------------------------------
# 🚀 СТАРТ БОТА
# ---------------------------------------------------------

if __name__ == "__main__":
    print("Бот запущен!")
    executor.start_polling(dp, skip_updates=True)


