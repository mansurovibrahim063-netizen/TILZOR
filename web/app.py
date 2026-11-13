import os
import hmac
import hashlib
from typing import Optional
from fastapi import FastAPI, Request, Response, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from config import settings
from database.db import get_db, init_db
from database.models import MessageLog
from services.message_service import MessageService
from services.report_service import ReportService
from moderation.pipeline import pipeline

app = FastAPI(title="AI-Moderator Dashboard")

# Shablonlar va statik fayllar yo'li
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, "templates")
static_dir = os.path.join(current_dir, "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

templates = Jinja2Templates(directory=templates_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

COOKIE_NAME = "ai_moderator_session"


def generate_session_token(password: str) -> str:
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, password.encode(), hashlib.sha256).hexdigest()


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    expected = generate_session_token(settings.ADMIN_PASSWORD)
    return hmac.compare_digest(token, expected)


@app.on_event("startup")
async def startup_event():
    await init_db()


# ---------------- AUTH ROUTES ----------------
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})


@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, response: Response, password: str = Form(...)):
    if password == settings.ADMIN_PASSWORD:
        token = generate_session_token(settings.ADMIN_PASSWORD)
        redirect = RedirectResponse(url="/", status_code=303)
        redirect.set_cookie(key=COOKIE_NAME, value=token, httponly=True, max_age=86400 * 7)
        return redirect

    return templates.TemplateResponse(request=request, name="login.html", context={"error": "Noto'g'ri parol kiritildi!"})


@app.get("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp


# ---------------- DASHBOARD ----------------
@app.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request, db: AsyncSession = Depends(get_db)):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    stats = await MessageService.get_statistics(db)
    recent_messages, _ = await MessageService.get_messages(db, skip=0, limit=10)

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "active_page": "dashboard",
        "stats": stats,
        "recent_messages": recent_messages,
        "pending_reports_count": stats.get("pending_reports", 0),
        "gemini_model_name": settings.GEMINI_MODEL
    })


# ---------------- MESSAGES LOG ----------------
@app.get("/messages", response_class=HTMLResponse)
async def messages_view(
    request: Request,
    page: int = 1,
    limit: int = 25,
    status: Optional[str] = "ALL",
    stage: Optional[str] = "ALL",
    violation_type: Optional[str] = "ALL",
    search: Optional[str] = "",
    db: AsyncSession = Depends(get_db)
):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    skip = (page - 1) * limit
    messages, total_count = await MessageService.get_messages(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        stage=stage,
        violation_type=violation_type,
        search=search
    )

    stats = await MessageService.get_statistics(db)

    return templates.TemplateResponse(request=request, name="messages.html", context={
        "active_page": "messages",
        "messages": messages,
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "current_status": status,
        "current_stage": stage,
        "current_violation": violation_type,
        "current_search": search,
        "pending_reports_count": stats.get("pending_reports", 0),
        "gemini_model_name": settings.GEMINI_MODEL
    })


