import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURAZIONE & CSS ---
st.set_page_config(page_title="REMS Connect PRO", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
    html, body, [class*="css"] { font-size: 19px !important; background-color: #f1f5f9; }
    .rems-header {
        text-align: center; color: #1e3a8a; font-family: 'Orbitron', sans-serif;
        font-size: 2.5rem !important; font-weight: 700; margin-bottom: 20px;
        text-transform: uppercase; letter-spacing: 3px; text-shadow: 0 0 8px rgba(37, 99, 235, 0.2);
    }
    .stButton>button { 
        height: 3.5rem !important; font-size: 1.1rem !important; border-radius: 12px !important; 
        background-color: #2563eb !important; color: white !important; font-weight: bold !important; 
        width: 100%; font-family: 'Orbitron', sans-serif;
    }
    .nota-card { padding: 12px; margin-bottom: 8px; border-radius: 8px; color: #1e293b; border-left: 6px solid #cbd5e1; background-color: #f8fafc; }
    .agenda-card { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 10px; border-top: 4px solid #2563eb; }
    .nota-Psichiatra { border-left-color: #ef4444 !important; }
    .nota-Infermiere { border-left-color: #3b82f6 !important; }
    .nota-OSS { border-left-color: #8b5cf6 !important; }
    .nota-Psicologo { border-left-color: #10b981 !important; }
    .nota-Educatore { border-left-color: #f59e0b !important; }
    .allerta-agitato { background-color: #fee2e2 !important; border: 2px solid #dc2626 !important; animation: blinker 2s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.8; } }
    div[data-testid="stRadio"] > div { flex-direction: row !important; gap: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE (CON AUTO-REPAIR) ---
def init_db():
    conn = sqlite3.connect("rems_connect_v1.db", check_same_thread=
