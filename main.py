import streamlit as st
import sqlite3
import calendar
from datetime import datetime

# --- 1. DATABASE ---
def db_run(query, params=(), commit=False):
    with sqlite3.connect("rems_final.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit: conn.commit()
        return cursor.fetchall()

db_run("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
db_run("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY, p_id INTEGER, farmaco TEXT, dose TEXT, h8 INT, h13 INT, h16 INT, h20 INT, tab INT)")
db_run("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, nota TEXT, esito TEXT, op TEXT)")

# --- 2. CSS "TABLET-REMS" (FORZA ORIZZONTALE E MINIATURA) ---
st.markdown("""
<style>
    /* Riduce i margini della pagina */
    .block-container { padding: 10px !important; }
    
    /* Testo e tabelle piccolissime */
    html, body, [class*="css"] { font-size: 11px !important; }
    
    /* Griglia Smarcamento: Forza tutto su una riga */
    .row-smarc {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 4px 0;
        border-bottom: 1px solid #eee;
    }
    .farmaco-label { width: 35%; font-weight: bold; line-height: 1; }
    .orario-box { width: 12%; text-align: center; }
    
    /* Bottoni minuscoli e affiancati */
    div.stButton > button {
        width: 24px !important;
        height: 20px !important;
        padding: 0 !important;
        font-size: 10px !important;
        border-radius: 4px !important;
        margin: 0 1px !important;
    }
    
    /* Colori esiti */
    .v-sign { color: #16a34a; font-weight: bold; font-size: 12px; }
    .x-sign { color: #dc2626; font-weight: bold; font-size: 12px; }
    
    /* S.T.U. Mensile: Compattezza massima */
    .stu-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .stu-table th, .stu-table td { border: 1px solid #999; padding: 1px; font-size: 9px; text-align: center; }
    .today { background: #fffde7 !important; border: 1.5px solid #fbc02d !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. SESSIONE ---
if 'op' not in st.session_state:
    st.session_state.op = st.text_input("Operatore (Firma):")
    if not st.session_state.op: st.stop()

# --- 4. SELEZIONE PAZIENTE ---
p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
p_nomi = [p[1] for p in p_lista]
col_sel, col_add = st.columns([3, 1])
p_sel = col_sel.selectbox("Paziente:", p_nomi if p_nomi else ["Nessuno"])

with col_add.expander("+"):
    n = st.text_input("Nome:")
    if st.button("OK"):
        db_run("INSERT INTO pazienti (nome) VALUES (?)", (n,), True); st.rerun()

if not p_nomi: st.stop()
p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
now = datetime.now()
data_oggi = now.strftime("%d/%m/%Y")

# --- 5. AREA MEDICA (COMPATTA) ---
with st.expander("🩺 Prescrizione"):
    c1, c2, c3 = st.columns([2,1,2])
    f = c1.text_input("Farmaco")
    d = c2.text_input("Dose")
    h = c3.multiselect("Orari", ["08","13","16","20","TAB"])
    if st.button("Salva"):
        db_run("INSERT INTO terapie (p_id, farmaco, dose, h8, h13, h16, h20, tab) VALUES (?,?,?,?,?,?,?,?)",
               (p_id, f, d, "08" in h, "13" in h, "16" in h, "20" in h, "TAB" in h), True); st.rerun()

# --- 6. SMARCAMENTO ORIZZONTALE (LA SOLUZIONE) ---
st.markdown(f"### ✍️ SMARCAMENTO {data_oggi}")
terapie = db_run("SELECT * FROM terapie WHERE p_id=?", (p_id,))

# Testata fissa
t1, t2, t3, t4, t5, t6 = st.columns([3, 1, 1, 1, 1, 1])
t1.caption("Farmaco/Dose")
t2.caption("08")
t3.caption("13")
t4.caption("16")
t5.caption("20")
t6.caption("TAB")

for t in terapie:
    # t[2]=farmaco, t[3]=dose, t[4-8]=orari
    r_far, r8, r13, r16, r20, rtab = st.columns([3, 1, 1, 1, 1, 1])
    
    r_far.markdown(f"**{t[2]}** {t[3]}")
    
    col_objs = [r8, r13, r16, r20, rtab]
    labels = ["08", "13", "16", "20", "TAB"]
    idx_sql = [4, 5, 6, 7, 8]

    for i in range(5):
        if t[idx_sql[i]]:
            # Cerca se già firmato
            gia = db_run("SELECT esito FROM eventi WHERE p_id=? AND data LIKE ? AND nota LIKE ?", 
                         (p_id, f"{data_oggi}%", f"%({labels[i]}): {t[2]}%"))
            
            if gia:
                sym = gia[0][0]
                cl = "v-sign" if sym == "V" else "x-sign"
                col_objs[i].markdown(f"<div style='text-align:center' class='{cl}'>{sym}</div>", unsafe_allow_html=True)
            else:
                # Bottoni affiancati nella mini-colonna
                with col_objs[i]:
                    c_v, c_x = st.columns(2)
                    if c_v.button("V", key=f"v{t[0]}{labels[i]}"):
                        db_run("INSERT INTO eventi (p_id, data, nota, esito, op) VALUES (?,?,?,?,?)",
                               (p_id, now.strftime("%d/%m/%Y %H:%M"), f"({labels[i]}): {t[2]}", "V", st.session_state.op), True); st.rerun()
                    if c_x.button("X", key=f"x{t[0]}{labels[i]}"):
                        db_run("INSERT INTO eventi (p_id, data, nota, esito, op) VALUES (?,?,?,?,?)",
                               (p_id, now.strftime("%d/%m/%Y %H:%M"), f"({labels[i]}): {t[2]}", "X", st.session_state.op), True); st.rerun()

st.write("---")

# --- 7. S.T.U. MENSILE ---
st.markdown("### 📊 SCHEDA TERAPIA MENSILE")
gg, mm, aa = now.day, now.month, now.year
ult_gg = calendar.monthrange(aa, mm)[1]

html = f"<table class='stu-table'><tr class='header-stu'><th>F/D</th><th>H</th>"
for i in range(1, ult_gg + 1):
    html += f"<th class='{'today' if i == gg else ''}'>{i}</th>"
html += "</tr>"

for t in terapie:
    config = [("08", t[4]), ("13", t[5]), ("16", t[6]), ("20", t[7]), ("TAB", t[8])]
    for lab, active in config:
        if active:
            html += f"<tr><td style='text-align:left'><b>{t[2]}</b> {t[3]}</td><td>{lab}</td>"
            for d in range(1, ult_gg + 1):
                cl_t = "today" if d == gg else ""
                data_c = f"{d:02d}/{mm:02d}/{aa}"
                check = db_run("SELECT esito FROM eventi WHERE p_id=? AND data LIKE ? AND nota LIKE ?", 
                               (p_id, f"{data_c}%", f"%({lab}): {t[2]}%"))
                if check:
                    es = check[0][0]
                    col = "#16a34a" if es == "V" else "#dc2626"
                    html += f"<td class='{cl_t}' style='color:{col}; font-weight:bold;'>{es}</td>"
                else:
                    html += f"<td class='{cl_t}'></td>"
            html += "</tr>"
html += "</table>"
st.markdown(html, unsafe_allow_html=True)