@app.post("/messages/status")
async def update_message_status(
    request: Request,
    message_id: int = Form(...),
    new_status: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    await MessageService.update_message_status(db, message_id=message_id, status=new_status, admin_reason="Panel orqali o'zgartirildi")
    return RedirectResponse(url="/messages", status_code=303)


# ---------------- REPORTS (SHIKOYATLAR) ----------------
@app.get("/reports", response_class=HTMLResponse)
async def reports_view(
    request: Request,
    status: Optional[str] = "PENDING",
    db: AsyncSession = Depends(get_db)
):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    reports, total_count = await ReportService.get_reports(db, status=status)
    stats = await MessageService.get_statistics(db)

    return templates.TemplateResponse(request=request, name="reports.html", context={
        "active_page": "reports",
        "reports": reports,
        "total_count": total_count,
        "current_status": status,
        "pending_reports_count": stats.get("pending_reports", 0),
        "gemini_model_name": settings.GEMINI_MODEL
    })


@app.post("/reports/resolve")
async def resolve_report_view(
    request: Request,
    report_id: int = Form(...),
    action: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    await ReportService.resolve_report(db, report_id=report_id, action=action)
    return RedirectResponse(url="/reports", status_code=303)


# ---------------- TESTER LABORATORY ----------------
@app.get("/tester", response_class=HTMLResponse)
async def tester_view(request: Request, db: AsyncSession = Depends(get_db)):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    stats = await MessageService.get_statistics(db)
    return templates.TemplateResponse(request=request, name="tester.html", context={
        "active_page": "tester",
        "pending_reports_count": stats.get("pending_reports", 0),
        "gemini_model_name": settings.GEMINI_MODEL
    })


class TestPayload(BaseModel):
    text: str


@app.post("/api/test")
async def api_test_message(payload: TestPayload):
    text = payload.text.strip()
    
    # 1. Regex Tekshiruvi
    regex_res = pipeline.regex_engine.evaluate(user_id=1, text=text)

    # 2. Gemini AI Tekshiruvi
    ai_res = await pipeline.gemini_engine.analyze_message(text)

    # To'liq Pipeline qarori
    full_res = await pipeline.evaluate_message(user_id=1, text=text)

    return JSONResponse({
        "is_violation": full_res.is_violation,
        "status": full_res.status,
        "detection_stage": full_res.detection_stage,
        "violation_type": full_res.violation_type,
        "toxicity_score": full_res.toxicity_score,
        "reason": full_res.reason,
        "translated_uz": full_res.translated_uz,
        "translated_ru": full_res.translated_ru,
        "regex": {
            "is_violation": regex_res.is_violation,
            "violation_type": regex_res.violation_type,
            "reason": regex_res.reason,
            "matched_text": regex_res.matched_text
        },
        "gemini": {
            "is_violation": ai_res.is_violation,
            "violation_type": ai_res.violation_type,
            "toxicity_score": ai_res.toxicity_score,
            "reason": ai_res.reason
        }
    })


# ---------------- SETTINGS ----------------
@app.get("/settings", response_class=HTMLResponse)
async def settings_view(request: Request, db: AsyncSession = Depends(get_db)):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    stats = await MessageService.get_statistics(db)
    return templates.TemplateResponse(request=request, name="settings.html", context={
        "active_page": "settings",
        "settings": settings,
        "message": None,
        "pending_reports_count": stats.get("pending_reports", 0),
        "gemini_model_name": settings.GEMINI_MODEL
    })


@app.post("/settings", response_class=HTMLResponse)
async def update_settings(
    request: Request,
    TOXICITY_THRESHOLD: int = Form(...),
    GEMINI_MODEL: str = Form(...),
    GEMINI_API_KEY: Optional[str] = Form(""),
    BOT_TOKEN: Optional[str] = Form(""),
    ADMIN_TELEGRAM_ID: Optional[int] = Form(0),
    ADMIN_PASSWORD: str = Form(...),
    STRICT_LINK_BLOCKING: Optional[str] = Form(None),
    ENABLE_FLOOD_PROTECTION: Optional[str] = Form(None),
    AUTO_TRANSLATE: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    # In-memory settings update
    settings.TOXICITY_THRESHOLD = TOXICITY_THRESHOLD
    settings.GEMINI_MODEL = GEMINI_MODEL
    if GEMINI_API_KEY:
        settings.GEMINI_API_KEY = GEMINI_API_KEY
    if BOT_TOKEN:
        settings.BOT_TOKEN = BOT_TOKEN
    settings.ADMIN_TELEGRAM_ID = ADMIN_TELEGRAM_ID or 0
    if ADMIN_PASSWORD:
        settings.ADMIN_PASSWORD = ADMIN_PASSWORD
    settings.STRICT_LINK_BLOCKING = (STRICT_LINK_BLOCKING == "true")
    settings.ENABLE_FLOOD_PROTECTION = (ENABLE_FLOOD_PROTECTION == "true")
    settings.AUTO_TRANSLATE = (AUTO_TRANSLATE == "true")

    # Update pipeline instances with new config
    pipeline.gemini_engine.api_key = settings.GEMINI_API_KEY
    pipeline.gemini_engine.model = settings.GEMINI_MODEL

    stats = await MessageService.get_statistics(db)
    return templates.TemplateResponse(request=request, name="settings.html", context={
        "active_page": "settings",
        "settings": settings,
        "message": "Sozlamalar muvaffaqiyatli saqlandi va kuchga kirdi!",
        "pending_reports_count": stats.get("pending_reports", 0),
        "gemini_model_name": settings.GEMINI_MODEL
    })
