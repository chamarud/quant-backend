import yfinance as yf
import pandas as pd
import pandas_ta as ta
from transformers import pipeline

# --- AI Setup ---
print("Loading FinBERT AI Model...")
sentiment_analyzer = pipeline("sentiment-analysis", model="ProsusAI/finbert")

def get_forex_data(ticker):
    """Pulls historical data and cleans the formatting."""
    df = yf.download(ticker, period="1y", interval="1d", progress=False)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df

def calculate_indicators(df):
    """Calculates SMA, EMA, RSI, and Volume trends."""
    df.ta.sma(length=50, append=True)
    df.ta.ema(length=200, append=True)
    df.ta.rsi(length=14, append=True)
    df['Volume_SMA_20'] = df['Volume'].rolling(window=20).mean()
    df.dropna(inplace=True)
    return df

def get_ai_sentiment(ticker_symbol):
    """Pulls recent news headlines and uses AI to determine sentiment."""
    ticker = yf.Ticker(ticker_symbol)
    news = ticker.news
    
    if not news:
        return "Neutral (No News)"
        
    # THE FIX: Safely extract titles to prevent KeyErrors from ads/videos
    headlines = []
    for article in news[:5]:
        if 'title' in article:
            headlines.append(article['title'])
        # Handle alternate yfinance formats just in case
        elif 'content' in article and 'title' in article['content']: 
            headlines.append(article['content']['title'])
            
    if not headlines:
         return "Neutral (No Readable Headlines)"
    
    # Feed headlines to the AI
    ai_results = sentiment_analyzer(headlines)
    
    # Tally the results
    positive = sum(1 for res in ai_results if res['label'] == 'positive')
    negative = sum(1 for res in ai_results if res['label'] == 'negative')
    
    if positive > negative:
        return "Bullish"
    elif negative > positive:
        return "Bearish"
    else:
        return "Mixed / Neutral"

# --- Main Screener Loop ---
if __name__ == "__main__":
    # List of major forex pairs to scan
    forex_pairs = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]
    
    print("\nStarting AI-Powered Screener Scan...\n" + "="*40)
    
    dashboard_data = []

    for pair in forex_pairs:
        print(f"Scanning {pair}...")
        
        # 1. Technical Analysis
        raw_data = get_forex_data(pair)
        if raw_data is not None:
            processed_data = calculate_indicators(raw_data)
            latest_data = processed_data.iloc[-1] 
            
            # 2. AI Fundamental/News Analysis
            ai_sentiment = get_ai_sentiment(pair)
            
            # 3. Determine basic Technical Trend
            tech_trend = "Uptrend" if latest_data['Close'] > latest_data['EMA_200'] else "Downtrend"
            
            # 4. Save results
            dashboard_data.append({
                "Pair": pair.replace("=X", ""), 
                "Price": round(latest_data['Close'], 4),
                "RSI": round(latest_data['RSI_14'], 2),
                "Tech Trend": tech_trend,
                "AI Sentiment": ai_sentiment
            })

    # --- Print the Final Dashboard ---
    print("\n" + "="*40)
    print("        SCREENER RESULTS DASHBOARD")
    print("="*40)
    results_df = pd.DataFrame(dashboard_data)
    results_df.set_index('Pair', inplace=True) 
    print(results_df.to_string())
    print("="*40)