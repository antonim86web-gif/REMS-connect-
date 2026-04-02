import streamlit as st
import sqlite3
import calendar
from datetime import datetime

# --- 1. DATABASE SETUP ---
def db_run(query, params=(), commit=False):
    with sqlite3.connect("stu_pro.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit: conn.commit()
        return cursor.fetchall()

db_run("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
db_run("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY, p_id INTEGER, farmaco TEXT, dose TEXT, h8 INT, h13 INT, h16 INT, h20 INT, tab INT)")
db_run("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, nota TEXT, esito TEXT, op TEXT)")

# --- 2. CSS PROFESSIONALE ---
st.markdown("""
<style>
    .stu-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 11px; }
    .stu-table th, .stu-table td { border: 1px solid #ccc; text-align: center; padding: 3px; }
    .header-stu { background: #2c3e50; color: white; }
    .col-farmaco { text-align: left !important; font-weight: bold; width: 180px; background: #f9f9f9; }
    .cell-today { background-color: #fff9c4 !important; border: 1.5px solid #fbc02d !important; }
    .v-assunto { color: #2e7d32; font-weight: bold; }
    .x-rifiuto { color: #d32f2f; font-weight: bold; }
    .btn-v { background-color: #4caf50 !important; color: white !important; font-size: 10px !important; }
    .btn-x { background-color: #f44336 !important; color: white !important; font-size: 10px !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. GESTIONE ACCESSO ---
if 'op' not in st.session_state:
    with st.form("login"):
        op = st.text_input("Operatore (Firma)")
        if st.form_submit_button("ACCEDI"):
            st.session_state.op = op
            st.rerun()
    st.stop()

# --- 4. INTERFACCIA ---
st.sidebar.write(f"✍️ Operatore: **{st.session_state.op}**")
if st.sidebar.button("Logout"):
    del st.session_state.op
    st.rerun()

# Selezione Paziente
paz_lista = db_run("SELECT * FROM pazienti")
p_sel_nome = st.selectbox("Paziente:", [p[1] for p in paz_lista] + ["+ Aggiungi Nuovo"])

if p_sel_nome == "+ Aggiungi Nuovo":
    nuovo = st.text_input("Nome Paziente:")
    if st.button("Salva"):
        db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True)
        st.rerun()
    st.stop()

p_id = [p[0] for p in paz_lista if p[1] == p_sel_nome][0]

# Gestione Terapie
with st.expander("⚙️ Gestione Terapia (Medico)"):
    f = st.text_input("Farmaco")
    d = st.text_input("Dose")
    h = st.multiselect("Orari", ["08", "13", "16", "20", "TAB"])
    if st.button("Salva in S.T.U."):
        db_run("INSERT INTO terapie (p_id, farmaco, dose, h8, h13, h16, h20, tab) VALUES (?,?,?,?,?,?,?,?)",
               (p_id, f, d, "08" in h, "13" in h, "16" in h, "20" in h, "TAB" in h), True)
        st.rerun()
    st.write("---")
    ter_attive = db_run("SELECT id_u, farmaco FROM terapie WHERE p_id=?", (p_id,))
    for tid, tfn in ter_attive:
        if st.button(f"Sospendi {tfn}", key=f"del_{tid}"):
            db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
            st.rerun()

# --- 5. GRIGLIA S.T.U. (STILE CARTACEO) ---
now = datetime.now()
gg, mm, aa = now.day, now.month, now.year
ult_gg = calendar.monthrange(aa, mm)[1]

terapie = db_run("SELECT * FROM terapie WHERE p_id=?", (p_id,))
html = f"<table class='stu-table'><tr class='header-stu'><th>FARMACO / DOSE</th><th>H</th>"
for i in range(1, ult_gg + 1):
    html += f"<th class='{'cell-today' if i == gg else ''}'>{i}</th>"
html += "</tr>"

for t in terapie:
    # Mappatura: t[4]=h8, t[5]=h13, t[6]=h16, t[7]=h20, t[8]=tab
    config = [("08", t[4]), ("13", t[5]), ("16", t[6]), ("20", t[7]), ("TAB", t[8])]
    for label, attivo in config:
        if attivo:
            html += f"<tr><td class='col-farmaco'>{t[2]} ({t[3]})</td><td><b>{label}</b></td>"
            for d in range(1, ult_gg + 1):
                cl_today = "cell-today" if d == gg else ""
                data_c = f"{d:02d}/{mm:02d}/{aa}"
                check = db_run("SELECT esito FROM eventi WHERE p_id=? AND data LIKE ? AND nota LIKE ?", 
                               (p_id, f"{data_c}%", f"%({label}): {t[2]}%"))
                
                if check:
                    esito = check[0][0]
                    classe = "v-assunto" if esito == "V" else "x-rifiuto"
                    html += f"<td class='{cl_today} {classe}'>{esito}</td>"
                else:
                    html += f"<td class='{cl_today}'></td>"
            html += "</tr>"
html += "</table>"
st.markdown(html, unsafe_allow_html=True)

# --- 6. SMARCAMENTO RAPIDO (OGGI) ---
st.write("### ✍️ Firma Somministrazione (Oggi)")
if terapie:
    for t in terapie:
        cols = st.columns([2, 4])
        cols[0].write(f"**{t[2]}**")
        btn_cols = cols[1].columns(5)
        config = [("08", t[4]), ("13", t[5]), ("16", t[6]), ("20", t[7]), ("TAB", t[8])]
        
        for idx, (label, attivo) in enumerate(config):
            if attivo:
                # Controlla se già firmato oggi
                data_oggi = now.strftime("%d/%m/%Y")
                gia_fatto = db_run("SELECT id_u FROM eventi WHERE p_id=? AND data LIKE ? AND nota LIKE ?", 
                                   (p_id, f"{data_oggi}%", f"%({label}): {t[2]}%"))
                
                if not gia_fatto:
                    with btn_cols[idx]:
                        if st.button(f"V {label}", key=f"v_{t[0]}_{label}", help="Assunta"):
                            db_run("INSERT INTO eventi (p_id, data, nota, esito, op) VALUES (?,?,?,?,?)",
                                   (p_id, now.strftime("%d/%m/%Y %H:%M"), f"({label}): {t[2]}", "V", st.session_state.op), True)
                            st.rerun()
                        if st.button(f"X {label}", key=f"x_{t[0]}_{label}", help="Rifiutata"):
                            db_run("INSERT INTO eventi (p_id, data, nota, esito, op) VALUES (?,?,?,?,?)",
                                   (p_id, now.strftime("%d/%m/%Y %H:%M"), f"({label}): {t[2]}", "X", st.session_state.op), True)
                            st.rerun()
                else:
                    btn_cols[idx].write("✅")
