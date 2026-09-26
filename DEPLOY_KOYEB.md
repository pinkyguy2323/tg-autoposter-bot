# Деплой на Koyeb (лучший бесплатный 2026, без сна, без карты)

Почему Koyeb, а не Render/Railway:
- Render free: Web спит через 15 мин без трафика, а Background Worker теперь только от $7/мес → для polling-бота не подходит бесплатно.
- Railway: после триала всего $1/мес → не хватает на 24/7 (надо $5 Hobby).
- Fly.io: для новых юзеров free-tier убран + нужна карта.
- Koyeb Hobby: 2 nano-сервиса (512MB), без сна, без карты, есть Frankfurt (близко к RU/EU).

## Шаги (5 минут)
1. Залей папку `telegram-autoposter` на GitHub:
   - Создай репозиторий, залей файлы `bot.py`, `requirements.txt`, `Dockerfile`, `.dockerignore` (Procfile не обязателен для Docker).
2. Зайди на koyeb.com → Sign up через GitHub.
3. Create Service → From GitHub repo → выбери репозиторий.
   - Builder: Dockerfile (рекомендую, уже лежит) или Buildpack Python.
   - Run command (если Buildpack): `python bot.py`
   - Port: 8000 (бот сам читает $PORT, health на `/` и `/health`)
   - Health check path: `/health`
   - Region: Frankfurt (fra) для минимальной задержки.
4. В Environment Variables добавь:
   - `BOT_TOKEN` = токен от @BotFather
   - `PORT` = 8000 (обычно Koyeb сам подставляет, можно не трогать)
5. Deploy → жди 2-3 мин → в логах должно быть:
   `🌐 Health-check слушает порт 8000` + `✅ Бот запущен`
6. Проверь в Telegram бота, затем в Koyeb открой `...koyeb.app/health` — должно вернуть `{"status":"ok"}`.

## Важно
- `autoposter_data.json` на free-хостинге стирается при редеплое. Настройки канала/постов сделай заново в боте после деплоя. Для постоянства позже прикрутим БД.
- Токен НЕ храни в коде, только в Env панели Koyeb.
- Локально: `$env:BOT_TOKEN="твой_токен"; python bot.py` или вставь токен в `bot.py` в `BOT_TOKEN`.
