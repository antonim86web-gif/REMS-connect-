import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import plotly.express as px

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .card {padding: 12px; margin: 8px 0; border-radius: 10px; background: white; border-left: 5px solid #64748b; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    .nota-header {font-size: 0.75rem; color: #64748b; border-bottom: 1px solid #f1f5f9; margin-bottom: 5px;}
    .agitato {border-left-color: #ef4444 !important; background-color: #fef2f2 !important;}
    .log-cambio {border-left: 5px solid #f59e0b !important; background-color: #fffbeb !important;}
</style>
""", unsafe_allow_html=True)

DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# Inizializzazione Tabelle (se non esistono)
db_run("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)", commit=True)
db_run("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)", commit=True)

# --- LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Accesso", type="password")
    if st.button("Entra"):
        if pwd in ["rems2026", "admin2026"]: 
            st.session_state.auth = True
            st.rerun()
    st.stop()

menu = st.sidebar.radio("Menu", ["Monitoraggio", "Statistiche & Calendario", "Gestione"])

# --- MONITORAGGIO CON CERCA E FILTRO DATE ---
if menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()} - Diario"):
            # Inserimento rapido
            c1, c2 = st.columns(2)
            u = c1.radio("Stato", ["Stabile", "Agitato", "Cupo"], horizontal=True, key=f"u{p_id}")
            n = st.text_area("Nota", key=f"n{p_id}")
            if st.button("Salva", key=f"b{p_id}"):
                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                       (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), u, n, "Operatore", "User"), True)
                st.rerun()
            
            st.divider()
            # SEZIONE CERCA E CALENDARIZZAZIONE (Filtri)
            st.markdown("🔍 **Filtra Storico**")
            f1, f2 = st.columns([2, 1])
            search_query = f1.text_input("Cerca parola chiave...", key=f"sq{p_id}")
            date_filter = f2.date_input("Data specifica", value=None, key=f"dt{p_id}")
            
            # Query Dinamica
            sql = "SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=?"
            params = [p_id]
            if search_query:
                sql += " AND nota LIKE ?"
                params.append(f"%{search_query}%")
            if date_filter:
                sql += " AND data LIKE ?"
                params.append(f"{date_filter}%")
            sql += " ORDER BY data DESC"
            
            note = db_run(sql, tuple(params))
            if not note: st.info("Nessun risultato per questi filtri.")
            for d, um, tx, ru, fi in note:
                cl = "card agitato" if um=="Agitato" else "card"
                st.markdown(f'<div class="{cl}"><div class="nota-header">{d}</div><b>{um}</b><br>{tx}</div>', unsafe_allow_html=True)

# --- STATISTICHE & CALENDARIZZAZIONE ---
elif menu == "Statistiche & Calendario":
    paz = db_run("SELECT id, nome FROM pazienti")
    if paz:
        sel_p = st.selectbox("Paziente", [p[1] for p in paz])
        p_id = [p[0] for p in paz if p[1] == sel_p][0]
        res = db_run("SELECT data, umore FROM eventi WHERE id=?", (p_id,))
        if res:
            df = pd.DataFrame(res, columns=["Data", "Umore"])
            df['Data_Day'] = pd.to_datetime(df['Data']).dt.date
            
            # 1. Calendario di attività (Heatmap semplificata)
            st.subheader("📅 Calendarizzazione Attività")
            cal_data = df.groupby('Data_Day').count()['Umore'].reset_index()
            fig_cal = px.bar(cal_data, x='Data_Day', y='Umore', labels={'Umore':'Num. Note', 'Data_Day':'Giorno'}, title="Frequenza annotazioni nel tempo")
            st.plotly_chart(fig_cal, use_container_width=True)
            
            # 2. Statistiche Umore
            st.subheader("📊 Analisi Clinica")
            st.plotly_chart(px.pie(df, names="Umore", hole=0.4), use_container_width=True)
        else:
            st.warning("Ancora nessun dato per questo paziente.")

elif menu == "Gestione":
    st.subheader("Anagrafica")
    nuovo = st.text_input("Nome Paziente")
    if st.button("Aggiungi"):
        db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True)
        st.rerun()
