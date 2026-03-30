import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE E STILE ADATTIVO ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Orbitron:wght@700&display=swap');
    
    /* Font e Sfondo */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #f8fafc; }
    .rems-h { text-align: center; color: #1e3a8a; font-family: 'Orbitron', sans-serif; font-size: clamp(1.5rem, 5vw, 2.5rem); margin-bottom: 25px; letter-spacing: 2px; }

    /* NAVIGAZIONE SEGMENTED (ADATTIVA PC/TABLET) */
    .stRadio > div { 
        background-color: #e2e8f0; padding: 5px; border-radius: 12px; 
        display: flex; justify-content: space-around; gap: 4px;
    }
    .stRadio label { 
        flex: 1; text-align: center; background: transparent; border: none; 
        padding: 10px 5px; border-radius: 8px; cursor: pointer; transition: 0.2s;
        font-weight: 600; color: #64748b; font-size: 0.95rem;
    }
    .stRadio div[data-checked="true"] label { 
        background: white !important; color: #2563eb !important; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
    }
    .stRadio label p { font-size: 1rem !important; }

    /* CARD E CONTENUTI */
    .card { padding: 15px; margin: 10px 0; border-radius: 12px; border-left: 6px solid #cbd5e1; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .agitato { background: #fff1f2 !important; border-left-color: #e11d48 !important; }
    .stButton>button { border-radius: 10px; height: 3.5rem; font-weight: bold; background-color: #2563eb !important; }
    
    /* Pulizia Interfaccia */
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 2. MOTORE DATABASE ---
def run_db(q, p=(), commit=False):
    with sqlite3.connect("rems_v4.db", check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (p_id INTEGER, tipo TEXT, d_ora TEXT, note TEXT, rif TEXT)")
        cur.execute(q, p)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. LOGICA DI SESSIONE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'menu' not in st.session_state: st.session_state.menu = "Monitoraggio"
if 'v_a' not in st.session_state: st.session_state.v_a = 0

# --- 4. LOGIN ---
if not st.session_state.auth:
    st.markdown('<h1 class="rems-h">REMS CONNECT</h1>', unsafe_allow_html=True)
    c_login, _ = st.columns([1, 1])
    with c_login:
        pwd = st.text_input("Codice Identificativo", type="password")
        if st.button("ENTRA"):
            if pwd in ["rems2026", "admin2026"]:
                st.session_state.auth = True
                st.session_state.role = "admin" if "admin" in pwd else "user"
                st.rerun()
            else: st.error("Accesso negato")
    st.stop()

# --- 5. NAVIGAZIONE SEGMENTED ---
st.markdown('<h1 class="rems-h">REMS CONNECT</h1>', unsafe_allow_html=True)

nav_options = ["Monitoraggio", "Agenda", "Gestione"]
if st.session_state.role != "admin": nav_options.remove("Gestione")

# Questo widget simula il Segmented Control
scelta = st.radio("", nav_options, index=nav_options.index(st.session_state.menu) if st.session_state.menu in nav_options else 0, horizontal=True, label_visibility="collapsed")

if scelta != st.session_state.menu:
    st.session_state.menu = scelta
    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# --- 6. MODULI ---

if st.session_state.menu == "Monitoraggio":
    paz = run_db("SELECT * FROM pazienti ORDER BY nome")
    if not paz: st.info("Nessun paziente. Vai in Gestione.")
    for p_id, nome in paz:
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            v_i = st.session_state.get(f"v_{p_id}", 0)
            c1, c2 = st.columns(2)
            ruolo = c1.selectbox("Ruolo", ["OSS", "Infermiere", "Psichiatra", "Psicologo", "Educatore"], key=f"r{p_id}{v_i}")
            firma = c2.text_input("Firma", key=f"f{p_id}{v_i}")
            umore = st.radio("Stato", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}{v_i}", horizontal=True)
            nota = st.text_area("Nota di turno", key=f"n{p_id}{v_i}")
            
            if st.button("SALVA REGISTRAZIONE", key=f"b{p_id}"):
                if nota and firma:
                    run_db("INSERT INTO eventi VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), umore, nota, ruolo, firma), True)
                    st.session_state[f"v_{p_id}"] = v_i + 1
                    st.rerun()
            
            st.divider()
            for e in run_db("SELECT * FROM eventi WHERE id=? ORDER BY rowid DESC LIMIT 5", (p_id,)):
                st.markdown(f'<div class="card {"agitato" if e[2]=="Agitato" else ""}"><small>{e[1]} | {e[4]} | {e[5]}</small><br><b>{e[2]}</b><br>{e[3]}</div>', unsafe_allow_html=True)

elif st.session_state.menu == "Agenda":
    paz = run_db("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        p
