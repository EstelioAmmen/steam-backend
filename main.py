from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

# ── приложные роутеры ────────────────────────────────
from auth             import router as auth_router
from inventory        import router as inventory_router
from routers import steamid_resolver
from routers import inventory_json

# ── конфиг / секреты ────────────────────────────────
import configparser
import os

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "config.ini"))

SESSION_SECRET = config["app"]["session_secret"]

app = FastAPI()

# ── CORS (только ваш домен) ──────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://buff-163.ru",
        "https://www.buff-163.ru",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── cookie‑сессии ────────────────────────────────────
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="none",
    https_only=True,
)

# ── подключаем роутеры ───────────────────────────────
app.include_router(auth_router)                   # авторизация
app.include_router(steamid_resolver.router)       # /{appid}/steamid
app.include_router(inventory_router)              # /inventory/{steamid}/{appid}
app.include_router(inventory_json.router)         # /getjsoninv/{steamid}
