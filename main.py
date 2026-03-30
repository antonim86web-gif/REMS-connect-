import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect PRO", page_icon="🏥", layout="wide")

# Caricamento Font Particolare (Orbitron) e Stili CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');

    html, body, [class*="css"] { font-size: 19px !important; background-color: #f1f5f9; }
    
    /* TITOLO PRINCIPALE CON FONT PARTICOLARE */
    .rems-header {
        text-align: center;
        color: #1e3a8a;
        font-family: 'Orbitron', sans-serif;
        font-size: 3.2rem !important;
        font-weight: 700;
        margin-bottom: 25px;
        text-transform: uppercase;
        letter-spacing: 5px;
        /* Effetto Bagliore */
        text-shadow: 0 0 10px rgba(37, 99, 235, 0.2), 2px 2px 0px #ffffff;
    }

    .stButton>button { 
        height: 3.5rem !important; 
        font-size: 1.1rem !important; 
        border-radius: 12px !important; 
        background-color: #2563eb !important; 
        color: white !important; 
        font-weight: bold !important; 
        width: 100%; 
        font-family: 'Orbitron', sans-serif; /* Font anche sui tasti principali */
    }
    
    .nota-card { padding: 12px; margin-bottom: 8px; border-radius: 8px; color: #1e293b; border-left: 6px solid #cbd5e1; background-color: #f8fafc; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .nota-Psichiatra { border-left-color: #ef4444 !important; }
    .nota-Infermiere { border-left-color: #3b82f6 !important; }
    .nota-OSS { border-left-color: #8b5cf6 !important; }
    .nota-Psicologo { border-left-color: #10b981 !important; }
    .nota-Educatore { border-left-color: #f59e0b !important; }
    
    .allerta-agitato { 
        background-color: #fee2e2 !important; 
        border: 2px solid #dc2626 !important; 
        border-left: 10px solid #dc2626 !important;
        animation: blinker 2s linear infinite;
    }
    @keyframes blinker { 50% { opacity: 0.8; } }
    
    div[data-testid="stRadio"] > div { flex-direction: row !important; gap: 10px; }
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
def db_query(query, params=(), commit=False):
    conn = sqlite3.connect("rems_connect_v1.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, operatore TEXT)")
    cur.execute(query, params)
    res = cur.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'role' not in st.session_state: st.session_state.role = "user"

if not st.session_state.auth:
    st.markdown('<h1 class="rems-header">REMS CONNECT</h1>', unsafe_allow_html=True)
    pwd = st.text_input("Codice Identificativo", type="password")
    if st.button("ENTRA"):
        if pwd == "rems2026":
            st.session_state.auth = True; st.session_state.role = "user"; st.rerun()
        elif pwd == "admin2026":
            st.session_state.auth = True; st.session_state.role = "admin"; st.rerun()
        else: st.error("Codice errato")
    st.stop()

# --- 4. INTESTAZIONE E NAVIGAZIONE ---
st.markdown('<h1 class="rems-header">REMS CONNECT</h1>', unsafe_allow_html=True)

if 'menu_val' not in st.session_state: st.session_state.menu_val = "📊 Monitoraggio"
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("📊 Monitoraggio"): st.session_state.menu_val = "📊 Monitoraggio"; st.rerun()
with col_nav2:
    if st.session_state.role == "admin":
        if st.button("⚙️ Gestione"): st.session_state.menu_val = "⚙️ Gestione"; st.rerun()
    else: st.button("⚙️ Gestione (Protetto)", disabled=True)

menu = st.session_state.menu_val

# --- 5. MONITORAGGIO ---
if menu == "📊 Monitoraggio":
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            if f"v_{p_id}" not in st.session_state: st.session_state[f"v_{p_id}"] = 0
            
            c1, c2 = st.columns(2)
            with c1: ruolo = st.selectbox("Ruolo:", ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"], key=f"sel_{p_id}_{st.session_state[f'v_{p_id}']}")
            with c2: operatore = st.text_input("Firma:", key=f"op_{p_id}_{st.session_state[f'v_{p_id}']}")
            
            st.markdown("---")
            st.write("**Stato Attuale del Paziente:**")
            umore = st.radio(
                label="Stato",
                options=["🟢 Stabile", "🟡 Cupo", "🟠 Deflesso", "🔴 Agitato"],
                index=0,
                key=f"u_{p_id}_{st.session_state[f'v_{p_id}']}",
                horizontal=True,
                label_visibility="collapsed"
            )
            
            nota = st.text_area("Nota di Turno:", key=f"n_{p_id}_{st.session_state[f'v_{p_id}']}", height=120)
            
            if st.button("SALVA NOTA", key=f"btn_{p_id}"):
                if nota and operatore:
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    umore_clean = umore.split(" ")[1]
                    db_query("INSERT INTO eventi (p_id, data, umore, nota, ruolo, operatore) VALUES (?,?,?,?,?,?)", (p_id, dt, umore_clean, nota, ruolo, operatore), commit=True)
                    st.session_state[f"v_{p_id}"] += 1
                    st.rerun()

            st.divider()
            
            # DIARIO RAGGRUPPATO
            eventi_raw = db_query("SELECT data, umore, ruolo, operatore, nota FROM eventi WHERE p_id=? ORDER BY data DESC", (p_id,))
            if eventi_raw:
                df = pd.DataFrame(eventi_raw, columns=['Data', 'Umore', 'Ruolo
