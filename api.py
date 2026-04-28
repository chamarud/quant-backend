from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import uvicorn
import json
import os
import asyncio
import random
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Initialize App & VADER
app = FastAPI()
analyzer = SentimentIntensityAnalyzer()

# CORS: Allows your React frontend (and Vercel) to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Asset Universe
TICKERS = {
    "crypto": [("BTC-USD", "Bitcoin"), ("ETH-USD", "Ethereum"), ("SOL-USD", "Solana")],
    "stocks": [("AAPL", "Apple"), ("TSLA", "Tesla"), ("NVDA", "Nvidia")],
    "forex": [("EURUSD=X", "EUR/USD"), ("GBPUSD=X", "GBP/USD"), ("JPY=X", "USD/JPY")]
}

def get_ai_sentiment(ticker):
    """Fetches recent news via yfinance and analyzes sentiment using VADER."""
    try:
        asset = yf.Ticker(ticker)
        news = asset.news
        if news and len(news) > 0:
            title = news[0]['title']
            score = analyzer.polarity_scores(title)['compound']
        else:
            score = 0
            
        if score > 0.05: return "BULLISH"
        elif score < -0.05: return "BEARISH"
        else: return "NEUTRAL"
    except:
        return "NEUTRAL"

@app.get("/api/history")
def get_history():
    """Mock database for the history tab."""
    return [
        {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "pair": "BTC-USD", "action": "BUY", "price": "67,450.00"},
        {"timestamp": "2024-05-19 09:15", "pair": "EURUSD=X", "action": "SELL", "price": "1.0845"},
        {"timestamp": "2024-05-18 16:45", "pair": "NVDA", "action": "BUY", "price": "945.20"}
    ]

@app.get("/api/screener")
def get_screener(category: str = "crypto"):
    """Pulls historical data, calculates indicators, and runs VADER sentiment."""
    assets = TICKERS.get(category, TICKERS["crypto"])
    results = []
    
    for raw, name in assets:
        try:
            ticker = yf.Ticker(raw)
            hist = ticker.history(period="1mo")
            if hist.empty: continue

            current_price = float(hist['Close'].iloc[-1])
            prices = hist['Close'].tolist()
            sparkline = prices[-15:] if len(prices) >= 15 else prices
            
            # Simple algorithmic mock for the UI based on price action
            trend = "UP" if current_price > hist['Close'].iloc[-2] else "DOWN"
            rsi = random.randint(30, 70) # Replace with actual pandas TA calc if needed

            results.append({
                "Raw_Ticker": raw,
                "Pair": name,
                "Price": round(current_price, 4),
                "hist": sparkline,
                "A1": "STRONG BUY" if trend == "UP" else "SELL",
                "A2": "BULL FLAG" if trend == "UP" else "BEAR PENNANT",
                "Pat": "Breakout" if trend == "UP" else "Consolidation",
                "RSI": rsi,
                "Trend": trend,
                "AI": get_ai_sentiment(raw)
            })
        except Exception as e:
            print(f"Error loading {raw}: {e}")
            
    return results

@app.websocket("/ws/market")
async def websocket_endpoint(websocket: WebSocket):
    """Streams live price updates to make the frontend flash."""
    await websocket.accept()
    
    # Store base prices so we can simulate realistic live ticks
    base_prices = {}
    for cat in TICKERS.values():
        for raw, _ in cat:
            try:
                base_prices[raw] = yf.Ticker(raw).history(period="1d")['Close'].iloc[-1]
            except:
                base_prices[raw] = 100.0

    try:
        while True:
            updates = {}
            for ticker, base in base_prices.items():
                # Wiggle the price slightly (0.05%) to simulate live market ticks
                wiggle = base * random.uniform(-0.0005, 0.0005)
                new_price = base + wiggle
                base_prices[ticker] = new_price # update base
                updates[ticker] = round(new_price, 4)

            now = datetime.now().strftime("%H:%M:%S")
            await websocket.send_json({
                "type": "PRICE_UPDATE",
                "timestamp": now,
                "updates": updates
            })
            await asyncio.sleep(2) # Send a tick every 2 seconds
            
    except WebSocketDisconnect:
        print("Client disconnected from WebSocket")

if __name__ == "__main__":
    # Render assigns a dynamic port. If running locally, defaults to 8000.
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)