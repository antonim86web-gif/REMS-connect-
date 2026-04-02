import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar

# --- 1. DATABASE & LOGICA (INVARIATA v12) ---
DB_NAME = "rems_final_v12.db"

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, stato TEXT DEFAULT 'ATTIVO')")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT, figura_professionale TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

def get_now_it(): return datetime.now(timezone.utc) + timedelta(hours=2)

# --- 2. CSS "TABLET-DENSE" (RISOLVE IL PROBLEMA DELLO SCROLL) ---
st.set_page_config(page_title="REMS Connect ELITE PRO", layout="wide")

st.markdown("""
<style>
    /* Riduzione generale font per densità dati */
    html, body, [class*="css"] { font-size: 12px !important; }
    .block-container { padding: 1rem !important; }
    
    /* Card Post-it più sottili */
    .postit { padding: 8px; margin-bottom: 5px; border-radius: 4px; font-size: 11px; }
    
    /* Layout Somministrazione Orizzontale (IL FIX) */
    .therapy-row {
        display: flex;
        align-items: center;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 5px 10px;
        margin-bottom: 4px;
    }
    .farmaco-info { width: 40%; font-weight: bold; }
    .turno-col { width: 20%; text-align: center; border-left: 1px solid #ddd; }
    
    /* Bottoni firma minuscoli */
    div.stButton > button {
        padding: 2px 5px !important;
        height: 22px !important;
        font-size: 10px !important;
        min-width: 30px !important;
    }
    
    /* Sidebar blu scuro come da tua v12 */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: white !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. SESSIONE E LOGIN (SINTETIZZATO) ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    # ... (Qui va il tuo blocco login originale, rimosso per brevità) ...
    st.title("REMS Connect - Login")
    u_i = st.text_input("Username")
    p_i = st.text_input("Password", type="password")
    if st.button("ACCEDI"):
        res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
        if res:
            st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}
            st.rerun()
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"
oggi = get_now_it().strftime("%d/%m/%Y")

# --- 4. NAVIGAZIONE ---
nav = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Posti Letto"])

# --- 5. IL NUOVO MODULO INFERMIERE (VERSIONE COMPATTA) ---
if nav == "👥 Modulo Equipe":
    st.subheader(f"Modulo Operativo: {u['ruolo']}")
    p_lista = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        
        if u['ruolo'] in ["Infermiere", "Admin"]:
            t1, t2 = st.tabs(["💊 SMARCAMENTO TERAPIA", "📝 ALTRE CONSEGNE"])
            
            with t1:
                st.caption(f"Firma somministrazioni per {p_sel} - {oggi}")
                terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                
                # Header Tabella
                h1, h2, h3, h4 = st.columns([4, 2, 2, 2])
                h1.write("**FARMACO / DOSE**")
                h2.write("**MAT (08)**")
                h3.write("**POM (13/16)**")
                h4.write("**NOT (20)**")
                
                for f in terapie:
                    # f[0]:id, f[1]:nome, f[2]:dose, f[3]:mat, f[4]:pom, f[5]:nott
                    r1, r2, r3, r4 = st.columns([4, 2, 2, 2])
                    
                    # Colonna Farmaco
                    r1.markdown(f"**{f[1]}**<br><small>{f[2]}</small>", unsafe_allow_html=True)
                    
                    # Gestione Turni (Logica compatta)
                    turni_config = [("MAT", f[3], r2), ("POM", f[4], r3), ("NOT", f[5], r4)]
                    
                    for t_nome, attivo, col_obj in turni_config:
                        if attivo:
                            check = db_run("SELECT esito FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                                         (p_id, f"%({t_nome}): {f[1]}%", f"{oggi}%"))
                            if check:
                                col_obj.markdown("✅ **OK**")
                            else:
                                if col_obj.button("FIRMA", key=f"sig_{f[0]}_{t_nome}"):
                                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                                          (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({t_nome}): {f[1]}", "Infermiere", firma_op), True)
                                    st.rerun()
                        else:
                            col_obj.write("-")
                st.divider()

# --- 6. RESTO DEL CODICE (MAPPA, MONITORAGGIO ECC) ---
# ... qui continua il tuo codice originale per le altre sezioni ...
