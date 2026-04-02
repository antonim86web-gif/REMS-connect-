import streamlit as st
import sqlite3
import calendar
from datetime import datetime

# --- 1. DATABASE SETUP ---
def db_run(query, params=(), commit=False):
    with sqlite3.connect("rems_stu_v4.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit: conn.commit()
        return cursor.fetchall()

# Inizializzazione tabelle
db_run("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
db_run("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY, p_id INTEGER, farmaco TEXT, dose TEXT, h8 INT, h13 INT, h16 INT, h20 INT, tab INT)")
db_run("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, nota TEXT, esito TEXT, op TEXT)")

# --- 2. CSS PROFESSIONALE ULTRA-COMPATTO ---
st.markdown("""
<style>
    .reportview-container .main .block-container { padding-top: 1rem; }
    .stu-table { width: 100%; border-collapse: collapse; font-size: 10px; margin-bottom: 20px; }
    .stu-table th, .stu-table td { border: 1px solid #999; text-align: center; padding: 2px; }
    .header-stu { background: #1e3a8a; color: white; }
    .col-farmaco { text-align: left !important; font-weight: bold; width: 140px; background: #f1f5f9; font-size: 10px; }
    .cell-today { background-color: #fff9c4 !important; }
    .v-sign { color: #16a34a; font-weight: bold; }
    .x-sign { color: #dc2626; font-weight: bold; }
    
    /* Riduzione bottoni firma */
    .stButton>button { 
        padding: 0px 1px !important; 
        height: 18px !important; 
        min-height: 18px !important;
        font-size: 9px !important; 
        width: 22px !important;
    }
    p { margin-bottom: 0px !important; font-size: 11px; }
</style>
""", unsafe_allow_html=True)

# --- 3. SESSIONE & LOGIN ---
if 'op' not in st.session_state:
    st.subheader("🖋️ Firma Digitale Operatore")
    op_input = st.text_input("Inserisci Nome e Cognome per operare:")
    if st.button("ACCEDI"):
        if op_input:
            st.session_state.op = op_input
            st.rerun()
    st.stop()

# --- 4. GESTIONE PAZIENTI ---
p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")

col_sel, col_add = st.columns([3, 1])
if not p_lista:
    st.warning("Nessun paziente. Aggiungine uno a destra ➡️")
    p_sel_nome = None
else:
    p_sel_nome = col_sel.selectbox("Paziente:", [p[1] for p in p_lista])

with col_add.expander("+ NUOVO"):
    nuovo_n = st.text_input("Nome:")
    if st.button("SALVA"):
        db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo_n,), True)
        st.rerun()

if not p_sel_nome:
    st.stop()

# Recupero ID Corretto del paziente selezionato
p_id = [p[0] for p in p_lista if p[1] == p_sel_nome][0]
now = datetime.now()
data_oggi = now.strftime("%d/%m/%Y")

# --- 5. PRESCRIZIONE MEDICA ---
with st.expander("🩺 Area Medica (Aggiungi/Sospendi)"):
    c1, c2, c3 = st.columns([2,1,2])
    f_input = c1.text_input("Farmaco")
    d_input = c2.text_input("Dose")
    h_input = c3.multiselect("Orari", ["08","13","16","20","TAB"])
    if st.button("INSERISCI"):
        db_run("INSERT INTO terapie (p_id, farmaco, dose, h8, h13, h16, h20, tab) VALUES (?,?,?,?,?,?,?,?)",
               (p_id, f_input, d_input, "08" in h_input, "13" in h_input, "16" in h_input, "20" in h_input, "TAB" in h_input), True)
        st.rerun()
    st.write("---")
    t_esistenti = db_run("SELECT id_u, farmaco FROM terapie WHERE p_id=?", (p_id,))
    for tid, tfn in t_esistenti:
        if st.button(f"Sospendi {tfn}", key=f"del_{tid}"):
            db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
            st.rerun()

# --- 6. SMARCAMENTO ORIZZONTALE COMPATTO ---
st.markdown(f"### ✍️ SMARCAMENTO OGGI ({data_oggi})")
terapie = db_run("SELECT * FROM terapie WHERE p_id=?", (p_id,))

