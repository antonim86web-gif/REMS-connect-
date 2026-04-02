import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar

# --- 1. CONFIGURAZIONE DATABASE ---
DB_NAME = "rems_final_v12.db"

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, stato TEXT DEFAULT 'ATTIVO')")
            cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT, figura_professionale TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT, tipo_evento TEXT, mezzo TEXT, accompagnatore TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT, FOREIGN KEY(p_id) REFERENCES pazienti(id))")
            
            if cur.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
                cur.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("perito2026"), "SUPER", "USER", "Admin"))
            
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}")
            return []

def get_now_it(): return datetime.now(timezone.utc) + timedelta(hours=2)

# --- 2. CSS CUSTOM PER TABLET (RISOLVE GLI SCREENSHOT) ---
st.set_page_config(page_title="REMS Connect ELITE PRO", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* Riduzione margini per densità massima */
    .block-container { padding: 0.5rem 1rem !important; }
    html, body, [class*="css"] { font-size: 13px !important; }
    
    /* FIX Sidebar v28.9 */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; min-width: 200px !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    
    /* Layout Orizzontale Smarcamento */
    .stButton > button { 
        width: 100% !important; 
        padding: 2px !important; 
        height: 28px !important; 
        font-size: 11px !important; 
    }
    
    /* Tabella S.T.U. */
    .stu-table { width: 100%; border-collapse: collapse; font-size: 10px; text-align: center; }
    .stu-table th, .stu-table td { border: 1px solid #ddd; padding: 2px; }
    .today { background-color: #fffde7; border: 2px solid #ffd600 !important; }
    
    /* Post-it colorati */
    .postit { padding: 10px; border-radius: 5px; margin-bottom: 8px; border-left: 6px solid; font-size: 12px; }
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; }
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; }
</style>
""", unsafe_allow_html=True)

# --- 3. LOGICA SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.title("🏥 REMS CONNECT ACCESS")
    col1, col2 = st.columns(2)
    with col1:
        u_i = st.text_input("User").lower().strip()
        p_i = st.text_input("Pass", type="password")
        if st.button("LOGIN"):
            res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
            if res:
                st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}
                st.rerun()
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"
oggi_iso = get_now_it().strftime("%Y-%m-%d")
oggi_it = get_now_it().strftime("%d/%m/%Y")

# --- 4. SIDEBAR ---
st.sidebar.title("Rems-connect")
st.sidebar.write(f"👤 {u['nome']} {u['cognome']}")
nav = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda", "🗺️ Mappa Posti"])
if st.sidebar.button("LOGOUT"):
    st.session_state.user_session = None
    st.rerun()

# --- 5. MODULO EQUIPE (IL CUORE DEL SISTEMA) ---
if nav == "👥 Modulo Equipe":
    st.subheader(f"Area {u['ruolo']}")
    p_lista = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]

        if u['ruolo'] in ["Infermiere", "Admin"]:
            t1, t2, t3 = st.tabs(["💊 SMARCAMENTO", "💓 PARAMETRI", "📝 DIARIO"])
            
            with t1:
                st.markdown(f"**Terapia di Oggi:** {oggi_it}")
                terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                
                # Header Colonne
                h1, h2, h3, h4 = st.columns([3, 1, 1, 1])
                h1.caption("Farmaco/Dose")
                h2.caption("MAT (08)")
                h3.caption("POM (16)")
                h4.caption("NOT (20)")
                
                for f in terapie:
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    c1.markdown(f"**{f[1]}** <br> {f[2]}", unsafe_allow_html=True)
                    
                    turni = [("MAT", f[3], c2), ("POM", f[4], c3), ("NOT", f[5], c4)]
                    for t_nome, attivo, col_obj in turni:
                        if attivo:
                            # Cerco se già firmato oggi (Uso id_u per evitare errore 'esito')
                            check = db_run("SELECT id_u FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                                         (p_id, f"%SOMM ({t_nome}): {f[1]}%", f"{oggi_it}%"))
                            if check:
                                col_obj.markdown("✅")
                            else:
                                if col_obj.button("F", key=f"f_{f[0]}_{t_nome}"):
                                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                                          (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({t_nome}): {f[1]}", "Infermiere", firma_op), True)
                                    st.rerun()
                        else:
                            col_obj.write("-")

            with t2:
                with st.form("vit"):
                    pa, fc, sat = st.text_input("PA"), st.text_input("FC"), st.text_input("SatO2")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                               (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"💓 PA:{pa} FC:{fc} Sat:{sat}", "Infermiere", firma_op), True)
                        st.rerun()
            
            with t3:
                # Visualizzazione Diario tipo Post-it
                res = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 10", (p_id,))
                for d, r, o, nt in res:
                    cls = "role-infermiere" if r == "Infermiere" else "role-psichiatra"
                    st.markdown(f'<div class="postit {cls}"><b>{o} ({r})</b> - {d}<br>{nt}</div>', unsafe_allow_html=True)

        elif u['ruolo'] == "Psichiatra":
            with st.form("presc"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3)
                m, p, n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                if st.form_submit_button("PRESCRIVI"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", 
                           (p_id, f, d, int(m), int(p), int(n), firma_op), True)
                    st.rerun()

# --- 6. ALTRE SEZIONI (SINTETIZZATE) ---
elif nav == "📊 Monitoraggio":
    st.subheader("Diario Clinico Generale")
    for pid, nome in db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome"):
        with st.expander(f"📁 {nome}"):
            eventi = db_run("SELECT data, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 5", (pid,))
            for d, o, n in eventi:
                st.write(f"**{d}** ({o}): {n}")

elif nav == "🗺️ Mappa Posti":
    st.write("Visualizzazione Posti Letto Reparto A/B")
    # Qui andrebbe la tua griglia stanze v12
