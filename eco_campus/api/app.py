import os
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
import secrets
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
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


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    global _router
    logger.info("Запуск EcoCampus API...")
    _router = CampusRouter()
    logger.info("API готов к работе")
    threading.Thread(target=_open_browser, daemon=True).start()
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


# ── Admin Panel ──────────────────────────────────────────────────
_security = HTTPBasic()

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "ecocampus2024")


def _check_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    """HTTP Basic Auth для панели администратора."""
    ok_user = secrets.compare_digest(credentials.username.encode(), ADMIN_USER.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), ADMIN_PASS.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=401,
            detail="Неверные учётные данные",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/admin", include_in_schema=False)
def admin_panel(_: str = Depends(_check_auth)) -> Response:
    """Панель администратора EcoCampus."""
    import datetime
    stats = stats_service.summary()
    hour = datetime.datetime.now().hour
    current_load = load_predictor.predict_hour(hour)
    load_label = load_predictor._load_label(current_load)
    best = load_predictor.best_hours(3)
    forecast = load_predictor.predict_day()
    co2 = stats_service.co2_saved_kg()
    trees = round(co2 / 21, 2)

    _total = max(1, stats.get("total_routes", 1))
    _waste = stats.get("top_waste_types", [])
    top_waste_rows = "".join(
        "<tr><td>{}</td><td>{}</td>"
        "<td><div style='width:{}px;height:8px;background:#2d9e59;border-radius:4px'></div></td>"
        "<td>{}</td></tr>".format(i+1, w["waste_type"], int(w["count"]/_total*200), w["count"])
        for i, w in enumerate(_waste)
    )

    forecast_bars = "".join(
        f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px'>"
        f"<span style='width:36px;font-size:11px;color:#666'>{h['hour']:02d}:00</span>"
        f"<div style='width:{int(h['load']/16*200)}px;height:10px;"
        f"background:{'#ef4444' if h['load']>=13 else '#f97316' if h['load']>=9 else '#4ade80'};"
        f"border-radius:4px'></div>"
        f"<span style='font-size:11px;color:#666'>{h['label']}</span></div>"
        for h in forecast
    )

    load_color = {"Свободно":"#4ade80","Умеренно":"#eab308","Оживлённо":"#f97316","Пик":"#ef4444"}.get(load_label,"#4ade80")
    best_str = " &nbsp;·&nbsp; ".join(f"{h['hour']}:00 ({h['label']})" for h in best)

    html_page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>EcoCampus — Панель администратора</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:system-ui,sans-serif;background:#f0faf4;color:#1a1a1a;min-height:100vh}}
    .header{{background:linear-gradient(135deg,#0f3d22,#2d9e59);color:white;padding:20px 32px;display:flex;justify-content:space-between;align-items:center}}
    .header h1{{font-size:20px;font-weight:700}}.header small{{font-size:12px;opacity:.7}}
    .badge{{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.15);border-radius:20px;padding:4px 12px;font-size:12px}}
    .dot{{width:8px;height:8px;border-radius:50%;background:#4caf7d;animation:pulse 2s infinite}}
    @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
    .wrap{{max-width:1100px;margin:0 auto;padding:24px 16px}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:24px}}
    .card{{background:white;border-radius:14px;padding:20px;box-shadow:0 1px 6px rgba(0,0,0,.06);border:1px solid #e5f0e8}}
    .card-title{{font-size:11px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px}}
    .card-val{{font-size:32px;font-weight:700;color:#1e6b3c;font-family:monospace;line-height:1}}
    .card-sub{{font-size:12px;color:#888;margin-top:4px}}
    .section{{background:white;border-radius:14px;padding:20px;box-shadow:0 1px 6px rgba(0,0,0,.06);border:1px solid #e5f0e8;margin-bottom:16px}}
    .section-title{{font-size:13px;font-weight:700;color:#1e6b3c;text-transform:uppercase;letter-spacing:.06em;margin-bottom:16px;padding-bottom:10px;border-bottom:1px solid #e5f0e8}}
    table{{width:100%;border-collapse:collapse;font-size:13px}}
    th{{text-align:left;padding:8px 12px;background:#f0faf4;color:#666;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
    td{{padding:8px 12px;border-bottom:1px solid #f0f0f0}}
    .status-pill{{display:inline-block;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:600}}
    .btn{{display:inline-flex;align-items:center;gap:6px;background:#1e6b3c;color:white;border:none;border-radius:8px;padding:9px 18px;font-size:13px;font-weight:600;cursor:pointer;text-decoration:none;transition:background .2s}}
    .btn:hover{{background:#2d9e59}}
    .btn-outline{{background:white;color:#1e6b3c;border:1px solid #c8e6c9}}
    .btn-outline:hover{{background:#f0faf4}}
    .alert{{background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:12px 16px;font-size:13px;color:#dc2626;margin-bottom:16px}}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>🌿 EcoCampus РУДН — Панель администратора</h1>
      <small>Данные обновляются в реальном времени · Сессия с {stats.get('started_at','—')}</small>
    </div>
    <div style="display:flex;gap:10px;align-items:center">
      <div class="badge"><span class="dot"></span>Система активна</div>
      <a href="/" class="btn btn-outline" style="margin-left:8px">← Сайт</a>
    </div>
  </div>

  <div class="wrap">
    {"<div class='alert'>⚠️ Пиковая нагрузка прямо сейчас — рекомендуется проверить наполняемость контейнеров.</div>" if current_load >= 13 else ""}

    <!-- KPI карточки -->
    <div class="grid">
      <div class="card">
        <div class="card-title">Маршрутов за сессию</div>
        <div class="card-val">{stats['total_routes']}</div>
        <div class="card-sub">С {stats.get('started_at','—')}</div>
      </div>
      <div class="card">
        <div class="card-title">CO₂ сэкономлено</div>
        <div class="card-val">{co2:.2f}</div>
        <div class="card-sub">кг · методология EPA+EEA</div>
      </div>
      <div class="card">
        <div class="card-title">Эквивалент деревьев</div>
        <div class="card-val">{trees}</div>
        <div class="card-sub">деревьев/год · 21 кг CO₂ = 1 дерево</div>
      </div>
      <div class="card">
        <div class="card-title">Загруженность сейчас</div>
        <div class="card-val" style="color:{load_color}">{current_load:.1f}</div>
        <div class="card-sub"><span class="status-pill" style="background:{load_color}22;color:{load_color}">{load_label}</span></div>
      </div>
      <div class="card">
        <div class="card-title">Время работы</div>
        <div class="card-val" style="font-size:22px">{stats.get('uptime','—')}</div>
        <div class="card-sub">Без перезапуска</div>
      </div>
      <div class="card">
        <div class="card-title">Экопунктов</div>
        <div class="card-val">7</div>
        <div class="card-sub">Лучшее время: {best_str}</div>
      </div>
    </div>

    <!-- Топ отходов -->
    <div class="section">
      <div class="section-title">📊 Топ типов отходов</div>
      {"<table><thead><tr><th>#</th><th>Тип отходов</th><th>Частота</th><th>Запросов</th></tr></thead><tbody>" + top_waste_rows + "</tbody></table>" if top_waste_rows else "<p style='color:#888;font-size:13px'>Пока нет данных — маршруты не строились</p>"}
    </div>

    <!-- Прогноз загруженности -->
    <div class="section">
      <div class="section-title">🤖 Прогноз загруженности по часам (ML регрессия)</div>
      <div style="columns:2;column-gap:24px">{forecast_bars}</div>
    </div>

    <!-- Действия -->
    <div class="section">
      <div class="section-title">⚙️ Действия</div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <a href="/stats" class="btn" target="_blank">📈 JSON статистика</a>
        <a href="/docs" class="btn" target="_blank">📖 Swagger API</a>
        <a href="/containers" class="btn" target="_blank">♻️ Все экопункты</a>
        <button class="btn btn-outline" onclick="window.location.reload()">🔄 Обновить</button>
      </div>
    </div>
  </div>

  <script>
    // Автообновление каждые 30 секунд
    setTimeout(() => window.location.reload(), 30000);
  </script>
</body>
</html>"""
    return Response(content=html_page, media_type="text/html")
