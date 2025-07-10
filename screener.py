import os
import requests
import pandas as pd
import datetime
from telegram import Bot

TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
POLYGON_API_KEY = "YOUR_POLYGON_API_KEY"

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
    "X:XAUUSD": "XAU/USD",
    "X:XAGUSD": "XAG/USD"
}

def fetch_polygon_data(symbol, multiplier=15, timespan="minute", limit=50):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/2024-01-01/{datetime.datetime.utcnow().strftime('%Y-%m-%d')}?adjusted=true&sort=desc&limit={limit}&apiKey={POLYGON_API_KEY}"
    res = requests.get(url)
    res.raise_for_status()
    data = res.json().get("results", [])
    if not data:
        return None
    df = pd.DataFrame(data)
    df["t"] = pd.to_datetime(df["t"], unit="ms")
    df = df.rename(columns={"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"})
    return df[["t", "Open", "High", "Low", "Close", "Volume"]].iloc[::-1].reset_index(drop=True)

def detect_bullish_engulfing(df):
    if len(df) < 2:
        return False
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    return (prev["Close"] < prev["Open"] and curr["Close"] > curr["Open"] and
            curr["Open"] < prev["Close"] and curr["Close"] > prev["Open"] and
            curr["Close"] < df["Close"].mean())

def detect_bearish_engulfing(df):
    if len(df) < 2:
        return False
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    return (prev["Close"] > prev["Open"] and curr["Close"] < curr["Open"] and
            curr["Open"] > prev["Close"] and curr["Close"] < prev["Open"] and
            curr["Close"] > df["Close"].mean())

def send_telegram_message(message):
    try:
        Bot(token=TELEGRAM_TOKEN).send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        print(f"Telegram error: {e}")

def run_screener():
    for symbol, name in symbols.items():
        try:
            df = fetch_polygon_data(symbol)
            if df is None or df.empty:
                continue
            message_parts = [f"📌 {name} | {symbol}"]
            if detect_bullish_engulfing(df):
                message_parts.append("✅ Bullish Engulfing at Lower Band")
            if detect_bearish_engulfing(df):
                message_parts.append("❌ Bearish Engulfing at Upper Band")
            if len(message_parts) > 1:
                send_telegram_message("\n".join(message_parts))
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")