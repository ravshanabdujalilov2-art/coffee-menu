from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

import os

TOKEN = os.environ.get("TOKEN")

# ID бариста
BARISTAS = [1109287655, 8274340723]  # замените на настоящие ID

# Меню
MENU = {
    "☕ Эспрессо": 150,
    "☕ Американо": 170,
    "☕ Капучино": 200,
    "☕ Латте": 220,
    "🥐 Круассан": 180,
    "🍰 Чизкейк": 250
}

# Главные кнопки
def main_keyboard():
    return ReplyKeyboardMarkup(
        [["☕ Напитки", "🥐 Еда"], ["🛒 Корзина", "📍 Адрес"], ["❌ Отменить заказ"]],
        resize_keyboard=True
    )

def category_keyboard(items):
    buttons = [[item] for item in items]
    buttons.append(["⬅ Назад"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def delivery_keyboard():
    return ReplyKeyboardMarkup([["🚴 Доставка", "🏠 Самовывоз"], ["⬅ Назад"]], resize_keyboard=True)

# Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cart"] = {}
    context.user_data["waiting_address"] = False
    context.user_data["address"] = ""
    context.user_data["delivery_type"] = ""
    await update.message.reply_text("Добро пожаловать в кофейню ☕\nВыберите категорию:", reply_markup=main_keyboard())

# Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    cart = context.user_data.setdefault("cart", {})

    drinks = [item for item in MENU if "☕" in item]
    food = [item for item in MENU if "🥐" in item or "🍰" in item]

    if text == "☕ Напитки":
        await update.message.reply_text("Выберите напиток:", reply_markup=category_keyboard(drinks))
    elif text == "🥐 Еда":
        await update.message.reply_text("Выберите еду:", reply_markup=category_keyboard(food))
    elif text in MENU:
        cart[text] = cart.get(text, 0) + 1
        await update.message.reply_text(f"{text} добавлен в корзину ✅ (всего: {cart[text]})")
    elif text == "🛒 Корзина":
        if not cart:
            await update.message.reply_text("Корзина пуста 🛒")
            return
        total = sum(MENU[item]*qty for item, qty in cart.items())
        lines = [f"{item} x{qty} — {MENU[item]*qty}₽" for item, qty in cart.items()]
        await update.message.reply_text(
            f"🛒 Ваша корзина:\n" + "\n".join(lines) + f"\n\n💰 Итого: {total}₽\n\nВыберите способ получения:",
            reply_markup=delivery_keyboard()
        )
    elif text == "🚴 Доставка":
        context.user_data["delivery_type"] = "Доставка"
        context.user_data["waiting_address"] = True
        await update.message.reply_text("✍️ Напишите адрес доставки:")
    elif text == "🏠 Самовывоз":
        context.user_data["delivery_type"] = "Самовывоз"
        context.user_data["address"] = "Самовывоз в кофейне"
        await send_order(update, context)
    elif context.user_data.get("waiting_address"):
        context.user_data["address"] = text
        context.user_data["waiting_address"] = False
        await send_order(update, context)
    elif text == "❌ Отменить заказ":
        context.user_data["cart"] = {}
        context.user_data["address"] = ""
        context.user_data["delivery_type"] = ""
        context.user_data["waiting_address"] = False
        await update.message.reply_text("❌ Ваш заказ отменён ✅", reply_markup=main_keyboard())
    elif text == "⬅ Назад":
        await update.message.reply_text("Главное меню", reply_markup=main_keyboard())
    elif text == "📍 Адрес":
        await update.message.reply_text("📍 г. Москва, ул. Примерная, 10")
    elif text == "⏰ Время работы":
        await update.message.reply_text("⏰ 08:00 — 22:00")
    else:
        await update.message.reply_text("Пожалуйста, используйте кнопки 👇", reply_markup=main_keyboard())

# Отправка заказа баристам
async def send_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cart = context.user_data.get("cart", {})
    address = context.user_data.get("address")
    delivery_type = context.user_data.get("delivery_type")
    if not cart or not address:
        await update.message.reply_text("Ошибка: корзина пуста или адрес не указан ❌")
        return

    total = sum(MENU[item]*qty for item, qty in cart.items())
    lines = [f"{item} x{qty} — {MENU[item]*qty}₽" for item, qty in cart.items()]
    order_text = "\n".join(lines)

    order_id = f"{update.message.from_user.id}_{update.message.date.timestamp()}"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Принять заказ", callback_data=f"accept_{order_id}")]])
    context.application.bot_data[order_id] = False  # заказ не принят

    message = (
        f"☕ НОВЫЙ ЗАКАЗ ({delivery_type})\n\n"
        f"👤 Клиент: @{update.message.from_user.username}\n"
        f"📍 Адрес: {address}\n\n"
        f"📋 Заказ:\n{order_text}\n💰 Сумма: {total}₽"
    )

    for barista in BARISTAS:
        await context.bot.send_message(chat_id=barista, text=message, reply_markup=keyboard)

    await update.message.reply_text(f"✅ Ваш заказ ({delivery_type}) отправлен баристам!", reply_markup=main_keyboard())

    context.user_data["cart"] = {}
    context.user_data["address"] = ""
    context.user_data["delivery_type"] = ""

# Принятие заказа баристом
async def accept_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = query.data.replace("accept_", "")
    if context.application.bot_data.get(order_id):
        await query.edit_message_text("❌ Заказ уже принят другим бариста")
        return
    context.application.bot_data[order_id] = True
    await query.edit_message_text("✅ Вы приняли заказ")
    for barista in BARISTAS:
        if barista != query.from_user.id:
            await context.bot.send_message(chat_id=barista, text="ℹ️ Заказ уже принят другим бариста")

# MAIN
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(accept_order))
    app.run_polling()

if __name__ == "__main__":
    main()
