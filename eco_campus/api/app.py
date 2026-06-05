"""
REST API для сервиса эко-логистики кампуса РУДН.

Предоставляет эндпоинты для получения локаций, типов отходов,
списка контейнеров, построения маршрута, статистики, эко-советов,
классификации отходов по тексту и генерации QR-кода.
"""

import io
import threading
import time
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import qrcode
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from functools import lru_cache

from eco_campus.core.classifier import classifier as waste_classifier
from eco_campus.core.eco_tips import get_tip
from eco_campus.core.exceptions import (
    ClassificationError,
    ContainerNotFoundError,
    EcoCampusError,
    InvalidWasteTypeError,
    LocationNotFoundError,
    NoRouteError,
)
from eco_campus.core.logger import setup_logger
from eco_campus.core.models import WasteType
from eco_campus.core.router import CampusRouter
from eco_campus.core.stats import stats_service
from eco_campus.core.predictor import load_predictor

logger = setup_logger(__name__)

_router: CampusRouter | None = None
STATIC_DIR = Path(__file__).parent / "static"


def _open_browser() -> None:
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000")


def _run_bot_in_thread() -> None:
    """Запускает Telegram-бота в отдельном потоке с собственным event loop."""
    import asyncio
    import os

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN не задан — Telegram-бот не запущен")
        return

    logger.info("Запуск Telegram-бота в фоновом потоке...")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        from eco_campus.bot.telegram_bot import run_bot
        run_bot()
    except Exception:
        logger.exception("Telegram-бот упал с ошибкой")


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    global _router
    logger.info("Запуск EcoCampus API...")
    _router = CampusRouter()
    logger.info("API готов к работе")

    # Открываем браузер только при локальном запуске
    import os
    if not os.environ.get("PORT"):
        threading.Thread(target=_open_browser, daemon=True).start()

    # Запускаем Telegram-бота в отдельном потоке
    bot_thread = threading.Thread(target=_run_bot_in_thread, daemon=True, name="telegram-bot")
    bot_thread.start()
    logger.info("Поток Telegram-бота запущен (id=%s)", bot_thread.ident)

    yield
    logger.info("Завершение работы API")


app = FastAPI(
    title="EcoCampus РУДН",
    description="Интеллектуальная навигация по экопунктам кампуса РУДН",
    version="4.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ContainerOut(BaseModel):
    container_id: str
    name: str
    location_name: str
    accepted_types: list[str]
    working_hours: str
    description: str
    lat: float
    lon: float


class RouteStepOut(BaseModel):
    from_node: str
    to_node: str
    distance_meters: float
    instruction: str


class RouteOut(BaseModel):
    container: ContainerOut
    waste_type: str
    steps: list[RouteStepOut]
    total_distance_meters: float
    estimated_minutes: float
    summary: str
    eco_tip: str


class LocationOut(BaseModel):
    node_id: str
    display_name: str
    lat: float | None
    lon: float | None


class ClassifyOut(BaseModel):
    waste_type: str
    waste_type_value: str
    confidence: float
    matched_keywords: list[str]
    is_confident: bool


def _get_router() -> CampusRouter:
    if _router is None:
        raise HTTPException(status_code=503, detail="Сервис маршрутизации не готов")
    return _router


def _container_to_out(c: Any) -> ContainerOut:
    return ContainerOut(
        container_id=c.container_id,
        name=c.name,
        location_name=c.location_name,
        accepted_types=[wt.label() for wt in c.accepted_types],
        working_hours=c.working_hours,
        description=c.description,
        lat=c.coordinates.lat,
        lon=c.coordinates.lon,
    )


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api", tags=["info"])
def api_info() -> dict[str, str]:
    return {
        "service": "EcoCampus РУДН",
        "version": "4.0.0",
        "description": "Интеллектуальная навигация к экопунктам кампуса",
        "docs": "/docs",
    }


@app.get("/locations", response_model=list[LocationOut], tags=["navigation"])
def get_locations() -> list[LocationOut]:
    """Возвращает все доступные точки кампуса."""
    campus_router = _get_router()
    return [
        LocationOut(
            node_id=loc.node_id,
            display_name=loc.display_name,
            lat=loc.coordinates.lat if loc.coordinates else None,
            lon=loc.coordinates.lon if loc.coordinates else None,
        )
        for loc in campus_router.get_locations()
    ]


@app.get("/waste-types", tags=["info"])
def get_waste_types() -> list[dict[str, str]]:
    """Возвращает все поддерживаемые типы отходов."""
    return [{"value": wt.value, "label": wt.label()} for wt in WasteType]


@app.get("/containers", response_model=list[ContainerOut], tags=["containers"])
def get_containers(
    waste_type: str | None = Query(default=None, description="Фильтр по типу отходов"),
) -> list[ContainerOut]:
    """Возвращает все контейнеры с опциональной фильтрацией."""
    campus_router = _get_router()
    try:
        if waste_type:
            try:
                wt = WasteType(waste_type)
            except ValueError:
                raise InvalidWasteTypeError(waste_type)
            containers = campus_router.find_containers(wt)
        else:
            containers = campus_router.all_containers()
    except ContainerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except InvalidWasteTypeError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    return [_container_to_out(c) for c in containers]


@app.get("/route", response_model=RouteOut, tags=["navigation"])
def get_route(
    from_location: str = Query(..., description="ID стартовой точки"),
    waste_type: str = Query(..., description="Тип отходов"),
) -> RouteOut:
    """Строит маршрут и возвращает эко-совет для данного типа отходов."""
    campus_router = _get_router()
    try:
        wt = WasteType(waste_type)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Неизвестный тип отходов: {waste_type!r}",
        )
    try:
        route = campus_router.find_nearest_route(from_location, wt)
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContainerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except NoRouteError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except EcoCampusError as exc:
        logger.exception("Неожиданная ошибка маршрутизации")
        raise HTTPException(status_code=500, detail=exc.message) from exc

    stats_service.record_route(wt.label(), from_location)

    return RouteOut(
        container=_container_to_out(route.target_container),
        waste_type=route.waste_type.label(),
        steps=[
            RouteStepOut(
                from_node=s.from_node,
                to_node=s.to_node,
                distance_meters=s.distance_meters,
                instruction=s.instruction,
            )
            for s in route.steps
        ],
        total_distance_meters=route.total_distance_meters,
        estimated_minutes=route.estimated_minutes,
        summary=route.summary(),
        eco_tip=get_tip(wt),
    )