if terapie:
    # Testata Colonne Firme
    h_c1, h_c2, h_c3, h_c4, h_c5, h_c6 = st.columns([2,1,1,1,1,1])
    h_c1.caption("FARMACO")
    h_c2.caption("08:00")
    h_c3.caption("13:00")
    h_c4.caption("16:00")
    h_c5.caption("20:00")
    h_c6.caption("TAB")

    for t in terapie:
        # t[0]:id_u, t[2]:farmaco, t[3]:dose, t[4-8]:orari
        r_far, r8, r13, r16, r20, rtab = st.columns([2,1,1,1,1,1])
        r_far.markdown(f"**{t[2]}** <br><small>{t[3]}</small>", unsafe_allow_html=True)
        
        col_list = [r8, r13, r16, r20, rtab]
        lab_list = ["08", "13", "16", "20", "TAB"]
        idx_list = [4, 5, 6, 7, 8]

        for i in range(5):
            if t[idx_list[i]]: # Se l'orario è attivo
                gia = db_run("SELECT esito FROM eventi WHERE p_id=? AND data LIKE ? AND nota LIKE ?", 
                             (p_id, f"{data_oggi}%", f"%({lab_list[i]}): {t[2]}%"))
                if gia:
                    col_list[i].markdown(f"<p class='{'v-sign' if gia[0][0]=='V' else 'x-sign'}'>{gia[0][0]}</p>", unsafe_allow_html=True)
                else:
                    cv, cx = col_list[i].columns(2)
                    if cv.button("V", key=f"v_{t[0]}_{lab_list[i]}"):
                        db_run("INSERT INTO eventi (p_id, data, nota, esito, op) VALUES (?,?,?,?,?)",
                               (p_id, now.strftime("%d/%m/%Y %H:%M"), f"({lab_list[i]}): {t[2]}", "V", st.session_state.op), True); st.rerun()
                    if cx.button("X", key=f"x_{t[0]}_{lab_list[i]}"):
                        db_run("INSERT INTO eventi (p_id, data, nota, esito, op) VALUES (?,?,?,?,?)",
                               (p_id, now.strftime("%d/%m/%Y %H:%M"), f"({lab_list[i]}): {t[2]}", "X", st.session_state.op), True); st.rerun()
    st.divider()

# --- 7. GRIGLIA MENSILE S.T.U. ---
st.markdown("### 📊 SCHEDA TERAPIA MENSILE")
gg, mm, aa = now.day, now.month, now.year
ult_gg = calendar.monthrange(aa, mm)[1]

html = f"<table class='stu-table'><tr class='header-stu'><th>FARMACO / DOSE</th><th>H</th>"
for i in range(1, ult_gg + 1):
    cl = "class='cell-today'" if i == gg else ""
    html += f"<th {cl}>{i}</th>"
html += "</tr>"

for t in terapie:
    config_tab = [("08", t[4]), ("13", t[5]), ("16", t[6]), ("20", t[7]), ("TAB", t[8])]
    for label, attivo in config_tab:
        if attivo:
            html += f"<tr><td class='col-farmaco'>{t[2]} {t[3]}</td><td><b>{label}</b></td>"
            for d in range(1, ult_gg + 1):
                cl_t = "cell-today" if d == gg else ""
                data_c = f"{d:02d}/{mm:02d}/{aa}"
                check = db_run("SELECT esito FROM eventi WHERE p_id=? AND data LIKE ? AND nota LIKE ?", 
                               (p_id, f"{data_c}%", f"%({label}): {t[2]}%"))
                if check:
                    es = check[0][0]
                    color = "v-sign" if es == "V" else "x-sign"
                    html += f"<td class='{cl_t} {color}'>{es}</td>"
                else:
                    html += f"<td class='{cl_t}'></td>"
            html += "</tr>"
html += "</table>"
st.markdown(html, unsafe_allow_html=True)

if st.sidebar.button("Logout"):
    del st.session_state.op
    st.rerun()
