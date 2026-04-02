import streamlit as stimport streamlit as st
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

import sqlite3
import pandas as pd
from datetime import datetime
import calendar

# --- 1. CONFIGURAZIONE E DATABASE ---
st.set_page_config(layout="wide", page_title="S.T.U. Peritale Elite")

def init_db():
    with sqlite3.connect("clinica.db") as conn:
        cursor = conn.cursor()
        # Tabella Pazienti
        cursor.execute("""CREATE TABLE IF NOT EXISTS pazienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nome TEXT, stato TEXT DEFAULT 'ATTIVO')""")
        # Tabella Terapie (Modificata per i tuoi 4 orari + TAB)
        cursor.execute("""CREATE TABLE IF NOT EXISTS terapie (
            id_u INTEGER PRIMARY KEY AUTOINCREMENT, 
            p_id INTEGER, farmaco TEXT, dose TEXT, 
            h8 INTEGER, h13 INTEGER, h16 INTEGER, h20 INTEGER, tab INTEGER,
            medico TEXT)""")
        # Tabella Eventi (Il registro legale delle firme)
        cursor.execute("""CREATE TABLE IF NOT EXISTS eventi (
            id_u INTEGER PRIMARY KEY AUTOINCREMENT, 
            id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT)""")
        conn.commit()

