import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
import numpy as np

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
# DEFAULT SYMBOLS
# -------------------------
SYMBOLS = [
    "A2A.MI", "AMP.MI", "BAMI.MI", "BC.MI", "BGN.MI", "BMPS.MI", "BPE.MI", "BMED.MI", 
    "BST.MI", "CE.MI", "CPR.MI", "DIA.MI", "ENEL.MI", "ENI.MI", "ERG.MI", "FBK.MI", 
    "GEO.MI", "IG.MI", "INRG.MI", "ISP.MI", "IVG.MI", "LDO.MI", "MB.MI", "MONC.MI", 
    "NEXI.MI", "PRY.MI", "PST.MI", "RACE.MI", "REC.MI", "SFER.MI", "SPM.MI", 
    "STLAM.MI", "STMMI.MI", "TES.MI", "TEN.MI", "TGYM.MI", "TIT.MI", "TRN.MI", 
    "UCG.MI", "UNI.MI"
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
    ha = df.copy()
    
    # Calcola HA_Close
    ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # Calcola HA_Open (ricorsivo)
    ha_open = [(df['Open'].iloc[0] + df['Close'].iloc[0]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + ha['HA_Close'].iloc[i-1]) / 2)
    
    ha['HA_Open'] = ha_open
    ha['HA_High'] = ha[['High', 'HA_Open', 'HA_Close']].max(axis=1)
    ha['HA_Low'] = ha[['Low', 'HA_Open', 'HA_Close']].min(axis=1)
    
    return ha

# -------------------------
# ANALISI CORRETTA
# -------------------------
def analyze_stock(symbol, all_data):
    try:
        df = all_data[symbol].copy()
    except KeyError:
        return None
    
    if df.empty or len(df) < 4:
        return None
    
    # Converti in Heikin Ashi
    ha = heikin_ashi(df)
    
    # Aggiungi colonne colore e data
    ha['Is_Green'] = ha['HA_Close'] > ha['HA_Open']
    ha['Date'] = ha.index
    
    # Prendi solo i giorni di trading (rimuovi NaN)
    ha = ha.dropna(subset=['HA_Close', 'HA_Open'])
    
    if len(ha) < 3:
        return None
    
    # Ottieni le ultime 3 candele con date valide
    recent = ha.tail(3).copy()
    
    # Ordina per data (più recente per ultimo)
    recent = recent.sort_index()
    
    # Debug: mostra le ultime candele per il simbolo corrente
    debug_info = {
        'symbol': symbol,
        'dates': recent.index.strftime('%Y-%m-%d').tolist(),
        'is_green': recent['Is_Green'].tolist(),
        'ha_open': recent['HA_Open'].round(4).tolist(),
        'ha_close': recent['HA_Close'].round(4).tolist()
    }
    
    # Verifica che abbiamo almeno 3 giorni
    if len(recent) < 3:
        return None
    
    # La più recente (ieri) è in posizione -1
    # La seconda più recente (altro ieri) è in posizione -2
    yesterday = recent.iloc[-1]
    day_before = recent.iloc[-2]
    
    # DEBUG: Visualizza per verificare
    st.session_state.setdefault('debug_data', []).append(debug_info)
    
    # Condizione: ieri verde, altro ieri rosso
    condition_met = (yesterday['Is_Green'] == True) and (day_before['Is_Green'] == False)
    
    if condition_met:
        return {
            "symbol": symbol,
            "ha": ha,
            "debug": debug_info
        }
    return None

# -------------------------
# RUN SCREENER
# -------------------------
# Prendiamo più dati per assicurarci di avere almeno 3 giorni di trading
end = date.today() + timedelta(days=1)
start = end - timedelta(days=30)  # 30 giorni per sicurezza

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
    st.success(f"✅ Trovati {len(results)} titoli")
    
    # Mostra tabella risultati
    df_results = pd.DataFrame({
        "Simbolo": [r["symbol"] for r in results],
        "Data Ieri": [r["debug"]["dates"][-1] for r in results],
        "Data Altro Ieri": [r["debug"]["dates"][-2] for r in results],
        "Colore Ieri": ["🟢 Verde" for r in results],
        "Colore Altro Ieri": ["🔴 Rosso" for r in results]
    })
    
    st.dataframe(df_results, use_container_width=True)
    
    # -------------------------
    # SELEZIONE GRAFICO E DEBUG
    # -------------------------
    selected = st.selectbox("Seleziona un titolo per il grafico Heikin Ashi", df_results["Simbolo"])
    selected_data = next(r for r in results if r["symbol"] == selected)
    ha = selected_data["ha"].tail(30)
    
    # DEBUG: Mostra info delle candele
    with st.expander(f"🔍 Debug per {selected}"):
        debug_info = selected_data["debug"]
        st.write(f"**Simbolo:** {debug_info['symbol']}")
        st.write(f"**Date:** {debug_info['dates']}")
        st.write(f"**Colore (True=verde):** {debug_info['is_green']}")
        st.write(f"**HA Open:** {debug_info['ha_open']}")
        st.write(f"**HA Close:** {debug_info['ha_close']}")
        
        # Verifica condizione
        if len(debug_info['is_green']) >= 3:
            cond1 = f"Ieri (pos. -1): {debug_info['dates'][-1]} - {'Verde' if debug_info['is_green'][-1] else 'Rosso'}"
            cond2 = f"Altro ieri (pos. -2): {debug_info['dates'][-2]} - {'Verde' if debug_info['is_green'][-2] else 'Rosso'}"
            st.write(f"**Condizione:** {cond1} | {cond2}")
            st.write(f"**Pattern trovato:** {'✅ SÌ' if debug_info['is_green'][-1] and not debug_info['is_green'][-2] else '❌ NO'}")
    
    # Grafico
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
    
    # Aggiungi volume se disponibile
    if 'Volume' in ha.columns:
        fig.add_trace(go.Bar(
            x=ha.index,
            y=ha['Volume'],
            name="Volume",
            marker_color='blue',
            yaxis="y2",
            opacity=0.3
        ))
    
    # Evidenzia le 2 candele rilevanti
    if len(ha) >= 2:
        fig.add_vrect(
            x0=ha.index[-2], x1=ha.index[-1],
            fillcolor="rgba(255,255,0,0.1)",
            layer="below",
            line_width=0,
            annotation_text="Pattern",
            annotation_position="top left"
        )
    
    fig.update_layout(
        title=f"{selected} – Grafico Heikin Ashi (Ultimi 30 giorni)",
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
    
    **Condizione specifica:**
    1. 🔴 **Altro ieri**: Candela Heikin Ashi ROSSA (Close < Open)
    2. 🟢 **Ieri**: Candela Heikin Ashi VERDE (Close > Open)
    
    **Nota:** Lo script ora verifica esplicitamente le date e gestisce correttamente i giorni senza trading.
    """)

st.markdown("---")
st.caption("Dati Yahoo Finance • Analisi Heikin Ashi")