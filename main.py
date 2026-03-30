import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .block-container {padding-top: 1.5rem;}
    .card {padding: 12px; margin: 8px 0; border-radius: 10px; background: white; border-left: 5px solid #64748b; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    .nota-header {font-size: 0.75rem; color: #64748b; border-bottom: 1px solid #f1f5f9; margin-bottom: 5px;}
    .agitato {border-left-color: #ef4444 !important; background-color: #fef2f2 !important;}
    .terapia-card {border-left-color: #10b981 !important; background-color: #f0fdf4 !important;}
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (p_id INTEGER, tipo TEXT, d_ora TEXT, note TEXT, rif TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, data TEXT, medico TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS documenti (p_id INTEGER, nome_doc TEXT, file_blob BLOB, data TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        
        try:
            cur.execute("SELECT medico FROM terapie LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE terapie ADD COLUMN medico TEXT DEFAULT 'N.D.'")
            conn.commit()

        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. SESSIONE & LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<h3 style='text-align:center;'>REMS CONNECT SYSTEM</h3>", unsafe_allow_html=True)
    pwd = st.text_input("Codice Accesso", type="password")
    if st.button("ACCEDI"):
        if pwd in ["rems2026", "admin2026"]:
            st.session_state.auth = True
            st.session_state.role = "admin" if "admin" in pwd else "user"
            st.rerun()
    st.stop()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color:#1e3a8a;'>REMS Connect</h2>", unsafe_allow_html=True)
    st.write(f"Utente: **{st.session_state.role.upper()}**")
    st.divider()
    menu_options = ["Monitoraggio", "Agenda", "Terapie", "Statistiche", "Documenti"]
    if st.session_state.role == "admin": menu_options.append("Gestione")
    st.session_state.menu = st.radio("VAI A:", menu_options)
    st.divider()
    if st.button("Logout"):
        st.session_state.auth = False
        st.rerun()

# --- 5. CONTENUTO ---
st.title(f"{st.session_state.menu}")

# --- MODULO STATISTICHE (AGGIORNATO) ---
if st.session_state.menu == "Statistiche":
    paz_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if not paz_list:
        st.info("Nessun paziente disponibile.")
    else:
        p_map = {p[1]: p[0] for p in paz_list}
        sel_p = st.selectbox("Seleziona Paziente per l'analisi:", list(p_map.keys()))
        pid = p_map[sel_p]
        
        res = db_run("SELECT data, umore FROM eventi WHERE id=? ORDER BY data ASC", (pid,))
        
        if res:
            df = pd.DataFrame(res, columns=["Data", "Umore"])
            df['Data'] = pd.to_datetime(df['Data'])
            
            c1, c2 = st.columns(2)
            
            # Grafico a Torta (Distribuzione Umore)
            with c1:
                st.subheader("Distribuzione Umore")
                fig_pie = px.pie(df, names="Umore", color="Umore", 
                                color_discrete_map={"Agitato":"#ef4444", "Stabile":"#10b981", "Cupo":"#1e3a8a", "Deflesso":"#f59e0b"})
                st.plotly_chart(fig_pie, use_container_width=True)
            
            # Grafico Temporale (Andamento)
            with c2:
                st.subheader("Andamento Temporale")
                # Mappiamo l'umore su una scala numerica per il grafico a linee
                umore_ordine = {"Agitato": 0, "Cupo": 1, "Deflesso": 2, "Stabile": 3}
                df['Livello'] = df['Umore'].map(umore_ordine)
                
                fig_line = px.line(df, x="Data", y="Livello", markers=True, 
                                  title="Evoluzione (0:Agitato -> 3:Stabile)")
                fig_line.update_yaxes(tickvals=[0, 1, 2, 3], ticktext=["Agitato", "Cupo", "Deflesso", "Stabile"])
                st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.warning(f"Non ci sono ancora dati di monitoraggio per {sel_p}.")

# --- ALTRI MODULI (MANTENUTI) ---
elif st.session_state.menu == "Monitoraggio":
    for p_id, nome in db_run("SELECT * FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}"):
            # (Codice monitoraggio identico alla versione precedente...)
            st.write(f"Gestione dati per {nome}")
            # ... (omesso per brevità, ma resta nel tuo file originale)

elif st.session_state.menu == "Gestione":
    # (Codice gestione identico alla versione precedente...)
    st.write("Gestione anagrafica")
