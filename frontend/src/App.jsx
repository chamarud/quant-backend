import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { supabase } from './supabaseClient';
import './App.css';

// =====================================================================
// 🛑 CONFIGURATION: PASTE YOUR LIVE LINKS HERE
// =====================================================================
const STRIPE_PAYMENT_LINK = "https://buy.stripe.com/4gM4gAgBvgziekN6Dm7IY00"; 
const BACKEND_API_URL = "https://quant-backend-7uo3.onrender.com"; 
const WEBSOCKET_URL = "wss://quant-backend-7uo3.onrender.com/ws/market"; 
// =====================================================================

// --- 1. THE AUTHENTICATION LANDING PAGE ---
const AuthPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');
    try {
      if (isLogin) {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      } else {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        alert('Check your email for the confirmation link!');
      }
    } catch (error) {
      setErrorMsg(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        <h1>QUANT<span>TERMINAL</span></h1>
        <p className="subtitle">Institutional-Grade Market Intelligence</p>
        <form onSubmit={handleAuth} className="auth-form">
          {errorMsg && <div className="error-banner">{errorMsg}</div>}
          <input type="email" placeholder="Email Address" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          <button type="submit" disabled={loading} className="auth-submit-btn">
            {loading ? 'Authenticating...' : isLogin ? 'Access Terminal' : 'Create Account'}
          </button>
        </form>
        <p className="auth-switch" onClick={() => setIsLogin(!isLogin)}>
          {isLogin ? "Need an account? Sign up here." : "Already a member? Log in."}
        </p>
      </div>
    </div>
  );
};

// --- 2. THE PAYWALL ---
const PaywallPage = ({ session, onBypass }) => {
  return (
    <div className="auth-container">
      <div className="auth-box paywall-box">
        <h1>UNLOCK <span>PRO</span></h1>
        <p className="subtitle">You need an active subscription to access the live terminal.</p>
        <div className="pricing-card">
          <h2>$29<span>/month</span></h2>
          <ul className="features-list">
            <li>✅ Live Institutional Polygon Data</li>
            <li>✅ AI Sentiment Analysis (VADER)</li>
            <li>✅ V2 Quantitative Trend Filters</li>
            <li>✅ Dynamic Volatility Targets (ATR)</li>
          </ul>
          <a href={STRIPE_PAYMENT_LINK} target="_blank" rel="noreferrer" className="auth-submit-btn pay-btn">
            Subscribe Securely via Stripe
          </a>
          <button onClick={onBypass} className="bypass-btn">[Developer: Bypass Paywall]</button>
        </div>
        <div className="user-profile paywall-profile">
           <p className="user-email">Logged in as: {session.user.email}</p>
           <button className="logout-btn" onClick={() => supabase.auth.signOut()}>Sign Out</button>
        </div>
      </div>
    </div>
  );
};

// --- 3. THE PRO TRADINGVIEW COMPONENT ---
const TradingViewWidget = ({ symbol }) => {
  const container = useRef();
  useEffect(() => {
    let tvSymbol = symbol.replace('=X', '').replace('-', '');
    if (tvSymbol === 'BRKB') tvSymbol = 'BRK.B';
    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = `{"autosize": true, "symbol": "${tvSymbol}", "interval": "D", "timezone": "Etc/UTC", "theme": "dark", "style": "1", "locale": "en", "enable_publishing": false, "backgroundColor": "#0f172a", "gridColor": "#1e293b", "hide_top_toolbar": false, "hide_legend": false, "save_image": false, "container_id": "tradingview_widget"}`;
    container.current.appendChild(script);
    return () => { if (container.current) container.current.innerHTML = ''; }
  }, [symbol]);
  return <div className="tradingview-widget-container" ref={container} style={{ height: "100%", width: "100%" }} />;
}

