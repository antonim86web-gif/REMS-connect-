import streamlit as st
import sqlite3
import calendar
from datetime import datetime

# 1. CONFIGURAZIONE
st.set_page_config(page_title="REMS Registro", layout="wide")

# 2. STILE CSS (Corretto per non vedere il codice HTML)
st.markdown("""
    <style>
    .scroll-giorni { display: flex; overflow-x: auto; gap: 8px; padding: 10px; background: #f8f9fa; border-radius: 10px; }
    .quadratino { min-width: 42px; height: 55px; border-radius: 8px; border: 1px solid #ddd; display: flex; flex-direction: column; align-items: center; justify-content: center; background: white; flex-shrink: 0; }
    .oggi { border: 3px solid #1e3a8a !important; background: #fff9c4 !important; }
    .info-f { font-size: 7px; color: #777; text-align: center; line-height: 1; }
    </style>
""", unsafe_allow_html=True)

# 3. FUNZIONE DATABASE (Ignora errori di colonne doppie)
def db_run(query, params=(), commit=False):
    with sqlite3.connect("rems_v12.db", timeout=10) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit: conn.commit()
            return cursor.fetchall()
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e): return []
            st.error(f"Errore DB: {e}")
            return []

# 4. INIZIALIZZAZIONE SILENZIOSA
db_run("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT, stato TEXT DEFAULT 'ATTIVO')", commit=True)
db_run("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY, id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, esito TEXT)", commit=True)
db_run("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, is_prn INTEGER DEFAULT 0)", commit=True)
db_run("ALTER TABLE eventi ADD COLUMN esito TEXT", commit=True)
db_run("ALTER TABLE terapie ADD COLUMN is_prn INTEGER DEFAULT 0", commit=True)

# 5. GESTIONE TEMPO (Sidebar)
oggi = datetime.now()
mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
with st.sidebar:
    st.header("📅 Archivio")
    m_sel = st.selectbox("Mese", mesi, index=oggi.month - 1)
    a_sel = st.number_input("Anno", 2024, 2030, oggi.year)
    m_idx = mesi.index(m_sel) + 1
    filtro_m = f"{m_idx:02d}/{a_sel}"
    gg_mese = calendar.monthrange(a_sel, m_idx)[1]

# 6. APP
p_list = db_run("SELECT id, nome FROM pazienti")
if not p_list:
    if st.button("Crea Paziente Test"):
        db_run("INSERT INTO pazienti (nome) VALUES ('PAZIENTE 1')", commit=True)
        st.rerun()
else:
    sel_p = st.selectbox("Seleziona Paziente", [p[1] for p in p_list])
    p_id = [p[0] for p in p_list if p[1] == sel_p][0]
    
    t1, t2 = st.tabs(["💊 REGISTRO", "🩺 MEDICO"])
    
    with t1:
        turno = st.selectbox("Turno", ["Mattina (08-13)", "Pomeriggio/Notte (16-20)", "TAB"])
        farmaci = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, is_prn FROM terapie WHERE p_id=?", (p_id,))
        
        # Mappa indici: MAT=3, POM=4, NOT=5, TAB=6
        mappa = {"Mattina (08-13)": [3, 4], "Pomeriggio/Notte (16-20)": [4, 5], "TAB": [6]}
        
        for f in farmaci:
            if any(f[i] == 1 for i in mappa[turno]):
                st.markdown(f"### {f[1]}")
                st.caption(f"Dose: {f[2]}")
                
                # Firme
                firme = db_run("SELECT data, esito, op FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                               (p_id, f"%{f[1]}%", f"%/{filtro_m}%"))
                f_map = {int(d[0].split("/")[0]): {"e": d[1], "o": d[2], "h": d[0].split(" ")[1]} for d in firme if d[0]}

                # Striscia
                h = "<div class='scroll-giorni'>"
                for d in range(1, gg_mese + 1):
                    info = f_map.get(d)
                    cl = "quadratino oggi" if (d == oggi.day and m_idx == oggi.month) else "quadratino"
                    es, col, bg = (info['e'], "green", "#dcfce7") if info else ("-", "#888", "white")
                    if es == "R": col, bg = "red", "#fee2e2"
                    op_t = f"{info['o']}<br>{info['h']}" if info else ""
                    h += f"<div class='{cl}' style='background:{bg}; color:{col};'><span style='font-size:8px;'>{d}</span><b>{es}</b><div class='info-f'>{op_t}</div></div>"
                h += "</div>"
                st.markdown(h, unsafe_allow_html=True)

                # Firma
                with st.popover(f"Smarca {f[1]}"):
                    g_f = st.number_input("Giorno", 1, gg_mese, value=min(oggi.day, gg_mese), key=f"g_{f[0]}")
                    c1, c2 = st.columns(2)
                    if c1.button("✅ A", key=f"A_{f[0]}"):
                        dt = f"{g_f:02d}/{filtro_m} {datetime.now().strftime('%H:%M')}"
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", (p_id, dt, f"✔️ {f[1]}", "Inf", "Op.1", "A"), commit=True)
                        st.rerun()
                    if c2.button("❌ R", key=f"R_{f[0]}"):
                        dt = f"{g_f:02d}/{filtro_m} {datetime.now().strftime('%H:%M')}"
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", (p_id, dt, f"✔️ {f[1]}", "Inf", "Op.1", "R"), commit=True)
                        st.rerun()
                st.divider()

    with t2:
        with st.form("med"):
            f_n = st.text_input("Farmaco")
            f_d = st.text_input("Dose")
            ora = st.selectbox("Orario", ["MATTINO", "POMERIGGIO", "NOTTE", "TAB"])
            if st.form_submit_button("Salva"):
                m, p, n, t = (1,0,0,0) if ora=="MATTINO" else ((0,1,0,0) if ora=="POMERIGGIO" else ((0,0,1,0) if ora=="NOTTE" else (0,0,0,1)))
                db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, is_prn) VALUES (?,?,?,?,?,?,?)", (p_id, f_n, f_d, m, p, n, t), commit=True)
                st.rerun()
