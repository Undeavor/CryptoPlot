import requests
import pandas as pd
import sqlite3

# -------------------------------
# 1️⃣ Database setup
# -------------------------------
db_file = "crypto_prices.db"
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Coins to fetch from Binance (symbol mapping)
coins = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "ADA": "ADAUSDT",
    "AVAX": "AVAXUSDT"
}

interval = "1d"  # daily candles
limit = 5*365      # last 30 days

for coin, symbol in coins.items():
    # Create table per coin
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {coin}_prices (
        timestamp TEXT PRIMARY KEY,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL
    )
    """)
    
    # -------------------------------
    # 2️⃣ Fetch data from Binance
    # -------------------------------
    print(f"Fetching {coin} data...")
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        print(f"Failed to fetch {coin}, status {response.status_code}")
        continue
    
    data = response.json()
    
    df = pd.DataFrame(data, columns=[
        "OpenTime", "Open", "High", "Low", "Close", "Volume",
        "CloseTime", "QuoteAssetVolume", "NumberOfTrades",
        "TakerBuyBaseAssetVolume", "TakerBuyQuoteAssetVolume", "Ignore"
    ])
    
    df = df[["OpenTime", "Open", "High", "Low", "Close", "Volume"]]
    df["OpenTime"] = pd.to_datetime(df["OpenTime"], unit='ms').dt.strftime('%Y-%m-%d %H:%M:%S')
    df[["Open", "High", "Low", "Close", "Volume"]] = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
    
    # -------------------------------
    # 3️⃣ Store in SQLite
    # -------------------------------
    for _, row in df.iterrows():
        cursor.execute(f"""
        INSERT OR REPLACE INTO {coin}_prices (timestamp, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (row["OpenTime"], row["Open"], row["High"], row["Low"], row["Close"], row["Volume"]))
    
    conn.commit()
    print(f"{coin} data stored in crypto_prices.db!")

conn.close()
print("All coins updated successfully!")