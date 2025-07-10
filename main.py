import os
import time
import requests
import pandas as pd
from datetime import datetime
from telegram import Bot

# Load Polygon and Telegram keys from environment
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Define all symbols (Polygon format)
symbols = {
    "C:EURUSD": "EUR/USD",
    "C:GBPUSD": "GBP/USD",
    "C:USDJPY": "USD/JPY",
    "C:USDCHF": "USD/CHF",
    "C:USDCAD": "USD/CAD",
    "C:AUDUSD": "AUD/USD",
    "C:NZDUSD": "NZD/USD",
    "X:BTCUSD": "BTC/USD",
    "X:ETHUSD": "ETH/USD",
    "X:XAUUSD": "XAU/USD",   # Gold
    "X:XAGUSD": "XAG/USD"    # Silver
}

def fetch_polygon_data(ticker, limit=50):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/15/minute/2024-07-01/{datetime.utcnow().date()}?adjusted=true&sort=desc&limit={limit}&apiKey={POLYGON_API_KEY}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        if "results" not in data:
            return None
        df = pd.DataFrame(data["results"])
        df["t"] = pd.to_datetime(df["t"], unit="ms")
        df = df.rename(columns={
            "o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"
        })
        return df[["t", "Open", "High", "Low", "Close", "Volume"]].iloc[::-1]
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

def detect_double_bottom(df):
    if len(df) < 4: return False
    lows = df['Low']
    return (lows.iloc[-2] > lows.iloc[-3] and
            abs(lows.iloc[-1] - lows.iloc[-3]) / lows.iloc[-3] < 0.005)

def detect_double_top(df):
    if len(df) < 4: return False
    highs = df['High']
    return (highs.iloc[-2] < highs.iloc[-3] and
            abs(highs.iloc[-1] - highs.iloc[-3]) / highs.iloc[-3] < 0.005)

def send_telegram_alert(message):
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")
        print("✅ Alert sent!")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def scan_all():
    for symbol, name in symbols.items():
        df = fetch_polygon_data(symbol)
        if df is None or df.empty:
            continue
        alerts = []
        if detect_double_bottom(df):
            alerts.append("🟢 Double Bottom")
        if detect_double_top(df):
            alerts.append("🔴 Double Top")
        if alerts:
            latest = df.iloc[-1]
            msg = (
                f"<b>{name} ({symbol})</b>\n"
                f"🕒 {latest['t'].strftime('%Y-%m-%d %H:%M')}\n"
                f"💰 Price: {latest['Close']:.4f}\n"
                + "\n".join(alerts)
                + "\n\n📌 Sans D Fx Trader"
            )
            send_telegram_alert(msg)

if __name__ == "__main__":
    print("🚀 Screener Started (15m TF, Polygon Data)...")
    while True:
        scan_all()
        time.sleep(900)  # 15 minutes
