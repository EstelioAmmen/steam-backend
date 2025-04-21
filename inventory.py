import os
import logging
import configparser
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import asyncpg
import httpx

router = APIRouter()

# === КОНФИГ ===
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "config.ini"))

# === НАСТРОЙКИ ===
API_KEY = config["steam"]["api_key"]
BASE_URL = (
    "https://api.steamapis.com/steam/inventory/{steamid}/{appid}/2?api_key=" + API_KEY
)

DB_CONFIG = {
    "user":     config["database"]["user"],
    "password": config["database"]["password"],
    "database": config["database"]["dbname"],
    "host":     config["database"]["host"],
    "port":     config.getint("database", "port"),
}

LOG_DIR = "./logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "inventory_api.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# константа для сдвига UTC→МСК
MSK_OFFSET = timedelta(hours=3)

# === Вспомогательные функции ===
def parse_tags(tags: list) -> tuple[str, str]:
    cats, vals = [], []
    for tag in tags:
        if "localized_category_name" in tag and "localized_tag_name" in tag:
            cats.append(tag["localized_category_name"])
            vals.append(tag["localized_tag_name"])
    return ";".join(cats), ";".join(vals)


async def load_and_store_inventory(steamid: str, appid: int) -> bool:
    """
    Загружает инвентарь частями (по 2 000 предметов), объединяет результаты
    и сохраняет в таблицу user_inventory.
    """
    start_assetid: str | None = None           # курсор постраничной выборки
    all_assets: list[dict] = []
    descriptions: dict[tuple[str, str], dict] = {}

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            url = BASE_URL.format(steamid=steamid, appid=appid)
            if start_assetid:
                url += f"&start_assetid={start_assetid}"

            logging.info(
                f"📥 Запрос инвент: steamid={steamid}, appid={appid}, start={start_assetid or '0'}"
            )

            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logging.error(f"❌ Ошибка загрузки с API: {e}")
                return False

            # аккумулируем данные
            all_assets.extend(data.get("assets", []))
            for d in data.get("descriptions", []):
                descriptions[(d["classid"], d["instanceid"])] = d

            # проверяем, есть ли ещё предметы
            if data.get("more_items") and data.get("last_assetid"):
                start_assetid = data["last_assetid"]
            else:
                break       # получили всё

    if not all_assets:
        logging.warning("⚠️ Нет предметов для вставки")
        return False

    # московское время фиксируем после полной выгрузки
    now = datetime.utcnow() + MSK_OFFSET
    rows = []

    for asset in all_assets:
        key = (asset["classid"], asset["instanceid"])
        desc = descriptions.get(key)
        if not desc:
            continue

        cat_str, val_str = parse_tags(desc.get("tags", []))

        rows.append(
            (
                steamid,
                asset["appid"],
                asset["assetid"],
                asset["classid"],
                asset["instanceid"],
                desc.get("market_hash_name"),
                desc.get("tradable"),
                desc.get("marketable"),
                desc.get("type"),
                cat_str,
                val_str,
                desc.get("icon_url"),
                now,
            )
        )

    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_inventory (
                steamid TEXT,
                appid INTEGER,
                assetid TEXT,
                classid TEXT,
                instanceid TEXT,
                market_hash_name TEXT,
                tradable INTEGER,
                marketable INTEGER,
                type TEXT,
                categories TEXT,
                tags TEXT,
                icon_url TEXT,
                updated_at TIMESTAMP
            );
        """
        )
        await conn.execute(
            "DELETE FROM user_inventory WHERE steamid = $1 AND appid = $2",
            steamid,
            appid,
        )
        await conn.executemany(
            """
            INSERT INTO user_inventory (
                steamid, appid, assetid, classid, instanceid,
                market_hash_name, tradable, marketable, type,
                categories, tags, icon_url, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8, $9, $10,
                $11, $12, $13
            )
        """,
            rows,
        )
        await conn.close()
        logging.info(
            f"✅ Сохранено {len(rows)} предметов в user_inventory для {steamid}/{appid}"
        )
        return True
    except Exception as e:
        logging.critical(f"🔥 Ошибка сохранения в БД: {e}")
        return False


# === Эндпоинт ===
@router.get("/inventory/{steamid}/{appid}")
async def inventory_endpoint(steamid: str, appid: int, request: Request):
    if "steamid" not in request.session:
        raise HTTPException(status_code=401, detail="Unauthorized")

    success = await load_and_store_inventory(steamid, appid)
    if success:
        return JSONResponse(content={"message": "Inventory saved to database"})
    else:
        return JSONResponse(
            status_code=500, content={"error": "Failed to process inventory"}
        )
