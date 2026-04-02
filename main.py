import streamlit as st
import sqlite3
from datetime import datetime
import calendar

# --- DATABASE MINIMAL ---
def db_run(query, params=(), commit=False):
    with sqlite3.connect("stu_minimal.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit: conn.commit()
        return cursor.fetchall()

db_run("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
db_run("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY, p_id INTEGER, farmaco TEXT, dose TEXT, h8 INT, h13 INT, h16 INT, h20 INT, tab INT)")
db_run("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, nota TEXT, op TEXT)")

# --- CSS MINIMAL (STILE FOGLIO) ---
st.markdown("""
<style>
    .stu-table { width: 100%; border-collapse: collapse; font-family: monospace; font-size: 12px; }
    .stu-table th, .stu-table td { border: 1px solid black; text-align: center; padding: 2px; }
    .today { background-color: #ffff00; }
    .farmaco-nome { text-align: left !important; font-weight: bold; padding-left: 5px !important; width: 150px; }
    button { padding: 0px !important; height: 20px !important; min-width: 30px !important; font-size: 10px !important; }
</style>
""", unsafe_allow_html=True)

# --- LOGIN RAPIDO ---
if 'user' not in st.session_state:
    st.session_state.user = st.text_input("Chi sei? (Firma)")
    if not st.session_state.user: st.stop()

# --- GESTIONE PAZIENTI ---
c1, c2 = st.columns([2,1])
nuovo_p = c1.text_input("Aggiungi Paziente")
if c2.button("SALVA PAZIENTE") and nuovo_p:
    db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo_p,), True)

pazienti = db_run("SELECT * FROM pazienti")
if not pazienti: st.stop()
p_sel = st.selectbox("PAZIENTE SELEZIONATO:", [p[1] for p in pazienti])
p_id = [p[0] for p in pazienti if p[1] == p_sel][0]

# --- PRESCRIZIONE MINIMAL ---
with st.expander("➕ NUOVA TERAPIA"):
    f = st.text_input("Farmaco")
    d = st.text_input("Dose")
    h = st.multiselect("Orari:", ["08", "13", "16", "20", "TAB"])
    if st.button("CONFERMA PRESCRIZIONE"):
        db_run("INSERT INTO terapie (p_id, farmaco, dose, h8, h13, h16, h20, tab) VALUES (?,?,?,?,?,?,?,?)",
               (p_id, f, d, "08" in h, "13" in h, "16" in h, "20" in h, "TAB" in h), True)
        st.rerun()

# --- GRIGLIA S.T.U. ---
now = datetime.now()
gg, mm, aa = now.day, now.month, now.year
ult_gg = calendar.monthrange(aa, mm)[1]

terapie = db_run("SELECT * FROM terapie WHERE p_id=?", (p_id,))
html = f"<table class='stu-table'><tr><th>FARMACO / DOSE</th><th>H</th>"
for i in range(1, ult_gg + 1):
    html += f"<th class='{'today' if i == gg else ''}'>{i}</th>"
html += "</tr>"

for t in terapie:
    orari = [("08", t[4]), ("13", t[5]), ("16", t[6]), ("20", t[7]), ("TAB", t[8])]
    for label, attivo in orari:
        if attivo:
            html += f"<tr><td class='farmaco-nome'>{t[2]} {t[3]}</td><td>{label}</td>"
            for d in range(1, ult_gg + 1):
                data_c = f"{d:02d}/{mm:02d}/{aa}"
                firma = db_run("SELECT op FROM eventi WHERE p_id=? AND data LIKE ? AND nota LIKE ?", (p_id, f"{data_c}%", f"%({label}): {t[2]}%"))
                if firma:
                    html += f"<td class='{'today' if d == gg else ''}'>X</td>"
                else:
                    html += f"<td class='{'today' if d == gg else ''}'></td>"
            html += "</tr>"
html += "</table>"
st.markdown(html, unsafe_allow_html=True)

# --- SMARCAMENTO VELOCE ---
st.write("### SMARCA OGGI:")
cols = st.columns(4)
for i, t in enumerate(terapie):
    with cols[i % 4]:
        st.write(f"**{t[2]}**")
        for label, attivo in [("08", t[4]), ("13", t[5]), ("16", t[6]), ("20", t[7]), ("TAB", t[8])]:
            if attivo:
                if st.button(f"FIRMA {label}", key=f"f_{t[0]}_{label}"):
                    db_run("INSERT INTO eventi (p_id, data, nota, op) VALUES (?,?,?,?)",
                           (p_id, now.strftime("%d/%m/%Y %H:%M"), f"({label}): {t[2]}", st.session_state.user), True)
                    st.rerun()
