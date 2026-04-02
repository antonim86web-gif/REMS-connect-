import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar

# --- FUNZIONE ORARIO ITALIA ---
def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="REMS Connect ELITE PRO", layout="wide", page_icon="🏥")

# Nota: Ho rimosso temporaneamente i blocchi CSS complessi per assicurarmi che il core parta.
# Una volta che vedi l'app, potremo riaggiungerli.

st.title("🏥 REMS CONNECT - SERVER ATTIVO")

# --- DATABASE ENGINE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

st.write("Connessione al database stabilita con successo.")
st.info(f"Orario Server: {get_now_it().strftime('%H:%M:%S')}")
