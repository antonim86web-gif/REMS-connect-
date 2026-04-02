import streamlit as st
import sqlite3
import calendar
import hashlib
from datetime import datetime

# --- CONFIGURAZIONE PAGINA E STILE ---
st.set_page_config(page_title="REMS Connect ELITE", layout="wide", page_icon="🏥")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .st-emotion-cache-1kyxreq { justify-content: center; }
    .farmaco-card { 
        background: white; 
        padding: 15px; 
        border-radius: 10px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
        margin-bottom: 15px; 
        border-left: 5px solid #1e3a8a;
    }
    .scroll-giorni { 
        display: flex; 
        overflow-x: auto; 
        gap: 5px; 
        padding: 10px 0;
    }
    .quadratino {
        min-width: 32px; 
        height: 40px; 
        border-radius: 4px; 
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        justify-content: center; 
        font-size: 10px;
        border: 1px solid #ddd;
    }
    .oggi-border { border: 2px solid #1e3a8a !important; background-color: #fff9c4; }
    .header-turno { 
        background: #1e3a8a; 
        color: white; 
        padding: 8px 15px; 
        border-radius: 5px; 
        margin: 20px 0 10px 0; 
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- MOTORE DATABASE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit: conn.commit()
            return cursor.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}")
            return []

def inizializza_db():
    db_run("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT, stato TEXT DEFAULT 'ATTIVO')", commit=True)
    db_run("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY, id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, esito TEXT)", commit=True)
    db_run("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, is_prn INTEGER DEFAULT 0)", commit=True)
    
    # Check colonne mancanti
    cols_ev = [c[1] for d in [db_run("PRAGMA table_info(eventi)")] for c in d]
    if "esito" not in cols_ev: db_run("ALTER TABLE eventi ADD COLUMN esito TEXT", commit=True)
    
    cols_ter = [c[1] for d in [db_run("PRAGMA table_info(terapie)")] for c in d]
    if "is_prn" not in cols_ter: db_run("ALTER TABLE terapie ADD COLUMN is_prn INTEGER DEFAULT 0", commit=True)

inizializza_db()

# --- LOGICA DI FIRMA ---
def registra_firma(p_id, farmaco, turno, esito):
    ora = datetime.now().strftime("%d/%m/%Y %H:%M")
    nota = f"✔️ SOMM ({turno}): {farmaco}"
    db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
           (p_id, ora, nota, "Infermiere", "Operatore", esito), commit=True)
    st.rerun()

# --- INTERFACCIA INFERMIERE: SMARCAMENTO ---
def genera_smarcamento(p_id, farmaci, turno_target, titolo):
    if turno_target == "TAB":
        f_list = [f for f in farmaci if len(f) > 6 and f[6] == 1]
    else:
        mappa = {"MAT": 3, "POM": 4, "NOT": 5}
        f_list = [f for f in farmaci if len(f) > mappa[turno_target] and f[mappa[turno_target]] == 1]

    if not f_list: return

    st.markdown(f"<div class='header-turno'>{titolo}</div>", unsafe_allow_html=True)
    oggi = datetime.now()
    giorni_mese = calendar.monthrange(oggi.year, oggi.month)[1]

    for f in f_list:
        with st.container():
            st.markdown(f"<div class='farmaco-card'><b>{f[1]}</b> - <small>{f[2]}</small></div>", unsafe_allow_html=True)
            
            # Recupero firme del mese
            mese_anno = oggi.strftime("%m/%Y")
            firme = db_run("SELECT data, esito FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                           (p_id, f"%({turno_target}): {f[1]}%", f"%/{mese_anno}%"))
            firme_map = {int(d[0].split("/")[0]): d[1] for d in firme if d[1]}

            # Striscia dei giorni
            html_giorni = "<div class='scroll-giorni'>"
            for d in range(1, giorni_mese + 1):
                esito = firme_map.get(d, "")
                classe = "quadratino oggi-border" if d == oggi.day else "quadratino"
                color = "green" if esito == "A" else ("red" if esito == "R" else "#333")
                bg = "#dcfce7" if esito == "A" else ("#fee2e2" if esito == "R" else "white")
                
                html_giorni += f"""
                <div class='{classe}' style='background:{bg}; color:{color};'>
                    <span style='font-size:8px;'>{d}</span>
                    <b>{esito if esito else '-'}</b>
                </div>
                """
            html_giorni += "</div>"
            st.markdown(html_giorni, unsafe_allow_html=True)

            # Bottoni Azione
            if oggi.day not in firme_map:
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write("Smarca oggi:")
                if c2.button(f"Assunto (A)", key=f"A_{f[0]}_{turno_target}"):
                    registra_firma(p_id, f[1], turno_target, "A")
                if c3.button(f"Rifiutato (R)", key=f"R_{f[0]}_{turno_target}"):
                    registra_firma(p_id, f[1], turno_target, "R")
            st.write("---")

# --- INTERFACCIA MEDICO: PRESCRIZIONE ---
def modulo_medico(p_id):
    st.markdown("### 🩺 Area Medica")
    with st.form("presc_univoca"):
        f_nome = st.text_input("Farmaco")
        f_dose = st.text_input("Dose")
        scelta = st.selectbox("Orario / Regime", ["MATTINO (08:00)", "POMERIGGIO (16:00)", "NOTTE (20:00)", "TAB (Al Bisogno)"])
        
        if st.form_submit_button("REGISTRA PRESCRIZIONE"):
            m, p, n, tsu = 0, 0, 0, 0
            if "MATTINO" in scelta: m = 1
            elif "POMERIGGIO" in scelta: p = 1
            elif "NOTTE" in scelta: n = 1
            else: tsu = 1
            
            db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, is_prn) VALUES (?,?,?,?,?,?,?)", 
                   (p_id, f_nome, f_dose, m, p, n, tsu), commit=True)
            st.success("Prescrizione Salvata!")
            st.rerun()

# --- MAIN APP ---
st.title("🏥 REMS Connect v28.9.5")

# Selezione Paziente
p_list = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
if not p_list:
    st.warning("Nessun paziente. Aggiungine uno in Admin.")
    if st.button("Aggiungi Test"): db_run("INSERT INTO pazienti (nome) VALUES ('PAZIENTE TEST')", commit=True); st.rerun()
else:
    nomi = [p[1] for p in p_list]
    sel = st.selectbox("Seleziona Paziente", nomi)
    p_id = [p[0] for p in p_list if p[1] == sel][0]

    menu = st.tabs(["💊 Infermiere", "🩺 Medico"])

    with menu[1]:
        modulo_medico(p_id)

    with menu[0]:
        st.markdown(f"## Smarcamento: {sel}")
        farmaci = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, is_prn FROM terapie WHERE p_id=?", (p_id,))
        if farmaci:
            genera_smarcamento(p_id, farmaci, "MAT", "☀️ MATTINO (08:00)")
            genera_smarcamento(p_id, farmaci, "POM", "⛅ POMERIGGIO (16:00)")
            genera_smarcamento(p_id, farmaci, "NOT", "🌙 NOTTE (20:00)")
            genera_smarcamento(p_id, farmaci, "TAB", "🆘 TAB (Al Bisogno)")
        else:
            st.info("Nessuna terapia attiva.")
