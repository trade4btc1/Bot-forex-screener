import os
import time
import requests
import pandas as pd
import datetime
import ta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_KEY = os.getenv("POLYGON_API_KEY")
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
    return df[["t", "Open", "High", "Low", "Close", "Volume"]]

def add_indicators(df):
    bb = ta.volatility.BollingerBands(df['Close'], window=20)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    return df

def detect_bearish_engulfing(df):
    prev, curr = df.iloc[-2], df.iloc[-1]
    return (
        prev["Close"] > prev["Open"] and
        curr["Close"] < curr["Open"] and
        curr["Open"] > prev["Close"] and
        curr["Close"] < prev["Open"]
    )

def detect_bullish_engulfing(df):
    prev, curr = df.iloc[-2], df.iloc[-1]
    return (
        prev["Close"] < prev["Open"] and
        curr["Close"] > curr["Open"] and
        curr["Open"] < prev["Close"] and
        curr["Close"] > prev["Open"]
    )

def is_bearish_engulfing_at_upper_bb(df):
    if detect_bearish_engulfing(df):
        return df.iloc[-1]["Close"] >= df.iloc[-1]["bb_upper"] * 0.98
    return False

def is_bullish_engulfing_at_lower_bb(df):
    if detect_bullish_engulfing(df):
        return df.iloc[-1]["Close"] <= df.iloc[-1]["bb_lower"] * 1.02
    return False

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
        print("Telegram alert failed:", e)

def analyze():
    for symbol, name in SYMBOLS.items():
        try:
            df = fetch_data(symbol)
            if df is None or len(df) < 30:
                continue
            df = add_indicators(df)

            alerts = []
            if is_bullish_engulfing_at_lower_bb(df):
                alerts.append(f"🟢 <b>Bullish Engulfing</b> at Lower BB on {name}")
            if is_bearish_engulfing_at_upper_bb(df):
                alerts.append(f"🔴 <b>Bearish Engulfing</b> at Upper BB on {name}")

            if alerts:
                price = df.iloc[-1]["Close"]
                time_ist = df.iloc[-1]["t"] + datetime.timedelta(hours=5, minutes=30)
                time_str = time_ist.strftime("%Y-%m-%d %H:%M")
                message = f"<b>📡 Pattern Alert</b>\nSymbol: <b>{name}</b>\nPrice: {price:.4f}\nTime: {time_str} IST\n" + "\n".join(alerts) + "\n\n📌 Sans D Fx Trader"
                send_alert(message)

        except Exception as e:
            print(f"Error scanning {name}: {e}")

# === Bot Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Screener Bot is Online. Use /scan to scan the market.")

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning Market Now...")
    analyze()
    await update.message.reply_text("✅ Scan Complete.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    print("🚀 Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
