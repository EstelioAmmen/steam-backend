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

# ────────────────────────────
#  Конфиг
# ────────────────────────────
config = configparser.ConfigParser()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
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

MSK = timedelta(hours=3)        # UTC→MSK

# ────────────────────────────
#  SQL‑helpers
# ────────────────────────────
async def _get_user_inventory(conn, steamid: str):
    query = """
        SELECT 
            appid,
            market_hash_name,
            tradable,
            marketable,
            icon_url,
            MAX(updated_at)  AS updated_at,
            COUNT(*)         AS count
        FROM user_inventory
        WHERE steamid = $1
        GROUP BY appid, market_hash_name, tradable, marketable, icon_url
    """
    return await conn.fetch(query, steamid)


async def _get_price_map(conn):
    rows = await conn.fetch("""
        SELECT appid, market_hash_name, 
               prise_24h, prise_7d, avg
        FROM steamapis_items
    """)
    price_map = {}
    for r in rows:
        price = r["prise_24h"] or r["prise_7d"] or r["avg"] or 0
        price_map[(r["appid"], r["market_hash_name"])] = float(price)
    return price_map


async def _get_currency_factors(conn):
    """
    Возвращает множители стоимости от USD к каждой валюте.
    dict: {"USD":1, "RUB": rub_per_usd, ...}
    """
    rows = await conn.fetch("SELECT valute, curse FROM curse")
    rub_per = {r["valute"]: float(r["curse"]) for r in rows}

    rub_per_usd = rub_per.get("USD")
    if not rub_per_usd:
        raise RuntimeError("В таблице curse нет строки USD")

    factors = {"USD": 1.0, "RUB": rub_per_usd}
    for cur, rub_value in rub_per.items():
        if cur in ("USD", "RUB"):
            continue
        factors[cur] = rub_per_usd / rub_value  # сколько валюты за 1 USD
    return factors


def _compose_item_json(rec, price_usd, factors):
    data = {
        "appid":            rec["appid"],
        "market_hash_name": rec["market_hash_name"],
        "tradable":         rec["tradable"],
        "marketable":       rec["marketable"],
        "count":            rec["count"],
        "icon_url":         rec["icon_url"],
        "updated_at":       (rec["updated_at"] + MSK).strftime("%Y-%m-%d %H:%M:%S"),
        "prices": {}
    }
    for cur, coef in factors.items():
        data["prices"][cur] = round(price_usd * coef, 3)
    return data

# ────────────────────────────
#  API‑эндпоинт
# ────────────────────────────
@router.get("/getjsoninv/{steamid}")
async def generate_json_inventory(steamid: str, request: Request):
    # нужен факт авторизации (любого пользователя)
    if "steamid" not in request.session:
        raise HTTPException(401, "Unauthorized")

    logging.info(f"🚀 Генерация JSON для {steamid}")

    try:
        conn = await asyncpg.connect(**DB_CONFIG)

        items   = await _get_user_inventory(conn, steamid)
        prices  = await _get_price_map(conn)
        factors = await _get_currency_factors(conn)

        out = [
            _compose_item_json(rec, prices.get((rec["appid"], rec["market_hash_name"]), 0.0), factors)
            for rec in items
        ]

        file_path = os.path.join(JSON_DIR, f"{steamid}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

        await conn.close()
        logging.info(f"✅ Сформирован {file_path} ({len(out)} предметов)")
        return JSONResponse(content=out)

    except Exception as exc:
        logging.critical(f"🔥 Ошибка JSON‑инвентаря: {exc}")
        raise HTTPException(500, "Internal error")
