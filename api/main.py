"""
FastAPI application entry point.

Startup:  initialise DB → start BotRunner
Shutdown: stop BotRunner gracefully
WebSocket /ws — authenticated live event stream
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from api.database import init_db
from api.bot_runner import bot_runner
from api.ws_manager import ws_manager
from api.auth import decode_token
from api.routers import auth_router, signal_router, htf_router, news_router, positions_router, account_router, bot_router, equity_router, lotsize_router, admin_router, ea_router, user_router, trades_router, settings_router


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await bot_runner.start()
    yield
    await bot_runner.stop()


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AurumEdge",
    version="1.0.0",
    description="Automated Gold trading bot dashboard API",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(signal_router.router)
app.include_router(htf_router.router)
app.include_router(news_router.router)
app.include_router(positions_router.router)
app.include_router(account_router.router)
app.include_router(bot_router.router)
app.include_router(equity_router.router)
app.include_router(lotsize_router.router)
app.include_router(trades_router.router)
app.include_router(admin_router.router)
app.include_router(settings_router.router)
app.include_router(ea_router.router)


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    try:
        decode_token(token)
    except HTTPException:
        await websocket.close(code=4001)
        return

    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
async def health():
    return {
        "status": "ok",
        "ws_connections": ws_manager.connection_count,
    }
