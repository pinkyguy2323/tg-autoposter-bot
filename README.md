# ТГ Бот-автопостер

## Запуск локально
1. Создай бота в @BotFather → получи токен
2. Открой `bot.py` → вставь токен в `BOT_TOKEN`
3. Установи и запусти:
```
pip install -r requirements.txt
python bot.py
```

## Как пользоваться (в самом боте)
- `📢 Мой канал` — добавь бота в админы канала, потом перешли пост из канала боту
- `📝 Мои посты` — добавь варианты постов (текст / фото)
- `⏱ Интервал` — 30 сек / 60 сек / 10 мин / 60 мин или свой
- `▶️ Запустить` / `⏸ Остановить`

## Бесплатный хостинг (когда скажешь - залью)
Готово для:
- Render.com → New → Background Worker → `pip install -r requirements.txt` + `python bot.py`, токен в Environment Variable (потом переделаю на os.getenv)
- Railway.app → Deploy from repo
- PythonAnywhere / Replit — просто загрузить bot.py и запустить

Данные хранятся в `autoposter_data.json` рядом с ботом.
