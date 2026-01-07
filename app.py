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
# DATA FETCH - VERSIONE CORRETTA
# -------------------------
@st.cache_data(ttl=3600)
def fetch_all_data(symbols, start, end):
    try:
        # Scarica i dati in modo diverso per gestire MultiIndex
        data = yf.download(symbols, start=start, end=end, group_by='ticker', progress=False, threads=True)
        return data
    except Exception as e:
        st.error(f"Errore fetch dati: {e}")
        return None

# -------------------------
# HEIKIN ASHI
# -------------------------
def heikin_ashi(df):
    """Calcola le candele Heikin Ashi da un DataFrame OHLC"""
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
    
    # Aggiungi colonna colore
    ha['Is_Green'] = ha['HA_Close'] > ha['HA_Open']
    
    return ha

# -------------------------
# ANALISI CORRETTA
# -------------------------
def analyze_stock(symbol, all_data):
    try:
        # Estrai i dati per il singolo simbolo dal MultiIndex
        if isinstance(all_data.columns, pd.MultiIndex):
            # Se abbiamo MultiIndex (download multiplo)
            df = all_data.xs(symbol, axis=1, level=0).copy()
        else:
            # Se abbiamo un singolo simbolo
            df = all_data.copy()
    except Exception as e:
        st.warning(f"Errore estrazione dati per {symbol}: {e}")
        return None
    
    if df.empty or len(df) < 4:
        return None
    
    # Verifica che abbiamo le colonne necessarie
    required_columns = ['Open', 'High', 'Low', 'Close']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        st.warning(f"{symbol}: Manca colonne {missing_cols}")
        return None
    
    # Converti in Heikin Ashi
    ha = heikin_ashi(df)
    
    # Prendi solo i giorni con dati validi
    ha = ha.dropna(subset=['HA_Close', 'HA_Open'])
    
    if len(ha) < 3:
        return None
    
    # Prendi le ultime 3 candele
    recent = ha.tail(3).copy()
    
    # Ordina per data (assicurati che sia cronologico)
    recent = recent.sort_index()
    
    # Estrai le candele di interesse
    yesterday = recent.iloc[-1]
    day_before = recent.iloc[-2]
    
    # DEBUG: informazioni per verifica
    debug_info = {
        'symbol': symbol,
        'dates': recent.index.strftime('%Y-%m-%d').tolist(),
        'is_green': recent['Is_Green'].tolist(),
        'ha_open': recent['HA_Open'].round(4).tolist(),
        'ha_close': recent['HA_Close'].round(4).tolist()
    }
    
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
# MAIN APP
# -------------------------

# Data range
end = date.today() + timedelta(days=1)
start = end - timedelta(days=30)  # 30 giorni per sicurezza

# Aggiungi opzione per testare singolo simbolo
test_mode = st.checkbox("Modalità Test (analizza solo primo simbolo)")

if test_mode:
    symbols_to_check = [SYMBOLS[0]]
    st.info(f"Modalità test attiva - Analizzo solo: {symbols_to_check[0]}")
else:
    symbols_to_check = SYMBOLS

