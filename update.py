import requests
import pandas as pd
import sqlite3
import time

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
limit = 1000     # max allowed per Binance request

# -------------------------------
# 2️⃣ Fetch all historical data
# -------------------------------
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
    
    print(f"Fetching {coin} data...")

    url = "https://api.binance.com/api/v3/klines"

    # Start from a reasonable historical date (e.g., coin launch)
    start_ts = int(pd.Timestamp("2017-01-01").timestamp() * 1000)

    while True:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ts,
            "limit": limit
        }
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            print(f"Failed to fetch {coin}, status {response.status_code}")
            break
        
        data = response.json()
        if not data:
            break  # finished fetching all data
        
        df = pd.DataFrame(data, columns=[
            "OpenTime", "Open", "High", "Low", "Close", "Volume",
            "CloseTime", "QuoteAssetVolume", "NumberOfTrades",
            "TakerBuyBaseAssetVolume", "TakerBuyQuoteAssetVolume", "Ignore"
        ])
        df = df[["OpenTime", "Open", "High", "Low", "Close", "Volume"]]
        df["OpenTime"] = pd.to_datetime(df["OpenTime"], unit='ms').dt.strftime('%Y-%m-%d %H:%M:%S')
        df[["Open", "High", "Low", "Close", "Volume"]] = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
        
        # Store in SQLite
        for _, row in df.iterrows():
            cursor.execute(f"""
            INSERT OR REPLACE INTO {coin}_prices (timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (row["OpenTime"], row["Open"], row["High"], row["Low"], row["Close"], row["Volume"]))
        
        conn.commit()
        print(f"Stored {len(df)} records for {coin} (up to {df['OpenTime'].iloc[-1]})")

        # Next batch: start after last candle
        start_ts = data[-1][0] + 1
        time.sleep(0.5)  # polite delay to avoid rate limits

conn.close()
print("All coins updated successfully!")