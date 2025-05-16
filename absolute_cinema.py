import os
import sys
import asyncio
from dotenv import load_dotenv
import math

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from search_movie import AiSearcher

import sqlite3

# Загрузка апи телеграмма

load_dotenv()

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN not set")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Загрузка класса для поиска фильмов

searcher = AiSearcher()

# Подгрузка бд

connection = sqlite3.connect('searcher_db.sqlite')
cursor = connection.cursor()


@dp.message(Command(commands=["start"]))
async def welcome(message: Message):
    await message.answer("Приветик, я ищейка фильмов!\n"
                         "Набери название или то, что ты помнишь о фильме, который надо найти\n"
                         "Я найду его и скину ссылку и описание 👀")


@dp.message(Command(commands=["help"]))
async def assistance(message: Message):
    await message.answer("Приветик, пока сам себе помоги")


def get_user_history(user_id, offset=0, limit=None):
    if not limit:
        cursor.execute(
            '''SELECT request, title FROM requests WHERE user_id = ? ORDER BY rowid DESC''',
            (user_id,)
        )
        return cursor.fetchall()
    cursor.execute(
        '''SELECT request, title FROM requests WHERE user_id = ? ORDER BY rowid DESC LIMIT ? OFFSET ?''',
        (user_id, limit, offset)
    )
    return cursor.fetchall()


@dp.message(Command(commands=["stats"]))
async def get_statistic(message: Message):
    history = get_user_history(message.chat.id)
    stat_dict = {}
    for (req, title) in history:
        stat_dict[title] = stat_dict.get(title, 0) + 1
    await message.answer("\n".join([f"{title} – {num}" for title, num in stat_dict.items()]))


@dp.message(Command(commands=["history"]))
async def get_search_history(message: Message):
    await send_history_page(message.chat.id, page=0)


async def send_history_page(user_id, page):
    per_page = 5
    offset = page * per_page
    history = get_user_history(user_id, offset=offset, limit=per_page)

    if not history:
        await bot.send_message(user_id, "История пуста 📭")
        return

    text = "📜 История поисков:\n"
    for i, (req, title) in enumerate(history):
        text += f"{i + 1 + offset}. 🔎 {req} → 🎬 {title}\n"

    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"history_page:{page-1}"))
    if len(history) == per_page:
        buttons.append(InlineKeyboardButton(text="➡️ Далее", callback_data=f"history_page:{page+1}"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None

    await bot.send_message(user_id, text, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data and c.data.startswith("history_page:"))
async def handle_history_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    await callback.answer()
    await send_history_page(callback.from_user.id, page)


@dp.message()
async def response_search(message: Message):
    title = None
    try:
        response = await searcher.get_movie_info(message.text)
        title = response.split('\n')[0]
    except Exception as e:
        response = f"❗️ Ошибка при обращении к модели: {e}"
    cursor.execute(
        '''INSERT INTO requests (user_id, request, title) VALUES (?, ?, ?)''',
        (message.chat.id, message.text, title)
    )
    connection.commit()
    await message.answer(response)


async def main():
    print("Let`s start")
    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
