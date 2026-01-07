import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
import numpy as np

# -------------------------
st.set_page_config(page_title="Heikin Ashi Screener ITA", page_icon="📈", layout="wide")
st.title("📊 Screener Heikin Ashi – Inversione Rialzista")
st.markdown("""
**Pattern di ricerca:**  
- 🔴 Heikin Ashi **altro ieri rossa**  
- 🟢 Heikin Ashi **ieri verde**
""")

SYMBOLS = [
    "A2A.MI", "AMP.MI", "BAMI.MI", "BC.MI", "BGN.MI", "BMPS.MI", "BPE.MI", "BMED.MI",
    "BST.MI", "CE.MI", "CPR.MI", "DIA.MI", "ENEL.MI", "ENI.MI", "ERG.MI", "FBK.MI",
    "GEO.MI", "IG.MI", "INRG.MI", "ISP.MI", "IVG.MI", "LDO.MI", "MB.MI", "MONC.MI",
    "NEXI.MI", "PRY.MI", "PST.MI", "RACE.MI", "REC.MI", "SFER.MI", "SPM.MI", "STLAM.MI",
    "STMMI.MI", "TES.MI", "TEN.MI", "TGYM.MI", "TIT.MI", "TRN.MI", "UCG.MI", "UNI.MI"
]

# -------------------------
def heikin_ashi(df):
    """Calcola candele Heikin Ashi"""
    if df is None or df.empty:
        return None
    
    if not all(col in df.columns for col in ['Open','High','Low','Close']):
        return None

    # Creare una copia ordinata
    df = df.sort_index()
    
    # Creare DataFrame Heikin Ashi
    ha = pd.DataFrame(index=df.index)
    
    # HA_Close = (Open + High + Low + Close) / 4
    ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # HA_Open = (HA_Open_previous + HA_Close_previous) / 2
    ha['HA_Open'] = 0.0
    if len(ha) > 0:
        # Primo valore: media del primo Open e Close originale
        ha.iloc[0, ha.columns.get_loc('HA_Open')] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
        
        # Calcolare i valori successivi
        for i in range(1, len(ha)):
            ha.iloc[i, ha.columns.get_loc('HA_Open')] = (ha['HA_Open'].iloc[i-1] + ha['HA_Close'].iloc[i-1]) / 2
    
    # HA_High = max(High, HA_Open, HA_Close)
    ha['HA_High'] = pd.concat([df['High'], ha['HA_Open'], ha['HA_Close']], axis=1).max(axis=1)
    
    # HA_Low = min(Low, HA_Open, HA_Close)
    ha['HA_Low'] = pd.concat([df['Low'], ha['HA_Open'], ha['HA_Close']], axis=1).min(axis=1)
    
    # Aggiungere Volume se presente
    if 'Volume' in df.columns:
        ha['Volume'] = df['Volume']
    else:
        ha['Volume'] = 0
        
    return ha

# -------------------------
def fetch_data(symbol, start, end):
    """Scarica dati da Yahoo Finance"""
    try:
        df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
        if df.empty or len(df) < 3:
            return None
        return df
    except Exception as e:
        st.write(f"Errore nel download di {symbol}: {str(e)}")
        return None

# -------------------------
def analyze_stock(symbol, start, end):
    """Analizza un singolo titolo per pattern Heikin Ashi"""
    df = fetch_data(symbol, start, end)
    if df is None or len(df) < 3:
        return None

    ha = heikin_ashi(df)
    if ha is None or len(ha) < 3:
        return None

    # Verificare che abbiamo abbastanza dati
    if len(ha) >= 3:
        # Ieri (penultimo giorno)
        yesterday = ha.iloc[-2] if len(ha) >= 2 else None
        # Altro ieri (terzultimo giorno)
        day_before = ha.iloc[-3] if len(ha) >= 3 else None
        
        if yesterday is not None and day_before is not None:
            # Pattern: altro ieri rossa (HA_Close < HA_Open) e ieri verde (HA_Close > HA_Open)
            if day_before['HA_Close'] < day_before['HA_Open'] and yesterday['HA_Close'] > yesterday['HA_Open']:
                return {
                    "symbol": symbol,
                    "ha": ha,
                    "yesterday_close": yesterday['HA_Close'],
                    "day_before_close": day_before['HA_Close'],
                    "change_pct": ((yesterday['HA_Close'] - day_before['HA_Close']) / day_before['HA_Close']) * 100
                }
    
    return None

# -------------------------
# Interfaccia Streamlit
start = date.today() - timedelta(days=30)  # Più giorni per sicurezza
end = date.today() + timedelta(days=1)

