import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600&family=Orbitron:wght@700&display=swap');
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; background-color: #f4f7f9; }
    .rems-h { text-align: center; color: #0f172a; font-family: 'Orbitron', sans-serif; font-size: 2.2rem; margin-bottom: 20px; }
    
    .stButton>button { 
        border-radius: 8px !important; height: 3.8rem !important; 
        background-color: white !important; color: #475569 !important;
        border: 1px solid #e2e8f0 !important; font-weight: 600 !important;
    }
    .active-btn > div > button { 
        background-color: #2563eb !important; color: white !important; 
        border: 1px solid #1d4ed8 !important; box-shadow: 0 4px 6px rgba(37,99,235,0.2);
    }
    
    .card { padding: 15px; margin: 10px 0; border-radius: 10px; background: white; border-left: 5px solid #64748b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .card-header { font-size: 0.85rem; color: #94a3b8; margin-bottom: 5px; border-bottom: 1px solid #f1f5f9; }
    .agitato { border-left-color: #ef4444 !important; background-color: #fef2f2 !important; }
    
    #MainMenu, footer, header { visibility
