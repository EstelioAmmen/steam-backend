import os
import logging
import re
import configparser

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from fastapi import BackgroundTasks
import httpx


# ────────────────────────────
#  Конфигурация и логирование
# ────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config.ini")
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

STEAM_API_KEY = config["steam"]["api_key"]

LOG_DIR = "./logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "steamid_resolver.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

INVENTORY_API = "http://localhost:8000/inventory"          # внутренний вызов
SUPPORTED_APPS = {"730", "570", "440", "252490"}           # CS2, Dota 2, TF2, Rust


# ────────────────────────────
#  Регулярки
# ────────────────────────────
VANITY_RE   = re.compile(r"(?:https?://)?steamcommunity\.com/id/([^/]+)")
STEAMID_RE  = re.compile(r"(?:https?://)?steamcommunity\.com/profiles/(\d+)")
JUST_ID_RE  = re.compile(r"^\d{17}$")


# ────────────────────────────
#  Роутер
# ────────────────────────────
router = APIRouter()


@router.get("/{appid}/steamid")
async def resolve_and_trigger_inventory_load(
    appid: str,
    text: str = Query(...),
    background_tasks: BackgroundTasks
):


    """
    Принимает любое «text» от пользователя, извлекает SteamID64,
    а затем фоном вызывает /inventory/{steamid}/{appid}.
    Клиенту сразу возвращается {"status": "ok"}.
    """
    if appid not in SUPPORTED_APPS:
        logging.warning(f"Unsupported appid={appid}")
        raise HTTPException(status_code=400, detail="Unsupported appid")

    try:
        steamid = await _extract_steamid(text)
    except HTTPException as e:
        logging.error(f"SteamID resolve failed for '{text}': {e.detail}")
        raise

    logging.info(f"Resolved '{text}' → steamid={steamid} (appid={appid})")

    # Фоновая задача, чтобы не ждать ответ /inventory
    background_tasks.add_task(_trigger_inventory_load, steamid, appid)
    return {"status": "ok"}


# ────────────────────────────
#  Вспомогательные функции
# ────────────────────────────
async def _extract_steamid(text: str) -> str:
    """Пытается вытащить SteamID64 из URL, vanity‑нейма или числа."""
    if JUST_ID_RE.match(text):
        return text

    if (m := STEAMID_RE.match(text)):
        return m.group(1)

    if (m := VANITY_RE.match(text)):
        return await _resolve_vanity(m.group(1))

    # просто «MannCoKey» без URL
    return await _resolve_vanity(text)


async def _resolve_vanity(username: str) -> str:
    url = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/"
    params = {"key": STEAM_API_KEY, "vanityurl": username}

    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(url, params=params)
        data = resp.json()

    if data["response"]["success"] == 1:
        return data["response"]["steamid"]

    raise HTTPException(status_code=404, detail="Profile not found")


async def _trigger_inventory_load(steamid: str, appid: str) -> None:
    url = f"{INVENTORY_API}/{steamid}/{appid}"
    logging.info(f"Trigger inventory load → {url}")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.get(url)
    except Exception as exc:
        logging.error(f"Inventory API call failed: {exc}")
