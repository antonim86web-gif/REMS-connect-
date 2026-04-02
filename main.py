import streamlit as st
import sqlite3
import calendar
import hashlib
from datetime import datetime

# --- CONFIGURAZIONE E CSS ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
    <style>
    .scroll-box { overflow-x: auto; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 25px; background: white; }
    .m-table { border-collapse: collapse; width: 100%; font-size: 11px; }
    .m-table th, .m-table td { border: 1px solid #eee; padding: 8px; text-align: center; min-width: 35px; }
    .f-name { position: sticky; left: 0; background: #f8f9fa; z-index: 5; min-width: 140px !important; text-align: left !important; font-weight: bold; border-right: 2px solid #ddd !important; }
    .today-highlight { background-color: #fff9c4 !important; font-weight: bold; }
    .header-block { background: #1e3a8a; color: white; padding: 10px; border-radius: 5px; margin-top: 20px; }
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

def inizializza_sistema():
    # Creazione tabelle se mancano
    db_run("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT, stato TEXT DEFAULT 'ATTIVO')", commit=True)
    db_run("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY, id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, esito TEXT)", commit=True)
    db_run("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, is_prn INTEGER DEFAULT 0)", commit=True)
    
    # FIX: Aggiunta colonne se il DB è vecchio (previene sqlite3.OperationalError)
    cols_eventi = [c[1] for c in db_run("PRAGMA table_info(eventi)")]
    if "esito" not in cols_eventi:
        db_run("ALTER TABLE eventi ADD COLUMN esito TEXT", commit=True)
    
    cols_terapie = [c[1] for c in db_run("PRAGMA table_info(terapie)")]
    if "is_prn" not in cols_terapie:
        db_run("ALTER TABLE terapie ADD COLUMN is_prn INTEGER DEFAULT 0", commit=True)

inizializza_sistema()

# --- LOGICA GRIGLIA ---
def genera_blocco(p_id, farmaci, turno_target, titolo):
    # Selezione farmaci in base al turno
    if turno_target == "TAB":
        f_list = [f for f in farmaci if len(f) > 6 and f[6] == 1]
    else:
        mappa = {"MAT": 3, "POM": 4, "NOT": 5}
        f_list = [f for f in farmaci if len(f) > mappa[turno_target] and f[mappa[turno_target]] == 1]

    if not f_list: return

    st.markdown(f"<div class='header-block'>{titolo}</div>", unsafe_allow_html=True)
    
    oggi = datetime.now()
    giorni_mese = calendar.monthrange(oggi.year, oggi.month)[1]
    
    header = "".join([f"<th class='{'today-highlight' if d == oggi.day else ''}'>{d}</th>" for d in range(1, giorni_mese + 1)])
    html = f"<div class='scroll-box'><table class='m-table'><tr><th class='f-name'>Farmaco / Dose</th>{header}</tr>"
    
    for f in f_list:
        nome_f = f"{f[1]} ({f[2]})"
        # Recupero firme del mese corrente
        mese_anno = oggi.strftime("%m/%Y")
        firme = db_run("SELECT data, esito FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                       (p_id, f"%({turno_target}): {f[1]}%", f"%/{mese_anno}%"))
        firme_map = {int(d[0].split("/")[0]): d[1] for d in firme if d[1]}

        celle = ""
        for d in range(1, giorni_mese + 1):
            esito = firme_map.get(d, "")
            colore = "green" if esito == "A" else "red"
            celle += f"<td class='{'today-highlight' if d == oggi.day else ''}' style='color:{colore}; font-weight:bold;'>{esito}</td>"
        
        html += f"<tr><td class='f-name'>{nome_f}</td>{celle}</tr>"
    
    html += "</table></div>"
    st.markdown(html, unsafe_allow_html=True)

    # Pulsanti firma per oggi
    cols = st.columns(len(f_list))
    for i, f in enumerate(f_list):
        with cols[i]:
            st.caption(f[1])
            c1, c2 = st.columns(2)
            if c1.button("A", key=f"A_{f[0]}_{turno_target}"):
                eseguire_firma(p_id, f[1], turno_target, "A")
            if c2.button("R", key=f"R_{f[0]}_{turno_target}"):
                eseguire_firma(p_id, f[1], turno_target, "R")

def eseguire_firma(p_id, farmaco, turno, esito):
    data_ora = datetime.now().strftime("%d/%m/%Y %H:%M")
    nota = f"✔️ SOMM ({turno}): {farmaco}"
    db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
           (p_id, data_ora, nota, "Infermiere", "Operatore", esito), commit=True)
    st.rerun()

# --- INTERFACCIA PRINCIPALE ---
st.title(f"📊 Registro Terapie - {datetime.now().strftime('%B %Y')}")

# Selezione Paziente
p_data = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
if p_data:
    p_nomi = [p[1] for p in p_data]
    sel = st.selectbox("Seleziona Paziente", p_nomi)
    p_id = [p[0] for p in p_data if p[1] == sel][0]
    
    # Caricamento Farmaci (Previene NameError)
    farmaci = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, is_prn FROM terapie WHERE p_id=?", (p_id,))
    
    if farmaci:
        genera_blocco(p_id, farmaci, "MAT", "☀️ MATTINO (08:00)")
        genera_blocco(p_id, farmaci, "POM", "⛅ POMERIGGIO (13:00/16:00)")
        genera_blocco(p_id, farmaci, "NOT", "🌙 NOTTE (20:00)")
        genera_blocco(p_id, farmaci, "TAB", "🆘 TAB (Al Bisogno)")
    else:
        st.info("Nessuna terapia impostata per questo paziente.")
else:
    st.warning("Nessun paziente attivo nel database.")
