# inventory_json.py
import os
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

import asyncpg
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import configparser

router = APIRouter()

# ────────────────────────────
#  Конфигурация
# ────────────────────────────
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "config.ini"))

DB_CONFIG = {
    "user":     config["database"]["user"],
    "password": config["database"]["password"],
    "database": config["database"]["dbname"],
    "host":     config["database"]["host"],
    "port":     config.getint("database", "port"),
}

JSON_DIR = "/root/Site/inventoryJson"
os.makedirs(JSON_DIR, exist_ok=True)

# ────────────────────────────
#  Логирование
# ────────────────────────────
LOG_DIR = "/root/Site/logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "inventory_json.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# московское время
MSK = timedelta(hours=3)

# ────────────────────────────
#  Вспомогательные функции
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
    """
    Возвращает {(appid, market_hash_name): priceUSD}
    """
    rows = await conn.fetch("SELECT * FROM steamapis_items")
    price_map = {}
    for r in rows:
        price = (
            r["prise_24h"]
            or r["prise_7d"]
            or r["avg"]
            or 0
        )
        price_map[(r["appid"], r["market_hash_name"])] = float(price)
    return price_map


async def _get_currency_factors(conn):
    """
    Возвращает множители: {"USD":1, "CNY": x, …}
    """
    rows = await conn.fetch("SELECT valute, curse FROM curse")
    rub_per = {r["valute"]: float(r["curse"]) for r in rows}

    rub_per_usd = rub_per.get("USD")
    if not rub_per_usd:
        raise RuntimeError("В таблице curse нет строки USD")

    factors = {"USD": 1.0}
    for val, rub_val in rub_per.items():
        if val == "USD":
            continue
        factors[val] = rub_per_usd / rub_val     # сколько валюты за 1 USD
    return factors


def _compose_item_json(rec, price_usd, factors):
    result = {
        "appid":            rec["appid"],
        "market_hash_name": rec["market_hash_name"],
        "tradable":         rec["tradable"],
        "marketable":       rec["marketable"],
        "count":            rec["count"],
        "icon_url":         rec["icon_url"],
        "updated_at":       (rec["updated_at"] + MSK).strftime("%Y-%m-%d %H:%M:%S"),
        "prices": {}
    }
    for cur, k in factors.items():
        result["prices"][cur] = round(price_usd * k, 3)
    return result

# ────────────────────────────
#  Основной энд‑поинт
# ────────────────────────────
@router.get("/getjsoninv/{steamid}")
async def generate_json_inventory(steamid: str, request: Request):
    """
    Формирует <steamid>.json и отдаёт его же контентом.
    Доступно только владельцу сессии.
    """
    sess_sid = request.session.get("steamid")
    if sess_sid != steamid:
        raise HTTPException(401, "Unauthorized")

    logging.info(f"🚀 Генерация JSON‑инвентаря для {steamid}")

    try:
        conn = await asyncpg.connect(**DB_CONFIG)

        user_items   = await _get_user_inventory(conn, steamid)
        price_map    = await _get_price_map(conn)
        factors      = await _get_currency_factors(conn)

        out_items = []
        for rec in user_items:
            price_usd = price_map.get((rec["appid"], rec["market_hash_name"]), 0.0)
            out_items.append(_compose_item_json(rec, price_usd, factors))

        file_path = os.path.join(JSON_DIR, f"{steamid}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(out_items, f, ensure_ascii=False, indent=2)

        await conn.close()
        logging.info(f"✅ Файл сформирован: {file_path} ({len(out_items)} позиций)")
        return JSONResponse(content=out_items)

    except Exception as exc:
        logging.critical(f"🔥 Ошибка формирования JSON: {exc}")
        raise HTTPException(500, "Internal error")
