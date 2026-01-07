import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
import numpy as np

# -------------------------
# CONFIG STREAMLIT
# -------------------------
st.set_page_config(
    page_title="Heikin Ashi Screener",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Screener Heikin Ashi – Inversione Rialzista")

st.markdown("""
**Condizione di ricerca**
- 🔴 Heikin Ashi **altro ieri rossa**
- 🟢 Heikin Ashi **ieri verde**
""")

# -------------------------
# DEFAULT SYMBOLS ITALIA
# -------------------------
SYMBOLS = [
    "A2A.MI", "AMP.MI", "BAMI.MI", "BC.MI", "BGN.MI", "BMPS.MI", "BPE.MI", 
    "BMED.MI", "BST.MI", "CE.MI", "CPR.MI", "DIA.MI", "ENEL.MI", "ENI.MI", 
    "ERG.MI", "FBK.MI", "GEO.MI", "IG.MI", "INRG.MI", "ISP.MI", "IVG.MI", 
    "LDO.MI", "MB.MI", "MONC.MI", "NEXI.MI", "PRY.MI", "PST.MI", "RACE.MI", 
    "REC.MI", "SFER.MI", "SPM.MI", "STLAM.MI", "STMMI.MI", "TES.MI", "TEN.MI", 
    "TGYM.MI", "TIT.MI", "TRN.MI", "UCG.MI", "UNI.MI"
]

# -------------------------
# DATA FETCH
# -------------------------
@st.cache_data(ttl=3600)
def fetch_all_data(symbols, start, end):
    try:
        data = yf.download(symbols, start=start, end=end, group_by='ticker', progress=False)
        return data
    except Exception as e:
        st.error(f"Errore fetch dati: {e}")
        return None

# -------------------------
# HEIKIN ASHI
# -------------------------
def heikin_ashi(df):
    df = df.copy()
    # Assicuriamoci che siano numerici
    for col in ['Open', 'High', 'Low', 'Close']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['Open','High','Low','Close'])

    df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = [(df['Open'].iloc[0] + df['Close'].iloc[0]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + df['HA_Close'].iloc[i-1]) / 2)
    df['HA_Open'] = ha_open

    df['HA_High'] = df[['High','HA_Open','HA_Close']].max(axis=1)
    df['HA_Low'] = df[['Low','HA_Open','HA_Close']].min(axis=1)
    return df

# -------------------------
# ANALISI PATTERN
# -------------------------
def analyze_stock(symbol, all_data):
    try:
        df = all_data[symbol].copy()
    except KeyError:
        return None

    if df.empty or len(df) < 3:
        return None

    ha = heikin_ashi(df)
    yesterday = ha.iloc[-2]
    day_before = ha.iloc[-3]

    if yesterday['HA_Close'] > yesterday['HA_Open'] and day_before['HA_Close'] < day_before['HA_Open']:
        return {"symbol": symbol, "ha": ha}
    return None

# -------------------------
# RUN SCREENER
# -------------------------
end = date.today() + timedelta(days=1)
start = end - timedelta(days=15)

with st.spinner("Analisi in corso..."):
    all_data = fetch_all_data(SYMBOLS, start, end)
    results = []
    if all_data is not None:
        for s in SYMBOLS:
            r = analyze_stock(s, all_data)
            if r:
                results.append(r)

# -------------------------
# RISULTATI
# -------------------------
if results:
    st.success(f"✅ Trovati {len(results)} titoli con inversione rialzista")
    df_results = pd.DataFrame({"Simbolo": [r["symbol"] for r in results]})
    st.dataframe(df_results, use_container_width=True)

    # -------------------------
    # GRAFICO HEIKIN ASHI
    # -------------------------
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
    if 'Volume' in ha.columns:
        fig.add_trace(go.Bar(
            x=ha.index,
            y=ha['Volume'],
            name="Volume",
            marker_color='blue',
            yaxis="y2",
            opacity=0.3
        ))

    fig.update_layout(
        title=f"{selected} – Grafico Heikin Ashi",
        xaxis_title="Data",
        yaxis_title="Prezzo",
        yaxis2=dict(title='Volume', overlaying='y', side='right', showgrid=False),
        height=600,
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("❌ Nessun titolo soddisfa il pattern Heikin Ashi")

# -------------------------
# INFO
# -------------------------
with st.expander("ℹ️ Logica del Pattern"):
    st.markdown("""
    **Pattern di inversione Heikin Ashi**
    - Candela rossa → perdita di momentum
    - Candela verde successiva → possibile ripartenza
    - Filtra rumore di mercato rispetto alle candele classiche
    """)

st.markdown("---")
st.caption("Dati Yahoo Finance • Analisi Heikin Ashi")
