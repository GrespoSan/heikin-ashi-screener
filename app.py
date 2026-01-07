import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

# -------------------------
# CONFIG STREAMLIT
# -------------------------
st.set_page_config(
    page_title="Heikin Ashi Screener ITA",
    page_icon="📈",
    layout="wide"
)

st.title("📊 Screener Heikin Ashi – Titoli Italiani")
st.markdown("""
**Pattern di ricerca:**  
- 🔴 Heikin Ashi **altro ieri rossa**  
- 🟢 Heikin Ashi **ieri verde**
""")

# -------------------------
# SIMBOLI DEFAULT ITALIA
# -------------------------
DEFAULT_SYMBOLS = [
    "A2A.MI", "AMP.MI", "BAMI.MI", "BC.MI", "BGN.MI", "BMPS.MI", "BPE.MI",
    "BMED.MI", "BST.MI", "CE.MI", "CPR.MI", "DIA.MI", "ENEL.MI", "ENI.MI",
    "ERG.MI", "FBK.MI", "GEO.MI", "IG.MI", "INRG.MI", "ISP.MI", "IVG.MI",
    "LDO.MI", "MB.MI", "MONC.MI", "NEXI.MI", "PRY.MI", "PST.MI", "RACE.MI",
    "REC.MI", "SFER.MI", "SPM.MI", "STLAM.MI", "STMMI.MI", "TES.MI", "TEN.MI",
    "TGYM.MI", "TIT.MI", "TRN.MI", "UCG.MI", "UNI.MI"
]

# -------------------------
# UPLOAD FILE OPZIONALE
# -------------------------
uploaded_file = st.file_uploader("Carica file TXT con simboli (uno per riga)", type=['txt'])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    symbols = [s.strip().upper() for s in file_content.splitlines() if s.strip()]
    st.sidebar.success(f"Caricati {len(symbols)} simboli dal file")
else:
    symbols = DEFAULT_SYMBOLS
    st.sidebar.info(f"Analisi su {len(symbols)} simboli predefiniti")

# -------------------------
# CALCOLO HEIKIN ASHI
# -------------------------
def heikin_ashi(df):
    df = df.copy()
    df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = [(df['Open'].iloc[0] + df['Close'].iloc[0]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + df['HA_Close'].iloc[i-1]) / 2)
    df['HA_Open'] = ha_open
    df['HA_High'] = df[['High', 'HA_Open', 'HA_Close']].max(axis=1)
    df['HA_Low'] = df[['Low', 'HA_Open', 'HA_Close']].min(axis=1)
    return df

# -------------------------
# FETCH DATI YFINANCE
# -------------------------
@st.cache_data(ttl=3600)
def fetch_data(symbol, start, end):
    try:
        df = yf.download(symbol, start=start, end=end, progress=False)
        if df.empty:
            return None
        return df
    except:
        return None

# -------------------------
# ANALISI INVERSIONE
# -------------------------
def analyze_stock(symbol, start, end):
    df = fetch_data(symbol, start, end)
    if df is None or len(df) < 3:
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

results = []
with st.spinner(f"Analisi in corso per {len(symbols)} titoli..."):
    for s in symbols:
        r = analyze_stock(s, start, end)
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

st.caption("Dati Yahoo Finance • Analisi Heikin Ashi")
