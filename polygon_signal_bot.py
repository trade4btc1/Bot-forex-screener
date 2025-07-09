import os
import time
import requests
import pandas as pd
import numpy as np
import ta

# User settings
API_KEY = "YOUR_POLYGON_API_KEY"
TICKER = "AAPL"
INTERVAL = "5"  # 1, 5, 15, 30, or day
LOOKBACK = 100  # Number of candles to fetch
POLL_SECONDS = 60  # How often to poll for new data

def get_polygon_bars(ticker, interval, limit=100):
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/"
        f"{interval}/minute/2024-01-01/{pd.Timestamp.now().strftime('%Y-%m-%d')}?adjusted=true&limit={limit}&sort=desc&apiKey={API_KEY}"
    )
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    if "results" not in data:
        raise Exception("No data from Polygon")
    df = pd.DataFrame(data["results"])
    df = df.iloc[::-1].reset_index(drop=True)  # Oldest first
    df["t"] = pd.to_datetime(df["t"], unit="ms")
    df = df.rename(columns={"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"})
    return df[["t", "Open", "High", "Low", "Close", "Volume"]]

def calculate_indicators(df):
    df["ema20"] = ta.trend.ema_indicator(df["Close"], window=20)
    df["rsi14"] = ta.momentum.rsi(df["Close"], window=14)
    macd = ta.trend.macd(df["Close"])
    macd_signal = ta.trend.macd_signal(df["Close"])
    df["macd"] = macd
    df["macd_signal"] = macd_signal
    return df

def detect_price_patterns(df):
    # Simple bullish engulfing pattern
    last, prev = df.iloc[-1], df.iloc[-2]
    bullish_engulfing = (
        prev["Close"] < prev["Open"] and    # Previous bearish
        last["Close"] > last["Open"] and    # Last bullish
        last["Close"] > prev["Open"] and
        last["Open"] < prev["Close"]
    )
    return {"bullish_engulfing": bullish_engulfing}

def generate_signal(df):
    signal = None
    price = df.iloc[-1]["Close"]
    rsi = df.iloc[-1]["rsi14"]
    ema = df.iloc[-1]["ema20"]
    macd = df.iloc[-1]["macd"]
    macd_sig = df.iloc[-1]["macd_signal"]
    patterns = detect_price_patterns(df)
    
    # Example logic (combine all signals)
    if (
        price > ema and
        rsi > 50 and
        macd > macd_sig and
        patterns["bullish_engulfing"]
    ):
        signal = "BUY"
    elif (
        price < ema and
        rsi < 50 and
        macd < macd_sig
    ):
        signal = "SELL"
    return signal

def main():
    print("Polygon.io Signal Bot Started")
    while True:
        try:
            df = get_polygon_bars(TICKER, INTERVAL, LOOKBACK)
            df = calculate_indicators(df)
            sig = generate_signal(df)
            price = df.iloc[-1]["Close"]
            ts = df.iloc[-1]["t"]
            if sig:
                print(f"{ts} | {TICKER} | {sig} @ ${price:.2f}")
            else:
                print(f"{ts} | {TICKER} | No clear signal @ ${price:.2f}")
        except Exception as e:
            print("Error:", e)
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()