st.write(f"**Periodo di analisi:** {start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}")
st.write(f"**Numero di titoli da analizzare:** {len(SYMBOLS)}")

results = []
with st.spinner("Analisi in corso... Potrebbe richiedere qualche secondo..."):
    progress_bar = st.progress(0)
    
    for i, symbol in enumerate(SYMBOLS):
        result = analyze_stock(symbol, start, end)
        if result:
            results.append(result)
        
        # Aggiornare progress bar
        progress_bar.progress((i + 1) / len(SYMBOLS))

# -------------------------
# Visualizzazione risultati
if results:
    st.success(f"✅ **Trovati {len(results)} titoli con pattern Heikin Ashi di inversione rialzista**")
    
    # Creare DataFrame con risultati
    df_results = pd.DataFrame([
        {
            "Simbolo": r["symbol"],
            "Prezzo Ieri": f"{r['yesterday_close']:.2f}",
            "Variazione %": f"{r['change_pct']:.2f}%",
            "Colore": "🟢" if r['change_pct'] > 0 else "🔴"
        }
        for r in results
    ])
    
    # Ordinare per variazione percentuale (decrescente)
    df_results = df_results.sort_values("Variazione %", key=lambda x: x.str.replace('%','').astype(float), ascending=False)
    
    st.dataframe(df_results, use_container_width=True, hide_index=True)
    
    # Selezionare titolo per grafico dettagliato
    if results:
        selected_symbol = st.selectbox(
            "Seleziona un titolo per visualizzare il grafico Heikin Ashi dettagliato",
            [r["symbol"] for r in results]
        )
        
        selected_data = next(r for r in results if r["symbol"] == selected_symbol)
        ha = selected_data["ha"]
        
        # Visualizzare ultimi 20 giorni
        ha_display = ha.tail(20)
        
        # Creare grafico Plotly
        fig = go.Figure()
        
        # Aggiungere candele Heikin Ashi
        fig.add_trace(go.Candlestick(
            x=ha_display.index,
            open=ha_display['HA_Open'],
            high=ha_display['HA_High'],
            low=ha_display['HA_Low'],
            close=ha_display['HA_Close'],
            increasing_line_color='green',
            decreasing_line_color='red',
            name='Heikin Ashi'
        ))
        
        # Aggiungere volume se disponibile
        if 'Volume' in ha_display.columns and ha_display['Volume'].sum() > 0:
            # Normalizzare volume per visualizzazione
            max_price = ha_display[['HA_High', 'HA_Low']].max().max()
            min_price = ha_display[['HA_High', 'HA_Low']].min().min()
            price_range = max_price - min_price
            
            if price_range > 0:
                # Aggiungere volume come barre
                fig.add_trace(go.Bar(
                    x=ha_display.index,
                    y=ha_display['Volume'],
                    name='Volume',
                    marker_color='rgba(100, 100, 255, 0.3)',
                    yaxis='y2',
                    opacity=0.5
                ))
        
        # Personalizzare layout
        fig.update_layout(
            title=f"{selected_symbol} - Grafico Heikin Ashi (ultimi 20 giorni)",
            xaxis_title="Data",
            yaxis_title="Prezzo",
            yaxis2=dict(
                title="Volume",
                overlaying="y",
                side="right",
                showgrid=False
            ),
            height=600,
            hovermode="x unified",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        # Configurare asse x
        fig.update_xaxes(
            rangeslider_visible=False,
            rangeselector=dict(
                buttons=list([
                    dict(count=5, label="5g", step="day", stepmode="backward"),
                    dict(count=10, label="10g", step="day", stepmode="backward"),
                    dict(count=20, label="20g", step="day", stepmode="backward"),
                    dict(step="all", label="Tutto")
                ])
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Mostrare dati recenti
        with st.expander("Vedi dati Heikin Ashi recenti"):
            recent_data = ha_display[['HA_Open', 'HA_High', 'HA_Low', 'HA_Close']].copy()
            recent_data.columns = ['Apertura HA', 'Massimo HA', 'Minimo HA', 'Chiusura HA']
            st.dataframe(recent_data.style.format("{:.2f}"), use_container_width=True)
else:
    st.warning("❌ **Nessun titolo trovato che soddisfa il pattern Heikin Ashi di inversione rialzista**")
    st.info("""
    **Suggerimenti:**
    - Prova ad aumentare il periodo di analisi
    - Verifica la connessione a internet
    - I simboli potrebbero non essere più validi
    """)

# Footer
st.markdown("---")
st.markdown("**Note:** I dati sono forniti da Yahoo Finance. L'analisi è a scopo informativo e non costituisce consiglio finanziario.")