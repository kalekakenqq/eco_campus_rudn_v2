"""
Telegram-бот для эко-навигации по кампусу РУДН.

Предоставляет интерфейс выбора локации и типа отходов через
inline-кнопки и строит маршрут до ближайшего экопункта.
Токен бота загружается из переменной окружения TELEGRAM_BOT_TOKEN.
"""

import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from eco_campus.core.classifier import classifier as waste_classifier
from eco_campus.core.eco_tips import get_tip
from eco_campus.core.exceptions import (
    ClassificationError,
    ContainerNotFoundError,
    EcoCampusError,
    LocationNotFoundError,
    NoRouteError,
)
from eco_campus.core.logger import setup_logger
from eco_campus.core.models import WasteType
from eco_campus.core.router import CampusRouter

logger = setup_logger(__name__)

ROUTER = CampusRouter()

KEY_LOCATION_ID = "location_id"
KEY_LOCATION_NAME = "location_name"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Приветствие и выбор локации."""
    await _ask_location(update, context)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Справка по командам бота."""
    text = (
        "EcoCampus РУДН — навигатор к экопунктам кампуса.\n\n"
        "Команды:\n"
        "/start — начать поиск маршрута\n"
        "/containers — все экопункты\n"
        "/help — справка\n\n"
        "Также можно написать что хотите выбросить — "
        "например 'старый телефон' или 'пластиковая бутылка' — "
        "и бот определит тип отходов автоматически."
    )
    if update.message:
        await update.message.reply_text(text)


async def cmd_containers(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Показывает список всех экопунктов кампуса."""
    containers = ROUTER.all_containers()
    lines = ["Все экопункты кампуса РУДН:\n"]
    for c in containers:
        types_str = ", ".join(wt.label() for wt in c.accepted_types)
        lines.append(f"{c.name}\nПринимает: {types_str}\nРежим работы: {c.working_hours}\n")
    if update.message:
        await update.message.reply_text("\n".join(lines))


async def handle_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Обрабатывает произвольный текст от пользователя.

    Классифицирует описание предмета и предлагает найти
    ближайший контейнер для определённого типа отходов.
    """
    text = update.message.text if update.message else ""
    if not text:
        return

    try:
        result = waste_classifier.classify(text)
    except ClassificationError:
        await update.message.reply_text(
            "Не удалось определить тип отходов по вашему описанию.\n"
            "Попробуйте написать точнее, например: 'пластиковая бутылка' или 'старый телефон'.\n"
            "Или используйте /start для выбора типа из списка."
        )
        return

    waste_label = result.waste_type.label()
    confidence_pct = int(result.confidence * 100)

    if result.is_confident():
        message = (
            f"Определён тип отходов: {waste_label} "
            f"(уверенность {confidence_pct}%)\n\n"
            "Теперь выберите своё местоположение:"
        )
        context.user_data["auto_waste"] = result.waste_type.value
    else:
        message = (
            f"Возможно, это: {waste_label} (уверенность {confidence_pct}%)\n"
            "Используйте /start для точного выбора типа отходов."
        )
        await update.message.reply_text(message)
        return

    locations = ROUTER.get_locations()
    keyboard = [
        [InlineKeyboardButton(loc.display_name, callback_data=f"loc:{loc.node_id}")]
        for loc in locations
    ]
    await update.message.reply_text(
        message, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _ask_location(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Показывает кнопки выбора локации."""
    locations = ROUTER.get_locations()
    keyboard = [
        [InlineKeyboardButton(loc.display_name, callback_data=f"loc:{loc.node_id}")]
        for loc in locations
    ]
    markup = InlineKeyboardMarkup(keyboard)
    text = "Где вы сейчас находитесь? Выберите ближайшую точку кампуса:"

    if update.message:
        await update.message.reply_text(text, reply_markup=markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup)


async def _ask_waste_type(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Показывает кнопки выбора типа отходов."""
    keyboard = [
        [InlineKeyboardButton(wt.label(), callback_data=f"waste:{wt.value}")]
        for wt in WasteType
    ]
    keyboard.append(
        [InlineKeyboardButton("Назад к локации", callback_data="back:location")]
    )
    location_name = context.user_data.get(KEY_LOCATION_NAME, "")
    await update.callback_query.edit_message_text(
        f"Локация: {location_name}\n\nЧто нужно выбросить?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Обрабатывает нажатия на inline-кнопки."""
    query = update.callback_query
    await query.answer()
    data: str = query.data or ""

    if data.startswith("loc:"):
        node_id = data.removeprefix("loc:")
        locations = {loc.node_id: loc.display_name for loc in ROUTER.get_locations()}
        context.user_data[KEY_LOCATION_ID] = node_id
        context.user_data[KEY_LOCATION_NAME] = locations.get(node_id, node_id)

        if "auto_waste" in context.user_data:
            waste_value = context.user_data.pop("auto_waste")
            await _build_and_send_route(query, context, node_id, waste_value)
        else:
            await _ask_waste_type(update, context)

    elif data.startswith("waste:"):
        waste_value = data.removeprefix("waste:")
        location_id = context.user_data.get(KEY_LOCATION_ID, "")
        if not location_id:
            await query.edit_message_text(
                "Сначала выберите локацию. Нажмите /start"
            )
            return
        await _build_and_send_route(query, context, location_id, waste_value)

    elif data == "back:location":
        await _ask_location(update, context)

    elif data == "back:start":
        context.user_data.clear()
        await _ask_location(update, context)

    elif data == "show:all":
        containers = ROUTER.all_containers()
        lines = ["Все экопункты:\n"]
        for c in containers:
            types_str = ", ".join(wt.label() for wt in c.accepted_types)
            lines.append(f"{c.name}\n{types_str}\n{c.working_hours}\n")
        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Назад", callback_data="back:start")
            ]]),
        )


