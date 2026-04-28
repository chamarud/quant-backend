from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import uvicorn
import json
import os
import asyncio
import websockets
from datetime import datetime
from transformers import pipeline

print("Waking up V2 Quant Brain & Institutional Data Engine...")
sentiment_analyzer = pipeline("sentiment-analysis", model="ProsusAI/finbert")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

LOG_FILE = "signals_log.json"

# --- 1. WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"User Connected. Active Dashboards: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_data(self, data: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(data))
            except:
                pass

manager = ConnectionManager()

# --- 2. INSTITUTIONAL DATA FEED (Binance Free WebSocket) ---

async def binance_stream():
    """Connects to Binance's Public Feed - No API Key Required!"""
    # We listen to Bitcoin, Ethereum, and Solana (USD/Tether pairs)
    uri = "wss://stream.binance.com:9443/ws/btcusdt@ticker/ethusdt@ticker/solusdt@ticker"
    
    while True:
        try:
            async with websockets.connect(uri) as ws:
                print("🟢 Connected to Binance Live Feed (Free Institutional Data)!")
                
                while True:
                    message = await ws.recv()
                    data = json.loads(message)
                    
                    # Binance returns "s" for symbol and "c" for close price
                    raw_symbol = data.get("s")
                    price = float(data.get("c"))
                    
                    # Map Binance symbols to our App tickers
                    symbol_map = {
                        "BTCUSDT": "BTC-USD",
                        "ETHUSDT": "ETH-USD",
                        "SOLUSDT": "SOL-USD"
                    }
                    
                    react_ticker = symbol_map.get(raw_symbol)
                    if react_ticker:
                        live_update = {
                            "type": "PRICE_UPDATE",
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "updates": {react_ticker: round(price, 2)}
                        }
                        await manager.broadcast_data(live_update)
                        
        except Exception as e:
            print(f"🔴 Binance Feed Dropped: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    # Only one task: The free Binance stream
    asyncio.create_task(binance_stream())

# --- 3. QUANTITATIVE CORE LOGIC ---
def log_signal(pair, price, action, pattern, tp, sl):
    if action == "WAIT": return
    entry = {"timestamp": datetime.now().strftime("%H:%M:%S"), "pair": pair, "price": price, "action": action, "pattern": pattern, "tp": tp, "sl": sl}
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try: logs = json.load(f)
            except: logs = []
    if logs and logs[-1]["pair"] == pair and logs[-1]["action"] == action: return
    logs.append(entry)
    with open(LOG_FILE, "w") as f: json.dump(logs[-100:], f, indent=4)

def get_market_data(ticker_symbol):
    t = yf.Ticker(ticker_symbol)
    hist = t.history(period="1y")
    if hist.empty or len(hist) < 200: return {"Price": 0, "RSI": 50, "Trend": "Unknown", "SMA_200": 0, "ATR": 0, "hist": [], "df": None}
    
    prices = hist['Close'].tolist()
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = 100 - (100 / (1 + (gain / loss)))
    cur_rsi = round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else 50
    
    sma_200_series = hist['Close'].rolling(window=200).mean()
    cur_sma_200 = round(sma_200_series.iloc[-1], 4)
    
    hist['High-Low'] = hist['High'] - hist['Low']
    hist['High-PrevClose'] = abs(hist['High'] - hist['Close'].shift(1))
    hist['Low-PrevClose'] = abs(hist['Low'] - hist['Close'].shift(1))
    hist['TR'] = hist[['High-Low', 'High-PrevClose', 'Low-PrevClose']].max(axis=1)
    cur_atr = round(hist['TR'].rolling(window=14).mean().iloc[-1], 4)
    
    trend = "Macro Uptrend" if prices[-1] > cur_sma_200 else "Macro Downtrend"
    return {"Price": round(prices[-1], 4), "RSI": cur_rsi, "Trend": trend, "SMA_200": cur_sma_200, "ATR": cur_atr, "hist": prices[-15:], "df": hist}

def get_ai_sentiment(ticker):
    try:
        news = yf.Ticker(ticker).news
        if not news: return "Mixed"
        headlines = [a.get('title', '') for a in news[:3] if a.get('title')]
        if not headlines: return "Mixed"
        res = sentiment_analyzer(headlines)
        bull = sum(1 for r in res if r['label'] == 'positive')
        bear = sum(1 for r in res if r['label'] == 'negative')
        return "Bullish" if bull > bear else "Bearish" if bear > bull else "Mixed"
    except: return "Mixed"

# --- 4. ROUTES ---
@app.websocket("/ws/market")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/screener")
def get_screener(category: str = "forex"):
    forex = [{"name": "EUR/USD", "ticker": "EURUSD=X"}, {"name": "USD/JPY", "ticker": "USDJPY=X"}, {"name": "GBP/USD", "ticker": "GBPUSD=X"}, {"name": "USD/CHF", "ticker": "USDCHF=X"}, {"name": "AUD/USD", "ticker": "AUDUSD=X"}]
    stocks = [{"name": "Apple", "ticker": "AAPL"}, {"name": "Microsoft", "ticker": "MSFT"}, {"name": "Nvidia", "ticker": "NVDA"}, {"name": "Tesla", "ticker": "TSLA"}]
    crypto = [{"name": "Bitcoin", "ticker": "BTC-USD"}, {"name": "Ethereum", "ticker": "ETH-USD"}, {"name": "Solana", "ticker": "SOL-USD"}]
    
    target = stocks if category == "stocks" else crypto if category == "crypto" else forex
    final = []
    
    for a in target:
        m = get_market_data(a["ticker"])
        if m["SMA_200"] == 0: continue
        s = get_ai_sentiment(a["ticker"])
        
        p_price, sma, atr = m["Price"], m["SMA_200"], m["ATR"]
        a1 = "BUY" if (s == "Bullish" and m["RSI"] < 55 and p_price > sma) else "SELL" if (s == "Bearish" and m["RSI"] > 45 and p_price < sma) else "WAIT"
        
        a2, pat = "WAIT", "Consolidating"
        if m["df"] is not None and len(m["df"]) >= 2:
            prev, curr = m["df"].iloc[-2], m["df"].iloc[-1]
            if prev['Close']<prev['Open'] and curr['Close']>curr['Open'] and curr['Open']<prev['Close'] and curr['Close']>prev['Open']: 
                if p_price > sma: a2, pat = "BUY", "Bullish Engulfing"
            elif prev['Close']>prev['Open'] and curr['Close']<curr['Open'] and curr['Open']>prev['Close'] and curr['Close']<prev['Open']: 
                if p_price < sma: a2, pat = "SELL", "Bearish Engulfing"
        
        master = a2 if a2 != "WAIT" else a1
        tp = round(p_price + (atr * 3.0), 4) if master == "BUY" else round(p_price - (atr * 3.0), 4) if master == "SELL" else "-"
        sl = round(p_price - (atr * 1.5), 4) if master == "BUY" else round(p_price + (atr * 1.5), 4) if master == "SELL" else "-"
        
        log_signal(a["name"], p_price, master, pat, tp, sl)
        final.append({"Pair": a["name"], "Raw_Ticker": a["ticker"], "Price": p_price, "RSI": m["RSI"], "Trend": m["Trend"], "hist": m["hist"], "AI": s, "A1": a1, "A2": a2, "Pat": pat, "TP": tp, "SL": sl, "Master": master})
    return final

@app.get("/api/history")
def get_history():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f: return json.load(f)[::-1]
    return []

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)