with st.spinner("Analisi in corso..."):
    all_data = fetch_all_data(symbols_to_check, start, end)
    
    if all_data is None:
        st.error("Impossibile scaricare i dati. Verifica la connessione o i simboli.")
    else:
        # Mostra info sui dati scaricati
        st.info(f"Dati scaricati: {all_data.shape[0]} giorni per {len(symbols_to_check)} simboli")
        
        # DEBUG: mostra struttura dati
        with st.expander("📊 Struttura dati scaricati"):
            st.write(f"Colonne: {all_data.columns[:10]}")
            st.write(f"Tipo colonne: {type(all_data.columns)}")
            st.write(f"Prime righe:")
            st.dataframe(all_data.head())
        
        results = []
        
        # Analizza ogni simbolo
        for symbol in symbols_to_check:
            with st.spinner(f"Analisi {symbol}..."):
                result = analyze_stock(symbol, all_data)
                if result:
                    results.append(result)
        
        # Mostra risultati
        if results:
            st.success(f"✅ Trovati {len(results)} titoli")
            
            # Crea tabella risultati
            results_data = []
            for r in results:
                debug = r["debug"]
                if len(debug['dates']) >= 2:
                    results_data.append({
                        "Simbolo": r["symbol"],
                        "Data Ieri": debug['dates'][-1],
                        "Data Altro Ieri": debug['dates'][-2],
                        "Ieri": "🟢 Verde" if debug['is_green'][-1] else "🔴 Rosso",
                        "Altro Ieri": "🟢 Verde" if debug['is_green'][-2] else "🔴 Rosso",
                        "Pattern": "✅ SÌ" if debug['is_green'][-1] and not debug['is_green'][-2] else "❌ NO"
                    })
            
            if results_data:
                df_results = pd.DataFrame(results_data)
                st.dataframe(df_results, use_container_width=True)
                
                # -------------------------
                # SELEZIONE GRAFICO
                # -------------------------
                if not test_mode:  # Solo se non in modalità test
                    selected = st.selectbox(
                        "Seleziona un titolo per il grafico Heikin Ashi",
                        [r["symbol"] for r in results]
                    )
                    
                    selected_data = next(r for r in results if r["symbol"] == selected)
                    ha = selected_data["ha"].tail(30)
                    
                    # Mostra info debug
                    with st.expander(f"🔍 Dettagli per {selected}"):
                        debug_info = selected_data["debug"]
                        st.write(f"**Simbolo:** {debug_info['symbol']}")
                        st.write(f"**Date:** {debug_info['dates']}")
                        st.write(f"**Verde?:** {debug_info['is_green']}")
                        st.write(f"**HA Open:** {debug_info['ha_open']}")
                        st.write(f"**HA Close:** {debug_info['ha_close']}")
                        
                        # Tabella chiara
                        summary_df = pd.DataFrame({
                            'Data': debug_info['dates'],
                            'HA Open': debug_info['ha_open'],
                            'HA Close': debug_info['ha_close'],
                            'Colore': ['🟢' if g else '🔴' for g in debug_info['is_green']]
                        })
                        st.dataframe(summary_df)
                    
                    # Grafico
                    fig = go.Figure()
                    
                    # Candele Heikin Ashi
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
                    
                    # Evidenzia le 2 candele del pattern
                    if len(ha) >= 2:
                        # Rettangolo evidenziato
                        fig.add_vrect(
                            x0=ha.index[-2], x1=ha.index[-1],
                            fillcolor="rgba(255,255,0,0.1)",
                            layer="below",
                            line_width=0
                        )
                        
                        # Annotazioni
                        fig.add_annotation(
                            x=ha.index[-2],
                            y=ha['HA_High'].iloc[-2],
                            text="Altro ieri 🔴",
                            showarrow=True,
                            arrowhead=2
                        )
                        
                        fig.add_annotation(
                            x=ha.index[-1],
                            y=ha['HA_Low'].iloc[-1],
                            text="Ieri 🟢",
                            showarrow=True,
                            arrowhead=2
                        )
                    
                    fig.update_layout(
                        title=f"{selected} – Heikin Ashi (Ultimi 30 giorni)",
                        xaxis_title="Data",
                        yaxis_title="Prezzo",
                        height=600,
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("❌ Nessun titolo soddisfa il pattern Heikin Ashi")

# -------------------------
# INFO
# -------------------------
with st.expander("ℹ️ Informazioni sul Pattern"):
    st.markdown("""
    ### Pattern di inversione Heikin Ashi
    
    **Logica:**
    - 🔴 **Altro ieri**: Candela Heikin Ashi ROSSA (Close < Open) → Momentum negativo
    - 🟢 **Ieri**: Candela Heikin Ashi VERDE (Close > Open) → Potenziale inversione
    
    **Vantaggi Heikin Ashi:**
    - Filtra il rumore del mercato
    - Mostra trend più chiaramente
    - Riduce i falsi segnali
    
    **Nota tecnica:**
    - Lo script gestisce automaticamente i giorni senza trading
    - Verifica le date effettive dei giorni di borsa
    - Gestisce correttamente i dati multi-simbolo da Yahoo Finance
    """)

st.markdown("---")
st.caption("Dati Yahoo Finance • Analisi Heikin Ashi • Aggiornamento giornaliero")