def db_run(query, params=(), commit=False):
    with sqlite3.connect("clinica.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit: conn.commit()
        return cursor.fetchall()

init_db()

# --- 2. STILI CSS (LAYOUT PROFESSIONALE) ---
st.markdown("""
<style>
    .main-title { color: #1e3a8a; text-align: center; border-bottom: 3px solid #1e3a8a; }
    .stu-container { overflow-x: auto; border: 2px solid #1e3a8a; border-radius: 10px; background: white; padding: 5px; }
    .stu-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 11px; }
    .stu-table th { background: #1e3a8a; color: white; padding: 4px; border: 1px solid #cbd5e1; }
    .stu-table td { border: 1px solid #cbd5e1; text-align: center; padding: 2px; height: 25px; }
    .row-farmaco { background: #f1f5f9; font-weight: bold; text-align: left !important; min-width: 180px; padding-left: 8px !important; }
    .cell-today { background: #fef9c3 !important; border-left: 2px solid #eab308 !important; border-right: 2px solid #eab308 !important; }
    .sign-ok { color: #16a34a; font-weight: 900; }
    .sign-tab { color: #db2777; font-weight: 900; }
    .stButton>button { width: 100%; padding: 2px; font-size: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 3. LOGICA DI ACCESSO ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    with st.form("login"):
        st.title("🔐 Accesso Sistema S.T.U.")
        u = st.text_input("Utente")
        r = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Admin"])
        if st.form_submit_button("Entra"):
            st.session_state.auth = True
            st.session_state.user = u
            st.session_state.role = r
            st.rerun()
else:
    # --- 4. INTERFACCIA PRINCIPALE ---
    u_nome = st.session_state.user
    u_role = st.session_state.role
    
    st.sidebar.title(f"👤 {u_nome}")
    st.sidebar.info(f"Ruolo: {u_role}")
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    menu = st.sidebar.radio("Menu", ["Anagrafica Pazienti", "Gestione S.T.U."])

    # --- ANAGRAFICA ---
    if menu == "Anagrafica Pazienti":
        st.header("📋 Inserimento Nuovi Pazienti")
        with st.form("add_p"):
            n = st.text_input("Nome e Cognome Paziente")
            if st.form_submit_button("Registra"):
                db_run("INSERT INTO pazienti (nome) VALUES (?)", (n,), True)
                st.success(f"{n} aggiunto.")

    # --- GESTIONE S.T.U. (IL CUORE DEL SISTEMA) ---
    if menu == "Gestione S.T.U.":
        pazienti = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
        if not pazienti:
            st.info("Aggiungi un paziente in Anagrafica.")
        else:
            p_sel_nome = st.selectbox("Seleziona Paziente", [p[1] for p in pazienti])
            p_id = [p[0] for p in pazienti if p[1] == p_sel_nome][0]

            now = datetime.now()
            gg, mm, aa = now.day, now.month, now.year
            ult_gg = calendar.monthrange(aa, mm)[1]

            # A. Prescrizione Medico
            if u_role in ["Psichiatra", "Admin"]:
                with st.expander("📝 Nuova Prescrizione Farmaco"):
                    with st.form("prescr"):
                        f = st.text_input("Farmaco")
                        d = st.text_input("Dose")
                        st.write("Orari Somministrazione:")
                        c1,c2,c3,c4,c5 = st.columns(5)
                        h8 = c1.checkbox("08:00")
                        h13 = c2.checkbox("13:00")
                        h16 = c3.checkbox("16:00")
                        h20 = c4.checkbox("20:00")
                        tab = c5.checkbox("T.A.B.")
                        if st.form_submit_button("Invia in S.T.U."):
                            db_run("INSERT INTO terapie (p_id, farmaco, dose, h8, h13, h16, h20, tab, medico) VALUES (?,?,?,?,?,?,?,?,?)",
                                   (p_id, f, d, int(h8), int(h13), int(h16), int(h20), int(tab), u_nome), True)
                            st.rerun()

            # B. Rendering Griglia (Stile Foto: 08, 13, 16, 20, TAB)
            st.markdown(f"### 📊 S.T.U. Mensile - {p_sel_nome} ({mm}/{aa})")
            terapie = db_run("SELECT * FROM terapie WHERE p_id=?", (p_id,))
            
            if terapie:
                st.markdown("<div class='stu-container'>", unsafe_allow_html=True)
                html = "<table class='stu-table'><thead><tr><th>FARMACO / POSOLOGIA</th><th>H.</th>"
                for i in range(1, ult_gg + 1):
                    cl = "class='cell-today'" if i == gg else ""
                    html += f"<th {cl}>{i}</th>"
                html += "</tr></thead><tbody>"

                for t in terapie:
                    # t = (id_u, p_id, farmaco, dose, h8, h13, h16, h20, tab, medico)
                    orari_p = [("08", t[4]), ("13", t[5]), ("16", t[6]), ("20", t[7]), ("TAB", t[8])]
                    first_row = True
                    row_span = sum([1 for x in orari_p if x[1] == 1])

                    for label, attivo in orari_p:
                        if attivo == 1:
                            html += "<tr>"
                            if first_row:
                                html += f"<td rowspan='{row_span}' class='row-farmaco'>{t[2]}<br><small>{t[3]}</small></td>"
                                first_row = False
                            html += f"<td><b>{label}</b></td>"
                            
                            for d in range(1, ult_gg + 1):
                                cl = "class='cell-today'" if d == gg else ""
                                data_str = f"{d:02d}/{mm:02d}/{aa}"
                                # Controllo firma
                                f_check = db_run("SELECT op FROM eventi WHERE id=? AND data LIKE ? AND nota LIKE ?", 
                                               (p_id, f"{data_str}%", f"%({label}): {t[2]}%"))
                                if f_check:
                                    sym = "✔️" if label != "TAB" else "💊"
                                    color = "sign-ok" if label != "TAB" else "sign-tab"
                                    html += f"<td {cl} class='{color}' title='Firma: {f_check[0][0]}'>{sym}</td>"
                                else:
                                    html += f"<td {cl}></td>"
                            html += "</tr>"
                html += "</tbody></table></div>"
                st.markdown(html, unsafe_allow_html=True)

                # C. Area Firme per Infermieri (Smarcamento Rapido)
                if u_role in ["Infermiere", "Admin"]:
                    st.write("---")
                    st.subheader("✍️ Smarcamento Rapido (Oggi)")
                    for t in terapie:
                        with st.container():
                            c_f, c_h = st.columns([2, 3])
                            c_f.write(f"**{t[2]}**")
                            btns = c_h.columns(5)
                            labels = ["08", "13", "16", "20", "TAB"]
                            for idx, lab in enumerate(labels):
                                if t[idx+4] == 1: # Se l'orario è previsto
                                    if btns[idx].button(lab, key=f"btn_{t[0]}_{lab}"):
                                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                                               (p_id, now.strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({lab}): {t[2]} ({t[3]})", u_role, u_nome), True)
                                        st.rerun()

                # D. Sospensione (Solo Medico)
                if u_role in ["Psichiatra", "Admin"]:
                    with st.expander("🗑️ Sospendi Farmaci"):
                        for t in terapie:
                            if st.button(f"Elimina {t[2]} dalla scheda", key=f"del_{t[0]}"):
                                db_run("DELETE FROM terapie WHERE id_u=?", (t[0],), True)
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                                       (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🚫 SOSPESO: {t[2]}", u_role, u_nome), True)
                                st.rerun()
            else:
                st.warning("Nessuna terapia impostata per questo paziente.")