// --- 4. THE MAIN SAAS TERMINAL ---
const TerminalSaaS = ({ session }) => {
  const [data, setData] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState('crypto'); 
  const [viewMode, setViewMode] = useState('dashboard');
  const [selectedAssetTicker, setSelectedAssetTicker] = useState(null);
  const [serverStatus, setServerStatus] = useState("Connecting...");
  const [lastUp, setLastUp] = useState("");
  const [flashTicker, setFlashTicker] = useState(null);

  const activeAsset = data.find(a => a.Raw_Ticker === selectedAssetTicker);

  useEffect(() => {
    // 1. Fetch Initial Data via REST API
    if (category === 'history') {
      setLoading(true);
      axios.get(`${BACKEND_API_URL}/api/history`).then(res => { setHistory(res.data); setLoading(false); });
      return; 
    } else {
      setLoading(true);
      axios.get(`${BACKEND_API_URL}/api/screener?category=${category}`)
        .then(res => { if (Array.isArray(res.data)) { setData(res.data); } setLoading(false); })
        .catch(() => setLoading(false));
    }

    // 2. Connect to Live WebSocket for Flashing Prices
    const ws = new WebSocket(WEBSOCKET_URL);
    ws.onopen = () => setServerStatus("LIVE");
    ws.onmessage = (event) => {
      const liveData = JSON.parse(event.data);
      if (liveData.type === "PRICE_UPDATE") {
        setLastUp(liveData.timestamp);
        setData(prevData => prevData.map(asset => {
          if (liveData.updates[asset.Raw_Ticker]) {
            const newPrice = liveData.updates[asset.Raw_Ticker].toFixed(4);
            setFlashTicker(asset.Raw_Ticker);
            setTimeout(() => setFlashTicker(null), 500); 
            return { ...asset, Price: newPrice };
          }
          return asset;
        }));
      }
    };
    ws.onclose = () => setServerStatus("OFFLINE");
    return () => ws.close();
  }, [category]);

  const renderSparkline = (h) => {
    if (!h || h.length === 0) return null;
    const min = Math.min(...h), max = Math.max(...h), r = max - min || 1;
    const pts = h.map((v, i) => `${(i/14)*300},${60-((v-min)/r)*60}`).join(' ');
    return (
      <div className="spark-wrapper">
        <svg viewBox="0 0 300 60"><polyline fill="none" stroke={h[14] >= h[0] ? '#22c55e' : '#ef4444'} strokeWidth="3" points={pts} /></svg>
      </div>
    );
  }

  if (viewMode === 'terminal' && activeAsset) {
    return (
      <div className="terminal-layout">
        <div className="terminal-header">
          <button className="back-btn" onClick={() => {setViewMode('dashboard'); setSelectedAssetTicker(null);}}>← BACK TO SCREENER</button>
          <h2>{activeAsset.Pair} Live Terminal</h2>
          <div className={`terminal-price ${flashTicker === activeAsset.Raw_Ticker ? 'flash' : ''}`}>${activeAsset.Price}</div>
        </div>
        <div className="terminal-body">
          <div className="chart-area"><TradingViewWidget symbol={activeAsset.Raw_Ticker} /></div>
          <div className="order-panel">
            <h3>Trade Setup</h3>
            <div className="setup-metrics">
              <p><span>AI Sentiment</span><strong className={activeAsset.AI.toLowerCase()}>{activeAsset.AI}</strong></p>
              <p><span>RSI / Trend</span><strong>{activeAsset.RSI} / {activeAsset.Trend}</strong></p>
              <p><span>Pattern</span><strong>{activeAsset.Pat}</strong></p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="logo">AI Screener</div>
        <nav className="menu">
          <button className={category === 'forex' ? 'active' : ''} onClick={() => setCategory('forex')}>🌍 Global Forex</button>
          <button className={category === 'stocks' ? 'active' : ''} onClick={() => setCategory('stocks')}>📈 US Stocks</button>
          <button className={category === 'crypto' ? 'active' : ''} onClick={() => setCategory('crypto')}>🪙 24/7 Crypto</button>
          <button className={category === 'history' ? 'active' : ''} onClick={() => setCategory('history')}>📜 History</button>
        </nav>
        <div className="user-profile">
          <p className="user-email">{session.user.email}</p>
          <button className="logout-btn" onClick={() => supabase.auth.signOut()}>Sign Out</button>
        </div>
      </aside>

      <main className="main-content">
        <header>
          <h1>{category.toUpperCase()} PULSE</h1>
          {category !== 'history' && (
            <div className="status-bar">
              <span className={`status-dot ${serverStatus === 'LIVE' ? 'live' : 'offline'}`}></span>
              <p>Server: <strong>{serverStatus}</strong> | Last Tick: {lastUp}</p>
            </div>
          )}
        </header>

        {loading ? <div className="loading">Initializing Quant Engine...</div> : category === 'history' ? (
          <div className="table-container">
            <table className="history-table">
              <thead><tr><th>Time</th><th>Asset</th><th>Action</th><th>Entry Price</th></tr></thead>
              <tbody>{history.map((h, i) => (<tr key={i}><td>{h.timestamp}</td><td>{h.pair}</td><td className={h.action.toLowerCase()}>{h.action}</td><td>{h.price}</td></tr>))}</tbody>
            </table>
          </div>
        ) : (
          <div className="card-grid">
            {data.map((p, i) => (
              <div key={i} className="card clickable" onClick={() => {setSelectedAssetTicker(p.Raw_Ticker); setViewMode('terminal');}}>
                <div className="card-header">
                  <h2>{p.Pair}</h2>
                  <span className={`price-label ${flashTicker === p.Raw_Ticker ? 'flash' : ''}`}>{p.Price}</span>
                </div>
                {renderSparkline(p.hist)}
                <div className="multi-algo-container">
                  <div className={`sig-box split ${p.A1.toLowerCase()}`}><span>Momentum</span><h3>{p.A1}</h3></div>
                  <div className={`sig-box split ${p.A2.toLowerCase()}`}><span>Pattern</span><h3>{p.A2}</h3><small>{p.Pat}</small></div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

// --- 5. THE GATEKEEPER (Main App Router) ---
export default function App() {
  const [session, setSession] = useState(null);
  const [loadingInit, setLoadingInit] = useState(true);
  const [isProUser, setIsProUser] = useState(false); 

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoadingInit(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      if (!session) setIsProUser(false); 
    });

    return () => subscription.unsubscribe();
  }, []);

  if (loadingInit) return <div className="loading">Loading Secure Vault...</div>;

  if (!session) return <AuthPage />;
  if (!isProUser) return <PaywallPage session={session} onBypass={() => setIsProUser(true)} />;
  
  return <TerminalSaaS session={session} />;
}