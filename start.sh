#!/bin/bash
# Запуск Telegram-бота и FastAPI одновременно

echo "[start.sh] Запуск Telegram-бота в фоне..."
python -m eco_campus.bot.telegram_bot &
BOT_PID=$!
echo "[start.sh] Бот запущен, PID=$BOT_PID"

echo "[start.sh] Запуск uvicorn на порту 80..."
exec uvicorn eco_campus.api.app:app --host 0.0.0.0 --port 80 --workers 1 --timeout-keep-alive 30
