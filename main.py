import os
import time
import requests
import pandas as pd
import datetime
import ta
from telegram.ext import Updater, CommandHandler

# === CONFIG ===
API_KEY = os.getenv("POLYGON_API_KEY")  # Set in environment or .env file
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SYMBOLS = {
    "C:EURUSD": "EUR/USD",
    "C:GBPUSD": "GBP/USD",
    "C:USDJPY": "USD/JPY",
    "C:USDCHF": "USD/CHF",
    "C:USDCAD": "USD/CAD",
    "C:AUDUSD": "AUD/USD",
    "C:NZDUSD": "NZD/USD",
    "X:BTCUSD": "BTC/USD",
    "X:XAUUSD": "XAU/USD",
    "X:XAGUSD": "XAG/USD"
}

# === DATA FETCH ===
def fetch_data(symbol, interval="15", limit=100):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{interval}/minute/2024-01-01/{datetime.datetime.now().strftime('%Y-%m-%d')}?adjusted=true&limit={limit}&sort=desc&apiKey={API_KEY}"
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    if "results" not in data:
        return None
    df = pd.DataFrame(data["results"])
    df = df.iloc[::-1].reset_index(drop=True)
    df["t"] = pd.to_datetime(df["t"], unit="ms")
    df = df.rename(columns={"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"})
    df = df[["t", "Open", "High", "Low", "Close", "Volume"]]
    return df

# === INDICATORS ===
def add_indicators(df):
    bb = ta.volatility.BollingerBands(df['Close'], window=20)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    return df

# === PATTERN DETECTION ===
def detect_bearish_engulfing(df):
    if len(df) < 2:
        return False
    prev, curr = df.iloc[-2], df.iloc[-1]
    return (
        prev["Close"] > prev["Open"] and
        curr["Close"] < curr["Open"] and
        curr["Open"] > prev["Close"] and
        curr["Close"] < prev["Open"]
    )

def detect_bullish_engulfing(df):
    if len(df) < 2:
        return False
    prev, curr = df.iloc[-2], df.iloc[-1]
    return (
        prev["Close"] < prev["Open"] and
        curr["Close"] > curr["Open"] and
        curr["Open"] < prev["Close"] and
        curr["Close"] > prev["Open"]
    )

def is_bearish_engulfing_at_upper_bb(df):
    if detect_bearish_engulfing(df):
        curr = df.iloc[-1]
        return curr["Close"] >= curr["bb_upper"] * 0.98
    return False

def is_bullish_engulfing_at_lower_bb(df):
    if detect_bullish_engulfing(df):
        curr = df.iloc[-1]
        return curr["Close"] <= curr["bb_lower"] * 1.02
    return False

# === ALERT ===
def send_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Failed to send alert:", e)

# === ANALYSIS ===
def analyze():
    for symbol, name in SYMBOLS.items():
        try:
            df = fetch_data(symbol)
            if df is None or len(df) < 30:
                continue
            df = add_indicators(df)

            msg_lines = []
            if is_bullish_engulfing_at_lower_bb(df):
                msg_lines.append(f"🟢 <b>Bullish Engulfing</b> at Lower BB on {name}")
            if is_bearish_engulfing_at_upper_bb(df):
                msg_lines.append(f"🔴 <b>Bearish Engulfing</b> at Upper BB on {name}")

            if msg_lines:
                current_price = df["Close"].iloc[-1]
                time_now = df["t"].iloc[-1].strftime("%Y-%m-%d %H:%M")
                message = f"<b>📡 Pattern Alert</b>\nSymbol: <b>{name}</b>\nPrice: {current_price:.4f}\nTime: {time_now} IST\n" + "\n".join(msg_lines) + "\n\n📌 Sans D Fx Trader"
                send_alert(message)
        except Exception as e:
            print(f"Error analyzing {name}: {e}")

# === TELEGRAM BOT ===
def start(update, context):
    update.message.reply_text("✅ Screener Bot is Online.\nUse /scan to scan the market.")

def scan(update, context):
    update.message.reply_text("🔍 Scanning Market Now...")
    analyze()
    update.message.reply_text("✅ Scan Complete.")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("scan", scan))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