@app.get("/stats", tags=["analytics"])
def get_stats() -> dict:
    """Возвращает статистику использования сервиса."""
    return stats_service.summary()


@app.get("/predict/load", tags=["ai"])
def predict_load(
    hour: int | None = Query(default=None, ge=0, le=23, description="Час дня (0-23). Если не указан — прогноз на весь день"),
) -> dict:
    """
    Прогнозирует загруженность экопунктов с помощью линейной регрессии.

    Модель обучена на данных суточного ритма кампуса РУДН.
    Возвращает ожидаемое число посетителей и рекомендованные часы.
    """
    if hour is not None:
        return {
            "hour": hour,
            "load": load_predictor.predict_hour(hour),
            "label": load_predictor._load_label(load_predictor.predict_hour(hour)),
            "model_info": load_predictor.model_info,
        }
    return {
        "forecast": load_predictor.predict_day(),
        "best_hours": load_predictor.best_hours(),
        "model_info": load_predictor.model_info,
    }


@app.get("/eco-tip", tags=["info"])
def get_eco_tip(
    waste_type: str = Query(..., description="Тип отходов"),
) -> dict[str, str]:
    """Возвращает случайный эко-совет для данного типа отходов."""
    try:
        wt = WasteType(waste_type)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Неизвестный тип отходов: {waste_type!r}",
        )
    return {"waste_type": wt.label(), "tip": get_tip(wt)}


@app.get("/classify", response_model=ClassifyOut, tags=["ai"])
def classify_waste(
    text: str = Query(..., description="Текстовое описание предмета"),
) -> ClassifyOut:
    """
    Определяет тип отходов по текстовому описанию.

    Использует алгоритм классификации на основе взвешенного
    совпадения ключевых слов (TF-IDF-подобный подход).
    """
    try:
        result = waste_classifier.classify(text)
    except ClassificationError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc

    return ClassifyOut(
        waste_type=result.waste_type.label(),
        waste_type_value=result.waste_type.value,
        confidence=result.confidence,
        matched_keywords=result.matched_keywords,
        is_confident=result.is_confident(),
    )


@app.get("/qr", tags=["info"])
def get_qr(
    url: str = Query(default="http://127.0.0.1:8000", description="URL для QR-кода"),
) -> Response:
    """
    Генерирует QR-код для быстрого доступа к EcoCampus.

    Можно распечатать и разместить у входа в корпус.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1e6b3c", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.read(), media_type="image/png")


from eco_campus.core.chatbot import ask_yandex_gpt


class ChatRequest(BaseModel):
    message: str


class ChatOut(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatOut, tags=["ai"])
async def chat(request: ChatRequest) -> ChatOut:
    """
    Отвечает на вопрос пользователя об экологии через YandexGPT.

    Требует переменных окружения YANDEX_API_KEY и YANDEX_FOLDER_ID.
    """
    if not request.message.strip():
        raise HTTPException(status_code=422, detail="Сообщение не может быть пустым")
    try:
        reply = await ask_yandex_gpt(request.message)
    except RuntimeError as exc:
        logger.error("Ошибка чат-бота: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatOut(reply=reply)
