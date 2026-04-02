import streamlit as st
import sqlite3
import calendar
from datetime import datetime

# --- 1. DATABASE ---
def db_run(query, params=(), commit=False):
    with sqlite3.connect("stu_peritale_v3.db") as conn:
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
    .stu-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 11px; margin-bottom: 30px; }
    .stu-table th, .stu-table td { border: 1px solid #aaa; text-align: center; padding: 4px; }
    .header-stu { background: #1e3a8a; color: white; font-weight: bold; }
    .col-farmaco { text-align: left !important; font-weight: bold; width: 200px; background: #f8fafc; }
    .cell-today { background-color: #fffde7 !important; border: 2px solid #fbc02d !important; }
    .v-check { color: #16a34a; font-weight: bold; font-size: 14px; }
    .x-check { color: #dc2626; font-weight: bold; font-size: 14px; }
    .section-label { background: #e2e8f0; font-weight: bold; padding: 5px; border-radius: 4px; margin: 10px 0; color: #1e3a8a; }
</style>
""", unsafe_allow_html=True)

# --- 3. ACCESSO ---
if 'op' not in st.session_state:
    st.title("🔐 S.T.U. Login")
    op = st.text_input("Firma Operatore (Nome e Cognome)")
    if st.button("ENTRA"):
        if op: st.session_state.op = op; st.rerun()
    st.stop()

# --- 4. SELEZIONE ---
p_lista = db_run("SELECT * FROM pazienti")
col_p1, col_p2 = st.columns([3, 1])
p_sel = col_p1.selectbox("Seleziona Paziente", [p[1] for p in p_lista] + ["+ NUOVO"])
if p_sel == "+ NUOVO":
    n = st.text_input("Nome:")
    if st.button("Salva"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (n,), True); st.rerun()
    st.stop()

p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
now = datetime.now()
data_oggi = now.strftime("%d/%m/%Y")

# --- 5. AREA MEDICA (PRESCRIZIONE) ---
with st.expander("🩺 Prescrizione Medica"):
    f = st.text_input("Farmaco")
    d = st.text_input("Dose")
    st.write("Orari:")
    c1,c2,c3,c4,c5 = st.columns(5)
    m8 = c1.checkbox("08:00")
    m13 = c2.checkbox("13:00")
    p16 = c3.checkbox("16:00")
    p20 = c4.checkbox("20:00")
    tb = c5.checkbox("TAB")
    if st.button("Inserisci"):
        db_run("INSERT INTO terapie (p_id, farmaco, dose, h8, h13, h16, h20, tab) VALUES (?,?,?,?,?,?,?,?)",
               (p_id, f, d, int(m8), int(m13), int(p16), int(p20), int(tb)), True)
        st.rerun()

# --- 6. SMARCAMENTO RAPIDO (SUDDIVISO PER FASCE) ---
st.markdown("### ✍️ SMARCAMENTO FIRME")
terapie = db_run("SELECT * FROM terapie WHERE p_id=?", (p_id,))

def riga_firma(t, label, field_idx):
    if t[field_idx] == 1:
        gia = db_run("SELECT esito FROM eventi WHERE p_id=? AND data LIKE ? AND nota LIKE ?", 
                     (p_id, f"{data_oggi}%", f"%({label}): {t[2]}%"))
        if gia:
            st.markdown(f"**{label}**: ✅ {gia[0][0]}")
        else:
            c_v, c_x = st.columns(2)
            if c_v.button(f"V {label}", key=f"v{t[0]}{label}"):
                db_run("INSERT INTO eventi (p_id, data, nota, esito, op) VALUES (?,?,?,?,?)",
                       (p_id, now.strftime("%d/%m/%Y %H:%M"), f"({label}): {t[2]}", "V", st.session_state.op), True); st.rerun()
            if c_x.button(f"X {label}", key=f"x{t[0]}{label}"):
                db_run("INSERT INTO eventi (p_id, data, nota, esito, op) VALUES (?,?,?,?,?)",
                       (p_id, now.strftime("%d/%m/%Y %H:%M"), f"({label}): {t[2]}", "X", st.session_state.op), True); st.rerun()

if terapie:
    tabs = st.tabs(["☀️ MATTINO (08-13)", "🌙 POMERIGGIO (16-20)", "💊 AL BISOGNO (TAB)"])
    
    with tabs[0]: # MATTINO
        for t in terapie:
            if t[4] or t[5]:
                st.markdown(f"**{t[2]}** ({t[3]})")
                col1, col2 = st.columns(2)
                with col1: riga_firma(t, "08", 4)
                with col2: riga_firma(t, "13", 5)
                st.divider()

    with tabs[1]: # POMERIGGIO
        for t in terapie:
            if t[6] or t[7]:
                st.markdown(f"**{t[2]}** ({t[3]})")
                col1, col2 = st.columns(2)
                with col1: riga_firma(t, "16", 6)
                with col2: riga_firma(t, "20", 7)
                st.divider()

    with tabs[2]: # TAB
        for t in terapie:
            if t[8]:
                st.markdown(f"**{t[2]}** ({t[3]})")
                riga_firma(t, "TAB", 8)
                st.divider()

# --- 7. GRIGLIA S.T.U. MENSILE ---
st.markdown("### 📊 SCHEDA TERAPIA UNIFICATA")
gg, mm, aa = now.day, now.month, now.year
ult_gg = calendar.monthrange(aa, mm)[1]

html = f"<table class='stu-table'><tr class='header-stu'><th>FARMACO / POSOLOGIA</th><th>H</th>"
for i in range(1, ult_gg + 1):
    cl = "class='cell-today'" if i == gg else ""
    html += f"<th {cl}>{i}</th>"
html += "</tr>"

# Configurazione fissa oraria per la tabella
for t in terapie:
    config = [("08", t[4]), ("13", t[5]), ("16", t[6]), ("20", t[7]), ("TAB", t[8])]
    for label, attivo in config:
        if attivo:
            html += f"<tr><td class='col-farmaco'>{t[2]} ({t[3]})</td><td><b>{label}</b></td>"
            for d in range(1, ult_gg + 1):
                cl_t = "cell-today" if d == gg else ""
                data_c = f"{d:02d}/{mm:02d}/{aa}"
                check = db_run("SELECT esito FROM eventi WHERE p_id=? AND data LIKE ? AND nota LIKE ?", 
                               (p_id, f"{data_c}%", f"%({label}): {t[2]}%"))
                if check:
                    esito = check[0][0]
                    colore = "v-check" if esito == "V" else "x-check"
                    html += f"<td class='{cl_t} {colore}'>{esito}</td>"
                else:
                    html += f"<td class='{cl_t}'></td>"
            html += "</tr>"
html += "</table>"
st.markdown(html, unsafe_allow_html=True)

if st.sidebar.button("LOGOUT"):
    del st.session_state.op; st.rerun()
