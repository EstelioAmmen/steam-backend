from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
import psycopg2
import datetime
import requests
from urllib.parse import urlencode
import os
import configparser

router = APIRouter()

# === КОНФИГ ===
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))

DB_HOST = config['database']['host']
DB_USER = config['database']['user']
DB_PASSWORD = config['database']['password']
DB_NAME = config['database']['dbname']
STEAM_API_KEY = config['steam']['steam_api_key']

def get_db():
    return psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )


def is_safe_url(url: str) -> bool:
    return url.startswith("/")

@router.get("/login")
async def login(request: Request, next: str = "/"):
    if not is_safe_url(next):
        next = "/"
    redirect_uri = f"https://api.buff-163.ru/auth?next={next}"
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": redirect_uri,
        "openid.realm": "https://api.buff-163.ru/",
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select"
    }
    steam_url = "https://steamcommunity.com/openid/login?" + urlencode(params)
    return RedirectResponse(steam_url)

@router.get("/auth")
async def auth(request: Request, next: str = "/"):
    params = dict(request.query_params)
    steam_url = params.get("openid.claimed_id", "")
    if not steam_url:
        return JSONResponse({"error": "Steam response invalid"}, status_code=400)

    steamid = steam_url.split("/")[-1]
    request.session["steamid"] = steamid

    try:
        user_data = requests.get(
            f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
            f"?key={STEAM_API_KEY}&steamids={steamid}"
        ).json()["response"]["players"][0]
    except Exception:
        return JSONResponse({"error": "Failed to fetch Steam profile"}, status_code=500)

    request.session["name"] = user_data.get("personaname", "Unknown")
    request.session["avatar"] = user_data.get("avatarfull", "")

    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS steam_auth (
                    steam_id TEXT PRIMARY KEY,
                    personaname TEXT,
                    avatar TEXT,
                    registered_at TIMESTAMP
                )
            """)
            cursor.execute("""
                INSERT INTO steam_auth (steam_id, personaname, avatar, registered_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (steam_id) DO UPDATE
                SET personaname = EXCLUDED.personaname,
                    avatar = EXCLUDED.avatar
            """, (
                steamid,
                user_data.get("personaname", "Unknown"),
                user_data.get("avatarfull", ""),
                datetime.datetime.utcnow()
            ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB error: {e}")

    return RedirectResponse("https://buff-163.ru" + next if is_safe_url(next) else "/")

@router.get("/me")
async def me(request: Request):
    steamid = request.session.get("steamid")
    name = request.session.get("name")
    avatar = request.session.get("avatar")
    if steamid:
        return {"steamid": steamid, "name": name, "avatar": avatar}
    return JSONResponse({"error": "Not authenticated"}, status_code=401)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("https://buff-163.ru/")
