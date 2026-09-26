"""
ТГ Бот-автопостер в канал (готов к бесплатному хостингу Koyeb / Render)
======================================================================
Локально: BOT_TOKEN можно вставить ниже или задать env BOT_TOKEN.
На хостинге: задай env BOT_TOKEN в панели (токен НЕ хранить в коде).
Плюс HTTP health-check на PORT для Koyeb/Render: / и /health.
"""

import os
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬ_СЮДА_ТОКЕН_ОТ_BOTFATHER").strip()  # <-- локально вставь токен сюда ИЛИ задай env BOT_TOKEN

import asyncio
import json
import random

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

DATA_FILE = os.path.join(os.path.dirname(__file__), "autoposter_data.json")

# ---------- Хранилище ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(data, user_id: str):
    if user_id not in data:
        data[user_id] = {"channel_id": None, "channel_title": None, "posts": [], "interval": 3600}
    # для старых данных
    data[user_id].setdefault("channel_id", None)
    data[user_id].setdefault("channel_title", None)
    data[user_id].setdefault("posts", [])
    data[user_id].setdefault("interval", 3600)
    return data[user_id]

# ---------- Состояния ----------
class AddChannel(StatesGroup):
    waiting_channel = State()

class AddPost(StatesGroup):
    waiting_post = State()

class SetInterval(StatesGroup):
    waiting_interval = State()

class DelPost(StatesGroup):
    waiting_number = State()

# ---------- Клавиатуры ----------
def main_kb(is_running: bool = False):
    run_btn = "⏸ Остановить" if is_running else "▶️ Запустить"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Мой канал"), KeyboardButton(text="⏱ Интервал")],
            [KeyboardButton(text="📝 Мои посты"), KeyboardButton(text=run_btn)],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
    )

def interval_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="30 сек"), KeyboardButton(text="60 сек")],
            [KeyboardButton(text="10 мин"), KeyboardButton(text="60 мин")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )

def posts_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить пост"), KeyboardButton(text="📋 Список постов")],
            [KeyboardButton(text="🗑 Удалить пост"), KeyboardButton(text="🧹 Очистить все")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )

def format_interval(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} сек"
    if seconds < 3600:
        return f"{seconds // 60} мин ({seconds} сек)"
    return f"{seconds // 3600} ч ({seconds} сек)"

def parse_interval(text: str):
    """Принимает: '60', '60 сек', '10 мин', '1 час', '1h', '30s' и т.д. Возвращает секунды или None."""
    t = text.lower().strip().replace(",", ".")
    try:
        # чисто число = секунды? Нет, для удобства: если число <= 24 считаем часами? Лучше: число = минуты.
        # Чтобы не путаться: договоримся:
        # - "60" = 60 минут? Нет, это сбивает.
        # Простое правило: голое число = СЕКУНДЫ. А кнопки дают понятные значения.
        # Но пользователь просил "раз в 60 минут или секунд" — поэтому парсим слова.
        import re
        m = re.match(r"([\d.]+)\s*([a-zа-я]*)", t)
        if not m:
            return None
        num = float(m.group(1))
        unit = m.group(2)
        if unit in ("", "s", "sec", "сек", "секунд", "секунды", "c"):
            return int(num)
        if unit in ("m", "min", "мин", "минут", "минуты", "хв"):
            return int(num * 60)
        if unit in ("h", "hour", "ч", "час", "часов", "год"):
            return int(num * 3600)
        return int(num)  # по умолчанию секунды
    except Exception:
        return None

# ---------- Автопостинг ----------
tasks: dict[int, asyncio.Task] = {}

async def autopost_loop(bot: Bot, user_id: int):
    """Фоновая задача: каждые N секунд шлёт случайный пост в канал."""
    data = load_data()
    u = get_user(data, str(user_id))
    channel_id = u["channel_id"]
    try:
        while True:
            await asyncio.sleep(u["interval"])
            data = load_data()
            u = get_user(data, str(user_id))
            channel_id = u["channel_id"]
            if not channel_id or not u["posts"]:
                continue  # ждём пока настроят
            post = random.choice(u["posts"])
            try:
                if post["type"] == "photo":
                    await bot.send_photo(chat_id=channel_id, photo=post["file_id"], caption=post.get("caption", ""))
                else:
                    await bot.send_message(chat_id=channel_id, text=post["text"])
            except Exception as e:
                # например, бота удалили из админов — сообщаем владельцу и останавливаем
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"⚠️ Не смог отправить пост в канал {channel_id}.\nОшибка: {e}\nПроверь, что бот в админах канала и нажми ▶️ Запустить снова.",
                    )
                except Exception:
                    pass
                break
    except asyncio.CancelledError:
        pass

