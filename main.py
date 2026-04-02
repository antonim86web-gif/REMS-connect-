import streamlit as st
import sqlite3
import calendar
from datetime import datetime

# --- 1. DATABASE ---
def db_run(query, params=(), commit=False):
    with sqlite3.connect("stu_rems_compact.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit: conn.commit()
        return cursor.fetchall()

db_run("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
db_run("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY, p_id INTEGER, farmaco TEXT, dose TEXT, h8 INT, h13 INT, h16 INT, h20 INT, tab INT)")
db_run("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, nota TEXT, esito TEXT, op TEXT)")

# --- 2. CSS ULTRA-COMPATTO ---
st.markdown("""
<style>
    .reportview-container .main .block-container { padding-top: 1rem; }
    .stu-table { width: 100%; border-collapse: collapse; font-size: 10px; margin-bottom: 20px; }
    .stu-table th, .stu-table td { border: 1px solid #999; text-align: center; padding: 2px; }
    .header-stu { background: #1e3a8a; color: white; }
    .col-farmaco { text-align: left !important; font-weight: bold; width: 150px; background: #f1f5f9; font-size: 11px; }
    .cell-today { background-color: #fff9c4 !important; }
    .v-sign { color: #16a34a; font-weight: bold; }
    .x-sign { color: #dc2626; font-weight: bold; }
    
    /* Riduzione bottoni smarcamento */
    .stButton>button { 
        padding: 0px 2px !important; 
        height: 18px !important; 
        min-height: 18px !important;
        font-size: 9px !important; 
        line-height: 1 !important;
    }
    .compact-text { font-size: 10px; margin-bottom: 0px; }
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIN & SELEZIONE ---
if 'op' not in st.session_state:
    st.session_state.op = st.text_input("Firma Operatore:")
    if not st.session_state.op: st.stop()

p_lista = db_run("SELECT * FROM pazienti")
col_sel, col_add = st.columns([3, 1])
p_sel = col_sel.selectbox("Paziente", [p[1] for p in p_lista])
if col_add.button("+ PAZIENTE"):
    n = st.text_input("Nuovo nome:")
    if n: db_run("INSERT INTO pazienti (nome) VALUES (?)", (n,), True); st.rerun()

p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
now = datetime.now()
data_oggi = now.strftime("%d/%m/%Y")

# --- 4. PRESCRIZIONE (Nascosta in expander per spazio) ---
with st.expander("🩺 Prescrizione Medica"):
    c1,c2,c3 = st.columns([2,1,2])
    f = c1.text_input("Farmaco")
    d = c2.text_input("Dose")
    h = c3.multiselect("H", ["08","13","16","20","TAB"])
    if st.button("Aggiungi"):
        db_run("INSERT INTO terapie (p_id, farmaco, dose, h8, h13, h16, h20, tab) VALUES (?,?,?,?,?,?,?,?)",
               (p_id, f, d, "08" in h, "13" in h, "16" in h, "20" in h, "TAB" in h), True); st.rerun()

# --- 5. SMARCAMENTO ORIZZONTALE COMPATTO ---
st.markdown("### ✍️ SMARCAMENTO RAPIDO OGGI")
terapie = db_run("SELECT * FROM terapie WHERE p_id=?", (p_id,))

if terapie:
    # Intestazione mini-tabella firme
    h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([2,1,1,1,1,1])
    h_col1.caption("FARMACO")
    h_col2.caption("08:00")
    h_col3.caption("13:00")
    h_col4.caption("16:00")
    h_col5.caption("20:00")
    h_col6.caption("TAB")

    for t in terapie:
        c_far, c8, c13, c16, c20, ctab = st.columns([2,1,1,1,1,1])
        c_far.markdown(f"<p class='compact-text'><b>{t[2]}</b> ({t[3]})</p>", unsafe_allow_html=True)
        
        for idx, (lab, col_obj, f_idx) in enumerate([("08", c8, 4), ("13", c13, 5), ("16", c16, 6), ("20", c20, 7), ("TAB", ctab, 8)]):
            if t[f_idx]:
                gia = db_run("SELECT esito FROM eventi WHERE p_id=? AND data LIKE ? AND nota LIKE ?", 
                             (p_id, f"{data_oggi}%", f"%({lab}): {t[2]}%"))
                if gia:
                    col_obj.markdown(f"<span class='{'v-sign' if gia[0][0]=='V' else 'x-sign'}'>{gia[0][0]}</span>", unsafe_allow_html=True)
                else:
                    cv, cx = col_obj.columns(2)
                    if cv.button("V", key=f"v{t[0]}{lab}"):
                        db_run("INSERT INTO eventi (p_id, data, nota, esito, op) VALUES (?,?,?,?,?)",
                               (p_id, now.strftime("%d/%m/%Y %H:%M"), f"({lab}): {t[2]}", "V", st.session_state.op), True); st.rerun()
                    if cx.button("X", key=f"x{t[0]}{lab}"):
                        db_run("INSERT INTO eventi (p_id, data, nota, esito, op) VALUES (?,?,?,?,?)",
                               (p_id, now.strftime("%d/%m/%Y %H:%M"), f"({lab}): {t[2]}", "X", st.session_state.op), True); st.rerun()
    st.divider()

# --- 6. GRIGLIA MENSILE S.T.U. ---
st.markdown("### 📊 SCHEDA TERAPIA UNIFICATA")
gg, mm, aa = now.day, now.month, now.year
ult_gg = calendar.monthrange(aa, mm)[1]

html = f"<table class='stu-table'><tr class='header-stu'><th>FARMACO / DOSE</th><th>H</th>"
for i in range(1, ult_gg + 1):
    cl = "class='cell-today'" if i == gg else ""
    html += f"<th {cl}>{i}</th>"
html += "</tr>"

for t in terapie:
    for lab, active, f_idx in [("08", t[4], 4), ("13", t[5], 5), ("16", t[6], 6), ("20", t[7], 7), ("TAB", t[8], 8)]:
        if active:
            html += f"<tr><td class='col-farmaco'>{t[2]} {t[3]}</td><td><b>{lab}</b></td>"
            for d in range(1, ult_gg + 1):
                cl_t = "cell-today" if d == gg else ""
                data_c = f"{d:02d}/{mm:02d}/{aa}"
                check = db_run("SELECT esito FROM eventi WHERE p_id=? AND data LIKE ? AND nota LIKE ?", 
                               (p_id, f"{data_c}%", f"%({lab}): {t[2]}%"))
                if check:
                    esito = check[0][0]
                    col = "v-sign" if esito == "V" else "x-sign"
                    html += f"<td class='{cl_t} {col}'>{esito}</td>"
                else:
                    html += f"<td class='{cl_t}'></td>"
            html += "</tr>"
html += "</table>"
st.markdown(html, unsafe_allow_html=True)
