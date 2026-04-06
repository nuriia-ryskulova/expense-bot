import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from db import init_db, save_income, get_income, save_limit, get_limit

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

user_state = {}

CATEGORIES = [
    "Обязательные (страховки, аренда, подписки)",
    "Кафешки",
    "Продукты",
    "Покупки",
    "Такси",
    "Другое",
]


def get_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["➕ Добавить расход"],
            ["📊 Статистика", "💰 Осталось"],
            ["⚙️ Установить доход", "⚙️ Установить лимит"],
        ],
        resize_keyboard=True,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу тебе отслеживать расходы 💸",
        reply_markup=get_keyboard(),
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if text == "⚙️ Установить доход":
        user_state[user_id] = "waiting_for_income"
        await update.message.reply_text("Введи доход за месяц")
        return

    if text == "⚙️ Установить лимит":
        user_state[user_id] = "waiting_for_limit"
        await update.message.reply_text("Введи лимит на месяц")
        return

    if user_state.get(user_id) == "waiting_for_income":
        try:
            income = float(text.replace(",", "."))
            save_income(user_id, income)
            user_state[user_id] = None

            await update.message.reply_text(
                f"Доход сохранен: {income}", reply_markup=get_keyboard()
            )
        except:
            await update.message.reply_text("Введите число")
        return

    if user_state.get(user_id) == "waiting_for_limit":
        try:
            limit_amount = float(text.replace(",", "."))
            save_limit(user_id, limit_amount)
            user_state[user_id] = None

            await update.message.reply_text(
                f"Лимит сохранен: {limit_amount}", reply_markup=get_keyboard()
            )
        except:
            await update.message.reply_text("Введите число")
        return

    if text == "📊 Статистика":
        income = get_income(user_id)
        limit_amount = get_limit(user_id)

        await update.message.reply_text(
            f"Доход: {income}\nЛимит: {limit_amount}",
            reply_markup=get_keyboard(),
        )
        return


def main():
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()