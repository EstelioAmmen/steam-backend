# routers/inventory_json.py
import os
import json
import logging
from datetime import timedelta

import asyncpg
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import configparser

router = APIRouter()

# ───── конфиг ─────────────────────────────────────────
config = configparser.ConfigParser()
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config.read(os.path.join(ROOT_DIR, "config.ini"))

DB_CONFIG = {
    "user":     config["database"]["user"],
    "password": config["database"]["password"],
    "database": config["database"]["dbname"],
    "host":     config["database"]["host"],
    "port":     config.getint("database", "port"),
}

JSON_DIR = os.path.join(ROOT_DIR, "inventoryJson")
os.makedirs(JSON_DIR, exist_ok=True)

LOG_DIR = os.path.join(ROOT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "inventory_json.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

MSK = timedelta(hours=3)

# ───── SQL‑helpers ────────────────────────────────────
async def _get_user_inventory(conn, steamid):
    return await conn.fetch(
        """
        SELECT
            appid,
            market_hash_name,
            tradable,
            marketable,
            MIN(icon_url)   AS icon_url,     -- берём первый по алфавиту
            MAX(updated_at) AS updated_at,
            COUNT(*)        AS count
        FROM user_inventory
        WHERE steamid = $1
        GROUP BY appid, market_hash_name, tradable, marketable
        """,
        steamid,
    )



async def _get_price_map(conn):
    rows = await conn.fetch(
        "SELECT appid, market_hash_name, prise_24h, prise_7d, avg FROM steamapis_items"
    )
    mp = {}
    for r in rows:
        price = r["prise_24h"] or r["prise_7d"] or r["avg"] or 0
        mp[(r["appid"], r["market_hash_name"])] = float(price)
    return mp


async def _get_currency_factors(conn):
    rows = await conn.fetch("SELECT valute, curse FROM curse")
    rub_per = {r["valute"]: float(r["curse"]) for r in rows}
    rub_per_usd = rub_per["USD"]

    factors = {"USD": 1.0, "RUB": rub_per_usd}
    for cur, rub_val in rub_per.items():
        if cur in ("USD", "RUB"):
            continue
        factors[cur] = rub_per_usd / rub_val
    return factors

# ───── JSON‑builder ───────────────────────────────────
def _compose_item_json(rec, price_usd, fx):
    # округление до 2 знаков
    prices = {cur: round(price_usd * coef, 2) for cur, coef in fx.items()}
    prices_full = {cur: round(p * rec["count"], 2) for cur, p in prices.items()}

    return {
        "appid":            rec["appid"],
        "market_hash_name": rec["market_hash_name"],
        "tradable":         rec["tradable"],
        "marketable":       rec["marketable"],
        "count":            rec["count"],
        "icon_url":         rec["icon_url"],
        "updated_at":       (rec["updated_at"] + MSK).strftime("%Y-%m-%d %H:%M:%S"),
        "prices":           prices,
        "prices_full":      prices_full,
    }

# ───── endpoint ───────────────────────────────────────
@router.get("/getjsoninv/{steamid}")
async def generate_json_inventory(steamid: str, request: Request):
    if "steamid" not in request.session:
        raise HTTPException(401, "Unauthorized")

    logging.info(f"🚀 Формирование JSON для {steamid}")

    try:
        conn     = await asyncpg.connect(**DB_CONFIG)
        rows     = await _get_user_inventory(conn, steamid)
        price_mp = await _get_price_map(conn)
        factors  = await _get_currency_factors(conn)

        out = [
            _compose_item_json(r, price_mp.get((r["appid"], r["market_hash_name"]), 0.0), factors)
            for r in rows
        ]

        file_path = os.path.join(JSON_DIR, f"{steamid}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

        await conn.close()
        logging.info(f"✅ {file_path} создан ({len(out)} позиций)")
        return JSONResponse(content=out)

    except Exception as e:
        logging.critical(f"🔥 Ошибка JSON‑инвентаря: {e}")
        raise HTTPException(500, "Internal error")
