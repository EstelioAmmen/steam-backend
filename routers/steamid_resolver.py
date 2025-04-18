import os
import logging
import re
import configparser
from urllib.parse import urlsplit

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
import httpx

# ────────────────────────────
#  Конфигурация и логирование
# ────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config.ini")
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

STEAM_API_KEY = config["steam"].get("api_key", "").strip()

LOG_DIR = "./logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "steamid_resolver.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

INVENTORY_API = "http://localhost:8000/inventory"            # внутренний вызов
SUPPORTED_APPS = {"730", "570", "440", "252490"}             # CS2, Dota 2, TF2, Rust

# ────────────────────────────
#  Регулярки
# ────────────────────────────
VANITY_RE  = re.compile(r"(?:https?://)?(?:www\.)?steamcommunity\.com/id/([^/#?]+)", re.I)
STEAMID_RE = re.compile(r"(?:https?://)?(?:www\.)?steamcommunity\.com/profiles/(\d+)", re.I)
JUST_ID_RE = re.compile(r"^\d{17}$")

# ────────────────────────────
#  Роутер
# ────────────────────────────
router = APIRouter()

@router.get("/{appid}/steamid")
async def resolve_and_trigger_inventory_load(
    background_tasks: BackgroundTasks,
    appid: str,
    text: str = Query(...)
):
    """
    Принимает любой ввод (URL / ник / SteamID64), извлекает steamid64,
    запускает фоновый /inventory/{steamid}/{appid} и возвращает
    {"steamid64": "<id>"} — это ждёт фронт‑энд.
    """
    if appid not in SUPPORTED_APPS:
        raise HTTPException(400, "Unsupported appid")

    steamid = await _extract_steamid(text)
    logging.info(f"Resolved '{text}' → {steamid} (appid={appid})")

    background_tasks.add_task(_trigger_inventory_load, steamid, appid)
    return {"steamid64": steamid}

# ────────────────────────────
#  Вспомогательные функции
# ────────────────────────────
def _normalize(text: str) -> str:
    """Срезает query/#fragment/хвосты, приводит ссылку к базе /id/<name> или /profiles/<id>."""
    text = text.strip()

    if text.lower().startswith("steamcommunity.com"):
        text = "https://" + text

    if text.startswith("http"):
        parts = urlsplit(text)
        path  = parts.path

        m = re.match(r"/(id|profiles)/([^/]+)", path, re.I)
        if m:
            clean_path = f"/{m.group(1)}/{m.group(2)}"
            text = f"{parts.scheme}://{parts.netloc}{clean_path}"

    return text

async def _extract_steamid(text: str) -> str:
    """Возвращает SteamID64 или HTTPException 404/503/500."""
    text = _normalize(text)

    if JUST_ID_RE.match(text):
        return text

    if (m := STEAMID_RE.match(text)):
        return m.group(1)

    if (m := VANITY_RE.match(text)):
        return await _resolve_vanity(m.group(1))

    # «голый» vanity‑ID
    return await _resolve_vanity(text)

async def _resolve_vanity(username: str) -> str:
    if not STEAM_API_KEY:
        raise HTTPException(500, "Steam API key not configured")

    url = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/"
    params = {"key": STEAM_API_KEY, "vanityurl": username}

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(url, params=params)
    except httpx.RequestError as exc:
        logging.error(f"ResolveVanityURL network error: {exc}")
        raise HTTPException(503, "Steam API unreachable")

    # Steam часто отвечает text/plain; нам важен только код 200
    if resp.status_code != 200:
        logging.error(f"ResolveVanityURL HTTP {resp.status_code}: {resp.text[:120]}")
        raise HTTPException(503, "Steam API error")

    data = resp.json().get("response", {})
    if data.get("success") == 1:
        return data["steamid"]

    raise HTTPException(404, "Profile not found")

async def _trigger_inventory_load(steamid: str, appid: str) -> None:
    url = f"{INVENTORY_API}/{steamid}/{appid}"
    logging.info(f"Trigger inventory load → {url}")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.get(url)
    except Exception as exc:
        logging.error(f"Inventory API call failed: {exc}")
