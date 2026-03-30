import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .block-container {padding-top: 1.5rem;}
    .card {padding: 12px; margin: 8px 0; border-radius: 10px; background: white; border-left: 5px solid #64748b; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    .nota-header {font-size: 0.75rem; color: #64748b; border-bottom: 1px solid #f1f5f9; margin-bottom: 5px;}
    .agitato {border-left-color: #ef4444 !important; background-color: #fef2f2 !important;}
    .terapia-card {border-left-color: #10b981 !important; background-color: #f0fdf4 !important;}
    #MainMenu, footer, header {visibility: hidden;}
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

# --- 3. SESSIONE ---
if 'auth' not in st.session_state: st.session_state.auth = False
for k in ['v_g', 'v_a', 'v_t']: 
    if k not in st.session_state: st.session_state[k] = 0

# --- 4. LOGIN ---
if not st.session_state.auth:
    st.markdown("<h3 style='text-align:center;'>REMS CONNECT SYSTEM</h3>", unsafe_allow_html=True)
    pwd = st.text_input("Codice Accesso", type="password")
    if st.button("ACCEDI"):
        if pwd in ["rems2026", "admin2026"]:
            st.session_state.auth = True
            st.session_state.role = "admin" if "admin" in pwd else "user"
            st.rerun()
    st.stop()

# --- 5. MENU LATERALE (SIDEBAR) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2966/2966327.png", width=80)
    st.title("REMS Connect")
    st.write(f"Utente: **{st.session_state.role.upper()}**")
    st.divider()
    
    menu_options = ["Monitoraggio", "Agenda", "Terapie", "Statistiche", "Documenti"]
    if st.session_state.role == "admin":
        menu_options.append("Gestione")
    
    st.session_state.menu = st.radio("MENU PRINCIPALE", menu_options)
    
    st.divider()
    if st.button("LOGOUT"):
        st.session_state.auth = False
        st.rerun()

# --- 6. MODULI CENTRALI ---

st.header(f" {st.session_state.menu}")

if st.session_state.menu == "Monitoraggio":
    ruoli_list = ["Tutti", "Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"]
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    
    if not pazienti:
        st.info("Nessun paziente in anagrafica. Vai in Gestione per aggiungerli.")
    
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}"):
            vi = st.session_state.get(f"v_{p_id}", 0)
            
            st.markdown("#### Inserimento Nota")
            c1, c2 = st.columns(2)
            r = c1.selectbox("Ruolo", ruoli_list[1:], key=f"r{p_id}{vi}")
            o = c2.text_input("Firma Operatore", key=f"f{p_id}{vi}")
            u = st.radio("Stato", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}{vi}", horizontal=True)
            n = st.text_area("Nota Clinica", key=f"n{p_id}{vi}")
            if st.button("SALVA NOTA", key=f"btn{p_id}"):
                if n and o:
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), u, n, r, o), True)
                    st.session_state[f"v_{p_id}"] = vi + 1; st.rerun()
            
            st.divider()
            st.markdown("#### Ricerca Storico")
            col_f1, col_f2 = st.columns([2, 1])
            search_query = col_f1.text_input("🔍 Cerca parole chiave...", key=f"search{p_id}")
            filter_role = col_f2.selectbox("Filtra Ruolo", ruoli_list, key=f"frole{p_id}")

            q = "SELECT data, umore, nota, ruolo, op, row_id FROM eventi WHERE id=?"
            params = [p_id]
            if search_query: q += " AND nota LIKE ?"; params.append(f"%{search_query}%")
            if filter_role != "Tutti": q += " AND ruolo = ?"; params.append(filter_role)
            q += " ORDER BY data DESC"
            
            results = db_run(q, tuple(params))
            for d, um, tx, ru, fi, rid in results:
                cl = "card agitato" if um=="Agitato" else "card"
                st.markdown(f'<div class="{cl}"><div class="nota-header">{d} | {ru} | {fi}</div><b>{um}</b><br>{tx}</div>', unsafe_allow_html=True)
                if st.session_state.role == "admin":
                    if st.button(f"Elimina Nota #{rid}", key=f"del_ev_{rid}"):
                        db_run("DELETE FROM eventi WHERE row_id=?", (rid,), True); st.rerun()

elif st.session_state.menu == "Terapie":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        p_map = {p[1]: p[0] for p in paz}
        sel_p = st.selectbox("Seleziona Paziente", list(p_map.keys()))
        pid = p_map[sel_p]
