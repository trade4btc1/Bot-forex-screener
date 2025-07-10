import time
import pandas as pd
import numpy as np
import ta
import requests
import threading
from binance.client import Client
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Config ---
ALPHA_VANTAGE_KEY = "B5AZ6L8DSD83RDZ5"
BINANCE_API_KEY = ""  # Optional for public data
BINANCE_API_SECRET = ""  # Optional for public data

TELEGRAM_TOKEN = "7787144306:AAGQNw9vWDTwu5gTKqjahBOYpCNNDYvoCps"
TELEGRAM_CHAT_ID = 1833875678

FOREX_PAIRS = [
    ("EUR", "USD"),
    ("USD", "JPY"),
    ("GBP", "USD"),
    ("AUD", "USD"),
    ("USD", "CHF"),
    ("USD", "CAD"),
    ("NZD", "USD"),
    ("XAU", "USD"),
    ("XAG", "USD"),
]
CRYPTO_PAIRS = ["BTCUSDT"]
FOREX_INTERVAL = "15min"
FOREX_LOOKBACK = 100
CRYPTO_INTERVAL = Client.KLINE_INTERVAL_15MINUTE
CRYPTO_LOOKBACK = 100
POLL_SECONDS = 900  # 15min

def get_alpha_vantage_fx(pair, interval, lookback):
    url = (
        f"https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={pair[0]}&to_symbol={pair[1]}"
        f"&interval={interval}&outputsize=compact&apikey={ALPHA_VANTAGE_KEY}"
    )
    r = requests.get(url)
    data = r.json()
    time_series = data.get(f"Time Series FX ({interval})", {})
    if not time_series:
        print(f"AlphaVantage error or limit for {pair[0]}/{pair[1]}")
        return None
    df = pd.DataFrame(time_series).T
    df = df.rename(
        columns={
            "1. open": "Open",
            "2. high": "High",
            "3. low": "Low",
            "4. close": "Close"
        }
    )
    df = df.astype(float)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    if len(df) > lookback:
        df = df.iloc[-lookback:]
    df.reset_index(inplace=True)
    df = df.rename(columns={"index": "Time"})
    return df

def get_binance_klines(symbol, interval, lookback):
    client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
    klines = client.get_klines(symbol=symbol, interval=interval, limit=lookback)
    df = pd.DataFrame(klines, columns=[
        'OpenTime', 'Open', 'High', 'Low', 'Close', 'Volume',
        'CloseTime', 'QuoteAssetVolume', 'NumberOfTrades',
        'TakerBuyBase', 'TakerBuyQuote', 'Ignore'
    ])
    df["Open"] = df["Open"].astype(float)
    df["High"] = df["High"].astype(float)
    df["Low"] = df["Low"].astype(float)
    df["Close"] = df["Close"].astype(float)
    df["Volume"] = df["Volume"].astype(float)
    df["Time"] = pd.to_datetime(df["OpenTime"], unit='ms')
    return df[["Time", "Open", "High", "Low", "Close", "Volume"]]

def calculate_indicators(df):
    df["ema20"] = ta.trend.ema_indicator(df["Close"], window=20)
    df["rsi14"] = ta.momentum.rsi(df["Close"], window=14)
    df["macd"] = ta.trend.macd(df["Close"])
    df["macd_signal"] = ta.trend.macd_signal(df["Close"])
    bb = ta.volatility.BollingerBands(df["Close"], window=20)
    df["bb_high"] = bb.bollinger_hband()
    df["bb_low"] = bb.bollinger_lband()
    return df

def detect_bullish_engulfing_on_upper_band(df):
    if len(df) < 2:
        return False
    last, prev = df.iloc[-1], df.iloc[-2]
    bullish_engulf = (
        prev["Close"] < prev["Open"] and
        last["Close"] > last["Open"] and
        last["Close"] > prev["Open"] and
        last["Open"] < prev["Close"]
    )
    on_upper_band = last["Close"] >= last["bb_high"]
    return bullish_engulf and on_upper_band

def detect_bearish_engulfing_on_lower_band(df):
    if len(df) < 2:
        return False
    last, prev = df.iloc[-1], df.iloc[-2]
    bearish_engulf = (
        prev["Close"] > prev["Open"] and
        last["Close"] < last["Open"] and
        last["Close"] < prev["Open"] and
        last["Open"] > prev["Close"]
    )
    on_lower_band = last["Close"] <= last["bb_low"]
    return bearish_engulf and on_lower_band

