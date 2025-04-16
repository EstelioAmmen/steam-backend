import psycopg2
import requests
from datetime import datetime
import logging
import os
import configparser

# === КОНФИГ ===
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))


# === ЛОГГЕР ===
LOG_DIR = "/root/Site/logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "steamapi_sync.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# === НАСТРОЙКИ ===
API_KEY = config['steam']['api_key']
BASE_URL = "https://api.steamapis.com/market/items/{appid}?api_key=" + API_KEY

GAMES = {
    "csgo": 730,
    "dota2": 570,
    "rust": 252490,
    "tf2": 440
}

DB_CONFIG = {
    "dbname": config['database']['dbname'],
    "user": config['database']['user'],
    "password": config['database']['password'],
    "host": config['database']['host'],
    "port": config.getint('database', 'port')
}

def format_unix(timestamp):
    return datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")

def normalize_item(appid, item):
    p = item.get("prices", {})
    safe_ts = p.get("safe_ts", {})
    sold = p.get("sold", {})

    return {
        "appid": appid,
        "market_hash_name": item.get("market_hash_name"),
        "nameid": item.get("nameID", ""),
        "latest": p.get("latest", 0),
        "min": p.get("min", 0),
        "avg": p.get("avg", 0),
        "max": p.get("max", 0),
        "mean": p.get("mean", 0),
        "median": p.get("median", 0),
        "prise_24h": safe_ts.get("prise_last_24h", safe_ts.get("last_24h", 0)),
        "prise_7d": safe_ts.get("prise_last_7d", safe_ts.get("last_7d", 0)),
        "prise_30d": safe_ts.get("prise_last_30d", safe_ts.get("last_30d", 0)),
        "prise_90d": safe_ts.get("prise_last_90d", safe_ts.get("last_90d", 0)),
        "sold_24h": sold.get("sold_last_24h", sold.get("last_24h", 0)),
        "sold_7d": sold.get("sold_last_7d", sold.get("last_7d", 0)),
        "sold_30d": sold.get("sold_last_30d", sold.get("last_30d", 0)),
        "sold_90d": sold.get("sold_last_90d", sold.get("last_90d", 0)),
        "sold_avg": sold.get("avg_daily_volume", 0),
        "unstable": p.get("unstable", False),
        "unstable_reason": p.get("unstable_reason", False),
        "updated_at": format_unix(item.get("updated_at", 0)),
        "quality": item.get("quality", "none"),
        "rarity": item.get("rarity", "none"),
        "hero": item.get("hero", "none"),
        "image": item.get("image", "")
    }

def atomic_refresh_data():
    logging.info("🚀 Начало обновления steamapis_items")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # лог текущей базы
        cur.execute("SELECT current_database()")
        dbname = cur.fetchone()[0]
        logging.info(f"📦 Подключено к базе: {dbname}")

        cur.execute("DROP TABLE IF EXISTS steamapis_items_tmp")
        logging.info("🧱 Создание временной таблицы steamapis_items_tmp...")

        cur.execute("""
            CREATE TABLE steamapis_items_tmp (
                appid INT,
                market_hash_name TEXT,
                nameid TEXT,
                latest NUMERIC,
                min NUMERIC,
                avg NUMERIC,
                max NUMERIC,
                mean NUMERIC,
                median NUMERIC,
                prise_24h NUMERIC,
                prise_7d NUMERIC,
                prise_30d NUMERIC,
                prise_90d NUMERIC,
                sold_24h NUMERIC,
                sold_7d NUMERIC,
                sold_30d NUMERIC,
                sold_90d NUMERIC,
                sold_avg NUMERIC,
                unstable BOOLEAN,
                unstable_reason TEXT,
                updated_at TIMESTAMP,
                quality TEXT,
                rarity TEXT,
                hero TEXT,
                image TEXT
            );
        """)
        logging.info("✅ Временная таблица steamapis_items_tmp создана.")

        total_count = 0

        for game, appid in GAMES.items():
            url = BASE_URL.format(appid=appid)
            try:
                res = requests.get(url, timeout=30)
                res.raise_for_status()
                items = res.json().get("data", [])
                for item in items:
                    norm = normalize_item(appid, item)
                    cur.execute("""
                        INSERT INTO steamapis_items_tmp VALUES (
                            %(appid)s, %(market_hash_name)s, %(nameid)s, %(latest)s, %(min)s,
                            %(avg)s, %(max)s, %(mean)s, %(median)s,
                            %(prise_24h)s, %(prise_7d)s, %(prise_30d)s, %(prise_90d)s,
                            %(sold_24h)s, %(sold_7d)s, %(sold_30d)s, %(sold_90d)s, %(sold_avg)s,
                            %(unstable)s, %(unstable_reason)s, %(updated_at)s,
                            %(quality)s, %(rarity)s, %(hero)s, %(image)s
                        )
                    """, norm)
                logging.info(f"{game.upper()}: загружено {len(items)} предметов")
                total_count += len(items)
            except Exception as e:
                logging.error(f"❌ Ошибка загрузки {game.upper()}: {e}")

        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'steamapis_items'
            )
        """)
        exists = cur.fetchone()[0]

        cur.execute("BEGIN")

        if exists:
            cur.execute("DROP TABLE IF EXISTS steamapis_items_old")
            logging.info("♻️ Удалена старая steamapis_items_old (если была)")
            cur.execute("ALTER TABLE steamapis_items RENAME TO steamapis_items_old")
            logging.info("📤 Переименована steamapis_items → steamapis_items_old")

        cur.execute("ALTER TABLE steamapis_items_tmp RENAME TO steamapis_items")
        logging.info("✅ Переименована steamapis_items_tmp → steamapis_items")

        conn.commit()
        logging.info("🧾 Коммит выполнен. Данные зафиксированы.")
        logging.info(f"🎉 Обновление завершено. Всего загружено: {total_count} предметов.")

        cur.close()
        conn.close()

    except Exception as e:
        logging.critical(f"🔥 Глобальная ошибка обновления: {e}")

if __name__ == "__main__":
    atomic_refresh_data()
