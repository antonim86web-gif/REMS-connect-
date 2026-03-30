import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold; margin-bottom:20px;}
    .patient-header { background: #f8fafc; padding: 20px; border-radius: 12px; border-left: 8px solid #1e3a8a; margin-bottom: 25px; border: 1px solid #e2e8f0; }
    .allergy-alert { background: #fee2e2; color: #991b1b; padding: 8px 15px; border-radius: 6px; font-weight: bold; border: 1px solid #f87171; display: inline-block; }
    .diet-box { background: #fef9c3; color: #854d0e; padding: 8px 15px; border-radius: 6px; border: 1px solid #facc15; display: inline-block; }
    .custom-table {width: 100%; border-collapse: collapse; font-size: 0.85rem; background: white;}
    .custom-table th {background-color: #1e3a8a; color: white; padding: 10px; text-align: left; border: 1px solid #dee2e6;}
    .custom-table td {padding: 10px; border: 1px solid #dee2e6; vertical-align: middle;}
    .saldo-box { padding: 15px; border-radius: 10px; background-color: #f8fafc; text-align: center; border: 2px solid #1e3a8a; margin-bottom:15px; }
    .entrata { color: #10b981; font-weight: bold; }
    .uscita { color: #ef4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNZIONI DATABASE CON AUTO-RIPARAZIONE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        
        # FIX AUTOMATICO COLONNE (Per smartphone)
        cur.execute("PRAGMA table_info(pazienti)")
        esistenti = [col[1] for col in cur.fetchall()]
        nuove = {
            "data_nascita": "TEXT", "data_ingresso": "TEXT", "diagnosi": "TEXT",
            "allergie": "TEXT", "dieta": "TEXT", "giorno_lavatrice": "TEXT"
        }
        for col, tipo in nuove.items():
            if col not in esistenti:
                cur.execute(f"ALTER TABLE pazienti ADD COLUMN {col} {tipo}")
        
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
    with st.form("login"):
        pwd = st.text_input("Codice Accesso", type="password")
        if st.form_submit_button("ENTRA"):
            if pwd in ["rems2026", "admin2026"]:
                st.session_state.auth = True
                st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Equipe", "Gestione"])

# --- 5. GESTIONE (Aggiunta/Modifica/Elimina) ---
if menu == "Gestione":
    st.header("⚙️ Amministrazione Pazienti")
    t1, t2 = st.tabs(["➕ Nuovo Paziente", "📝 Modifica/Elimina"])
    
    with t1:
        with st.form("add_p"):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nome e Cognome")
            dn = c2.date_input("Data di Nascita", value=date(1980,1,1))
            di = c1.date_input("Data Ingresso", value=date.today())
            gl = c2.selectbox("Giorno Lavatrice", GIORNI)
            dia = st.text_area("Diagnosi")
            all = st.text_area("Allergie")
            diet = st.text_input("Dieta")
            if st.form_submit_button("REGISTRA PAZIENTE"):
                db_run("INSERT INTO pazienti (nome, data_nascita, data_ingresso, diagnosi, allergie, dieta, giorno_lavatrice) VALUES (?,?,?,?,?,?,?)",
                       (n, dn.strftime("%d/%m/%Y"), di.strftime("%d/%m/%Y"), dia, all, diet, gl), True)
                st.success("Registrato!"); st.rerun()
    
    with t2:
        paz_list = db_run("SELECT id, nome, diagnosi, allergie, dieta, giorno_lavatrice FROM pazienti ORDER BY nome")
        if paz_list:
            scelta = st.selectbox("Paziente da modificare", [p[1] for p in paz_list])
            p_sel = [p for p in paz_list if p[1] == scelta][0]
            with st.form(f"mod_{p_sel[0]}"):
                m_nome = st.text_input("Nome", p_sel[1])
                m_diag = st.text_area("Diagnosi", p_sel[2] if p_sel[2] else "")
                m_all = st.text_area("Allergie", p_sel[3] if p_sel[3] else "")
                m_diet = st.text_input("Dieta", p_sel[4] if p_sel[4] else "")
                m_gl = st.selectbox("Giorno Lavatrice", GIORNI, index=GIORNI.index(p_sel[5]) if p_sel[5] in GIORNI else 0)
                col1, col2 = st.columns(2)
                if col1.form_submit_button("✅ AGGIORNA"):
                    db_run("UPDATE pazienti SET nome=?, diagnosi=?, allergie=?, dieta=?, giorno_lavatrice=? WHERE id=?", (m_nome, m_diag, m_all, m_diet, m_gl, p_sel[0]), True); st.rerun()
                if col2.form_submit_button("🗑️ ELIMINA"):
                    db_run("DELETE FROM pazienti WHERE id=?", (p_sel[0],), True); st.rerun()

# --- 6. EQUIPE ---
elif menu == "Equipe":
    figura = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    paz_data = db_run("SELECT id, nome, data_nascita, data_ingresso, diagnosi, allergie, dieta, giorno_lavatrice FROM pazienti ORDER BY nome")
    
    if paz_data:
        sel_p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in paz_data])
        p_sel = [x for x in paz_data if x[1] == sel_p_nome][0]
        p_id = p_sel[0]

        # INTESTAZIONE CLINICA
        st.markdown(f"""
        <div class="patient-header">
            <h3>{p_sel[1].upper()}</h3>
            <p>Nato il: <b>{p_sel[2]}</b> | Ingresso: <b>{p_sel[3]}</b> | Lavatrice: <b>{p_sel[7]}</b></p>
            <p><i>Diagnosi: {p_sel[4]}</i></p>
            <div style="margin-top:10px;">
                <span class="allergy-alert">⚠️ Allergie: {p_sel[5]}</span> &nbsp;
                <span class="diet-box">🍽️ Dieta: {p_sel[6]}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if figura == "Psichiatra":
            st.subheader("📋 Gestione Terapie")
            with st.form("p_f"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                med = st.text_input("Firma Medico")
                if st.form_submit_button("PRESCRIVI"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, medico, data_prescr) VALUES (?,?,?,?,?)", 
                           (p_id, f, d, med, date.today().strftime("%d/%m/%Y")), True); st.rerun()

        elif figura == "Educatore":
            st.subheader("💰 Gestione Contabilità")
            storico = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            saldo = sum([s[2] if s[3] == "Entrata" else -s[2] for s in storico])
            st.markdown(f'<div class="saldo-box"><h2>Saldo Attuale: € {saldo:.2f}</h2></div>', unsafe_allow_html=True)
            with st.expander("Nuovo Movimento"):
                tipo = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
                imp = st.number_input("Cifra €", min_value=0.0)
                cau = st.text_input("Causale")
                f_ed = st.text_input("Firma Operatore")
                if st.button("SALVA MOVIMENTO"):
                    db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", 
                           (p_id, date.today().strftime("%d/%m/%Y"), cau, imp, tipo, f_ed), True); st.rerun()

        elif figura == "Infermiere" or figura == "OSS":
            with st.form("diario_n"):
                n_t = st.text_area("Nota Diario / Diario OSS")
                f_t = st.text_input("Firma")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO eventi (id, data, umore, nota, ruolo, op) VALUES (?,?,?,?,?,?)", 
                           (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", n_t, figura, f_t), True); st.rerun()

# --- 7. MONITORAGGIO ---
elif menu == "Monitoraggio":
    paz_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in paz_list:
        with st.expander(f"👤 {nome.upper()}"):
            note = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if note:
                h = "<table class='custom-table'><tr><th>DATA</th><th>RUOLO</th><th>OPERATORE</th><th>NOTA</th></tr>"
                for d, ru, op, nt in note:
                    h += f"<tr><td>{d}</td><td>{ru}</td><td>{op}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)
            else:
                st.info("Nessuna nota presente.")
