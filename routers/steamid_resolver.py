from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
import httpx
import re
import configparser

config = configparser.ConfigParser()
config.read("config.ini")

STEAM_API_KEY = config.get("steam", "api_key")
INVENTORY_API = "http://localhost:8000/inventory"  # внутренний вызов к API
SUPPORTED_APPS = {
    "730",       # CS2
    "570",       # Dota2
    "440",       # TF2
    "252490",    # Rust
}

router = APIRouter()

VANITY_RE = re.compile(r"(?:https?://)?steamcommunity\.com/id/([^/]+)")
STEAMID_RE = re.compile(r"(?:https?://)?steamcommunity\.com/profiles/(\d+)")
JUST_ID_RE = re.compile(r"^\d{17}$")


@router.get("/{appid}/steamid")
async def resolve_and_trigger_inventory_load(
    appid: str,
    text: str = Query(...),
    background_tasks: BackgroundTasks = None
):
    if appid not in SUPPORTED_APPS:
        raise HTTPException(status_code=400, detail="Unsupported appid")

    steamid = None

    if JUST_ID_RE.match(text):
        steamid = text
    elif m := STEAMID_RE.match(text):
        steamid = m.group(1)
    elif m := VANITY_RE.match(text):
        username = m.group(1)
        steamid = await resolve_vanity(username)
    else:
        steamid = await resolve_vanity(text)

    # ✅ Фоновый запрос (не тормозит клиента)
    background_tasks.add_task(trigger_inventory_load, steamid, appid)
    return {"status": "ok"}


async def resolve_vanity(username: str) -> str:
    async with httpx.AsyncClient() as client:
        url = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/"
        params = {"key": STEAM_API_KEY, "vanityurl": username}
        resp = await client.get(url, params=params)
        data = resp.json()
        if data["response"]["success"] == 1:
            return data["response"]["steamid"]
        raise HTTPException(status_code=404, detail="Профиль не найден")


async def trigger_inventory_load(steamid: str, appid: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.get(f"{INVENTORY_API}/{steamid}/{appid}", timeout=10)
        except Exception as e:
            print(f"[INVENTORY] Ошибка запроса: {e}")
