import requests
import pandas as pd
import datetime
import ta

POLYGON_API_KEY = "YOUR_POLYGON_API_KEY"

def fetch_polygon_data(ticker, interval='15', limit=100):
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{interval}/minute/2024-01-01/{today}?adjusted=true&limit={limit}&sort=desc&apiKey={POLYGON_API_KEY}"
    
    response = requests.get(url)
    data = response.json()
    
    if "results" not in data:
        print(f"No data from Polygon for {ticker}")
        return None

    df = pd.DataFrame(data['results']).iloc[::-1]
    df['t'] = pd.to_datetime(df['t'], unit='ms')
    df.rename(columns={'o':'Open', 'h':'High', 'l':'Low', 'c':'Close', 'v':'Volume'}, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def detect_engulfing(df):
    if len(df) < 2:
        return None

    prev = df.iloc[-2]
    curr = df.iloc[-1]
    
    bullish = (
        prev['Close'] < prev['Open'] and
        curr['Close'] > curr['Open'] and
        curr['Close'] > prev['Open'] and
        curr['Open'] < prev['Close']
    )

    bearish = (
        prev['Close'] > prev['Open'] and
        curr['Close'] < curr['Open'] and
        curr['Open'] > prev['Close'] and
        curr['Close'] < prev['Open']
    )
    
    return "Bullish Engulfing" if bullish else "Bearish Engulfing" if bearish else None

def run_screener():
    tickers = {
        "C:EURUSD": "EUR/USD",
        "C:XAUUSD": "XAU/USD",
        "C:XAGUSD": "XAG/USD",
        "X:BTCUSD": "BTC/USD",
        "X:ETHUSD": "ETH/USD"
    }
    
    for symbol, name in tickers.items():
        df = fetch_polygon_data(symbol)
        if df is None:
            continue

        pattern = detect_engulfing(df)
        if pattern:
            latest = df.iloc[-1]
            price = latest['Close']
            time = latest['t']
print(f"{pattern} detected on {name} at {price:.2f} ({time})\n📌 Sans D Fx Trader")
