import streamlit as st
import sqlite3
import calendar
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="REMS Connect ELITE", layout="wide")

# CSS CORRETTO PER QUADRATINI E SCROLL
st.markdown("""
    <style>
    .scroll-giorni { 
        display: flex; 
        overflow-x: auto; 
        gap: 5px; 
        padding: 15px 5px;
        background: #f8f9fa;
        border-radius: 8px;
    }
    .quadratino {
        min-width: 35px; 
        height: 45px; 
        border-radius: 6px; 
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        justify-content: center; 
        font-size: 11px;
        border: 1px solid #ddd;
        background: white;
    }
    .oggi-border { border: 2px solid #1e3a8a !important; background-color: #fffde7 !important; }
    .header-turno { 
        background: #1e3a8a; color: white; padding: 10px; 
        border-radius: 5px; margin-top: 20px; font-weight: bold;
    }
    .farmaco-box {
        padding: 10px; border-left: 5px solid #1e3a8a;
        background: #ffffff; margin-top: 10px; border-radius: 4px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNZIONI DATABASE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit: conn.commit()
            return cursor.fetchall()
        except Exception as e:
            st.error(f"Errore: {e}")
            return []

# Inizializzazione automatica colonne
def init_db():
    db_run("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT, stato TEXT DEFAULT 'ATTIVO')", commit=True)
    db_run("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY, id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, esito TEXT)", commit=True)
    db_run("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, is_prn INTEGER DEFAULT 0)", commit=True)
    try: db_run("ALTER TABLE eventi ADD COLUMN esito TEXT", commit=True)
    except: pass
    try: db_run("ALTER TABLE terapie ADD COLUMN is_prn INTEGER DEFAULT 0", commit=True)
    except: pass

init_db()

# --- LOGICA SMARCAMENTO ---
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
        st.markdown(f"<div class='farmaco-box'><b>{f[1]}</b> - {f[2]}</div>", unsafe_allow_html=True)
        
        # Recupero firme
        firme = db_run("SELECT data, esito FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                       (p_id, f"%({turno_target}): {f[1]}%", f"%/{oggi.strftime('%m/%Y')}%"))
        firme_map = {int(d[0].split("/")[0]): d[1] for d in firme if d[1]}

        # DISEGNO LA STRISCIA (Corretto con unsafe_allow_html)
        html_giorni = "<div class='scroll-giorni'>"
        for d in range(1, giorni_mese + 1):
            esito = firme_map.get(d, "")
            classe = "quadratino oggi-border" if d == oggi.day else "quadratino"
            color = "green" if esito == "A" else ("red" if esito == "R" else "#333")
            bg = "#dcfce7" if esito == "A" else ("#fee2e2" if esito == "R" else "white")
            
            html_giorni += f"""
            <div class='{classe}' style='background:{bg}; color:{color};'>
                <span style='font-size:9px; color:#666;'>{d}</span>
                <b style='font-size:14px;'>{esito if esito else '-'}</b>
            </div>"""
        html_giorni += "</div>"
        
        st.markdown(html_giorni, unsafe_allow_html=True)

        # BOTTONI FIRMA
        if oggi.day not in firme_map:
            c1, c2, c3 = st.columns([1, 1, 1])
            if c2.button(f"✅ ASSUNTO", key=f"A_{f[0]}_{turno_target}", use_container_width=True):
                registra_firma(p_id, f[1], turno_target, "A")
            if c3.button(f"❌ RIFIUTATO", key=f"R_{f[0]}_{turno_target}", use_container_width=True):
                registra_firma(p_id, f[1], turno_target, "R")
        else:
            st.success(f"Smarcato: {firme_map[oggi.day]}")

def registra_firma(p_id, farmaco, turno, esito):
    ora = datetime.now().strftime("%d/%m/%Y %H:%M")
    db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
           (p_id, ora, f"✔️ SOMM ({turno}): {farmaco}", "Infermiere", "Op", esito), commit=True)
    st.rerun()

# --- APP ---
p_list = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
if p_list:
    sel_p = st.selectbox("Paziente", [p[1] for p in p_list])
    p_id = [p[0] for p in p_list if p[1] == sel_p][0]

    t_inf, t_med = st.tabs(["💊 Infermiere", "🩺 Medico"])

    with t_inf:
        farmaci = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, is_prn FROM terapie WHERE p_id=?", (p_id,))
        if farmaci:
            genera_smarcamento(p_id, farmaci, "MAT", "☀️ MATTINO (08:00)")
            genera_smarcamento(p_id, farmaci, "POM", "⛅ POMERIGGIO (16:00)")
            genera_smarcamento(p_id, farmaci, "NOT", "🌙 NOTTE (20:00)")
            genera_smarcamento(p_id, farmaci, "TAB", "🆘 TAB (Al Bisogno)")
        else:
            st.info("Nessuna terapia.")

    with t_med:
        with st.form("med"):
            f = st.text_input("Farmaco")
            d = st.text_input("Dose")
            o = st.selectbox("Orario", ["MATTINO (08:00)", "POMERIGGIO (16:00)", "NOTTE (20:00)", "TAB (Al Bisogno)"])
            if st.form_submit_button("Prescrivi"):
                m, p, n, tsu = (1,0,0,0) if "MAT" in o else ((0,1,0,0) if "POM" in o else ((0,0,1,0) if "NOT" in o else (0,0,0,1)))
                db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, is_prn) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, m, p, n, tsu), commit=True)
                st.rerun()