def detect_double_top(df):
    # Simple double top: last three peaks, middle is the highest, and the two sides are similar and lower
    if len(df) < 5:
        return False
    highs = df["High"].values
    idx = np.argmax(highs[-5:])  # Index of the highest in the last 5
    if idx != 2:
        return False  # peak should be in the middle
    first = highs[-5]
    second = highs[-3]
    third = highs[-1]
    mid = highs[-3]
    # The two tops should be within 1% of each other, and both above the valleys
    if abs(first - third) / first < 0.01 and first > highs[-4] and third > highs[-2]:
        return True
    return False

def detect_double_bottom(df):
    # Simple double bottom: last three lows, middle is the lowest, and the two sides are similar and higher
    if len(df) < 5:
        return False
    lows = df["Low"].values
    idx = np.argmin(lows[-5:])  # Index of the lowest in the last 5
    if idx != 2:
        return False  # valley should be in the middle
    first = lows[-5]
    second = lows[-3]
    third = lows[-1]
    mid = lows[-3]
    # The two bottoms should be within 1% of each other, and both below the peaks
    if abs(first - third) / first < 0.01 and first < lows[-4] and third < lows[-2]:
        return True
    return False

def scan_all_assets():
    results = []
    for pair in FOREX_PAIRS:
        df = get_alpha_vantage_fx(pair, FOREX_INTERVAL, FOREX_LOOKBACK)
        if df is None or len(df) < 21:
            continue
        df = calculate_indicators(df)
        price = df.iloc[-1]["Close"]
        ts = df.iloc[-1]["Time"]
        name = f"{pair[0]}/{pair[1]}"
        # Double Top/Bottom
        if detect_double_top(df):
            results.append(f"{ts} | {name} | DOUBLE TOP detected @ {price:.5f}")
        if detect_double_bottom(df):
            results.append(f"{ts} | {name} | DOUBLE BOTTOM detected @ {price:.5f}")
        # Bullish Engulfing on Upper Bollinger
        if detect_bullish_engulfing_on_upper_band(df):
            results.append(f"{ts} | {name} | Bullish Engulfing ON UPPER BB @ {price:.5f}")
        # Bearish Engulfing on Lower Bollinger
        if detect_bearish_engulfing_on_lower_band(df):
            results.append(f"{ts} | {name} | Bearish Engulfing ON LOWER BB @ {price:.5f}")
        time.sleep(1.5)  # avoid hitting API rate limit

    for symbol in CRYPTO_PAIRS:
        df = get_binance_klines(symbol, CRYPTO_INTERVAL, CRYPTO_LOOKBACK)
        if df is None or len(df) < 21:
            continue
        df = calculate_indicators(df)
        price = df.iloc[-1]["Close"]
        ts = df.iloc[-1]["Time"]
        name = symbol.replace("USDT", "/USD")
        if detect_double_top(df):
            results.append(f"{ts} | {name} | DOUBLE TOP detected @ {price:.2f}")
        if detect_double_bottom(df):
            results.append(f"{ts} | {name} | DOUBLE BOTTOM detected @ {price:.2f}")
        if detect_bullish_engulfing_on_upper_band(df):
            results.append(f"{ts} | {name} | Bullish Engulfing ON UPPER BB @ {price:.2f}")
        if detect_bearish_engulfing_on_lower_band(df):
            results.append(f"{ts} | {name} | Bearish Engulfing ON LOWER BB @ {price:.2f}")
    return results

def send_telegram_alert(message):
    url = (
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        f"?chat_id={TELEGRAM_CHAT_ID}&text={requests.utils.quote(message)}"
    )
    try:
        requests.get(url)
    except Exception as e:
        print(f"Telegram alert failed: {e}")

# --- Telegram Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=(
        "Welcome to Multi-Asset Pattern Scanner Bot!\n"
        "Use /scan to manually scan all assets for Double Top/Bottom, Bullish Engulfing (upper BB), Bearish Engulfing (lower BB).\n"
        "It will also auto-scan every 15 minutes."
    ))

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Manual scan started...")
    results = scan_all_assets()
    if results:
        for msg in results:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No patterns detected.")

def background_auto_scan():
    while True:
        results = scan_all_assets()
        for msg in results:
            send_telegram_alert(msg)
        print("-" * 40)
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    # Start background thread for auto scan
    t = threading.Thread(target=background_auto_scan, daemon=True)
    t.start()

    # Start Telegram bot
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    print("Multi-Asset Pattern Scanner Bot with Telegram Commands Started!")
    app.run_polling()