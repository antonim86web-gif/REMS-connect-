import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect", page_icon="🏥", layout="wide")

# CSS Semplificato: rimosse le forzature sul pulsante menu che causavano il bug
st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 19px !important; background-color: #f1f5f9; }
    .stButton>button { height: 4rem !important; font-size: 1.2rem !important; border-radius: 12px !important; background-color: #2563eb !important; color: white !important; font-weight: bold !important; width: 100%; }
    .nota-card { padding: 12px; margin-bottom: 10px; border-radius: 8px; color: #1e293b; border-left: 6px solid #cbd5e1; background-color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .nota-Psichiatra { border-left-color: #ef4444 !important; background-color: #fef2f2 !important; }
    .nota-Infermiere { border-left-color: #3b82f6 !important; background-color: #eff6ff !important; }
    .nota-OSS { border-left-color: #8b5cf6 !important; background-color: #f5f3ff !important; }
    .nota-Psicologo { border-left-color: #10b981 !important; background-color: #ecfdf5 !important; }
    .nota-Educatore { border-left-color: #f59e0b !important; background-color: #fffbeb !important; }
    .date-header { background-color: #e2e8f0; padding: 5px 15px; border-radius: 20px; font-weight: bold; color: #475569; margin: 15px 0 10px 0; display: inline-block; font-size: 0.85rem; }
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
def db_query(query, params=(), commit=False):
    conn = sqlite3.connect("rems_connect_v1.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, operatore TEXT)")
    columns = [info[1] for info in cur.execute("PRAGMA table_info(eventi)").fetchall()]
    if "ruolo" not in columns: cur.execute("ALTER TABLE eventi ADD COLUMN ruolo TEXT DEFAULT 'Nota'")
    if "operatore" not in columns: cur.execute("ALTER TABLE eventi ADD COLUMN operatore TEXT DEFAULT 'Anonimo'")
    cur.execute(query, params)
    res = cur.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- 3. ACCESSO ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏥 REMS Connect")
    pwd = st.text_input("Codice", type="password")
    if st.button("ENTRA"):
        if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE DI EMERGENZA (Se il menu sparisce) ---
if 'menu_val' not in st.session_state: st.session_state.menu_val = "📊 Monitoraggio"

# Creiamo due pulsanti in alto per navigare senza dipendere dal menu laterale
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("📊 Monitoraggio"): st.session_state.menu_val = "📊 Monitoraggio"; st.rerun()
with col_nav2:
    if st.button("⚙️ Gestione"): st.session_state.menu_val = "⚙️ Gestione"; st.rerun()

menu = st.session_state.menu_val

# --- 5. MONITORAGGIO ---
if menu == "📊 Monitoraggio":
    st.title("Monitoraggio Clinico")
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}"):
            if f"v_{p_id}" not in st.session_state: st.session_state[f"v_{p_id}"] = 0
            
            c1, c2 = st.columns(2)
            with c1: ruolo = st.selectbox("Ruolo:", ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"], key=f"sel_{p_id}_{st.session_state[f'v_{p_id}']}")
            with c2: operatore = st.text_input("Nome:", key=f"op_{p_id}_{st.session_state[f'v_{p_id}']}", placeholder="Firma")
            
            umore = st.select_slider("Stato:", options=["Cupo", "Deflesso", "Stabile", "Agitato"], value="Stabile", key=f"u_{p_id}_{st.session_state[f'v_{p_id}']}")
            nota = st.text_area("Nota:", key=f"n_{p_id}_{st.session_state[f'v_{p_id}']}", height=100)
            
            if st.button("SALVA NOTA", key=f"btn_{p_id}"):
                if nota and operatore:
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    db_query("INSERT INTO eventi (p_id, data, umore, nota, ruolo, operatore) VALUES (?,?,?,?,?,?)", (p_id, dt, umore, nota, ruolo, operatore), commit=True)
                    st.session_state[f"v_{p_id}"] += 1
                    st.rerun()

            st.divider()
            f_ruolo = st.multiselect("Filtra per figura:", ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"], key=f"filter_{p_id}")
            
            eventi = db_query("SELECT data, umore, nota, ruolo, operatore FROM eventi WHERE p_id=? ORDER BY data DESC", (p_id,))
            current_date = ""
            for e in eventi:
                if f_ruolo and e[3] not in f_ruolo: continue
                raw_dt = str(e[0])
                try:
                    dt_obj = datetime.strptime(raw_dt.split(" ")[0], "%Y-%m-%d")
                    nice_date = dt_obj.strftime("%d/%m/%Y")
                    time_part = raw_dt.split(" ")[1]
                except:
                    nice_date = raw_dt.split(" ")[0]
                    time_part = raw_dt.split(" ")[1] if " " in raw_dt else ""

                if nice_date != current_date:
                    st.markdown(f'<div class="date-header">📅 {nice_date}</div>', unsafe_allow_html=True)
                    current_date = nice_date
                
                r_style = f"nota-{e[3].replace(' ', '')}" if e[3] else ""
                st.markdown(f"""
                <div class="nota-card {r_style}">
                    <small><b>{time_part}</b> | <b>{e[3].upper()}</b> | {e[4]}</small><br>
                    <b>Stato: {e[1]}</b><br>
                    <div style="margin-top:5px; white-space: pre-wrap;">{e[2]}</div>
                </div>
                """, unsafe_allow_html=True)

# --- 6. GESTIONE ---
elif menu == "⚙️ Gestione":
    st.title("Anagrafica")
    nuovo = st.text_input("Nuovo Paziente")
    if st.button("AGGIUNGI"):
        if nuovo: db_query("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), commit=True); st.rerun()
    st.divider()
    p_list = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_list:
        p_del = st.selectbox("Rimuovi", [p[1] for p in p_list])
        if st.button("ELIMINA"):
            db_query("DELETE FROM pazienti WHERE nome=?", (p_del,), commit=True); st.rerun()
