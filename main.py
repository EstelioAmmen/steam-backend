from fastapi import FastAPI
from auth import router as auth_router
from inventory import router as inventory_router
from routers import steamid_resolver

from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

import configparser
import os

# === КОНФИГ ===
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))

SESSION_SECRET = config['app']['session_secret']

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://buff-163.ru", "https://www.buff-163.ru"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Сессии
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="none",
    https_only=True
)

# Подключение роутеров
app.include_router(auth_router)
app.include_router(inventory_router)
app.include_router(steamid_resolver.router)
