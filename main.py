from fastapi import FastAPI
from auth import router as auth_router
from inventory import router as inventory_router

from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

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
    secret_key="super_secret_key",
    same_site="none",
    https_only=True
)

# Подключение роутеров
app.include_router(auth_router)
app.include_router(inventory_router)
