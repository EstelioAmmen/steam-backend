import psycopg2
import requests
from datetime import datetime
import logging
import os
import re

# === ЛОГГЕР ===
LOG_DIR = "/root/Site/logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "curse_sync.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# === НАСТРОЙКИ ===
API_URL = "https://steamcommunity.com/market/priceoverview/"
APP_ID = 730
ITEM_NAME = "Operation Bravo Case"

CURRENCIES = {
    "USD": 1,
    "EUR": 3,
    "CNY": 23,
    "TRY": 17,
    "KZT": 37,
    "RUB": 5
}

DB_CONFIG = {
    "dbname": "steaminventory_db",
    "user": "steamuser",
    "password": "MySecurePostgres123!",
    "host": "localhost",
    "port": 5432
}

def connect_db():
    return psycopg2.connect(**DB_CONFIG)

def create_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS curse (
            valute TEXT PRIMARY KEY,
            curse NUMERIC NOT NULL,
            time TIMESTAMP NOT NULL
        );
    """)
    cur.execute("DELETE FROM curse;")
    logging.info("✅ Таблица curse создана и очищена")

def save_rate(cur, valute, curse, time_str):
    cur.execute("""
        INSERT INTO curse (valute, curse, time)
        VALUES (%s, %s, %s)
        ON CONFLICT (valute) DO UPDATE SET
            curse = EXCLUDED.curse,
            time = EXCLUDED.time;
    """, (valute, curse, time_str))
    logging.info(f"💾 Сохранено: {valute} = {curse} RUB")

def fetch_price(currency_code):
    params = {
        "currency": currency_code,
        "country": "us",
        "appid": APP_ID,
        "market_hash_name": ITEM_NAME,
        "format": "json"
    }
    response = requests.get(API_URL, params=params)
    response.raise_for_status()
    return response.json()

def extract_median_price(data):
    if not data.get("success"):
        raise ValueError("Данные от API не являются успешными")
    
    raw = data.get("median_price", "")

    # Удаляем валютные символы и все пробелы/неразрывные пробелы
    cleaned = re.sub(r"[^\d,\.]", "", raw)

    # Спецлогика:
    # Если в числе 2 разделителя — это вероятно "тысячная точка + десятичная запятая"
    if cleaned.count('.') == 1 and cleaned.count(',') == 1:
        cleaned = cleaned.replace('.', '')  # убираем тысячную
        cleaned = cleaned.replace(',', '.')  # заменяем десятичную

    else:
        # обычная замена , на . для всех остальных
        cleaned = cleaned.replace(",", ".")

    cleaned = cleaned.rstrip(".")

    try:
        return float(cleaned)
    except ValueError:
        raise ValueError(f"Не удалось преобразовать цену: {raw} → {cleaned}")



def main():
    logging.info("🚀 Запуск обновления таблицы curse")
    try:
        conn = connect_db()
        cur = conn.cursor()

        create_table(cur)

        rub_data = fetch_price(CURRENCIES["RUB"])
        rub_price = extract_median_price(rub_data)

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        for valute, code in CURRENCIES.items():
            if valute == "RUB":
                continue
            try:
                data = fetch_price(code)
                val_price = extract_median_price(data)
                rate = round(rub_price / val_price, 3)
                save_rate(cur, valute, rate, now)
            except Exception as e:
                logging.error(f"❌ Ошибка при обработке {valute}: {e}")

        conn.commit()
        logging.info("✅ Данные записаны в базу")
        cur.close()
        conn.close()
    except Exception as e:
        logging.critical(f"🔥 Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
