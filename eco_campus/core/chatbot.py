"""
Модуль чат-бота на базе YandexGPT.

Принимает вопросы пользователя об экологии и раздельном сборе
отходов и отвечает с помощью языковой модели YandexGPT Lite.
Ключ и folder_id загружаются из переменных окружения.
"""

import os

import httpx

from eco_campus.core.logger import setup_logger

logger = setup_logger(__name__)

YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

SYSTEM_PROMPT = (
    "Ты — эко-ассистент кампуса РУДН. Помогаешь студентам разобраться "
    "с раздельным сбором отходов, экологией и переработкой. "
    "Отвечай коротко, по делу, на русском языке. "
    "Если вопрос не связан с экологией или отходами — вежливо скажи, "
    "что можешь помочь только по экологическим темам."
)


async def ask_yandex_gpt(user_message: str) -> str:
    """
    Отправляет запрос к YandexGPT и возвращает ответ.

    Args:
        user_message: Вопрос пользователя.

    Returns:
        Текст ответа от модели.

    Raises:
        RuntimeError: Если переменные окружения не заданы или API вернул ошибку.
    """
    api_key = os.environ.get("YANDEX_API_KEY")
    folder_id = os.environ.get("YANDEX_FOLDER_ID")

    if not api_key or not folder_id:
        logger.error("YANDEX_API_KEY или YANDEX_FOLDER_ID не заданы")
        raise RuntimeError(
            "Переменные окружения YANDEX_API_KEY и YANDEX_FOLDER_ID не заданы"
        )

    payload = {
        "modelUri": f"gpt://{folder_id}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.4,
            "maxTokens": 500,
        },
        "messages": [
            {"role": "system", "text": SYSTEM_PROMPT},
            {"role": "user", "text": user_message},
        ],
    }

    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(YANDEX_GPT_URL, json=payload, headers=headers)

    if response.status_code != 200:
        logger.error(
            "YandexGPT вернул ошибку %d: %s",
            response.status_code,
            response.text,
        )
        raise RuntimeError(f"Ошибка YandexGPT API: {response.status_code}")

    data = response.json()
    text = data["result"]["alternatives"][0]["message"]["text"]
    logger.info("YandexGPT ответил на запрос длиной %d символов", len(text))
    return text
