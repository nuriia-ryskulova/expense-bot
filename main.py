import logging
import os
import threading
from dotenv import load_dotenv
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from db import (
    get_expenses_by_category,
    get_income,
    get_limit,
    get_total_expenses,
    init_db,
    save_expense,
    save_income,
    save_limit,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

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


def get_category_inline_keyboard():
    rows = []
    for i, label in enumerate(CATEGORIES):
        rows.append([InlineKeyboardButton(label, callback_data=f"c:{i}")])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу тебе отслеживать расходы 💸",
        reply_markup=get_keyboard(),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        logger.warning("handle_callback: callback_query is None")
        return

    await query.answer()

    data = query.data or ""
    logger.info(
        "CallbackQuery: user_id=%s data=%r id=%s",
        query.from_user.id if query.from_user else None,
        data,
        query.id,
    )

    if data.startswith("c:"):
        try:
            idx = int(data[2:])
        except ValueError:
            logger.warning("bad callback_data: %r", data)
            return
        if not (0 <= idx < len(CATEGORIES)):
            return
        category = CATEGORIES[idx]
        uid = query.from_user.id
        user_state[uid] = ("expense_amount", category)
        await query.message.reply_text(
            f"Введи сумму расхода для категории «{category}»:",
            reply_markup=get_keyboard(),
        )
        return

    logger.warning("Неизвестный callback_data: %r", data)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    st = user_state.get(user_id)
    if isinstance(st, tuple) and st[0] == "expense_amount":
        category = st[1]
        try:
            amount = float(text.replace(",", "."))
            save_expense(user_id, amount, category)
            user_state[user_id] = None
            await update.message.reply_text(
                f"Записано: {amount} — {category}",
                reply_markup=get_keyboard(),
            )
        except Exception:
            logger.exception("expense_amount parse error")
            await update.message.reply_text("Введите число")
        return

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
        except Exception:
            logger.exception("waiting_for_income parse error")
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
        except Exception:
            logger.exception("waiting_for_limit parse error")
            await update.message.reply_text("Введите число")
        return

    if text == "📊 Статистика":
        income = get_income(user_id)
        limit_amount = get_limit(user_id)
        spent = get_total_expenses(user_id)
        remaining = limit_amount - spent
        can_save = income - spent
        by_category = get_expenses_by_category(user_id)

        category_lines = ""
        for category, amount in by_category:
            category_lines += f"  • {category}: {amount}\n"

        stats_text = (
            f"*📊 Статистика*\n\n"
            f"Доход: {income}\n"
            f"Лимит: {limit_amount}\n"
            f"Потрачено: {spent}\n"
            f"Осталось: {remaining}\n\n"
            f"*По категориям:*\n{category_lines}\n"
            f"Можно отложить: {can_save}"
        )

        await update.message.reply_text(
            stats_text,
            parse_mode="Markdown",
            reply_markup=get_keyboard(),
        )
        return

    if text == "➕ Добавить расход":
        await update.message.reply_text(
            "Выбери категорию:",
            reply_markup=get_category_inline_keyboard(),
        )
        return

    if text == "💰 Осталось":
        spent = get_total_expenses(user_id)
        limit_amount = get_limit(user_id)
        income = get_income(user_id)
        if limit_amount > 0:
            remaining = limit_amount - spent
            cap = limit_amount
            cap_label = "Лимит"
        else:
            remaining = income - spent
            cap = income
            cap_label = "Доход"
        await update.message.reply_text(
            f"Потрачено: {spent}\n{cap_label}: {cap}\nОсталось: {remaining}",
            reply_markup=get_keyboard(),
        )
        return


def run_http_server():
    port = int(os.environ.get("PORT", "10000"))
    http_app = Flask(__name__)

    @http_app.get("/")
    def health():
        return "ok", 200

    logger.info("Flask health server listening on 0.0.0.0:%s", port)
    http_app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)


def main():
    if not TOKEN:
        logger.error("BOT_TOKEN is not set")
        raise SystemExit(1)

    init_db()

    threading.Thread(target=run_http_server, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()