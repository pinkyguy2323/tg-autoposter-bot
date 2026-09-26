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

## Бесплатный хостинг 24/7 — Koyeb (деплой в 1 клик)

[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?type=git&repository=github.com/pinkyguy2323/tg-autoposter-bot&branch=main&builder=dockerfile&name=tg-autoposter-bot&ports=8000;http;/&env[PORT]=8000)

1. Жми кнопку выше → войди через GitHub.
2. В Environment Variables добавь `BOT_TOKEN` (токен от @BotFather).
3. Health check path: `/health`, Port: `8000`, Region: Frankfurt.
4. Deploy → в логах `✅ Бот запущен`.

Данные хранятся в `autoposter_data.json` рядом с ботом (на free-хостинге стирается при редеплое — настрой канал/посты заново в боте после деплоя).
