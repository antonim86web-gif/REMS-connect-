import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. DESIGN "TECH-CLINICAL" (DARK MODE & GLASS) ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;600&display=swap');
    
    /* Sfondo e Base */
    .stApp { background-color: #0f172a; color: #f8fafc; }
    .rems-h { 
        text-align: center; color: #38bdf8; font-family: 'Orbitron', sans-serif; 
        font-size: 2.8rem; margin-bottom: 30px; text-shadow: 0 0 15px rgba(56, 189, 248, 0.4);
    }

    /* NAVBAR TECH (Stile Plancia) */
    .nav-container { 
        display: flex; justify-content: center; gap: 15px; margin-bottom: 30px; 
    }
    .stButton>button { 
        border: 1px solid #334155 !important; background: rgba(30, 41, 59, 0.7) !important;
        color: #94a3b8 !important; border-radius: 12px !important; height: 4.5rem !important;
        font-family: 'Rajdhani', sans-serif; font-size: 1.2rem !important; font-weight: 600 !important;
        transition: 0.3s all !important; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .stButton>button:hover { border-color: #38bdf8 !important; color: #38bdf8 !important; transform: translateY(-2px); }
    
    /* Evidenzia il tasto attivo */
    .active-btn > div > button { 
        border-color: #38bdf8 !important; color: #38bdf8 !important; 
        background: rgba(56, 189, 248, 0.1) !important; box-shadow: 0 0 15px rgba(56, 189, 248, 0.2) !important;
    }

    /* CARD VETRO */
    .card { 
        padding: 18px; margin: 12px 0; border-radius: 15px; 
        background: rgba(30, 41, 59, 0.5); border: 1px solid #334155;
        backdrop-filter: blur(10px); color: #e2e8f0;
    }
    .nota-header { color: #38bdf8; font-weight: bold; font-size: 0.85rem; margin-bottom: 8px; border-bottom: 1px solid #334155; padding-bottom: 5px; }
    
    /* ALLERTA NEON */
    .agitato { 
        border: 1px solid #ef4444 !important; background: rgba(239, 68, 68, 0.05) !important;
        box-shadow: inset 0 0 10px rgba(239, 68, 68, 0.1) !important;
    }
    .agitato .nota-header { color: #f87171; }

    /* Input Fields */
    input, textarea, select { background-color: #1e293b !important; color: white !important; border: 1px solid #334155 !important; border-radius: 8px !important; }
    
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
def run_db(q, p=(), commit=False):
    with sqlite3.connect("rems_v5.db", check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (p_id INTEGER, tipo TEXT, d_ora TEXT, note TEXT, rif TEXT)")
        cur.execute(q, p)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'menu' not in st.session_state: st.session_state.menu = "Monitoraggio"
if 'v_a' not in st.session_state: st.session_state.v_a = 0

# --- 4. LOGIN ---
if not st.session_state.auth:
    st.markdown('<h1 class="rems-h">REMS CONNECT</h1>', unsafe_allow_html=True)
    c_login, _ = st.columns([1, 1.2])
    with c_login:
        pwd = st.text_input("SISTEMA PROTETTO - INSERIRE CODICE", type="password")
        if st.button("ACCEDI AL SISTEMA"):
            if pwd in ["rems2026", "admin2026"]:
                st.session_state.auth = True
                st.session_state.role = "admin" if "admin" in pwd else "user"
                st.rerun()
            else: st.error("Accesso negato")
    st.stop()

# --- 5. NAVIGAZIONE TECH ---
st.markdown('<h1 class="rems-h">REMS CONNECT</h1>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class