# ---------- Запуск ----------
async def health_server():
    """Мини HTTP-сервер чтобы Koyeb/Render видели что сервис жив: GET / и /health -> ok."""
    port = int(os.getenv("PORT", "8000"))
    try:
        from aiohttp import web

        async def ok(request):
            return web.json_response({"status": "ok", "bot": "autoposter"})

        app = web.Application()
        app.router.add_get("/", ok)
        app.router.add_get("/health", ok)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        print(f"🌐 Health-check слушает порт {port}")
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        print(f"Health-server не запущен (не критично): {e}")
        while True:
            await asyncio.sleep(3600)


async def main():
    if not BOT_TOKEN or BOT_TOKEN.startswith("ВСТАВЬ"):
        print("❌ Задай токен: env BOT_TOKEN или вставь в BOT_TOKEN в начале bot.py (возьми у @BotFather)")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # ----- /start -----
    @dp.message(CommandStart())
    async def cmd_start(msg: Message, state: FSMContext):
        await state.clear()
        data = load_data()
        u = get_user(data, str(msg.from_user.id))
        save_data(data)
        running = msg.from_user.id in tasks and not tasks[msg.from_user.id].done()
        await msg.answer(
            "👋 Привет! Я бот-автопостер.\n\n"
            "1️⃣ Добавь меня в админы своего канала\n"
            "2️⃣ Нажми «📢 Мой канал» и выбери канал\n"
            "3️⃣ Нажми «📝 Мои посты» и добавь варианты постов\n"
            "4️⃣ Нажми «⏱ Интервал» — раз в сколько писать (сек/мин)\n"
            "5️⃣ Нажми «▶️ Запустить»\n\n"
            f"Текущий канал: {u['channel_title'] or u['channel_id'] or 'не выбран'}\n"
            f"Постов: {len(u['posts'])}, интервал: {format_interval(u['interval'])}",
            reply_markup=main_kb(running),
        )

    @dp.message(Command("help"))
    @dp.message(F.text == "ℹ️ Помощь")
    async def cmd_help(msg: Message):
        await msg.answer(
            "ℹ️ Как подключить канал:\n"
            "1. Создай канал, затем: Управление каналом → Администраторы → Добавить → найди моего бота → дай право «Публикация сообщений».\n"
            "2. Здесь нажми «📢 Мой канал» и перешли мне любой пост ИЗ канала (или отправь @username / -100...).\n"
            "3. Добавь посты: «📝 Мои посты» → «➕ Добавить пост» (можно текст или фото).\n"
            "4. Интервал: «⏱ Интервал» → например «60 сек» или «60 мин» или своё «90 сек».\n"
            "5. «▶️ Запустить» — и я начну писать.\n\n"
            "Команды: /start /status /stop",
            reply_markup=main_kb(msg.from_user.id in tasks and not tasks.get(msg.from_user.id, asyncio.Task()).done() if msg.from_user.id in tasks else False),
        )

    @dp.message(Command("status"))
    async def cmd_status(msg: Message):
        data = load_data()
        u = get_user(data, str(msg.from_user.id))
        running = msg.from_user.id in tasks and not tasks[msg.from_user.id].done()
        posts_preview = "\n".join(
            f"{i+1}. {(p.get('caption') or p.get('text') or '[фото]')[:60]}"
            for i, p in enumerate(u["posts"][:10])
        ) or "— пусто —"
        await msg.answer(
            f"📊 Статус:\nКанал: {u['channel_title'] or u['channel_id'] or 'не выбран'}\n"
            f"Постов: {len(u['posts'])}\nИнтервал: {format_interval(u['interval'])}\n"
            f"Рассылка: {'▶️ работает' if running else '⏸ остановлена'}\n\n{posts_preview}"
        )

    # ----- Канал -----
    @dp.message(F.text == "📢 Мой канал")
    async def ask_channel(msg: Message, state: FSMContext):
        await state.set_state(AddChannel.waiting_channel)
        await msg.answer(
            "📢 Сначала добавь меня в АДМИНЫ канала (с правом публиковать).\n\n"
            "Потом либо:\n"
            "• Перешли мне любой пост ИЗ твоего канала, либо\n"
            "• Отправь @username канала (например @my_channel) или ID (например -1001234567890)",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True
            ),
        )

    @dp.message(AddChannel.waiting_channel)
    async def set_channel(msg: Message, state: FSMContext):
        if msg.text == "⬅️ Назад":
            await state.clear()
            await msg.answer("Ок.", reply_markup=main_kb(msg.from_user.id in tasks))
            return
        channel_id = None
        title = None
        # 1) пересланное из канала
        if msg.forward_from_chat and msg.forward_from_chat.type == "channel":
            channel_id = msg.forward_from_chat.id
            title = msg.forward_from_chat.title
        elif msg.text:
            txt = msg.text.strip()
            channel_id = txt  # @username или -100...
            if txt.lstrip("-").isdigit():
                channel_id = int(txt)
        if not channel_id:
            await msg.answer("❌ Не понял. Перешли пост из канала или отправь @username / ID.")
            return
        # проверяем доступ
        try:
            chat = await bot.get_chat(channel_id)
            title = chat.title or title or str(channel_id)
            me = await bot.get_me()
            try:
                member = await bot.get_chat_member(chat_id=channel_id, user_id=me.id)
                status = getattr(member, "status", "")
                can_post = getattr(member, "can_post_messages", True)
                if status not in ("administrator", "creator"):
                    await msg.answer(
                        f"⚠️ Я нашёл канал «{title}», но я НЕ админ там (статус: {status}).\n"
                        "Добавь меня в админы с правом публикации, потом нажми «📢 Мой канал» ещё раз.\n"
                        "Всё равно сохранить этот канал? Отправь его ещё раз словом «да сохранить» — но посты не отправятся пока не буду админом."
                    )
                    if msg.text and "да сохранить" in msg.text.lower():
                        pass
                    else:
                        return
                elif can_post is False:
                    await msg.answer("⚠️ Я админ, но без права публиковать. Дай право «Публикация сообщений».")
                    return
            except Exception:
                pass  # если не удалось проверить — всё равно сохраним
            data = load_data()
            u = get_user(data, str(msg.from_user.id))
            u["channel_id"] = channel_id
            u["channel_title"] = title
            save_data(data)
            await state.clear()
            await msg.answer(f"✅ Канал сохранён: {title} ({channel_id})", reply_markup=main_kb(msg.from_user.id in tasks))
        except Exception as e:
            await msg.answer(f"❌ Не могу найти канал {channel_id}.\nПроверь, что бот добавлен в канал и username/ID верный.\nОшибка: {e}")

    # ----- Посты -----
    @dp.message(F.text == "📝 Мои посты")
    async def posts_menu(msg: Message):
        data = load_data()
        u = get_user(data, str(msg.from_user.id))
        await msg.answer(f"📝 Постов сохранено: {len(u['posts'])}.\nВыбери действие:", reply_markup=posts_kb())

    @dp.message(F.text == "➕ Добавить пост")
    async def ask_post(msg: Message, state: FSMContext):
        await state.set_state(AddPost.waiting_post)
        await msg.answer("✍️ Отправь текст поста ИЛИ фото с подписью.\nМожно добавлять много раз — я буду выбирать случайный.\n(«⬅️ Назад» — отмена)")

    @dp.message(AddPost.waiting_post)
    async def save_post(msg: Message, state: FSMContext):
        if msg.text == "⬅️ Назад":
            await state.clear()
            await msg.answer("Ок.", reply_markup=posts_kb())
            return
        data = load_data()
        u = get_user(data, str(msg.from_user.id))
        if msg.photo:
            u["posts"].append({"type": "photo", "file_id": msg.photo[-1].file_id, "caption": msg.caption or ""})
        elif msg.text:
            u["posts"].append({"type": "text", "text": msg.text})
        else:
            await msg.answer("❌ Пришли текст или фото. Стикеры/доки пока не поддерживаю.")
            return
        save_data(data)
        await msg.answer(f"✅ Сохранено! Всего постов: {len(u['posts'])}.\nПришли ещё или нажми «⬅️ Назад».")
        # остаёмся в состоянии чтобы можно было накидать много

    @dp.message(F.text == "📋 Список постов")
    async def list_posts(msg: Message):
        data = load_data()
        u = get_user(data, str(msg.from_user.id))
        if not u["posts"]:
            await msg.answer("Пока пусто. Нажми «➕ Добавить пост».", reply_markup=posts_kb())
            return
        text = "📋 Твои посты:\n\n"
        for i, p in enumerate(u["posts"], 1):
            preview = (p.get("caption") or p.get("text") or "[фото]")[:100].replace("\n", " ")
            text += f"{i}. [{p['type']}] {preview}\n"
        # телеграм лимит 4096
        await msg.answer(text[:4000], reply_markup=posts_kb())

    @dp.message(F.text == "🗑 Удалить пост")
    async def ask_del(msg: Message, state: FSMContext):
        data = load_data()
        u = get_user(data, str(msg.from_user.id))
        if not u["posts"]:
            await msg.answer("Удалять нечего.", reply_markup=posts_kb())
            return
        await state.set_state(DelPost.waiting_number)
        await msg.answer(f"Отправь НОМЕР поста для удаления (1-{len(u['posts'])}) или «⬅️ Назад».")

    @dp.message(DelPost.waiting_number)
    async def del_post(msg: Message, state: FSMContext):
        if msg.text == "⬅️ Назад":
            await state.clear()
            await msg.answer("Ок.", reply_markup=posts_kb())
            return
        data = load_data()
        u = get_user(data, str(msg.from_user.id))
        try:
            n = int((msg.text or "").strip())
            assert 1 <= n <= len(u["posts"])
            u["posts"].pop(n - 1)
            save_data(data)
            await state.clear()
            await msg.answer(f"✅ Удалён пост №{n}. Осталось: {len(u['posts'])}.", reply_markup=posts_kb())
        except Exception:
            await msg.answer("❌ Неверный номер. Попробуй ещё.")

    @dp.message(F.text == "🧹 Очистить все")
    async def clear_posts(msg: Message):
        data = load_data()
        u = get_user(data, str(msg.from_user.id))
        u["posts"] = []
        save_data(data)
        await msg.answer("🧹 Все посты удалены.", reply_markup=posts_kb())

    # ----- Интервал -----
    @dp.message(F.text == "⏱ Интервал")
    async def ask_interval(msg: Message, state: FSMContext):
        data = load_data()
        u = get_user(data, str(msg.from_user.id))
        await state.set_state(SetInterval.waiting_interval)
        await msg.answer(
            f"⏱ Текущий интервал: {format_interval(u['interval'])}\n\n"
            "Выбери кнопкой или напиши свой, например:\n"
            "• «30 сек» / «60 сек»\n• «10 мин» / «60 мин»\n• «90 сек», «5 мин», «2 час»",
            reply_markup=interval_kb(),
        )

    @dp.message(SetInterval.waiting_interval)
    async def set_interval(msg: Message, state: FSMContext):
        if msg.text == "⬅️ Назад":
            await state.clear()
            await msg.answer("Ок.", reply_markup=main_kb(msg.from_user.id in tasks))
            return
        sec = parse_interval(msg.text or "")
        if not sec or sec < 10:
            await msg.answer("❌ Минимум 10 секунд (антиспам). Напиши например «30 сек» или «10 мин».")
            return
        data = load_data()
        u = get_user(data, str(msg.from_user.id))
        u["interval"] = sec
        save_data(data)
        await state.clear()
        running = msg.from_user.id in tasks and not tasks[msg.from_user.id].done()
        await msg.answer(
            f"✅ Интервал сохранён: {format_interval(sec)}\n"
            + ("🔄 Перезапусти рассылку («⏸ Остановить» → «▶️ Запустить»), чтобы применить." if running else "Нажми «▶️ Запустить»."),
            reply_markup=main_kb(running),
        )

    # ----- Запуск / Стоп -----
    @dp.message(F.text == "▶️ Запустить")
    async def start_posting(msg: Message):
        data = load_data()
        u = get_user(data, str(msg.from_user.id))
        if not u["channel_id"]:
            await msg.answer("❌ Сначала выбери канал: «📢 Мой канал».")
            return
        if not u["posts"]:
            await msg.answer("❌ Сначала добавь посты: «📝 Мои посты» → «➕ Добавить пост».")
            return
        if msg.from_user.id in tasks and not tasks[msg.from_user.id].done():
            await msg.answer("Уже запущено.", reply_markup=main_kb(True))
            return
        # пробный пост? Нет — сразу запускаем, первый пост через интервал
        tasks[msg.from_user.id] = asyncio.create_task(autopost_loop(bot, msg.from_user.id))
        await msg.answer(
            f"▶️ Запущено!\nКанал: {u['channel_title'] or u['channel_id']}\n"
            f"Постов: {len(u['posts'])}, каждые: {format_interval(u['interval'])}\n"
            "Первый пост придёт через интервал. Для теста можешь пока подождать.",
            reply_markup=main_kb(True),
        )

    @dp.message(Command("stop"))
    @dp.message(F.text == "⏸ Остановить")
    async def stop_posting(msg: Message):
        t = tasks.get(msg.from_user.id)
        if t and not t.done():
            t.cancel()
            await msg.answer("⏸ Остановлено.", reply_markup=main_kb(False))
        else:
            await msg.answer("Уже остановлено.", reply_markup=main_kb(False))

    @dp.message(F.text == "⬅️ Назад")
    async def back(msg: Message, state: FSMContext):
        await state.clear()
        running = msg.from_user.id in tasks and not tasks[msg.from_user.id].done()
        await msg.answer("Главное меню:", reply_markup=main_kb(running))

    print("✅ Бот запущен. Нажми Ctrl+C для остановки.")
    # health-check рядом с polling чтобы хостинг (Koyeb/Render) видел живой порт
    asyncio.create_task(health_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