async def _build_and_send_route(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    location_id: str,
    waste_value: str,
) -> None:
    """Строит маршрут и отправляет результат пользователю."""
    try:
        wt = WasteType(waste_value)
        route = ROUTER.find_nearest_route(location_id, wt)
    except (LocationNotFoundError, ContainerNotFoundError, NoRouteError) as exc:
        logger.warning("Ошибка маршрутизации для пользователя: %s", exc)
        await query.edit_message_text(
            f"{exc.message}\n\nПопробуйте другую локацию или тип отходов.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Начать заново", callback_data="back:start")
            ]]),
        )
        return
    except EcoCampusError as exc:
        logger.exception("Неожиданная ошибка")
        await query.edit_message_text(f"Внутренняя ошибка: {exc.message}")
        return

    # Форматируем расстояние
    if route.total_distance_meters == 0:
        dist = "вы уже здесь"
        time_str = "менее 1 мин"
    elif route.total_distance_meters < 1000:
        dist = f"{route.total_distance_meters:.0f} м"
        time_str = f"~{max(1, int(route.estimated_minutes))} мин"
    else:
        dist = f"{route.total_distance_meters / 1000:.1f} км"
        time_str = f"~{int(route.estimated_minutes)} мин"

    if not route.steps:
        steps_text = "  Контейнер находится прямо здесь — у вашей локации."
    else:
        steps_text = "\n".join(
            f"  {i + 1}. {s.instruction}" for i, s in enumerate(route.steps)
        )
    eco_tip = get_tip(wt)

    response = (
        f"✅ Маршрут найден!\n\n"
        f"📦 Контейнер: {route.target_container.name}\n"
        f"♻️ Принимает: {wt.label()}\n"
        f"📏 Расстояние: {dist}\n"
        f"🚶 Время: {time_str} пешком\n"
        f"🕐 Режим работы: {route.target_container.working_hours}\n\n"
        f"🗺 Пошаговый маршрут:\n{steps_text}\n\n"
        f"🌱 Факт: {eco_tip}"
    )

    keyboard = [[
        InlineKeyboardButton("Новый маршрут", callback_data="back:start"),
        InlineKeyboardButton("Все экопункты", callback_data="show:all"),
    ]]
    await query.edit_message_text(
        response, reply_markup=InlineKeyboardMarkup(keyboard)
    )


def run_bot() -> None:
    """Запускает Telegram-бота."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("Переменная TELEGRAM_BOT_TOKEN не задана")
        raise EnvironmentError(
            "Укажите токен бота в переменной окружения TELEGRAM_BOT_TOKEN"
        )

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("containers", cmd_containers))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    logger.info("Telegram-бот запущен")
    application.run_polling()


if __name__ == "__main__":
    run_bot()
