import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
import io

# -------------------------
# PAGE CONFIG
# -------------------------
st.set_page_config(
    page_title="Heikin Ashi Screener",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Screener Heikin Ashi – Inversione Rialzista")
st.markdown("""
**Pattern di ricerca:**  
- 🔴 Candela Heikin Ashi **giorno prima ieri** rossa  
- 🟢 Candela Heikin Ashi **ieri** verde
""")

# -------------------------
# DEFAULT SYMBOLS
# -------------------------
DEFAULT_SYMBOLS = [
    "AAPL","MSFT","AMZN","GOOGL","META","NVDA","TSLA",
    "AMD","NFLX","INTC","IBM","ORCL","CRM","PYPL",
    "JPM","BAC","WFC","GS","V","MA",
    "JNJ","PFE","UNH","ABBV",
    "KO","PEP","MCD","WMT","HD",
    "XOM","CVX","CAT","BA",
    "SPY","QQQ","IWM"
]

# -------------------------
# UPLOAD FILE SYMBOLS
# -------------------------
st.sidebar.header("📁 Carica simboli")
uploaded_file = st.sidebar.file_uploader(
    "Carica file TXT con simboli (uno per riga o separati da virgola)",
    type=['txt']
)

if uploaded_file is not None:
    try:
        file_content = uploaded_file.read().decode('utf-8')
        file_symbols = []
        for line in file_content.strip().split('\n'):
            line_symbols = [s.strip().upper() for s in line.split(',') if s.strip()]
            file_symbols.extend(line_symbols)
        SYMBOLS = list(dict.fromkeys(file_symbols))
        st.sidebar.success(f"✅ Caricati {len(SYMBOLS)} simboli dal file")
        st.sidebar.info(f"Simboli: {', '.join(SYMBOLS[:10])}{'...' if len(SYMBOLS) > 10 else ''}")
    except Exception as e:
        st.sidebar.error(f"❌ Errore nella lettura del file: {str(e)}")
        SYMBOLS = DEFAULT_SYMBOLS
else:
    SYMBOLS = DEFAULT_SYMBOLS
    st.sidebar.info(f"🔍 Analisi dei {len(DEFAULT_SYMBOLS)} simboli predefiniti")

# -------------------------
# FETCH DATA
# -------------------------
@st.cache_data
def fetch_stock_data(symbol, start, end):
    try:
        df = yf.download(symbol, start=start, end=end, progress=False)
        if df.empty:
            return None
        return df
    except:
        return None

# -------------------------
# HEIKIN ASHI CALCULATION
# -------------------------
def heikin_ashi(df):
    df = df.copy()
    required_cols = ['Open','High','Low','Close']
    for col in required_cols:
        if col not in df.columns:
            return None
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=required_cols)

    ha = df.copy()
    ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = [(df['Open'].iloc[0] + df['Close'].iloc[0]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + ha['HA_Close'].iloc[i-1]) / 2)
    ha['HA_Open'] = ha_open
    ha['HA_High'] = ha[['High','HA_Open','HA_Close']].max(axis=1)
    ha['HA_Low'] = ha[['Low','HA_Open','HA_Close']].min(axis=1)
    return ha

# -------------------------
# ANALYZE STOCK
# -------------------------
def analyze_stock(symbol):
    end = date.today() + timedelta(days=1)
    start = end - timedelta(days=60)
    df = fetch_stock_data(symbol, start, end)
    if df is None or len(df) < 3:
        return None

    ha = heikin_ashi(df)
    if ha is None or len(ha) < 3:
        return None

    ha_valid = ha.dropna(subset=['HA_Open','HA_Close','HA_High','HA_Low'])
    if len(ha_valid) < 3:
        return None

    yesterday = ha_valid.iloc[-2]
    day_before = ha_valid.iloc[-3]

    if (day_before['HA_Close'] < day_before['HA_Open']) and (yesterday['HA_Close'] > yesterday['HA_Open']):
        return {"symbol": symbol, "ha": ha_valid}

    return None

# -------------------------
# RUN SCREENER
# -------------------------
with st.spinner("Analisi in corso..."):
    results = []
    for s in SYMBOLS:
        r = analyze_stock(s)
        if r:
            results.append(r)

# -------------------------
# SHOW RESULTS
# -------------------------
if results:
    st.success(f"✅ Trovati {len(results)} titoli")
    df_results = pd.DataFrame({"Simbolo": [r["symbol"] for r in results]})
    st.dataframe(df_results, use_container_width=True)

    selected = st.selectbox("Seleziona un titolo per il grafico Heikin Ashi", df_results["Simbolo"])
    selected_data = next(r for r in results if r["symbol"] == selected)
    ha = selected_data["ha"].tail(30)

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=ha.index,
        open=ha['HA_Open'],
        high=ha['HA_High'],
        low=ha['HA_Low'],
        close=ha['HA_Close'],
        increasing_line_color='green',
        decreasing_line_color='red',
        name="Heikin Ashi"
    ))
    fig.update_layout(title=f"{selected} – Grafico Heikin Ashi", xaxis_title="Data", yaxis_title="Prezzo", height=600)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("❌ Nessun titolo soddisfa il pattern Heikin Ashi")

st.markdown("---")
st.caption("Dati Yahoo Finance • Analisi Heikin Ashi")
